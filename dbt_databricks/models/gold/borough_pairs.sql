{{ config(
    materialized='table',
    file_format='delta'
) }}

-- Gold Q2: top OD pairs por volume entre boroughs.
-- Tradução fiel de dbt_demo/models/gold/borough_pairs.sql.
select
    pickup_borough,
    dropoff_borough,
    count(*)                              as trips,
    round(sum(total_amount), 2)           as revenue_usd,
    round(avg(trip_miles), 2)             as avg_miles,
    round(avg(trip_minutes), 2)           as avg_minutes,
    round(avg(total_amount), 2)           as avg_fare_usd
from {{ ref('fhvhv_trips_enriched') }}
where pickup_borough is not null
  and dropoff_borough is not null
group by pickup_borough, dropoff_borough
