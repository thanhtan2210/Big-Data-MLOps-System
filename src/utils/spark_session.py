import os
from pyspark.sql import SparkSession
from delta import configure_spark_with_delta_pip
from dotenv import load_dotenv

# Nạp các biến môi trường từ file .env
load_dotenv()

def get_spark_session(app_name="BigData-MLOps-System"):
    """
    Khởi tạo Spark Session với cấu hình Delta Lake, Kafka và MinIO (S3)
    """
    
    # Sửa lỗi HADOOP_HOME trên Windows
    if os.name == 'nt': 
        hadoop_home = os.getenv('HADOOP_HOME', "C:\\hadoop")
        os.environ['HADOOP_HOME'] = hadoop_home
        if hadoop_home not in os.environ['PATH']:
            os.environ['PATH'] += os.pathsep + os.path.join(hadoop_home, 'bin')
        print(f"DEBUG: HADOOP_HOME set to {hadoop_home}")

    # Lấy thông tin MinIO từ .env
    minio_endpoint = os.getenv('MINIO_ENDPOINT', "http://localhost:9000")
    minio_access_key = os.getenv('MINIO_ACCESS_KEY', "admin")
    minio_secret_key = os.getenv('MINIO_SECRET_KEY', "password")

    # Khai báo các gói thư viện cần tải (Kafka & S3)
    # Phiên bản 3.4.1 của Spark tương ứng với các gói bên dưới
    packages = [
        "org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.1",
        "org.apache.hadoop:hadoop-aws:3.3.4",
        "com.amazonaws:aws-java-sdk-bundle:1.12.262"
    ]

    builder = SparkSession.builder.appName(app_name) \
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
        .config("spark.sql.catalog.spark_control_plane", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
        .config("spark.hadoop.fs.s3a.endpoint", minio_endpoint) \
        .config("spark.hadoop.fs.s3a.access.key", minio_access_key) \
        .config("spark.hadoop.fs.s3a.secret.key", minio_secret_key) \
        .config("spark.hadoop.fs.s3a.path.style.access", "true") \
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .config("spark.delta.logStore.class", "org.apache.spark.sql.delta.storage.S3SingleDriverLogStore") \
        .config("spark.sql.shuffle.partitions", "4") \
        .config("spark.jars.packages", ",".join(packages))
    
    # Tự động cấu hình Delta Lake và nạp các packages
    spark = configure_spark_with_delta_pip(builder, extra_packages=packages).getOrCreate()
    
    # Thiết lập log level để giảm noise
    spark.sparkContext.setLogLevel("ERROR")
    
    return spark

if __name__ == "__main__":
    print("Testing Spark session with Kafka and S3 support...")
    spark = get_spark_session()
    print(f"Spark Version: {spark.version}")
    print("Spark Session initialized successfully!")
    spark.stop()
