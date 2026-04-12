{{ config(
    materialized='table',
    file_format='parquet',
    pre_hook='DROP TABLE IF EXISTS {{ this }}'
) }}

SELECT * FROM parquet.`s3a://landing/fhvhv-2023/`
