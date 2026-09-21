"""Validate the v4 response. National/public filtering remains visible in SQL."""

import json
import logging
from datetime import date

from src.config import PipelineError
from src.http import get_json

LOGGER = logging.getLogger(__name__)


def parse_holidays(payload: list, country: str, year: int) -> list[dict]:
    if not isinstance(payload, list) or not payload:
        raise PipelineError(f"Empty or invalid holiday response for {country}/{year}")
    rows = []
    try:
        for item in payload:
            day = date.fromisoformat(item["date"])
            if item["countryCode"] != country or day.year != year:
                raise ValueError("country/year does not match request")
            if type(item["nationalHoliday"]) is not bool:
                raise ValueError("nationalHoliday must be boolean")
            types = item["holidayTypes"]
            if not isinstance(types, list) or not all(isinstance(t, str) for t in types):
                raise ValueError("holidayTypes must be a list of strings")
            if not isinstance(item["name"], str) or not item["name"].strip():
                raise ValueError("missing English holiday name")
            subdivisions = item.get("subdivisionCodes")
            if subdivisions is not None and (
                not isinstance(subdivisions, list)
                or not all(isinstance(s, str) for s in subdivisions)
            ):
                raise ValueError("invalid subdivisionCodes")
            rows.append(
                {
                    "country_code": country,
                    "date": item["date"],
                    "name": item["name"],
                    "national_holiday": item["nationalHoliday"],
                    "holiday_types": types,
                    "subdivision_codes": json.dumps(subdivisions),
                    "source_year": year,
                }
            )
    except (KeyError, ValueError, TypeError) as exc:
        raise PipelineError(f"Invalid holidays for {country}/{year}: {exc}") from exc
    return rows


def fetch_holidays(config: dict, fetch=get_json) -> list[dict]:
    api = config["sources"]["holidays"]
    rows = []
    for country in sorted({m["country_code"] for m in config["markets"]}):
        url = f"{api['base_url']}/{country}/{api['holiday_year']}"
        LOGGER.info("Fetching holidays for %s (%s)", country, api["holiday_year"])
        country_rows = parse_holidays(fetch(url), country, api["holiday_year"])
        for row in country_rows:
            row["source_url"] = url
        rows.extend(country_rows)
    return rows
