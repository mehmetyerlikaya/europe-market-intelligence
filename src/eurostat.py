"""Decode JSON-stat by dimension order, including sparse observations and flags."""

import logging
import math
from urllib.parse import urlencode

from src.config import PipelineError
from src.http import get_json

AGES = ("TOTAL", "Y_LT15", "Y15-64", "Y_GE65")
LOGGER = logging.getLogger(__name__)


def parse_jsonstat(payload: dict) -> list[dict]:
    try:
        ids, sizes = payload["id"], payload["size"]
        if len(ids) != len(sizes) or len(set(ids)) != len(ids):
            raise ValueError("invalid dimensions")
        categories = []
        for dim, size in zip(ids, sizes, strict=True):
            if type(size) is not int or size <= 0:
                raise ValueError("empty or invalid dimension")
            index = payload["dimension"][dim]["category"]["index"]
            if isinstance(index, dict):
                if sorted(index.values()) != list(range(size)):
                    raise ValueError(f"invalid category positions for {dim}")
                codes = sorted(index, key=index.get)
            else:
                codes = index
            if len(codes) != size or len(set(codes)) != size:
                raise ValueError(f"invalid category size for {dim}")
            categories.append(codes)
        values = payload["value"]
        if isinstance(values, list):
            if len(values) != math.prod(sizes):
                raise ValueError("dense value length does not match dimensions")
            entries = enumerate(values)
        elif isinstance(values, dict):
            entries = values.items()
        else:
            raise ValueError("value must be an object or array")
        rows = []
        seen = set()
        statuses = payload.get("status", {})
        for raw_position, value in entries:
            position = int(raw_position)
            if position in seen or not 0 <= position < math.prod(sizes):
                raise ValueError("invalid/duplicate observation position")
            seen.add(position)
            if value is None:
                continue
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError("observation is not numeric")
            if not math.isfinite(value):
                raise ValueError("observation is not finite")
            offset = position
            coordinates = []
            for size in reversed(sizes):
                coordinates.append(offset % size)
                offset //= size
            row = {
                dim: codes[i]
                for dim, codes, i in zip(ids, categories, reversed(coordinates), strict=True)
            }
            row["value"] = value
            row["status"] = (
                statuses[position] if isinstance(statuses, list) else statuses.get(str(position))
            )
            rows.append(row)
        return rows
    except (KeyError, TypeError, ValueError, IndexError) as exc:
        raise PipelineError(f"Invalid Eurostat JSON-stat: {exc}") from exc


def fetch_eurostat(config: dict, name: str, fetch=get_json) -> list[dict]:
    api = config["sources"]["eurostat"]
    source = api["datasets"][name]
    markets = config["markets"]
    geos = sorted({m["nuts3_code"] for m in markets})
    params = [
        ("lang", "EN"),
        ("freq", "A"),
        ("unit", source["unit"]),
        ("time", str(source["year"])),
    ]
    if name == "population":
        params += [("sex", "T")] + [("age", age) for age in AGES]
    params += [("geo", geo) for geo in geos]
    url = f"{api['base_url']}/{source['code']}?{urlencode(params)}"
    LOGGER.info("Fetching %s (%s)", name, source["year"])
    payload = fetch(url)
    rows = parse_jsonstat(payload)
    dimensions = {"freq", "unit", "geo", "time"}
    if name == "population":
        dimensions |= {"sex", "age"}
    if set(payload["id"]) != dimensions:
        raise PipelineError(f"Unexpected {name} dimensions: {payload['id']}")
    labels = payload["dimension"]["geo"]["category"].get("label", {})
    for market in markets:
        if labels.get(market["nuts3_code"]) != market["region_label"]:
            raise PipelineError(f"{market['market_id']}: {name} region label/code changed")
    expected = {(g, a) for g in geos for a in (AGES if name == "population" else (None,))}
    observed = set()
    for row in rows:
        key = (row["geo"], row.get("age"))
        if key in observed or key not in expected:
            raise PipelineError(f"Unexpected or duplicate {name} record: {key}")
        observed.add(key)
        if (
            row["freq"] != "A"
            or row["unit"] != source["unit"]
            or row["time"] != str(source["year"])
            or (name == "population" and row["sex"] != "T")
        ):
            raise PipelineError(f"Wrong source filters returned for {name}: {key}")
        if row["value"] < 0 or (name != "population" and row["value"] == 0):
            raise PipelineError(f"Invalid {name} value: {key}")
        if name == "population" and row["value"] != int(row["value"]):
            raise PipelineError(f"Fractional population: {key}")
        row.update(
            source_url=url, source_updated=payload.get("updated"), region_label=labels[row["geo"]]
        )
    missing = expected - observed
    if missing:
        raise PipelineError(f"Missing {name} observations for {source['year']}: {sorted(missing)}")
    return rows
