from __future__ import annotations

import pendulum

from airflow.models.dag import DAG
from airflow.operators.bash import BashOperator

with DAG(
    dag_id="example_dag",
    start_date=pendulum.datetime(2023, 10, 26, tz="UTC"),
    catchup=False,
    schedule="@daily",
    tags=["example"],
) as dag:
    bash_task = BashOperator(
        task_id="hello_world",
        bash_command="echo 'Hello World from Airflow DAG!'",
    )
