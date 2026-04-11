from __future__ import annotations

from datetime import datetime

from airflow.models.dag import DAG
from airflow.providers.standard.operators.bash import BashOperator

# git-sync mounts the repo read-only at DBT_SRC. dbt needs to write logs/
# and target/ dirs, so each task copies the project to a writable location
# under /tmp before running.
DBT_SRC = "/opt/airflow/dags/repo/dags/dbt_demo"
DBT_WORK = "/tmp/dbt_work"

COPY_PROJECT = f"rm -rf {DBT_WORK} && cp -r {DBT_SRC} {DBT_WORK} && cd {DBT_WORK}"

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
            f"{COPY_PROJECT} && "
            f"DBT_PROFILES_DIR={DBT_WORK} "
            f"dbt debug --no-version-check"
        ),
    )

    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=(
            f"{COPY_PROJECT} && "
            f"DBT_PROFILES_DIR={DBT_WORK} "
            f"dbt run --no-version-check --target dev"
        ),
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=(
            f"{COPY_PROJECT} && "
            f"DBT_PROFILES_DIR={DBT_WORK} "
            f"dbt test --no-version-check --target dev"
        ),
    )

    dbt_debug >> dbt_run >> dbt_test
