CREATE OR REPLACE TABLE staging.density AS
SELECT geo AS nuts3_code, CAST(reference_year AS INTEGER) AS reference_year,
       CAST(value AS DOUBLE) AS population_density_per_km2
FROM raw.eurostat_density
WHERE freq = 'A' AND unit = 'PER_KM2';
