# FROM apache/airflow:2.8.1
FROM apache/airflow:2.9.3

USER root

RUN apt-get update \
  && apt-get install -y --no-install-recommends \
  openjdk-17-jre-headless \
  && apt-get autoremove -yqq --purge \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

USER airflow

ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64

COPY requirements.txt /

RUN pip install --no-cache-dir "apache-airflow==${AIRFLOW_VERSION}" -r /requirements.txt

# docker build -t brunocza1/bx_airflow:2.9.3 .
# docker push brunocza1/bx_airflow:2.9.3
