CREATE OR REPLACE TABLE staging.holidays AS
SELECT country_code, CAST(holiday_date AS DATE) AS holiday_date,
       STRING_AGG(DISTINCT name, ' / ' ORDER BY name) AS holiday_name
FROM raw.holidays
WHERE national_holiday AND list_contains(holiday_types, 'Public')
GROUP BY country_code, CAST(holiday_date AS DATE);
