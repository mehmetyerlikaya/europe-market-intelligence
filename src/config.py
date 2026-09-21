"""Load and validate project-owned market identities and explicit source vintages."""

import re
from datetime import date, timedelta
from pathlib import Path

import yaml


class PipelineError(ValueError):
    """An actionable source, configuration, or data-contract failure."""


def load_config(path: str | Path) -> dict:
    path = Path(path).resolve()
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    sources_path = path.parent / config["sources"]
    config["sources"] = yaml.safe_load(sources_path.read_text(encoding="utf-8"))
    config["as_of_date"] = date.fromisoformat(str(config["as_of_date"]))
    for key in ("database", "export"):
        config[key] = (path.parent / config[key]).resolve()
    validate_config(config)
    return config


def validate_config(config: dict) -> None:
    markets = config["markets"]
    if not markets:
        raise PipelineError("At least one market must be configured")
    ids = [m["market_id"] for m in markets]
    if len(set(ids)) != len(ids):
        raise PipelineError("Duplicate market_id in configuration")
    for m in markets:
        if not all(
            isinstance(m[k], str) and m[k].strip()
            for k in ("market_id", "market_name", "country_code", "nuts3_code", "region_label")
        ):
            raise PipelineError("Market identifiers and labels must be nonempty strings")
        if not re.fullmatch(r"[A-Z]{2}", m["country_code"]):
            raise PipelineError(f"Invalid country code for {m['market_id']}")
        if not re.fullmatch(r"[A-Z]{2}[A-Z0-9]{3}", m["nuts3_code"]):
            raise PipelineError(f"Invalid NUTS 3 code for {m['market_id']}")
        # Eurostat uses EL for Greece, while the holiday API uses ISO GR.
        prefix = {"GR": "EL"}.get(m["country_code"], m["country_code"])
        if not m["nuts3_code"].startswith(prefix):
            raise PipelineError(f"Country/region mismatch for {m['market_id']}")
    expected_units = {"population": "NR", "density": "PER_KM2", "gdp": "PPS_EU27_2020_HAB"}
    for name, unit in expected_units.items():
        source = config["sources"]["eurostat"]["datasets"][name]
        if source["unit"] != unit:
            raise PipelineError(f"Unexpected {name} unit: {source['unit']}")
        if type(source["year"]) is not int or not 2000 <= source["year"] <= 2100:
            raise PipelineError(f"Invalid {name} reference year")
    year = config["sources"]["holidays"]["holiday_year"]
    as_of = config["as_of_date"]
    if as_of.year != year or (as_of + timedelta(days=30)).year != year:
        raise PipelineError("as_of_date and its full next-30-day window must be in holiday_year")
    if config["database"] == config["export"]:
        raise PipelineError("Database and CSV paths must differ")
