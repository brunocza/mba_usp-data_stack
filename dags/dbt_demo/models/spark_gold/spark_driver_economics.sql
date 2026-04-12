{{ config(materialized='table', file_format='parquet') }}

SELECT
    DATE_TRUNC('month', pickup_at)                                      AS month,
    COUNT(*)                                                            AS total_trips,
    ROUND(AVG(base_fare), 2)                                            AS avg_base_fare,
    ROUND(AVG(tips), 2)                                                 AS avg_tips,
    ROUND(AVG(driver_pay), 2)                                           AS avg_driver_pay,
    ROUND(AVG(driver_pct_of_fare), 2)                                   AS avg_driver_pct_of_fare,
    ROUND(SUM(driver_pay), 2)                                           AS total_driver_pay,
    ROUND(SUM(driver_pay) / NULLIF(SUM(trip_minutes) / 60.0, 0), 2)    AS approx_hourly_rate_usd
FROM {{ ref('spark_fhvhv_trips_clean') }}
GROUP BY month
