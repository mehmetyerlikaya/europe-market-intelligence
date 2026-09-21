from datetime import date

import duckdb
import pytest

from src.config import PipelineError, validate_config
from src.holidays import parse_holidays
from src.pipeline import run


def item(day, name="Test", national=True, types=None):
    return {
        "date": day,
        "name": name,
        "countryCode": "DE",
        "nationalHoliday": national,
        "holidayTypes": ["Public"] if types is None else types,
        "subdivisionCodes": None,
    }


@pytest.mark.parametrize(
    "field,value",
    [
        ("date", "2025-10-03"),
        ("date", "bad"),
        ("countryCode", "XX"),
        ("nationalHoliday", "true"),
        ("holidayTypes", "Public"),
        ("name", ""),
    ],
)
def test_malformed_response_fails(field, value):
    data = item("2026-10-03")
    data[field] = value
    with pytest.raises(PipelineError):
        parse_holidays([data], "DE", 2026)


def test_empty_calendar_fails():
    with pytest.raises(PipelineError, match="Empty"):
        parse_holidays([], "DE", 2026)


def test_calendar_boundaries_filtering_and_distinct_dates(config, fixture_fetch):
    def fetch(url):
        if "/Holidays/DE/" in url:
            return [
                item("2026-09-21", "Today"),
                item("2026-09-22", "First"),
                item("2026-09-22", "First"),
                item("2026-09-22", "Other name"),
                item("2026-09-23", "Regional", national=False),
                item("2026-09-24", "School", types=["School"]),
                item("2026-10-21", "Day 30"),
                item("2026-10-22", "Day 31"),
            ]
        return fixture_fetch(url)

    run(config, fetch)
    with duckdb.connect(str(config["database"])) as con:
        assert con.execute("""SELECT next_public_holiday_date, next_public_holiday_name,
            days_until_next_public_holiday, public_holidays_next_30d
            FROM mart.market_intelligence WHERE market_id = 'DE_BERLIN'""").fetchone() == (
            date(2026, 9, 22),
            "First / Other name",
            1,
            2,
        )


def test_no_future_holiday_is_null_not_fabricated(config, fixture_fetch):
    def fetch(url):
        return [item("2026-01-01")] if "/Holidays/DE/" in url else fixture_fetch(url)

    run(config, fetch)
    with duckdb.connect(str(config["database"])) as con:
        assert con.execute("""SELECT next_public_holiday_date, next_public_holiday_name,
            days_until_next_public_holiday, public_holidays_next_30d
            FROM mart.market_intelligence WHERE market_id = 'DE_BERLIN'""").fetchone() == (
            None,
            None,
            None,
            0,
        )


@pytest.mark.parametrize("as_of", [date(2026, 12, 2), date(2025, 9, 21)])
def test_incomplete_calendar_window_fails(config, as_of):
    config["as_of_date"] = as_of
    with pytest.raises(PipelineError, match="full next-30-day window"):
        validate_config(config)


def test_no_national_public_holidays_fails(config, fixture_fetch):
    def fetch(url):
        if "/Holidays/DE/" in url:
            return [item("2026-10-03", national=False)]
        return fixture_fetch(url)

    with pytest.raises(PipelineError, match="coverage"):
        run(config, fetch)
