{{ config(
    materialized='table',
    order_by='month',
    settings={'allow_nullable_key': 1}
) }}

-- Como os motoristas se saíram mês a mês:
--   tarifa média, gorjeta média, % do total que vai pro motorista,
--   ganho/hora estimado (baseado em trip_minutes — não inclui tempo idle).
select
    toStartOfMonth(pickup_at)                                       as month,
    count()                                                         as total_trips,
    round(avg(base_fare), 2)                                        as avg_base_fare,
    round(avg(tips), 2)                                             as avg_tips,
    round(avg(driver_pay), 2)                                       as avg_driver_pay,
    round(avg(driver_pct_of_fare), 2)                               as avg_driver_pct_of_fare,
    round(sum(driver_pay), 2)                                       as total_driver_pay,
    round(
        sum(driver_pay) / nullIf(sum(trip_minutes) / 60.0, 0),
        2
    )                                                                as approx_hourly_rate_usd
from {{ ref('fhvhv_trips_clean') }}
group by month
