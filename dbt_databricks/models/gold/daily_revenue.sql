{{ config(
    materialized='table',
    file_format='delta'
) }}

-- Gold Q1: receita e volume diários sobre fhvhv_trips_clean.
-- Tradução fiel de dbt_demo/models/gold/daily_revenue.sql.
select
    date(pickup_at)                                  as trip_date,
    count(*)                                         as total_trips,
    round(sum(total_amount), 2)                      as gross_revenue_usd,
    round(sum(driver_pay), 2)                        as total_driver_pay_usd,
    round(sum(tips), 2)                              as total_tips_usd,
    round(sum(congestion_surcharge), 2)              as total_congestion_usd,
    round(avg(trip_miles), 2)                        as avg_trip_miles,
    round(avg(trip_minutes), 2)                      as avg_trip_minutes,
    round(avg(waiting_minutes), 2)                   as avg_waiting_minutes,
    round(percentile_approx(total_amount, 0.5), 2)   as median_fare_usd,
    round(percentile_approx(total_amount, 0.95), 2)  as p95_fare_usd
from {{ ref('fhvhv_trips_clean') }}
group by date(pickup_at)
