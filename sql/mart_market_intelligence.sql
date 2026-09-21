CREATE OR REPLACE TABLE mart.market_intelligence AS
WITH calendar AS (
    SELECT h.country_code,
           MIN(h.holiday_date) AS next_public_holiday_date,
           ARG_MIN(h.holiday_name, h.holiday_date) AS next_public_holiday_name,
           CAST(COUNT(*) FILTER (
               WHERE h.holiday_date <= r.as_of_date + INTERVAL 30 DAY
           ) AS INTEGER) AS public_holidays_next_30d
    FROM staging.holidays h
    CROSS JOIN raw.run_context r
    WHERE h.holiday_date > r.as_of_date
    GROUP BY h.country_code
)
SELECT m.market_id, m.market_name, m.country_code, m.nuts3_code,
       p.population_total, d.population_density_per_km2,
       p.young_share_pct, p.working_age_share_pct, p.senior_share_pct,
       g.gdp_per_capita_pps,
       c.next_public_holiday_date, c.next_public_holiday_name,
       CAST(c.next_public_holiday_date - r.as_of_date AS INTEGER)
           AS days_until_next_public_holiday,
       COALESCE(c.public_holidays_next_30d, 0)::INTEGER AS public_holidays_next_30d,
       CASE WHEN p.reference_year = d.reference_year AND p.reference_year = g.reference_year
            THEN p.reference_year ELSE NULL END AS socioeconomic_reference_year,
       p.reference_year AS population_reference_year,
       d.reference_year AS density_reference_year,
       g.reference_year AS gdp_reference_year,
       r.holiday_reference_year, r.as_of_date, r.loaded_at_utc
FROM raw.markets m
CROSS JOIN raw.run_context r
LEFT JOIN staging.population p USING (nuts3_code)
LEFT JOIN staging.density d USING (nuts3_code)
LEFT JOIN staging.gdp g USING (nuts3_code)
LEFT JOIN calendar c USING (country_code)
ORDER BY m.market_id;
