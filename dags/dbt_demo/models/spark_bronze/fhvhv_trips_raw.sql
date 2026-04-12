{{ config(
    materialized='table',
    file_format='parquet'
) }}

SELECT * FROM parquet.`s3a://landing/fhvhv-2023/`
