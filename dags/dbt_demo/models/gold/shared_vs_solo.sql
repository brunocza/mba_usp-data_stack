{{ config(materialized='table') }}

-- Compara economia de viagens compartilhadas (shared) vs solo:
-- - share rate: requested vs effectively matched
-- - desconto médio na shared (assumindo que o passageiro paga menos)
-- - economia agregada
select
    if(shared_matched, 'shared_matched',
        if(shared_requested, 'shared_unmatched', 'solo'))   as ride_type,
    count()                                                  as trips,
    round(avg(total_amount), 2)                              as avg_total_usd,
    round(avg(trip_miles), 2)                                as avg_miles,
    round(avg(trip_minutes), 2)                              as avg_minutes,
    round(avg(driver_pay), 2)                                as avg_driver_pay_usd,
    round(sum(total_amount), 2)                              as total_revenue_usd
from {{ ref('fhvhv_trips_clean') }}
group by ride_type
