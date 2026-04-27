# dbt_databricks — espelho Databricks da medalhão FHVHV

Projeto dbt paralelo a [`dags/dbt_demo/`](../dags/dbt_demo/), traduzido pra dialeto Spark SQL e direcionado a um SQL Warehouse Serverless do Databricks. Existe **exclusivamente pro benchmark comparativo do TCC** (ClickHouse vs Databricks); não é orquestrado pelo Airflow.

## Escopo

- 1 mês de dados: `fhvhv_tripdata_2023-01.parquet` (18.479.031 linhas)
- 6 modelos: 2 bronze (views), 2 silver (1 table, 1 view), 2 gold (tables)
- Foco: alvos de Q1 (`daily_revenue`) e Q2 (`borough_pairs`) do `benchmark_medallion`

## Pré-requisitos

- `uv` instalado (rodamos via `uvx`, sem mexer no Python do host)
- 1 parquet HVFHV jan/2023 + `taxi_zones.csv` no Unity Catalog Volume `workspace.default.raw/`
- PAT Databricks com permissão de SQL Warehouse + Unity Catalog

## Variáveis de ambiente

```bash
export DATABRICKS_HOST="dbc-<id>.cloud.databricks.com"
export DATABRICKS_HTTP_PATH="/sql/1.0/warehouses/<warehouse-id>"
export DATABRICKS_TOKEN="dapi..."
export DATABRICKS_WAREHOUSE_ID="<warehouse-id>"   # só pro benchmark.py
export DBT_PROFILES_DIR=$(pwd)
```

## Reproduzir

```bash
cd dbt_databricks/

# 1. Validar conexão
uvx --with dbt-databricks --from dbt-core dbt debug

# 2. Buildar bronze→silver→gold
uvx --with dbt-databricks --from dbt-core dbt build
# tempo esperado: ~70s no Serverless 2X-Small

# 3. Rodar Q1/Q2 com 2 warm-ups + 5 medições por camada
uvx --with requests --from requests python3 benchmark_q1q2.py
# saída: ../tcc/evidencias/databricks_benchmark.json
```

## Diferenças vs `dags/dbt_demo/` (ClickHouse)

| Conceito | ClickHouse | Databricks |
|---|---|---|
| Fonte bronze | tabelas materializadas pelo Airflow (ingest task) | views dbt sobre `read_files()` no Volume |
| Catálogo | `default` (sem catálogo) | `workspace` (Unity Catalog) |
| Engine table | MergeTree + `order_by` | Delta + `cluster_by` (não usado nesse projeto) |
| Casts | `toFloat32`, `toUInt16OrNull` | `cast(x AS FLOAT)`, `cast(x AS SMALLINT)` |
| Time diff | `dateDiff('minute', a, b)` | `timestampdiff(MINUTE, a, b)` |
| Quantile | `quantile(0.5)(col)` | `percentile_approx(col, 0.5)` |
| `count()` | OK | exige `count(*)` |
| `if(c,a,b)` | OK | OK (Spark suporta) |
| Settings (ex `allow_nullable_key`) | aplicáveis | removidos |

A semântica de cada modelo é idêntica — mesmo conjunto de filtros, mesmas colunas derivadas, mesmas agregações.

## Resultados do benchmark (jan/2023)

Ver `tcc/evidencias/databricks_benchmark.json` para JSON completo. Resumo:

| Query | Bronze | Silver | Gold | Speedup gold/bronze |
|---|---|---|---|---|
| Q1 daily_revenue | 6041 ms | 1165 ms | 1179 ms | 5.1× |
| Q2 borough_pairs | 7741 ms | 3325 ms | 1089 ms | 7.1× |

CV% < 17% em todas as células. **Floor de latência ~1s** no Serverless 2X-Small explica por que Q1 silver e gold ficam empatados — o overhead de runtime distribuído domina queries muito leves.

Comparação com ClickHouse single-node (`benchmark_medallion`):
- CH: speedup gold/bronze ≈ 6266× (Q1) / 4237× (Q2)
- DBX: speedup gold/bronze ≈ 5× (Q1) / 7× (Q2)

A medalhão funciona em ambos engines, mas a magnitude do ganho depende fortemente da arquitetura: ClickHouse com MergeTree pré-agregado serve `gold` em microssegundos, enquanto Databricks Serverless tem teto imposto pelo runtime distribuído.
