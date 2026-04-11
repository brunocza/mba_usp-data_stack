{{ config(materialized='table') }}

select
    number                as id,
    toString(number)      as name,
    now()                 as loaded_at
from numbers(10)
