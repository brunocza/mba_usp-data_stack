{{ config(
    materialized='table',
    file_format='parquet'
) }}

SELECT
    pickup_datetime                                                    AS pickup_at,
    dropoff_datetime                                                   AS dropoff_at,
    CAST(PULocationID AS SMALLINT)                                     AS pickup_location_id,
    CAST(DOLocationID AS SMALLINT)                                     AS dropoff_location_id,
    CAST(trip_miles AS FLOAT)                                          AS trip_miles,
    CAST(base_passenger_fare AS FLOAT)                                 AS base_fare,
    CAST(tips AS FLOAT)                                                AS tips,
    CAST(congestion_surcharge AS FLOAT)                                AS congestion_surcharge,
    CAST(driver_pay AS FLOAT)                                          AS driver_pay,
    shared_request_flag = 'Y'                                          AS shared_requested,
    shared_match_flag = 'Y'                                            AS shared_matched,
    access_a_ride_flag = 'Y'                                           AS access_a_ride,
    wav_request_flag = 'Y'                                             AS wav_requested,

    CAST(TIMESTAMPDIFF(MINUTE, request_datetime, pickup_datetime) AS SMALLINT)  AS waiting_minutes,
    CAST(TIMESTAMPDIFF(MINUTE, pickup_datetime, dropoff_datetime) AS SMALLINT)  AS trip_minutes,
    CAST(base_passenger_fare + tolls + bcf + sales_tax
         + congestion_surcharge + airport_fee + tips AS FLOAT)         AS total_amount,
    CASE WHEN base_passenger_fare > 0
         THEN CAST(driver_pay / base_passenger_fare * 100 AS FLOAT)
         ELSE 0.0
    END                                                                AS driver_pct_of_fare
FROM {{ source('spark_bronze', 'fhvhv_trips_raw') }}
WHERE pickup_datetime >= TIMESTAMP '2023-01-01'
  AND pickup_datetime <  TIMESTAMP '2024-01-01'
  AND base_passenger_fare > 0
  AND trip_miles BETWEEN 0 AND 200
  AND trip_time BETWEEN 0 AND 21600
