FROM apache/spark:3.5.2

USER root

# RAPIDS accelerator for Spark (CUDA 12.x compatible)
ADD https://repo1.maven.org/maven2/com/nvidia/rapids-4-spark_2.12/24.12.1/rapids-4-spark_2.12-24.12.1.jar /opt/spark/jars/

# S3A / MinIO support
ADD https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/3.3.6/hadoop-aws-3.3.6.jar /opt/spark/jars/
ADD https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk-bundle/1.12.367/aws-java-sdk-bundle-1.12.367.jar /opt/spark/jars/

# GPU discovery script
COPY getGpusResources.sh /opt/spark/getGpusResources.sh
RUN chmod +x /opt/spark/getGpusResources.sh

RUN chmod 644 /opt/spark/jars/*.jar

USER spark
