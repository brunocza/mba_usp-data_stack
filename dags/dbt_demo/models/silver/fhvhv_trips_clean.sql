{{ config(
    materialized='table',
    order_by='pickup_at',
    settings={'allow_nullable_key': 1}
) }}

-- Silver: tipos forçados, filtros de qualidade, métricas derivadas.
-- Colunas slim: removidas as strings repetidas (license_num, base_num) que
-- inflam o tamanho da tabela; nenhum modelo gold depende delas.
with raw as (
    select * from {{ source('bronze', 'fhvhv_trips') }}
)
select
    pickup_datetime                                           as pickup_at,
    dropoff_datetime                                          as dropoff_at,
    toUInt16OrNull(toString(PULocationID))                    as pickup_location_id,
    toUInt16OrNull(toString(DOLocationID))                    as dropoff_location_id,
    toFloat32(trip_miles)                                     as trip_miles,
    toFloat32(base_passenger_fare)                            as base_fare,
    toFloat32(tips)                                           as tips,
    toFloat32(congestion_surcharge)                           as congestion_surcharge,
    toFloat32(driver_pay)                                     as driver_pay,
    shared_request_flag = 'Y'                                 as shared_requested,
    shared_match_flag   = 'Y'                                 as shared_matched,
    access_a_ride_flag  = 'Y'                                 as access_a_ride,
    wav_request_flag    = 'Y'                                 as wav_requested,

    -- métricas derivadas
    toUInt16(dateDiff('minute', request_datetime, pickup_datetime))   as waiting_minutes,
    toUInt16(dateDiff('minute', pickup_datetime, dropoff_datetime))   as trip_minutes,
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
