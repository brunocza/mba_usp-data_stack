from __future__ import annotations

from datetime import datetime

from airflow.models.dag import DAG
from airflow.operators.bash import BashOperator

DBT_DIR = "/opt/airflow/dags/repo/dags/dbt_demo"

with DAG(
    dag_id="dbt_demo",
    description="Run dbt_demo project against ClickHouse",
    start_date=datetime(2024, 1, 1),
    schedule=None,
    catchup=False,
    tags=["dbt", "clickhouse"],
) as dag:

    dbt_debug = BashOperator(
        task_id="dbt_debug",
        bash_command=(
            f"cd {DBT_DIR} && "
            f"DBT_PROFILES_DIR={DBT_DIR} "
            f"dbt debug --no-version-check"
        ),
    )

    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=(
            f"cd {DBT_DIR} && "
            f"DBT_PROFILES_DIR={DBT_DIR} "
            f"dbt run --no-version-check --target dev"
        ),
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=(
            f"cd {DBT_DIR} && "
            f"DBT_PROFILES_DIR={DBT_DIR} "
            f"dbt test --no-version-check --target dev"
        ),
    )

    dbt_debug >> dbt_run >> dbt_test
