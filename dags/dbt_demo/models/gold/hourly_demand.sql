{{ config(materialized='table') }}

-- Gold: demanda por hora do dia (0-23), com duração média e ticket médio.
select
    toHour(pickup_at)                  as hour_of_day,
    count()                            as trips,
    round(avg(duration_minutes), 2)    as avg_duration_min,
    round(avg(total_amount), 2)        as avg_fare_usd,
    round(avg(trip_distance_miles), 3) as avg_distance_miles
from {{ ref('yellow_tripdata_clean') }}
group by hour_of_day
order by hour_of_day
