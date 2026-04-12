{{ config(materialized='table', file_format='parquet') }}

SELECT
    CAST(pickup_at AS DATE)                        AS trip_date,
    COUNT(*)                                       AS total_trips,
    ROUND(SUM(total_amount), 2)                    AS gross_revenue_usd,
    ROUND(SUM(driver_pay), 2)                      AS total_driver_pay_usd,
    ROUND(SUM(tips), 2)                            AS total_tips_usd,
    ROUND(SUM(congestion_surcharge), 2)            AS total_congestion_usd,
    ROUND(AVG(trip_miles), 2)                      AS avg_trip_miles,
    ROUND(AVG(trip_minutes), 2)                    AS avg_trip_minutes,
    ROUND(AVG(waiting_minutes), 2)                 AS avg_waiting_minutes,
    ROUND(PERCENTILE_APPROX(total_amount, 0.5), 2)  AS median_fare_usd,
    ROUND(PERCENTILE_APPROX(total_amount, 0.95), 2) AS p95_fare_usd
FROM {{ ref('spark_fhvhv_trips_clean') }}
GROUP BY trip_date
