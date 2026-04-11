"""NYC Taxi medallion pipeline: MinIO (landing) → ClickHouse bronze → dbt silver/gold.

Ingestão usa a função nativa ``s3()`` do ClickHouse para ler o parquet direto
do MinIO sem passar os bytes pelo worker do Airflow. Credenciais do ClickHouse
e do MinIO vêm via envFrom do secret ``orchestrator2/clickhouse-credentials``.
"""
from __future__ import annotations

from datetime import datetime

from airflow.models.dag import DAG
from airflow.providers.standard.operators.bash import BashOperator
from airflow.providers.standard.operators.python import PythonOperator

DBT_SRC = "/opt/airflow/dags/repo/dags/dbt_demo"
DBT_WORK = "/tmp/dbt_nyc"
COPY_PROJECT = f"rm -rf {DBT_WORK} && cp -r {DBT_SRC} {DBT_WORK} && cd {DBT_WORK}"

OBJECT_KEY = "landing/nyc-taxi/yellow_tripdata_2024-01.parquet"


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
    for schema in ("bronze_nyc_taxi", "silver_nyc_taxi", "gold_nyc_taxi"):
        c.command(f"CREATE DATABASE IF NOT EXISTS {schema}")
        print(f"ok: schema {schema}")


def ingest_bronze():
    import os

    c = _client()
    endpoint = os.environ["MINIO_ENDPOINT"].rstrip("/")
    ak = os.environ["MINIO_ACCESS_KEY"]
    sk = os.environ["MINIO_SECRET_KEY"]
    s3_url = f"{endpoint}/{OBJECT_KEY}"

    c.command("DROP TABLE IF EXISTS bronze_nyc_taxi.yellow_tripdata_raw")
    c.command(
        f"""
        CREATE TABLE bronze_nyc_taxi.yellow_tripdata_raw
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
    rows = c.query(
        "SELECT count() FROM bronze_nyc_taxi.yellow_tripdata_raw"
    ).result_rows[0][0]
    size_bytes = c.query(
        """
        SELECT sum(bytes_on_disk)
        FROM system.parts
        WHERE database = 'bronze_nyc_taxi'
          AND table    = 'yellow_tripdata_raw'
          AND active
        """
    ).result_rows[0][0]
    print(f"bronze: {rows:,} linhas ingeridas, {size_bytes/1024/1024:.1f} MiB on disk")


with DAG(
    dag_id="nyc_taxi_pipeline",
    description="NYC Yellow Taxi — medallion pipeline (bronze → silver → gold)",
    start_date=datetime(2024, 1, 1),
    schedule=None,
    catchup=False,
    tags=["nyc-taxi", "medallion", "dbt", "clickhouse"],
) as dag:

    t_schemas = PythonOperator(
        task_id="create_schemas",
        python_callable=create_schemas,
    )

    t_bronze = PythonOperator(
        task_id="ingest_bronze",
        python_callable=ingest_bronze,
    )

    t_silver_gold = BashOperator(
        task_id="dbt_silver_gold",
        bash_command=(
            f"{COPY_PROJECT} && "
            f"DBT_PROFILES_DIR={DBT_WORK} "
            f"dbt run --select tag:silver tag:gold --no-version-check"
        ),
    )

    t_test = BashOperator(
        task_id="dbt_test",
        bash_command=(
            f"{COPY_PROJECT} && "
            f"DBT_PROFILES_DIR={DBT_WORK} "
            f"dbt test --select tag:silver tag:gold --no-version-check"
        ),
    )

    t_schemas >> t_bronze >> t_silver_gold >> t_test
