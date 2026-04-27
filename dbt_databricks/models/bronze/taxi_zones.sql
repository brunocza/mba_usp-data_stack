{{ config(materialized='view') }}

-- Bronze: view sobre o CSV de zonas TLC no Volume.
-- 265 linhas, mapeamento LocationID → (Borough, Zone, service_zone).
select *
from read_files(
    '/Volumes/workspace/default/raw/taxi_zones.csv',
    format => 'csv',
    header => true
)
