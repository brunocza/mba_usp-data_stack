{{ config(
    materialized='table',
    file_format='parquet',
    on_table_exists='drop'
) }}

SELECT * FROM parquet.`s3a://landing/fhvhv-2023/`
