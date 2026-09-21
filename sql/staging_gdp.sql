CREATE OR REPLACE TABLE staging.gdp AS
SELECT geo AS nuts3_code, CAST(reference_year AS INTEGER) AS reference_year,
       CAST(value AS DOUBLE) AS gdp_per_capita_pps
FROM raw.eurostat_gdp
WHERE freq = 'A' AND unit = 'PPS_EU27_2020_HAB';
