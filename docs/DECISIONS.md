# Decisions

## 2026-09-21 — Explicit source years replace the planned common 2024 snapshot

The initial brief required 2024 population, density and GDP for all eight markets.
Live Eurostat responses contain no 2024 GDP observations for Berlin (`DE300`),
Hamburg (`DE600`), Munich (`DE212`) or Vienna (`AT130`). A category existing in
the response does not mean that an observation exists.

Moving everything to 2023 also does not work: the current Amsterdam geography
(`NL32B`) has a density observation only for 2024. Its older code (`NL329`) has
no observations in the current GDP dataset. Substituting those geographies
without proving boundary equivalence would weaken the data contract.

The checked-in configuration therefore explicitly selects **2024 population
and density, and 2023 GDP for every market**. This is a departure from the
original design, necessary for a complete live output using the specified sources
and current regions. It does not implement automatic year fallback.

Contract change:

- Add required integer `population_reference_year`, `density_reference_year`
  and `gdp_reference_year` columns.
- Make `socioeconomic_reference_year` nullable. Populate it only if all three
  actual source years agree. It is NULL in the demo.
- Validate each source against its configured year, rather than asserting 2024
  globally. Changing GDP to 2024 currently fails with the missing region codes.

Tradeoff: consumers must account for GDP being one year older than demographics.
Do not describe this sample as a uniform 2024 snapshot. Future data availability
can be handled by reviewing and changing the explicit configuration.

Evidence and geographic labels: [SOURCE_VERIFICATION.md](SOURCE_VERIFICATION.md).

## 2026-09-21 — Verified NUTS 3 regions are proxies for business markets

All eight configured codes and English API labels were checked against the
population, density and GDP response categories, and actual required observations
were checked separately. Amsterdam uses `NL32B` (Groot-Amsterdam), not the city
municipality and not the older `NL329` code. Munich uses the city region, not
the surrounding Landkreis. Country codes map national calendars to markets.

The pipeline checks labels and identifiers on every refresh. Even a label-only
change fails until reviewed. This is deliberately conservative for eight markets.

## 2026-09-21 — SQL transformations, local DuckDB storage

Python fetches, parses, validates source structure and loads normalized rows.
SQL casts, aggregates age groups, filters holidays and joins from `raw.markets`.
Left joins make missing source coverage visible rather than silently losing markets.
DuckDB keeps the batch project easy to inspect locally; this is not a claim that
it is the right storage system for a large mobility company.

Raw Eurostat rows retain `status`, `source_url`, `source_updated` and the UTC load
timestamp. Provisional/estimated observations are allowed and their source flags
are retained; presence and positive values are not a claim of final statistical status.

## 2026-09-21 — Transactional snapshot replacement

All inputs are fetched and checked first. Raw, staging and mart tables are then
rebuilt in one DuckDB transaction. Quality checks and temporary CSV creation happen
before commit, so failure at those steps leaves the prior snapshot intact.

The CSV is replaced atomically after the database commits. DuckDB and the filesystem
cannot share one transaction: if that final replacement fails, the database is newer
than the CSV, the command fails visibly, and rerunning regenerates the export.
Only one pipeline writer should run at a time. No historical snapshots are kept.

Idempotency means stable business rows for unchanged source responses and config;
`loaded_at_utc` changes. Eurostat revisions may change later live reruns even with
the same configuration. Offline fixtures provide fixed input reproducibility.

## 2026-09-21 — National calendar scope and boundaries

Nager.Holidays v4 was verified directly. SQL keeps `nationalHoliday == true` and
`holidayTypes` containing `Public`. Raw rows retain regional/non-public records so
the filter is inspectable. A failed or empty country response fails the refresh;
it is not interpreted as zero holidays.

The next holiday is strictly after `as_of_date`. The 30-day count uses
`as_of_date < holiday_date <= as_of_date + 30 days`. It counts distinct holiday
dates, joining different names on the same date in sorted order. This prevents
duplicate records or coincident observances from inflating a holiday-day feature.

Only the configured calendar year is fetched. A null next holiday means no later
national public holiday in that fetched year, not no future holiday indefinitely.
Dates whose 30-day window crosses the year boundary fail clearly. Cross-year
calendar ingestion is deferred. The demo date remains `2026-09-21`.

## 2026-09-21 — Offline CI and operating-system certificate trust

Fixtures are small real source slices. The default test suite blocks Python socket
connections and tests failure and rollback paths without external services.
Live API runs are a separate manual check.

`truststore` supplies the operating system's trusted certificates because the
development machine's standalone Python certificate chain could not validate the
public API connection. TLS verification stays enabled. No credentials are needed.

Python 3.13 was used locally; CI checks the supported 3.12 and 3.13 versions.
Direct Python commands work on Windows without requiring GNU Make.

## 2026-09-24 — Optional local Streamlit presentation

The owner explicitly requested a browser interface after reviewing the pipeline,
superseding the initial no-dashboard scope restriction. Streamlit is an optional
`app` dependency: ingestion, modelling and validation still live in the original
pipeline. The UI runs that CLI in a subprocess, streams its actual log and reads
DuckDB with short-lived connections. It never silently substitutes fixture data.

Saved snapshot checks call the existing mart validator. Failure is displayed and
CSV download is disabled for an invalid snapshot. The UI's export is generated
from the displayed database rows, so it cannot accidentally serve a stale CSV.
Source years and the fixed calendar date are visible. A failed refresh is separate
from the saved snapshot's validity and load time. A process-wide lock serializes
browser-triggered refreshes; DuckDB still governs access from separate CLI processes.

The service binds to localhost. A Windows launcher opens the browser independently
of Codex. Default CI installs the optional app extra and tests empty, successful,
failed-refresh, filtering and invalid-snapshot views using Streamlit AppTest.
