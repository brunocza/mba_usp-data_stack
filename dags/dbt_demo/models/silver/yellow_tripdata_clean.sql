{{ config(materialized='table') }}

-- Silver layer: types + filtered + derived columns.
-- Remove trips with invalid fares, impossible distances, or pickup outside of
-- the target month. Also compute duration in minutes from pickup/dropoff.
with raw as (
    select * from {{ source('bronze_nyc_taxi', 'yellow_tripdata_raw') }}
)
select
    toUInt32(VendorID)                                               as vendor_id,
    tpep_pickup_datetime                                             as pickup_at,
    tpep_dropoff_datetime                                            as dropoff_at,
    toUInt8OrZero(toString(passenger_count))                         as passenger_count,
    toFloat32(trip_distance)                                         as trip_distance_miles,
    toUInt16(PULocationID)                                           as pickup_location_id,
    toUInt16(DOLocationID)                                           as dropoff_location_id,
    toUInt8OrZero(toString(payment_type))                            as payment_type,
    toFloat32(fare_amount)                                           as fare_amount,
    toFloat32(tip_amount)                                            as tip_amount,
    toFloat32(total_amount)                                          as total_amount,
    dateDiff('minute', tpep_pickup_datetime, tpep_dropoff_datetime)  as duration_minutes
from raw
where tpep_pickup_datetime >= toDateTime('2024-01-01')
  and tpep_pickup_datetime <  toDateTime('2024-02-01')
  and fare_amount  > 0
  and total_amount > 0
  and trip_distance between 0 and 200
