import copy

import pytest

from src.config import PipelineError
from src.eurostat import fetch_eurostat, parse_jsonstat


def small_payload():
    # Deliberately shuffled category-object order: numeric positions define the axes.
    return {
        "id": ["geo", "time"],
        "size": [2, 2],
        "dimension": {
            "geo": {"category": {"index": {"B": 1, "A": 0}}},
            "time": {"category": {"index": ["2023", "2024"]}},
        },
        "value": {"0": 10, "3": 40},
        "status": {"3": "p"},
    }


def test_sparse_jsonstat_uses_numeric_axes_and_preserves_flags():
    assert parse_jsonstat(small_payload()) == [
        {"geo": "A", "time": "2023", "value": 10, "status": None},
        {"geo": "B", "time": "2024", "value": 40, "status": "p"},
    ]


def test_dense_values_skip_null_but_preserve_zero():
    data = small_payload()
    data["value"] = [10, None, 0, 40]
    data["status"] = [None, None, None, "p"]
    rows = parse_jsonstat(data)
    assert len(rows) == 3
    assert rows[1] == {"geo": "B", "time": "2023", "value": 0, "status": None}


@pytest.mark.parametrize(
    "value", [{"4": 3}, {"-1": 2}, {"0": "bad"}, {"0": float("nan")}, {"0": True}, [1, 2]]
)
def test_invalid_observations_fail(value):
    data = small_payload()
    data["value"] = value
    with pytest.raises(PipelineError, match="JSON-stat"):
        parse_jsonstat(data)


def test_bad_category_positions_fail():
    data = small_payload()
    data["dimension"]["geo"]["category"]["index"] = {"A": 1, "B": 2}
    with pytest.raises(PipelineError, match="positions"):
        parse_jsonstat(data)


@pytest.mark.parametrize("name, count", [("population", 32), ("density", 8), ("gdp", 8)])
def test_real_fixtures_cover_every_market(config, fixture_fetch, name, count):
    rows = fetch_eurostat(config, name, fixture_fetch)
    assert len(rows) == count
    assert {r["geo"] for r in rows} == {m["nuts3_code"] for m in config["markets"]}


def test_metadata_membership_without_observation_is_not_coverage(config, fixture_fetch):
    def missing(url):
        data = fixture_fetch(url)
        data["value"].pop(next(iter(data["value"])))
        return data

    with pytest.raises(PipelineError, match="Missing gdp observations for 2023"):
        fetch_eurostat(config, "gdp", missing)


def test_region_label_change_requires_review(config, fixture_fetch):
    config["markets"][0]["region_label"] = "Different geography"
    with pytest.raises(PipelineError, match="region label/code changed"):
        fetch_eurostat(config, "gdp", fixture_fetch)


def test_unexpected_dimension_fails(config, fixture_fetch):
    def changed(url):
        data = fixture_fetch(url)
        data["id"].append("extra")
        data["size"].append(1)
        data["dimension"]["extra"] = {"category": {"index": {"X": 0}}}
        return data

    with pytest.raises(PipelineError, match="Unexpected gdp dimensions"):
        fetch_eurostat(config, "gdp", changed)


def test_unavailable_year_never_falls_back(config, fixture_fetch):
    old_config = copy.deepcopy(config)
    original = None

    def remember(url):
        nonlocal original
        original = fixture_fetch(url)
        return original

    fetch_eurostat(old_config, "gdp", remember)
    config["sources"]["eurostat"]["datasets"]["gdp"]["year"] = 2024
    calls = []

    def no_2024_data(url):
        calls.append(url)
        data = copy.deepcopy(original)
        data["value"] = {}
        data["dimension"]["time"]["category"] = {"index": {"2024": 0}}
        return data

    with pytest.raises(PipelineError, match="Missing gdp observations for 2024"):
        fetch_eurostat(config, "gdp", no_2024_data)
    assert len(calls) == 1 and "time=2024" in calls[0]
