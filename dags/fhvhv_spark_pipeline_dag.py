"""HVFHV Spark-RAPIDS GPU pipeline — processa no GPU, persiste no ClickHouse.

Lê os parquets do MinIO via Spark Thrift Server (RAPIDS GPU), transforma
bronze→silver→gold no GPU, e escreve as tabelas gold no ClickHouse em um
schema dedicado `spark_gold` pra comparação side-by-side com o pipeline
CPU (schema `gold`).

Pipeline:
    create_spark_gold_schema
        → run_dbt_spark            (Cosmos DbtTaskGroup, target=spark)
            → export_to_clickhouse (PythonOperator — copia Spark→ClickHouse)
"""
from __future__ import annotations

import time
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

DBT_PROJECT_PATH = Path("/opt/airflow/dags/repo/dags/dbt_demo")
DBT_PROFILES_PATH = DBT_PROJECT_PATH / "profiles.yml"
DBT_EXECUTABLE = "/home/airflow/.local/bin/dbt"

profile_config = ProfileConfig(
    profile_name="dbt_demo",
    target_name="spark",
    profiles_yml_filepath=DBT_PROFILES_PATH,
)

execution_config = ExecutionConfig(
    dbt_executable_path=DBT_EXECUTABLE,
)

render_config = RenderConfig(
    load_method=LoadMode.DBT_LS,
    select=["tag:spark"],
)


def _ch_client():
    import os
    import clickhouse_connect
    return clickhouse_connect.get_client(
        host=os.environ["CLICKHOUSE_HOST"],
        port=int(os.environ["CLICKHOUSE_PORT"]),
        username=os.environ["CLICKHOUSE_USER"],
        password=os.environ["CLICKHOUSE_PASSWORD"],
    )


def _spark_conn():
    from pyhive import hive
    import os
    return hive.connect(
        host=os.environ.get("SPARK_THRIFT_HOST",
                            "spark-thrift.spark-rapids.svc.cluster.local"),
        port=10000,
    )


def create_spark_gold_schema():
    c = _ch_client()
    c.command("CREATE DATABASE IF NOT EXISTS spark_gold")
    print("  ok: spark_gold schema created")


GOLD_TABLES = [
    "spark_daily_revenue",
    "spark_hourly_demand",
    "spark_borough_pairs",
    "spark_driver_economics",
    "spark_shared_vs_solo",
]


def export_to_clickhouse():
    """Read each gold table from Spark and write to ClickHouse spark_gold schema."""
    spark = _spark_conn()
    ch = _ch_client()

    for spark_table in GOLD_TABLES:
        ch_table = spark_table.replace("spark_", "")
        t0 = time.time()

        cursor = spark.cursor()
        cursor.execute(f"SELECT * FROM default.{spark_table}")
        cols = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        cursor.close()

        ch.command(f"DROP TABLE IF EXISTS spark_gold.{ch_table}")

        col_defs = []
        for col in cols:
            sample = rows[0][cols.index(col)] if rows else None
            if isinstance(sample, (int,)):
                col_defs.append(f"`{col}` Int64")
            elif isinstance(sample, (float,)):
                col_defs.append(f"`{col}` Float64")
            elif isinstance(sample, bool):
                col_defs.append(f"`{col}` UInt8")
            else:
                col_defs.append(f"`{col}` String")

        ch.command(
            f"CREATE TABLE spark_gold.{ch_table} "
            f"({', '.join(col_defs)}) "
            f"ENGINE = MergeTree() ORDER BY tuple()"
        )

        if rows:
            ch.insert(f"spark_gold.{ch_table}", rows, column_names=cols)

        elapsed = time.time() - t0
        print(f"  spark_gold.{ch_table}: {len(rows)} rows, {elapsed:.1f}s")

    spark.close()


with DAG(
    dag_id="fhvhv_spark_pipeline",
    description="HVFHV Spark-RAPIDS GPU pipeline — gold tables via GPU → ClickHouse",
    start_date=datetime(2024, 1, 1),
    schedule=None,
    catchup=False,
    max_active_tasks=2,
    tags=["fhvhv", "spark", "gpu", "rapids", "medallion", "dbt"],
) as dag:

    t_schema = PythonOperator(
        task_id="create_spark_gold_schema",
        python_callable=create_spark_gold_schema,
    )

    dbt_spark = DbtTaskGroup(
        group_id="dbt_spark_gpu",
        project_config=ProjectConfig(DBT_PROJECT_PATH),
        profile_config=profile_config,
        execution_config=execution_config,
        render_config=render_config,
    )

    t_export = PythonOperator(
        task_id="export_to_clickhouse",
        python_callable=export_to_clickhouse,
        execution_timeout=None,
    )

    t_schema >> dbt_spark >> t_export
