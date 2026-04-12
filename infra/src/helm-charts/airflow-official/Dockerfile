FROM apache/airflow:3.1.8

USER airflow

RUN pip install --no-cache-dir \
      apache-airflow-core==3.1.8 \
      dbt-core==1.10.4 \
      dbt-clickhouse==1.9.2 \
      astronomer-cosmos==1.14.0
