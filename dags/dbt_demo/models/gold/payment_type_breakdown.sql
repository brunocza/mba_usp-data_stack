{{ config(materialized='table') }}

-- Gold: distribuição de receita e volume por forma de pagamento.
-- Mapeia o enum numérico do TLC para strings legíveis.
select
    multiIf(
        payment_type = 1, 'credit_card',
        payment_type = 2, 'cash',
        payment_type = 3, 'no_charge',
        payment_type = 4, 'dispute',
        payment_type = 5, 'unknown',
        payment_type = 6, 'voided',
        'other'
    )                                   as payment_method,
    count()                             as trips,
    round(sum(total_amount), 2)         as revenue_usd,
    round(sum(tip_amount), 2)           as tips_usd,
    round(avg(total_amount), 2)         as avg_ticket_usd,
    round(
        sum(tip_amount) / nullIf(sum(fare_amount), 0) * 100,
        2
    )                                   as tip_pct_of_fare
from {{ ref('yellow_tripdata_clean') }}
group by payment_method
order by revenue_usd desc
