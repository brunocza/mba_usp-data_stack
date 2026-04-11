"""HVFHV (Uber/Lyft) medallion pipeline.

12 monthly parquet files (~5.5 GiB compactado, ~25 GiB descompactado em
MergeTree) com 24 colunas — request/on-scene/pickup/dropoff timestamps,
fares decompostos, driver_pay, flags de shared ride e acessibilidade.

Bronze   →  ingest 1:1 do MinIO (s3 glob) + dimensão taxi_zones
Silver   →  trips tipados, filtrados, enriquecidos com nomes de borough
Gold     →  agregações (daily revenue, hourly demand, borough pairs,
             driver economics, shared vs solo)

Credenciais via envFrom no secret orchestrator2/clickhouse-credentials.
ClickHouse puxa direto do MinIO via s3() — Airflow worker não toca os bytes.
"""
from __future__ import annotations

from datetime import datetime

from airflow.models.dag import DAG
from airflow.providers.standard.operators.bash import BashOperator
from airflow.providers.standard.operators.python import PythonOperator

DBT_SRC = "/opt/airflow/dags/repo/dags/dbt_demo"
DBT_WORK = "/tmp/dbt_fhvhv"
COPY_PROJECT = f"rm -rf {DBT_WORK} && cp -r {DBT_SRC} {DBT_WORK} && cd {DBT_WORK}"


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
        print(f"ok: {schema}")


def ingest_bronze_trips():
    """Read all 12 monthly parquets via s3 glob and load into bronze.fhvhv_trips."""
    import os

    c = _client()
    endpoint = os.environ["MINIO_ENDPOINT"].rstrip("/")
    ak = os.environ["MINIO_ACCESS_KEY"]
    sk = os.environ["MINIO_SECRET_KEY"]
    s3_url = f"{endpoint}/landing/fhvhv-2023/fhvhv_tripdata_2023-*.parquet"

    c.command("DROP TABLE IF EXISTS bronze.fhvhv_trips")
    c.command(
        f"""
        CREATE TABLE bronze.fhvhv_trips
        ENGINE = MergeTree()
        ORDER BY tuple()
        SETTINGS allow_nullable_key = 1
        AS SELECT * FROM s3(
            '{s3_url}',
            '{ak}', '{sk}',
            'Parquet'
        )
        """
    )
    rows = c.query("SELECT count() FROM bronze.fhvhv_trips").result_rows[0][0]
    size = c.query(
        """
        SELECT formatReadableSize(sum(bytes_on_disk))
        FROM system.parts
        WHERE database='bronze' AND table='fhvhv_trips' AND active
        """
    ).result_rows[0][0]
    print(f"bronze.fhvhv_trips: {rows:,} rows, {size} on disk")


def optimize_tables():
    """Force merge of inactive parts to reclaim disk after the dbt run.

    The CTAS (`dbt run`) leaves inactive parts behind that ClickHouse only
    GCs after `old_parts_lifetime` (default 480s). Forcing OPTIMIZE FINAL
    immediately merges + drops them, freeing disk before the next run.
    """
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
        # Drop the part-lifetime to 10s so the next merge cycle GC's the
        # backup parts left behind by dbt's CTAS swap.
        try:
            c.command(
                f"ALTER TABLE {db}.{tbl} MODIFY SETTING old_parts_lifetime = 10"
            )
        except Exception as e:
            print(f"  skip MODIFY SETTING on {db}.{tbl}: {e}")
        c.command(f"OPTIMIZE TABLE {db}.{tbl} FINAL")
        active = c.query(
            f"""
            SELECT formatReadableSize(sum(bytes_on_disk)), sum(rows)
            FROM system.parts
            WHERE database='{db}' AND table='{tbl}' AND active
            """
        ).result_rows[0]
        print(f"  {db}.{tbl}: {active[0]}, {active[1]:,} rows")


def ingest_bronze_zones():
    """Load taxi_zone_lookup.csv (~265 rows) into bronze.taxi_zones."""
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
    print(f"bronze.taxi_zones: {rows} rows")


with DAG(
    dag_id="fhvhv_pipeline",
    description="NYC HVFHV (Uber/Lyft) medallion pipeline — bronze/silver/gold",
    start_date=datetime(2024, 1, 1),
    schedule=None,
    catchup=False,
    max_active_tasks=4,
    tags=["fhvhv", "uber-lyft", "medallion", "dbt", "clickhouse"],
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

    t_silver = BashOperator(
        task_id="dbt_silver",
        bash_command=(
            f"{COPY_PROJECT} && DBT_PROFILES_DIR={DBT_WORK} "
            f"dbt run --select tag:silver --no-version-check"
        ),
    )

    t_gold = BashOperator(
        task_id="dbt_gold",
        bash_command=(
            f"{COPY_PROJECT} && DBT_PROFILES_DIR={DBT_WORK} "
            f"dbt run --select tag:gold --no-version-check"
        ),
    )

    t_test = BashOperator(
        task_id="dbt_test",
        bash_command=(
            f"{COPY_PROJECT} && DBT_PROFILES_DIR={DBT_WORK} "
            f"dbt test --select tag:silver tag:gold --no-version-check"
        ),
    )

    t_optimize = PythonOperator(
        task_id="optimize_tables",
        python_callable=optimize_tables,
        trigger_rule="all_done",  # roda mesmo se algum upstream falhar
    )

    t_schemas >> [t_trips, t_zones] >> t_silver >> t_gold >> t_test >> t_optimize
