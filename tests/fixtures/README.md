# API fixtures

Captured from live public APIs on 2026-09-21 using the checked-in configuration.
These are real source slices, not fabricated market values.

- `demo_r_pjanaggr3.json`: eight configured regions, 2024, `NR`, `sex=T`, four age groups.
- `demo_r_d3dens.json`: eight configured regions, 2024, `PER_KM2`.
- `nama_10r_3gdp.json`: eight configured regions, 2023, `PPS_EU27_2020_HAB`.
- `holidays_{AT,BE,CZ,DE,FR,NL}.json`: complete country responses for 2026 from
  `https://nagerholidays.com/api/v4/Holidays/{CountryCode}/2026`.

Eurostat base URL:
`https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data`.
Eurostat fixtures retain dimensions, observations, flags and update timestamps;
the large ancillary `extension` metadata was omitted. Holiday responses retain
regional and non-public records so tests exercise the real filtering behavior.

Tests also construct small synthetic responses for malformed data, sparse/dense
JSON-stat, duplicate holiday dates and date-window boundaries. Those mutations are
test cases and are never used in the public sample CSV.

To refresh fixtures, capture and review the same configured queries, keeping all
eight regions and required age groups. Review source-year and geography changes
before replacing files or updating expected assertions. Tests never refresh data
or contact live services automatically.
