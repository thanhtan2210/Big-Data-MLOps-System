import os
from pyspark.sql import SparkSession
from delta import configure_spark_with_delta_pip
from dotenv import load_dotenv

# Nạp các biến môi trường từ file .env
load_dotenv()

def get_spark_session(app_name="BigData-MLOps-System"):
    """
    Khởi tạo Spark Session tối ưu cho môi trường Local Windows/MinIO/Delta
    """
    
    if os.name == 'nt': 
        hadoop_home = os.getenv('HADOOP_HOME', "C:\\hadoop")
        os.environ['HADOOP_HOME'] = hadoop_home
        if hadoop_home not in os.environ['PATH']:
            os.environ['PATH'] += os.pathsep + os.path.join(hadoop_home, 'bin')

    # Cấu hình Add-Opens cho Java 17+
    java_17_options = (
        "--add-opens=java.base/java.nio=ALL-UNNAMED "
        "--add-opens=java.base/java.net=ALL-UNNAMED "
        "--add-opens=java.base/java.lang=ALL-UNNAMED "
        "--add-opens=java.base/java.util=ALL-UNNAMED "
        "--add-opens=java.base/java.util.concurrent=ALL-UNNAMED "
        "--add-opens=java.base/sun.nio.ch=ALL-UNNAMED"
    )

    # Lấy thông tin MinIO
    minio_endpoint = os.getenv('MINIO_ENDPOINT', "http://127.0.0.1:9000")
    minio_access_key = os.getenv('MINIO_ACCESS_KEY', "admin")
    minio_secret_key = os.getenv('MINIO_SECRET_KEY', "password")

    packages = [
        "org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.1",
        "org.apache.hadoop:hadoop-aws:3.3.4",
        "com.amazonaws:aws-java-sdk-bundle:1.12.262"
    ]

    builder = SparkSession.builder.appName(app_name) \
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
        .config("spark.hadoop.fs.s3a.endpoint", minio_endpoint) \
        .config("spark.hadoop.fs.s3a.access.key", minio_access_key) \
        .config("spark.hadoop.fs.s3a.secret.key", minio_secret_key) \
        .config("spark.hadoop.fs.s3a.path.style.access", "true") \
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .config("spark.delta.logStore.class", "org.apache.spark.sql.delta.storage.S3SingleDriverLogStore") \
        .config("spark.sql.shuffle.partitions", "4") \
        .config("spark.driver.extraJavaOptions", java_17_options) \
        .config("spark.executor.extraJavaOptions", java_17_options) \
        .config("spark.driver.memory", "2g") \
        .config("spark.hadoop.fs.s3a.attempts.maximum", "3") \
        .config("spark.hadoop.fs.s3a.fast.upload", "true")
    
    # Nạp các packages và khởi tạo
    spark = configure_spark_with_delta_pip(builder, extra_packages=packages).getOrCreate()
    spark.sparkContext.setLogLevel("ERROR")
    
    return spark

if __name__ == "__main__":
    spark = get_spark_session()
    print(f"Spark Version: {spark.version}")
    spark.stop()
