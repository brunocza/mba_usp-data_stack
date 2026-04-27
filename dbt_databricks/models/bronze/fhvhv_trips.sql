{{ config(materialized='view') }}

-- Bronze: view sobre o Parquet HVFHV no Unity Catalog Volume.
-- Equivalente ao bronze.fhvhv_trips no ClickHouse, mas sem materializar
-- (read_files lê o Parquet direto, mantendo paridade de fonte).
select *
from read_files(
    '/Volumes/workspace/default/raw/fhvhv_tripdata_2023-01.parquet',
    format => 'parquet'
)
