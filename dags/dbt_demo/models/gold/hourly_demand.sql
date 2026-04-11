{{ config(materialized='table', order_by='(weekday, hour_of_day)') }}

-- Demanda por hora-do-dia × dia-da-semana — clássico heatmap de transporte urbano.
select
    toDayOfWeek(pickup_at)                  as weekday,        -- 1=Mon..7=Sun
    toHour(pickup_at)                       as hour_of_day,    -- 0..23
    count()                                 as trips,
    round(avg(trip_minutes), 2)             as avg_trip_min,
    round(avg(waiting_minutes), 2)          as avg_wait_min,
    round(avg(total_amount), 2)             as avg_fare_usd,
    round(avg(driver_pay), 2)               as avg_driver_pay_usd
from {{ ref('fhvhv_trips_clean') }}
group by weekday, hour_of_day
