"""HVFHV Spark GPU pipeline — processa com RAPIDS na RTX 3090.

Submete um SparkApplication (cluster mode) via Spark Operator:
  - Driver pod: CPU, orquestra o job
  - Executor pod: GPU (nvidia.com/gpu: 1), RAPIDS cuDF acceleration

O PySpark script (spark_gpu_pipeline.py) lê parquets do MinIO,
transforma bronze→silver→gold, e escreve os resultados como parquet
de volta no MinIO (s3a://landing/spark-gold/).

Depois, a task import_gold_to_clickhouse usa a função s3() do
ClickHouse pra importar os parquets pro schema spark_gold —
permitindo comparação side-by-side com o pipeline CPU (schema gold).

Pipeline:
    create_spark_gold_schema
        → submit_spark_gpu_job  (SparkApplication cluster mode + GPU)
            → import_gold_to_clickhouse (ClickHouse s3() import)
"""
from __future__ import annotations

import time
from datetime import datetime

from airflow.models.dag import DAG
from airflow.providers.standard.operators.python import PythonOperator


SPARK_APP_NAME = "fhvhv-gpu-pipeline"
SPARK_NAMESPACE = "spark-rapids"
SPARK_JOB_YAML = "/opt/airflow/dags/repo/infra/src/k8s-manifests/spark-rapids/spark-gpu-job.yaml"

GOLD_TABLES = {
    "daily_revenue":    "trip_date Date, total_trips UInt64, gross_revenue_usd Float64, total_driver_pay_usd Float64, total_tips_usd Float64, total_congestion_usd Float64, avg_trip_miles Float64, avg_trip_minutes Float64, avg_waiting_minutes Float64, median_fare_usd Float64, p95_fare_usd Float64",
    "hourly_demand":    "weekday Int32, hour_of_day Int32, trips UInt64, avg_trip_min Float64, avg_wait_min Float64, avg_fare_usd Float64, avg_driver_pay_usd Float64",
    "borough_pairs":    "pickup_borough String, dropoff_borough String, trips UInt64, revenue_usd Float64, avg_miles Float64, avg_minutes Float64, avg_fare_usd Float64",
    "driver_economics": "month Date, total_trips UInt64, avg_base_fare Float64, avg_tips Float64, avg_driver_pay Float64, avg_driver_pct_of_fare Float64, total_driver_pay Float64, approx_hourly_rate_usd Float64",
    "shared_vs_solo":   "ride_type String, trips UInt64, avg_total_usd Float64, avg_miles Float64, avg_minutes Float64, avg_driver_pay_usd Float64, total_revenue_usd Float64",
}


def _ch_client():
    import os
    import clickhouse_connect
    return clickhouse_connect.get_client(
        host=os.environ["CLICKHOUSE_HOST"],
        port=int(os.environ["CLICKHOUSE_PORT"]),
        username=os.environ["CLICKHOUSE_USER"],
        password=os.environ["CLICKHOUSE_PASSWORD"],
    )


def create_spark_gold_schema():
    c = _ch_client()
    c.command("CREATE DATABASE IF NOT EXISTS spark_gold")
    print("  ok: spark_gold schema created")


def submit_spark_gpu_job():
    """Submit SparkApplication CRD and wait for completion."""
    import subprocess
    import json

    # Cleanup any previous run
    subprocess.run(
        ["kubectl", "-n", SPARK_NAMESPACE, "delete", "sparkapplication",
         SPARK_APP_NAME, "--ignore-not-found"],
        capture_output=True, timeout=30,
    )
    time.sleep(5)

    # Submit
    result = subprocess.run(
        ["kubectl", "apply", "-f", SPARK_JOB_YAML],
        capture_output=True, text=True, timeout=30,
    )
    print(f"  apply: {result.stdout.strip()}")
    if result.returncode != 0:
        raise RuntimeError(f"kubectl apply failed: {result.stderr}")

    # Poll for completion
    max_wait = 1800  # 30 min
    poll_interval = 15
    elapsed = 0
    while elapsed < max_wait:
        time.sleep(poll_interval)
        elapsed += poll_interval

        r = subprocess.run(
            ["kubectl", "-n", SPARK_NAMESPACE, "get", "sparkapplication",
             SPARK_APP_NAME, "-o", "jsonpath={.status.applicationState.state}"],
            capture_output=True, text=True, timeout=15,
        )
        state = r.stdout.strip()
        print(f"  [{elapsed}s] state={state}")

        if state == "COMPLETED":
            print("  Spark GPU job completed successfully!")
            # Print driver logs summary
            driver_logs = subprocess.run(
                ["kubectl", "-n", SPARK_NAMESPACE, "logs",
                 f"{SPARK_APP_NAME}-driver", "--tail=20"],
                capture_output=True, text=True, timeout=30,
            )
            print(driver_logs.stdout)
            return

        if state in ("FAILED", "SUBMISSION_FAILED"):
            # Get driver logs for debugging
            driver_logs = subprocess.run(
                ["kubectl", "-n", SPARK_NAMESPACE, "logs",
                 f"{SPARK_APP_NAME}-driver", "--tail=50"],
                capture_output=True, text=True, timeout=30,
            )
            print(driver_logs.stdout)
            raise RuntimeError(f"Spark GPU job failed with state: {state}")

    raise RuntimeError(f"Spark GPU job timed out after {max_wait}s")


def import_gold_to_clickhouse():
    """Import Spark-generated parquets from MinIO into ClickHouse."""
    import os

    c = _ch_client()
    endpoint = os.environ["MINIO_ENDPOINT"].rstrip("/")
    ak = os.environ["MINIO_ACCESS_KEY"]
    sk = os.environ["MINIO_SECRET_KEY"]

    for table, cols in GOLD_TABLES.items():
        t0 = time.time()
        s3_url = f"{endpoint}/landing/spark-gold/{table}/*.parquet"

        c.command(f"DROP TABLE IF EXISTS spark_gold.{table}")
        c.command(
            f"CREATE TABLE spark_gold.{table} ({cols}) "
            f"ENGINE = MergeTree() ORDER BY tuple()"
        )
        c.command(
            f"INSERT INTO spark_gold.{table} "
            f"SELECT * FROM s3('{s3_url}', '{ak}', '{sk}', 'Parquet')"
        )

        rows = c.query(f"SELECT count() FROM spark_gold.{table}").result_rows[0][0]
        elapsed = time.time() - t0
        print(f"  spark_gold.{table}: {rows:,} rows ({elapsed:.1f}s)")


with DAG(
    dag_id="fhvhv_spark_pipeline",
    description="HVFHV Spark GPU pipeline — RAPIDS on RTX 3090 → ClickHouse",
    start_date=datetime(2024, 1, 1),
    schedule=None,
    catchup=False,
    max_active_tasks=1,
    tags=["fhvhv", "spark", "gpu", "rapids", "medallion"],
) as dag:

    t_schema = PythonOperator(
        task_id="create_spark_gold_schema",
        python_callable=create_spark_gold_schema,
    )

    t_spark = PythonOperator(
        task_id="submit_spark_gpu_job",
        python_callable=submit_spark_gpu_job,
        execution_timeout=None,
    )

    t_import = PythonOperator(
        task_id="import_gold_to_clickhouse",
        python_callable=import_gold_to_clickhouse,
        execution_timeout=None,
    )

    t_schema >> t_spark >> t_import
