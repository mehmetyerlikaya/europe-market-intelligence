import duckdb
import pytest

from src.config import PipelineError, validate_config
from src.database import validate_mart
from src.pipeline import run


@pytest.mark.parametrize(
    "mutation",
    [
        "UPDATE mart.market_intelligence SET market_name=NULL",
        "UPDATE mart.market_intelligence SET country_code='XX'",
        "UPDATE mart.market_intelligence SET nuts3_code='DE999'",
        "UPDATE mart.market_intelligence SET population_total=0",
        "UPDATE mart.market_intelligence SET population_density_per_km2=-1",
        "UPDATE mart.market_intelligence SET gdp_per_capita_pps=NULL",
        "UPDATE mart.market_intelligence SET gdp_per_capita_pps='NaN'::DOUBLE",
        "UPDATE mart.market_intelligence SET young_share_pct=101",
        "UPDATE mart.market_intelligence SET young_share_pct=0",
        "UPDATE mart.market_intelligence SET gdp_reference_year=2024",
        "UPDATE mart.market_intelligence SET socioeconomic_reference_year=2024",
        "UPDATE mart.market_intelligence SET holiday_reference_year=2025",
        "UPDATE mart.market_intelligence SET next_public_holiday_date=as_of_date",
        "UPDATE mart.market_intelligence SET days_until_next_public_holiday=-1",
        "UPDATE mart.market_intelligence SET public_holidays_next_30d=-1",
        "DELETE FROM mart.market_intelligence WHERE market_id='DE_BERLIN'",
        "INSERT INTO mart.market_intelligence SELECT * FROM mart.market_intelligence LIMIT 1",
    ],
)
def test_corrupt_mart_is_rejected(config, fixture_fetch, mutation):
    run(config, fixture_fetch)
    with duckdb.connect(str(config["database"])) as con:
        con.execute(mutation)
        with pytest.raises(PipelineError):
            validate_mart(con, config)


@pytest.mark.parametrize(
    "field,value",
    [("country_code", "ZZ"), ("nuts3_code", "DE30"), ("market_name", ""), ("region_label", "")],
)
def test_invalid_market_config(config, field, value):
    config["markets"][0][field] = value
    with pytest.raises(PipelineError):
        validate_config(config)


def test_duplicate_market_configuration(config):
    config["markets"].append(config["markets"][0].copy())
    with pytest.raises(PipelineError, match="Duplicate"):
        validate_config(config)


def test_wrong_gdp_metric_cannot_be_substituted(config):
    config["sources"]["eurostat"]["datasets"]["gdp"]["unit"] = "PPS_HAB_EU27_2020"
    with pytest.raises(PipelineError, match="unit"):
        validate_config(config)
