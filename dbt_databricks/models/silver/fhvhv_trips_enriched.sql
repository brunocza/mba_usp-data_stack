{{ config(materialized='view') }}

-- Silver enriched: junta com bronze.taxi_zones pra resolver os IDs PU/DO
-- em (borough, zone). Output usado pelo gold.borough_pairs.
with trips as (
    select * from {{ ref('fhvhv_trips_clean') }}
)
select
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

    pu.Borough   as pickup_borough,
    pu.Zone      as pickup_zone,
    do_z.Borough as dropoff_borough,
    do_z.Zone    as dropoff_zone
from trips t
left join {{ ref('taxi_zones') }} pu
       on cast(pu.LocationID as smallint) = t.pickup_location_id
left join {{ ref('taxi_zones') }} do_z
       on cast(do_z.LocationID as smallint) = t.dropoff_location_id
