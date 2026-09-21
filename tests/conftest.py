import json
import socket
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

from src.config import load_config

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("Network access is forbidden in the default test suite")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket.socket, "connect_ex", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)


@pytest.fixture
def config(tmp_path):
    config = load_config(Path(__file__).resolve().parents[1] / "config/project.yml")
    config["database"] = tmp_path / "test.duckdb"
    config["export"] = tmp_path / "test.csv"
    return config


@pytest.fixture
def fixture_fetch():
    def fetch(url):
        parts = urlsplit(url).path.split("/")
        if "Holidays" in parts:
            assert parts[-1] == "2026"
            name = "holidays_" + parts[-2]
        else:
            name = parts[-1]
        payload = json.loads((FIXTURES / (name + ".json")).read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            query = parse_qs(urlsplit(url).query)
            for dimension in ("time", "unit", "geo", "freq"):
                assert set(query[dimension]) == set(
                    payload["dimension"][dimension]["category"]["index"]
                )
        return payload

    return fetch
