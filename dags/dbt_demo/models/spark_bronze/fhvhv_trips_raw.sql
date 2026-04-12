{{ config(
    materialized='view'
) }}

SELECT * FROM parquet.`s3a://landing/fhvhv-2023/`
