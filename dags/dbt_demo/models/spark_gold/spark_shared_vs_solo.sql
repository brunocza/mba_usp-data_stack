{{ config(materialized='table', file_format='parquet') }}

SELECT
    CASE
        WHEN shared_matched THEN 'shared_matched'
        WHEN shared_requested THEN 'shared_unmatched'
        ELSE 'solo'
    END                                              AS ride_type,
    COUNT(*)                                         AS trips,
    ROUND(AVG(total_amount), 2)                      AS avg_total_usd,
    ROUND(AVG(trip_miles), 2)                        AS avg_miles,
    ROUND(AVG(trip_minutes), 2)                      AS avg_minutes,
    ROUND(AVG(driver_pay), 2)                        AS avg_driver_pay_usd,
    ROUND(SUM(total_amount), 2)                      AS total_revenue_usd
FROM {{ ref('spark_fhvhv_trips_clean') }}
GROUP BY ride_type
