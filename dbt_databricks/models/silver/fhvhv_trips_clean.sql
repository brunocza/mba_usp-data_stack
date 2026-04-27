{{ config(
    materialized='table',
    file_format='delta'
) }}

-- Silver: tipos forçados, filtros de qualidade, métricas derivadas.
-- Tradução fiel do dbt_demo/models/silver/fhvhv_trips_clean.sql (ClickHouse)
-- pra Spark SQL/Databricks. Mantém mesma semântica e mesma janela 2023.
with raw as (
    select * from {{ ref('fhvhv_trips') }}
)
select
    pickup_datetime                                           as pickup_at,
    dropoff_datetime                                          as dropoff_at,
    cast(PULocationID as smallint)                            as pickup_location_id,
    cast(DOLocationID as smallint)                            as dropoff_location_id,
    cast(trip_miles as float)                                 as trip_miles,
    cast(base_passenger_fare as float)                        as base_fare,
    cast(tips as float)                                       as tips,
    cast(congestion_surcharge as float)                       as congestion_surcharge,
    cast(driver_pay as float)                                 as driver_pay,
    shared_request_flag = 'Y'                                 as shared_requested,
    shared_match_flag   = 'Y'                                 as shared_matched,
    access_a_ride_flag  = 'Y'                                 as access_a_ride,
    wav_request_flag    = 'Y'                                 as wav_requested,

    -- métricas derivadas
    cast(timestampdiff(MINUTE, request_datetime, pickup_datetime) as smallint)   as waiting_minutes,
    cast(timestampdiff(MINUTE, pickup_datetime, dropoff_datetime) as smallint)   as trip_minutes,
    cast(base_passenger_fare + tolls + bcf + sales_tax
              + congestion_surcharge + airport_fee + tips as float)              as total_amount,
    if(base_passenger_fare > 0,
       cast(driver_pay / base_passenger_fare * 100 as float),
       cast(0 as float))                                                          as driver_pct_of_fare
from raw
where pickup_datetime >= timestamp '2023-01-01'
  and pickup_datetime <  timestamp '2024-01-01'
  and base_passenger_fare > 0
  and trip_miles between 0 and 200
  and trip_time between 0 and 21600  -- max 6 horas
