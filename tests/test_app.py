from pathlib import Path

import duckdb
import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest

from src import presentation
from src.pipeline import run

APP = Path(__file__).resolve().parents[1] / "streamlit_app.py"


def app(config, monkeypatch):
    monkeypatch.setattr(presentation, "project_config", lambda: config)
    return AppTest.from_file(str(APP), default_timeout=30)


def test_empty_install_explains_first_run(config, monkeypatch):
    page = app(config, monkeypatch).run()
    assert not page.exception
    assert "No saved snapshot" in page.info[0].value


def test_saved_results_and_market_filter(config, fixture_fetch, monkeypatch):
    run(config, fixture_fetch)
    page = app(config, monkeypatch).run()
    assert not page.exception
    assert page.metric[0].value == "8"
    page.multiselect[0].set_value(["Berlin"]).run()
    assert not page.exception
    assert page.selectbox[0].value == "Berlin"
    assert page.dataframe[1].value["market_name"].tolist() == ["Berlin"]


def test_refresh_creates_snapshot(config, fixture_fetch, monkeypatch):
    def refresh(on_line):
        on_line("Fetching test fixtures")
        run(config, fixture_fetch)
        return 0

    monkeypatch.setattr(presentation, "refresh", refresh)
    page = app(config, monkeypatch).run()
    page.button[0].click().run()
    assert not page.exception
    assert page.metric[0].value == "8"
    assert page.session_state["run_ok"] is True


def test_failed_refresh_keeps_saved_results_visible(config, fixture_fetch, monkeypatch):
    run(config, fixture_fetch)
    monkeypatch.setattr(presentation, "refresh", lambda on_line: 1)
    page = app(config, monkeypatch).run()
    page.button[0].click().run()
    assert not page.exception
    assert page.metric[0].value == "8"
    assert "latest refresh failed" in page.warning[0].value


def test_invalid_snapshot_is_not_presented_as_passing(config, fixture_fetch, monkeypatch):
    run(config, fixture_fetch)
    with duckdb.connect(str(config["database"])) as con:
        con.execute("UPDATE mart.market_intelligence SET population_total=0")
    page = app(config, monkeypatch).run()
    assert not page.exception
    assert page.metric[3].value == "Failed"
    assert "validation failed" in page.error[0].value
