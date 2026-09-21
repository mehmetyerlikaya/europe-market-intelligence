# Implemented data contract

Table: `mart.market_intelligence`. Grain: one row per configured market, keyed by
`market_id`. The demo has eight rows. Types below are DuckDB types.

| Column | Type | Nullable | Meaning |
|---|---|---|---|
| market_id | VARCHAR | No | Stable project-owned market key |
| market_name | VARCHAR | No | Display name |
| country_code | VARCHAR | No | ISO alpha-2 country for national holidays |
| nuts3_code | VARCHAR | No | Verified regional statistical proxy |
| population_total | BIGINT | No | Population on 1 January, selected population year |
| population_density_per_km2 | DOUBLE | No | Persons per square kilometre, selected density year |
| young_share_pct | DOUBLE | No | Under 15 population divided by TOTAL × 100 |
| working_age_share_pct | DOUBLE | No | Age 15–64 divided by TOTAL × 100 |
| senior_share_pct | DOUBLE | No | Age 65+ divided by TOTAL × 100 |
| gdp_per_capita_pps | DOUBLE | No | GDP per inhabitant in PPS, selected GDP year |
| next_public_holiday_date | DATE | Yes | First national public holiday strictly after as_of_date within fetched year |
| next_public_holiday_name | VARCHAR | Yes | English name(s), ordered if coincident |
| days_until_next_public_holiday | INTEGER | Yes | Calendar-day difference; NULL with no next holiday |
| public_holidays_next_30d | INTEGER | No | Distinct national public-holiday dates in (as_of_date, as_of_date + 30 days] |
| socioeconomic_reference_year | INTEGER | Yes | Common year only when all three socioeconomic years agree |
| population_reference_year | INTEGER | No | Population/age year; demo 2024 |
| density_reference_year | INTEGER | No | Density year; demo 2024 |
| gdp_reference_year | INTEGER | No | GDP year; demo 2023 |
| holiday_reference_year | INTEGER | No | Fetched holiday year; demo 2026 |
| as_of_date | DATE | No | Fixed calendar-feature anchor; demo 2026-09-21 |
| loaded_at_utc | TIMESTAMP | No | UTC refresh timestamp, stored without timezone suffix |

Nullability and uniqueness are enforced by pre-commit validation, rather than
DDL constraints on the SQL-generated mart. Do not edit published tables manually.
CSV empty cells represent NULL; the blank common-year column is intentional.

Required checks: complete configured coverage, unique market keys, non-null
required fields, exact configured names/codes/years, positive finite population,
density and GDP, age shares in [0,100] summing to [99,101], and consistent holiday
dates and counts. Source validation also checks required observations, dimensions,
units, region labels and national calendar coverage. See [DECISIONS.md](DECISIONS.md)
for the justified change from the initial common-2024 contract.
