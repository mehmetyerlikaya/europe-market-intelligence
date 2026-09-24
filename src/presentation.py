"""Read short-lived database snapshots and invoke the existing pipeline for the UI."""

import subprocess
import sys
from pathlib import Path

import duckdb

from src.config import PipelineError, load_config
from src.database import validate_mart

ROOT = Path(__file__).resolve().parent.parent


def read_snapshot(config: dict) -> dict | None:
    if not config["database"].exists():
        return None
    with duckdb.connect(str(config["database"]), read_only=True) as con:
        exists = con.execute("""SELECT count(*) FROM information_schema.tables
            WHERE table_schema='mart' AND table_name='market_intelligence'""").fetchone()[0]
        if not exists:
            return None
        quality_error = None
        try:
            validate_mart(con, config)
        except PipelineError as exc:
            quality_error = str(exc)
        markets = con.execute(
            "SELECT * FROM mart.market_intelligence ORDER BY market_name"
        ).fetchdf()
        layers = []
        for source in ("population", "density", "gdp", "holidays"):
            raw = "holidays" if source == "holidays" else f"eurostat_{source}"
            layers.append(
                {
                    "Source": source.title(),
                    "Raw records": con.execute(f"SELECT count(*) FROM raw.{raw}").fetchone()[0],
                    "Staging records": con.execute(
                        f"SELECT count(*) FROM staging.{source}"
                    ).fetchone()[0],
                }
            )
        provenance = []
        for source in ("population", "density", "gdp"):
            result = con.execute(f"""SELECT DISTINCT reference_year, unit, source_url,
                source_updated FROM raw.eurostat_{source}""").fetchall()
            for year, unit, url, updated in result:
                provenance.append(
                    {
                        "Source": source.title(),
                        "Year": year,
                        "Unit": unit,
                        "URL": url,
                        "Source updated": updated,
                    }
                )
        return {
            "markets": markets,
            "layers": layers,
            "provenance": provenance,
            "quality_error": quality_error,
        }


def refresh(on_line) -> int:
    """Stream real CLI output; never run a separate set of business transformations."""
    with subprocess.Popen(
        [sys.executable, "-X", "utf8", "-m", "src.pipeline", "--config", "config/project.yml"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
    ) as process:
        for line in process.stdout:
            on_line(line.rstrip())
        return process.wait()


def project_config() -> dict:
    return load_config(ROOT / "config/project.yml")
