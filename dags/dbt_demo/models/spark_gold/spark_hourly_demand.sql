{{ config(materialized='table', file_format='parquet') }}

SELECT
    DAYOFWEEK(pickup_at)                           AS weekday,
    HOUR(pickup_at)                                AS hour_of_day,
    COUNT(*)                                       AS trips,
    ROUND(AVG(trip_minutes), 2)                    AS avg_trip_min,
    ROUND(AVG(waiting_minutes), 2)                 AS avg_wait_min,
    ROUND(AVG(total_amount), 2)                    AS avg_fare_usd,
    ROUND(AVG(driver_pay), 2)                      AS avg_driver_pay_usd
FROM {{ ref('spark_fhvhv_trips_clean') }}
GROUP BY weekday, hour_of_day
