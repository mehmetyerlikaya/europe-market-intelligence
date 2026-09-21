CREATE OR REPLACE TABLE staging.population AS
WITH population AS (
    SELECT geo AS nuts3_code, CAST(reference_year AS INTEGER) AS reference_year,
           MAX(CASE WHEN age = 'TOTAL' THEN CAST(value AS BIGINT) END) AS population_total,
           MAX(CASE WHEN age = 'Y_LT15' THEN CAST(value AS BIGINT) END) AS young,
           MAX(CASE WHEN age = 'Y15-64' THEN CAST(value AS BIGINT) END) AS working_age,
           MAX(CASE WHEN age = 'Y_GE65' THEN CAST(value AS BIGINT) END) AS senior
    FROM raw.eurostat_population
    WHERE freq = 'A' AND unit = 'NR' AND sex = 'T'
    GROUP BY geo, reference_year
)
SELECT nuts3_code, reference_year, population_total,
       100.0 * young / NULLIF(population_total, 0) AS young_share_pct,
       100.0 * working_age / NULLIF(population_total, 0) AS working_age_share_pct,
       100.0 * senior / NULLIF(population_total, 0) AS senior_share_pct
FROM population;
