"""HVFHV (Uber/Lyft) medallion pipeline — bronze nativo + dbt via Cosmos.

Cosmos transforma cada model dbt em uma task Airflow nativa, com lineage no
graph view, retries por model e tests como tasks separadas. Bem mais
visibilidade do que um único `BashOperator(dbt run)`.

Pipeline:
    create_schemas
        → ingest_bronze_trips, ingest_bronze_zones   (PythonOperator)
            → dbt_transform                          (Cosmos DbtTaskGroup)
                → optimize_tables                    (PythonOperator)

Cosmos descobre automaticamente:
    silver.fhvhv_trips_clean        (run + test)
    silver.fhvhv_trips_enriched     (run, sem test)
    gold.daily_revenue              (run + test)
    gold.hourly_demand              (run + test)
    gold.borough_pairs              (run + test)
    gold.driver_economics           (run + test)
    gold.shared_vs_solo             (run + test)
e cria as dependências baseado em ref()/source().
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from airflow.models.dag import DAG
from airflow.providers.standard.operators.python import PythonOperator

from cosmos import (
    DbtTaskGroup,
    ExecutionConfig,
    ProfileConfig,
    ProjectConfig,
    RenderConfig,
)
from cosmos.constants import LoadMode

# -----------------------------------------------------------------------------
# Paths
# -----------------------------------------------------------------------------
DBT_PROJECT_PATH = Path("/opt/airflow/dags/repo/dags/dbt_demo")
DBT_PROFILES_PATH = DBT_PROJECT_PATH / "profiles.yml"
DBT_EXECUTABLE = "/home/airflow/.local/bin/dbt"


# -----------------------------------------------------------------------------
# Cosmos config
# -----------------------------------------------------------------------------
profile_config = ProfileConfig(
    profile_name="dbt_demo",
    target_name="dev",
    profiles_yml_filepath=DBT_PROFILES_PATH,
)

execution_config = ExecutionConfig(
    dbt_executable_path=DBT_EXECUTABLE,
)

# DBT_LS_FILE is the most reliable load mode without committing manifest.json:
# Cosmos runs `dbt ls` ONCE at parse time and caches the result. We let it
# auto-detect models from the project (which now only has silver/ and gold/).
render_config = RenderConfig(
    load_method=LoadMode.DBT_LS,
    select=["tag:silver", "tag:gold"],
)


# -----------------------------------------------------------------------------
# Helpers — ClickHouse client used by the non-dbt tasks
# -----------------------------------------------------------------------------
def _client():
    import os

    import clickhouse_connect

    return clickhouse_connect.get_client(
        host=os.environ["CLICKHOUSE_HOST"],
        port=int(os.environ["CLICKHOUSE_PORT"]),
        username=os.environ["CLICKHOUSE_USER"],
        password=os.environ["CLICKHOUSE_PASSWORD"],
    )


def create_schemas():
    c = _client()
    for schema in ("bronze", "silver", "gold"):
        c.command(f"CREATE DATABASE IF NOT EXISTS {schema}")
        print(f"  ok: {schema}")


def ingest_bronze_trips():
    """Ingest 12 monthly parquets into bronze.fhvhv_trips, one month at a time.

    Doing all 12 files in a single CTAS via the s3() glob blew the 7.2 GiB
    memory limit on ClickHouse (DB::Exception 241). Looping per-month keeps
    each batch under ~600 MB and lets the inserts checkpoint to disk.
    """
    import os

    c = _client()
    endpoint = os.environ["MINIO_ENDPOINT"].rstrip("/")
    ak = os.environ["MINIO_ACCESS_KEY"]
    sk = os.environ["MINIO_SECRET_KEY"]

    c.command("DROP TABLE IF EXISTS bronze.fhvhv_trips")

    # Build the empty table from the schema of the first parquet so column
    # types match exactly what s3() returns. CREATE ... EMPTY AS SELECT skips
    # the data scan but keeps the inferred schema.
    first_url = f"{endpoint}/landing/fhvhv-2023/fhvhv_tripdata_2023-01.parquet"
    c.command(
        f"""
        CREATE TABLE bronze.fhvhv_trips
        ENGINE = MergeTree()
        ORDER BY tuple()
        SETTINGS allow_nullable_key = 1
        EMPTY AS SELECT * FROM s3('{first_url}', '{ak}', '{sk}', 'Parquet')
        """
    )

    total_rows = 0
    for month in range(1, 13):
        url = f"{endpoint}/landing/fhvhv-2023/fhvhv_tripdata_2023-{month:02d}.parquet"
        c.command(
            f"""
            INSERT INTO bronze.fhvhv_trips
            SELECT * FROM s3('{url}', '{ak}', '{sk}', 'Parquet')
            SETTINGS max_threads = 2,
                     max_insert_threads = 2,
                     max_insert_block_size = 524288,
                     min_insert_block_size_rows = 524288,
                     input_format_parquet_max_block_size = 65536
            """
        )
        rows = c.query(
            "SELECT count() FROM bronze.fhvhv_trips"
        ).result_rows[0][0]
        added = rows - total_rows
        total_rows = rows
        print(f"  2023-{month:02d}: +{added:,} rows (total {rows:,})")

    size = c.query(
        """
        SELECT formatReadableSize(sum(bytes_on_disk))
        FROM system.parts
        WHERE database='bronze' AND table='fhvhv_trips' AND active
        """
    ).result_rows[0][0]
    print(f"  bronze.fhvhv_trips final: {total_rows:,} rows, {size}")


def ingest_bronze_zones():
    """Load taxi_zone_lookup.csv into bronze.taxi_zones."""
    import os

    c = _client()
    endpoint = os.environ["MINIO_ENDPOINT"].rstrip("/")
    ak = os.environ["MINIO_ACCESS_KEY"]
    sk = os.environ["MINIO_SECRET_KEY"]
    s3_url = f"{endpoint}/landing/fhvhv-2023/taxi_zone_lookup.csv"

    c.command("DROP TABLE IF EXISTS bronze.taxi_zones")
    c.command(
        f"""
        CREATE TABLE bronze.taxi_zones
        (
            LocationID  UInt16,
            Borough     String,
            Zone        String,
            service_zone String
        )
        ENGINE = MergeTree()
        ORDER BY LocationID
        AS SELECT LocationID, Borough, Zone, service_zone FROM s3(
            '{s3_url}',
            '{ak}', '{sk}',
            'CSVWithNames'
        )
        """
    )
    rows = c.query("SELECT count() FROM bronze.taxi_zones").result_rows[0][0]
    print(f"  bronze.taxi_zones: {rows} rows")


def optimize_tables():
    """OPTIMIZE FINAL em todas as tabelas materializadas pra reciclar disco."""
    c = _client()
    targets = [
        ("bronze", "fhvhv_trips"),
        ("silver", "fhvhv_trips_clean"),
        ("gold",   "daily_revenue"),
        ("gold",   "hourly_demand"),
        ("gold",   "borough_pairs"),
        ("gold",   "driver_economics"),
        ("gold",   "shared_vs_solo"),
    ]
    for db, tbl in targets:
        try:
            c.command(
                f"ALTER TABLE {db}.{tbl} MODIFY SETTING old_parts_lifetime = 10"
            )
        except Exception as e:
            print(f"  skip MODIFY SETTING on {db}.{tbl}: {e}")
        try:
            c.command(f"OPTIMIZE TABLE {db}.{tbl} FINAL")
            active = c.query(
                f"""
                SELECT formatReadableSize(sum(bytes_on_disk)), sum(rows)
                FROM system.parts
                WHERE database='{db}' AND table='{tbl}' AND active
                """
            ).result_rows[0]
            print(f"  {db}.{tbl}: {active[0]}, {active[1]:,} rows")
        except Exception as e:
            print(f"  skip OPTIMIZE on {db}.{tbl}: {e}")


# -----------------------------------------------------------------------------
# DAG
# -----------------------------------------------------------------------------
with DAG(
    dag_id="fhvhv_pipeline",
    description="NYC HVFHV (Uber/Lyft) medallion — Cosmos-native dbt DAG",
    start_date=datetime(2024, 1, 1),
    schedule="@hourly",
    catchup=False,
    max_active_runs=1,
    max_active_tasks=4,
    tags=["fhvhv", "uber-lyft", "medallion", "cosmos", "dbt", "clickhouse"],
) as dag:

    t_schemas = PythonOperator(
        task_id="create_schemas",
        python_callable=create_schemas,
    )

    t_trips = PythonOperator(
        task_id="ingest_bronze_trips",
        python_callable=ingest_bronze_trips,
        execution_timeout=None,
    )

    t_zones = PythonOperator(
        task_id="ingest_bronze_zones",
        python_callable=ingest_bronze_zones,
    )

    dbt_transform = DbtTaskGroup(
        group_id="dbt_transform",
        project_config=ProjectConfig(DBT_PROJECT_PATH),
        profile_config=profile_config,
        execution_config=execution_config,
        render_config=render_config,
    )

    t_optimize = PythonOperator(
        task_id="optimize_tables",
        python_callable=optimize_tables,
        trigger_rule="all_done",
    )

    t_schemas >> [t_trips, t_zones] >> dbt_transform >> t_optimize
