# docker 
```sh
docker build . -t bx_airflow:2.8.1 --platform linux/amd64
docker tag bx_airflow:2.8.1 owshq/owshq-apache-airflow:2.8.1
docker push brunocza1/bx_airflow:2.8.1
```