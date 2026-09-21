import csv

import duckdb
import pytest

from src import pipeline
from src.config import PipelineError


def business_rows(config):
    with duckdb.connect(str(config["database"]), read_only=True) as con:
        return con.execute("""SELECT * EXCLUDE (loaded_at_utc)
            FROM mart.market_intelligence ORDER BY market_id""").fetchall()


def test_full_offline_pipeline_and_idempotency(config, fixture_fetch):
    assert pipeline.run(config, fixture_fetch) == 8
    before = business_rows(config)
    assert pipeline.run(config, fixture_fetch) == 8
    assert business_rows(config) == before
    with config["export"].open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == len({r["market_id"] for r in rows}) == 8
    berlin = next(r for r in rows if r["market_id"] == "DE_BERLIN")
    assert berlin["population_total"] == "3662381"
    assert berlin["gdp_per_capita_pps"] == "48700.0"
    assert berlin["population_reference_year"] == "2024"
    assert berlin["gdp_reference_year"] == "2023"
    assert berlin["socioeconomic_reference_year"] == ""
    with duckdb.connect(str(config["database"])) as con:
        assert con.execute("SELECT count(*) FROM raw.eurostat_population").fetchone()[0] == 32
        assert con.execute("SELECT count(*) FROM raw.eurostat_density").fetchone()[0] == 8
        assert con.execute("SELECT count(*) FROM raw.eurostat_gdp").fetchone()[0] == 8
        assert con.execute("SELECT status FROM raw.eurostat_density WHERE geo='NL32B'").fetchone()[
            0
        ]


def test_source_failure_preserves_database_and_csv(config, fixture_fetch):
    pipeline.run(config, fixture_fetch)
    before, csv_before = business_rows(config), config["export"].read_bytes()

    def broken(url):
        if "nama_10r_3gdp" in url:
            raise PipelineError("GDP service unavailable")
        return fixture_fetch(url)

    with pytest.raises(PipelineError, match="GDP service"):
        pipeline.run(config, broken)
    assert business_rows(config) == before
    assert config["export"].read_bytes() == csv_before


def test_quality_failure_rolls_back_raw_and_mart(config, fixture_fetch, monkeypatch):
    pipeline.run(config, fixture_fetch)
    before, csv_before = business_rows(config), config["export"].read_bytes()
    with duckdb.connect(str(config["database"])) as con:
        old_raw = con.execute("SELECT * FROM raw.eurostat_population ORDER BY geo, age").fetchall()
    original = pipeline.transform

    def broken(con):
        original(con)
        con.execute("UPDATE mart.market_intelligence SET population_total=0")

    monkeypatch.setattr(pipeline, "transform", broken)
    with pytest.raises(PipelineError, match="must be positive"):
        pipeline.run(config, fixture_fetch)
    assert business_rows(config) == before
    assert config["export"].read_bytes() == csv_before
    with duckdb.connect(str(config["database"])) as con:
        assert (
            con.execute("SELECT * FROM raw.eurostat_population ORDER BY geo, age").fetchall()
            == old_raw
        )


def test_csv_write_failure_rolls_back(config, fixture_fetch, monkeypatch):
    pipeline.run(config, fixture_fetch)
    before = business_rows(config)

    def fail(**kwargs):
        raise OSError("Disk full")

    monkeypatch.setattr(pipeline.tempfile, "NamedTemporaryFile", fail)
    with pytest.raises(OSError, match="Disk full"):
        pipeline.run(config, fixture_fetch)
    assert business_rows(config) == before
