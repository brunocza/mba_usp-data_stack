{{ config(
    materialized='table',
    file_format='parquet'
) }}

SELECT * FROM csv.`s3a://landing/fhvhv-2023/taxi_zone_lookup.csv`
