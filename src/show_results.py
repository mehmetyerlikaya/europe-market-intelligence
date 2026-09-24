"""Display the local pipeline's saved layers and market output for the Windows launcher."""

import duckdb

from src.config import load_config


def main() -> None:
    config = load_config("config/project.yml")
    with duckdb.connect(str(config["database"]), read_only=True) as con:
        print("HOW THE DATA MOVES")
        print("Public APIs -> raw source rows -> SQL staging -> validated market table -> CSV")
        print()
        for name in ("population", "density", "gdp"):
            raw = con.execute(f"SELECT count(*) FROM raw.eurostat_{name}").fetchone()[0]
            staged = con.execute(f"SELECT count(*) FROM staging.{name}").fetchone()[0]
            print(f"  {name.title():12} {raw:3} source rows -> {staged:3} regional rows")
        raw = con.execute("SELECT count(*) FROM raw.holidays").fetchone()[0]
        staged = con.execute("SELECT count(*) FROM staging.holidays").fetchone()[0]
        print(f"  Holidays     {raw:3} source rows -> {staged:3} national public-holiday dates")
        print()
        print("SAVED MARKET RESULTS")
        print(
            con.sql("""
            SELECT market_name AS market, population_total AS population,
                   gdp_per_capita_pps AS gdp_pps_per_person,
                   next_public_holiday_date AS next_holiday
            FROM mart.market_intelligence ORDER BY market_name
        """)
        )
        context = con.execute("""
            SELECT population_reference_year, density_reference_year, gdp_reference_year,
                   as_of_date, loaded_at_utc
            FROM mart.market_intelligence LIMIT 1
        """).fetchone()
        print(
            f"Population year: {context[0]} | Density year: {context[1]} | GDP year: {context[2]}"
        )
        print(f"Holiday calculations as of: {context[3]} | Last loaded (UTC): {context[4]}")
        print(f"\nCSV:      {config['export']}")
        print(f"Database: {config['database']}")


if __name__ == "__main__":
    main()
