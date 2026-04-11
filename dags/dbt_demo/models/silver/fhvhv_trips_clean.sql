{{ config(materialized='table', order_by='pickup_at') }}

-- Silver: tipos forçados, filtros de qualidade, métricas derivadas.
-- Mantém todas as 24 colunas originais e adiciona:
--   waiting_minutes        — entre request e pickup (proxy de demanda)
--   on_scene_to_pickup_min — quanto tempo o motorista esperou
--   trip_minutes           — duração total da viagem
--   total_amount           — soma de fare + tolls + bcf + sales_tax + cs + airport + tips
--   net_to_driver_pct      — percentual do total que vai pro motorista
with raw as (
    select * from {{ source('bronze', 'fhvhv_trips') }}
)
select
    hvfhs_license_num,
    dispatching_base_num,
    originating_base_num,
    request_datetime                                          as request_at,
    on_scene_datetime                                         as on_scene_at,
    pickup_datetime                                           as pickup_at,
    dropoff_datetime                                          as dropoff_at,
    toUInt16OrNull(toString(PULocationID))                    as pickup_location_id,
    toUInt16OrNull(toString(DOLocationID))                    as dropoff_location_id,
    toFloat32(trip_miles)                                     as trip_miles,
    toFloat32(trip_time)                                      as trip_seconds,
    toFloat32(base_passenger_fare)                            as base_fare,
    toFloat32(tolls)                                          as tolls,
    toFloat32(bcf)                                            as black_car_fund,
    toFloat32(sales_tax)                                      as sales_tax,
    toFloat32(congestion_surcharge)                           as congestion_surcharge,
    toFloat32(airport_fee)                                    as airport_fee,
    toFloat32(tips)                                           as tips,
    toFloat32(driver_pay)                                     as driver_pay,
    shared_request_flag = 'Y'                                 as shared_requested,
    shared_match_flag   = 'Y'                                 as shared_matched,
    access_a_ride_flag  = 'Y'                                 as access_a_ride,
    wav_request_flag    = 'Y'                                 as wav_requested,
    wav_match_flag      = 'Y'                                 as wav_matched,

    -- métricas derivadas
    dateDiff('minute', request_datetime, pickup_datetime)     as waiting_minutes,
    dateDiff('minute', on_scene_datetime, pickup_datetime)    as on_scene_to_pickup_min,
    dateDiff('minute', pickup_datetime, dropoff_datetime)     as trip_minutes,
    toFloat32(base_passenger_fare + tolls + bcf + sales_tax
              + congestion_surcharge + airport_fee + tips)    as total_amount,
    if(base_passenger_fare > 0,
       toFloat32(driver_pay / base_passenger_fare * 100),
       toFloat32(0))                                          as driver_pct_of_fare
from raw
where pickup_datetime >= toDateTime('2023-01-01')
  and pickup_datetime <  toDateTime('2024-01-01')
  and base_passenger_fare > 0
  and trip_miles between 0 and 200
  and trip_time between 0 and 21600  -- max 6 horas
