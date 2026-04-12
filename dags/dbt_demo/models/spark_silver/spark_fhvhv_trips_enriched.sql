{{ config(materialized='view') }}

SELECT
    t.pickup_at,
    t.dropoff_at,
    t.waiting_minutes,
    t.trip_minutes,
    t.trip_miles,
    t.base_fare,
    t.tips,
    t.driver_pay,
    t.total_amount,
    t.driver_pct_of_fare,
    t.shared_requested,
    t.shared_matched,
    t.wav_requested,
    t.access_a_ride,

    pu.Borough  AS pickup_borough,
    pu.Zone     AS pickup_zone,
    do_z.Borough AS dropoff_borough,
    do_z.Zone   AS dropoff_zone
FROM {{ ref('spark_fhvhv_trips_clean') }} t
LEFT JOIN {{ source('spark_bronze', 'taxi_zones_raw') }} pu
       ON pu.LocationID = t.pickup_location_id
LEFT JOIN {{ source('spark_bronze', 'taxi_zones_raw') }} do_z
       ON do_z.LocationID = t.dropoff_location_id
