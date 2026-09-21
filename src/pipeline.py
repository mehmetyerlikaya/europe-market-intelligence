"""Run a complete snapshot; leave the previous database intact on a failed refresh."""

import argparse
import csv
import logging
import os
import tempfile
from pathlib import Path

import duckdb

from src.config import PipelineError, load_config, validate_config
from src.database import load_raw, transform, validate_mart
from src.eurostat import fetch_eurostat
from src.holidays import fetch_holidays
from src.http import get_json

LOGGER = logging.getLogger(__name__)


def run(config: dict, fetch=get_json) -> int:
    validate_config(config)
    # Fetch and validate all required inputs before touching an existing snapshot.
    data = {name: fetch_eurostat(config, name, fetch) for name in ("population", "density", "gdp")}
    data["holidays"] = fetch_holidays(config, fetch)
    database, export = Path(config["database"]), Path(config["export"])
    database.parent.mkdir(parents=True, exist_ok=True)
    export.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    con = duckdb.connect(str(database))
    try:
        con.execute("BEGIN TRANSACTION")
        load_raw(con, config, data)
        transform(con)
        validate_mart(con, config)
        result = con.execute("SELECT * FROM mart.market_intelligence ORDER BY market_id")
        columns = [d[0] for d in result.description]
        rows = result.fetchall()
        with tempfile.NamedTemporaryFile(
            mode="w", newline="", encoding="utf-8", dir=export.parent, suffix=".tmp", delete=False
        ) as handle:
            temporary = Path(handle.name)
            writer = csv.writer(handle)
            writer.writerow(columns)
            writer.writerows(rows)
        con.execute("COMMIT")
        # Each destination is atomic individually, not a cross-filesystem transaction.
        # The database is authoritative if this replacement fails; rerun to re-export.
        os.replace(temporary, export)
        LOGGER.info("Published %s markets to %s and %s", len(rows), database, export)
        return len(rows)
    except Exception:
        try:
            con.execute("ROLLBACK")
        except duckdb.TransactionException:
            LOGGER.error("Database committed but CSV publication failed; rerun to export")
        raise
    finally:
        con.close()
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config/project.yml")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    try:
        run(load_config(args.config))
    except (PipelineError, OSError, KeyError, TypeError, duckdb.Error) as exc:
        LOGGER.error("Pipeline failed: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
