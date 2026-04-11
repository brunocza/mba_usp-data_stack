{{ config(
    materialized='table',
    order_by='pickup_at',
    settings={'allow_nullable_key': 1}
) }}

-- Silver enriched: junta com bronze.taxi_zones pra resolver os IDs de PU/DO
-- em (borough, zone) tanto pro pickup quanto pro dropoff. Output usado pelos
-- modelos gold que precisam saber NOMES de bairro em vez de IDs numéricos.
with trips as (
    select * from {{ ref('fhvhv_trips_clean') }}
)
select
    t.pickup_at,
    t.dropoff_at,
    t.request_at,
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
    t.hvfhs_license_num,

    pu.Borough  as pickup_borough,
    pu.Zone     as pickup_zone,
    do_z.Borough as dropoff_borough,
    do_z.Zone   as dropoff_zone
from trips t
left join {{ source('bronze', 'taxi_zones') }} pu
       on pu.LocationID = t.pickup_location_id
left join {{ source('bronze', 'taxi_zones') }} do_z
       on do_z.LocationID = t.dropoff_location_id
