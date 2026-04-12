{{ config(materialized='table', file_format='parquet') }}

SELECT
    pickup_borough,
    dropoff_borough,
    COUNT(*)                              AS trips,
    ROUND(SUM(total_amount), 2)           AS revenue_usd,
    ROUND(AVG(trip_miles), 2)             AS avg_miles,
    ROUND(AVG(trip_minutes), 2)           AS avg_minutes,
    ROUND(AVG(total_amount), 2)           AS avg_fare_usd
FROM {{ ref('spark_fhvhv_trips_enriched') }}
WHERE pickup_borough IS NOT NULL
  AND dropoff_borough IS NOT NULL
GROUP BY pickup_borough, dropoff_borough
