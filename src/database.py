"""Load normalized source rows and validate the SQL-built snapshot before commit."""

from datetime import UTC, datetime
from pathlib import Path

import duckdb

from src.config import PipelineError

SQL_DIR = Path(__file__).resolve().parent.parent / "sql"


def load_raw(con: duckdb.DuckDBPyConnection, config: dict, data: dict) -> None:
    for schema in ("raw", "staging", "mart"):
        con.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
    loaded = datetime.now(UTC).replace(tzinfo=None)
    con.execute("""CREATE OR REPLACE TABLE raw.markets (
        market_id VARCHAR PRIMARY KEY, market_name VARCHAR NOT NULL,
        country_code VARCHAR NOT NULL, nuts3_code VARCHAR NOT NULL, region_label VARCHAR NOT NULL
    )""")
    con.executemany(
        "INSERT INTO raw.markets VALUES (?, ?, ?, ?, ?)",
        [
            [
                m[k]
                for k in ("market_id", "market_name", "country_code", "nuts3_code", "region_label")
            ]
            for m in config["markets"]
        ],
    )
    con.execute("""CREATE OR REPLACE TABLE raw.run_context (
        as_of_date DATE, holiday_reference_year INTEGER, loaded_at_utc TIMESTAMP
    )""")
    con.execute(
        "INSERT INTO raw.run_context VALUES (?, ?, ?)",
        [config["as_of_date"], config["sources"]["holidays"]["holiday_year"], loaded],
    )
    for name in ("population", "density", "gdp"):
        con.execute(f"""CREATE OR REPLACE TABLE raw.eurostat_{name} (
            freq VARCHAR, unit VARCHAR, geo VARCHAR, reference_year VARCHAR,
            sex VARCHAR, age VARCHAR, value VARCHAR, status VARCHAR,
            region_label VARCHAR, source_url VARCHAR, source_updated VARCHAR,
            loaded_at_utc TIMESTAMP
        )""")
        con.executemany(
            f"INSERT INTO raw.eurostat_{name} VALUES ({','.join(['?'] * 12)})",
            [
                [
                    r["freq"],
                    r["unit"],
                    r["geo"],
                    r["time"],
                    r.get("sex"),
                    r.get("age"),
                    str(r["value"]),
                    r["status"],
                    r["region_label"],
                    r["source_url"],
                    r["source_updated"],
                    loaded,
                ]
                for r in data[name]
            ],
        )
    con.execute("""CREATE OR REPLACE TABLE raw.holidays (
        country_code VARCHAR, holiday_date VARCHAR, name VARCHAR, national_holiday BOOLEAN,
        holiday_types VARCHAR[], subdivision_codes VARCHAR, source_year INTEGER,
        source_url VARCHAR, loaded_at_utc TIMESTAMP
    )""")
    con.executemany(
        "INSERT INTO raw.holidays VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            [
                r["country_code"],
                r["date"],
                r["name"],
                r["national_holiday"],
                r["holiday_types"],
                r["subdivision_codes"],
                r["source_year"],
                r["source_url"],
                loaded,
            ]
            for r in data["holidays"]
        ],
    )


def transform(con: duckdb.DuckDBPyConnection) -> None:
    for name in ("population", "density", "gdp", "holidays"):
        con.execute((SQL_DIR / f"staging_{name}.sql").read_text(encoding="utf-8"))
    con.execute((SQL_DIR / "mart_market_intelligence.sql").read_text(encoding="utf-8"))


def validate_mart(con: duckdb.DuckDBPyConnection, config: dict) -> None:
    result = con.execute("SELECT * FROM mart.market_intelligence ORDER BY market_id")
    columns = [d[0] for d in result.description]
    rows = [dict(zip(columns, row, strict=True)) for row in result.fetchall()]
    expected = {m["market_id"]: m for m in config["markets"]}
    if len(rows) != len(expected) or {r["market_id"] for r in rows} != set(expected):
        raise PipelineError("Mart market coverage or uniqueness check failed")
    nullable = {
        "next_public_holiday_date",
        "next_public_holiday_name",
        "days_until_next_public_holiday",
        "socioeconomic_reference_year",
    }
    years = config["sources"]["eurostat"]["datasets"]
    common_year = years["population"]["year"]
    if len({v["year"] for v in years.values()}) > 1:
        common_year = None
    for row in rows:
        errors = []
        market = expected[row["market_id"]]
        if any(row[c] is None for c in columns if c not in nullable):
            errors.append("required field is null")
        if any(row[k] != market[k] for k in ("market_name", "country_code", "nuts3_code")):
            errors.append("market mapping differs from configuration")
        for key in ("population_total", "population_density_per_km2", "gdp_per_capita_pps"):
            if row[key] is None or not 0 < row[key] < float("inf"):
                errors.append(f"{key} must be positive and finite")
        shares = [row[k] for k in ("young_share_pct", "working_age_share_pct", "senior_share_pct")]
        if any(v is None or not 0 <= v <= 100 for v in shares):
            errors.append("age shares outside 0–100")
        elif not 99 <= sum(shares) <= 101:
            errors.append("age shares do not sum to approximately 100")
        for name in ("population", "density", "gdp"):
            if row[f"{name}_reference_year"] != years[name]["year"]:
                errors.append(f"wrong {name} reference year")
        if row["socioeconomic_reference_year"] != common_year:
            errors.append("common socioeconomic year is misleading")
        if row["holiday_reference_year"] != config["sources"]["holidays"]["holiday_year"]:
            errors.append("wrong holiday year")
        if row["as_of_date"] != config["as_of_date"]:
            errors.append("wrong as_of_date")
        day = row["next_public_holiday_date"]
        if day is None:
            if any(
                row[k] is not None
                for k in ("next_public_holiday_name", "days_until_next_public_holiday")
            ):
                errors.append("inconsistent nullable holiday fields")
        elif (
            day <= config["as_of_date"]
            or day.year != row["holiday_reference_year"]
            or row["days_until_next_public_holiday"] != (day - config["as_of_date"]).days
            or not row["next_public_holiday_name"]
        ):
            errors.append("invalid next holiday")
        count = row["public_holidays_next_30d"]
        if count is None or not 0 <= count <= 30:
            errors.append("invalid holiday-day count")
        if errors:
            raise PipelineError(f"{row['market_id']}: {'; '.join(errors)}")
    # An empty filtered response must never masquerade as a zero-holiday calendar.
    covered = {
        r[0] for r in con.execute("SELECT DISTINCT country_code FROM staging.holidays").fetchall()
    }
    if covered != {m["country_code"] for m in config["markets"]}:
        raise PipelineError("National public-holiday country coverage check failed")
