{{ config(
    materialized='table',
    order_by='(pickup_borough, dropoff_borough)',
    settings={'allow_nullable_key': 1}
) }}

-- Top OD pairs por volume entre boroughs (Manhattan→Manhattan etc.).
-- Usa a view enriquecida que já tem os nomes dos bairros resolvidos.
select
    pickup_borough,
    dropoff_borough,
    count()                              as trips,
    round(sum(total_amount), 2)          as revenue_usd,
    round(avg(trip_miles), 2)            as avg_miles,
    round(avg(trip_minutes), 2)          as avg_minutes,
    round(avg(total_amount), 2)          as avg_fare_usd
from {{ ref('fhvhv_trips_enriched') }}
where pickup_borough is not null
  and dropoff_borough is not null
group by pickup_borough, dropoff_borough
