{{ config(materialized='table') }}

-- Gold: receita agregada por dia.
select
    toDate(pickup_at)                    as trip_date,
    count()                              as total_trips,
    round(sum(total_amount), 2)          as total_revenue_usd,
    round(sum(tip_amount), 2)            as total_tips_usd,
    round(avg(trip_distance_miles), 3)   as avg_distance_miles,
    round(avg(duration_minutes), 2)      as avg_duration_min,
    round(quantile(0.5)(total_amount), 2) as median_fare_usd
from {{ ref('yellow_tripdata_clean') }}
group by trip_date
order by trip_date
