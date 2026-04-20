from pyspark.sql import SparkSession
from delta import configure_spark_with_delta_pip
import os

def get_spark_session(app_name="BigData-MLOps-System"):
    """
    Khởi tạo Spark Session với cấu hình Delta Lake và MinIO (S3)
    """
    
    # Cấu hình các gói thư viện cần thiết (Delta & AWS SDK)
    builder = SparkSession.builder.appName(app_name) \
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
        .config("spark.sql.catalog.spark_control_plane", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
        .config("spark.hadoop.fs.s3a.endpoint", "http://localhost:9000") \
        .config("spark.hadoop.fs.s3a.access.key", "admin") \
        .config("spark.hadoop.fs.s3a.secret.key", "password") \
        .config("spark.hadoop.fs.s3a.path.style.access", "true") \
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .config("spark.delta.logStore.class", "org.apache.spark.sql.delta.storage.S3SingleDriverLogStore") \
        .config("spark.sql.shuffle.partitions", "4")  # Giảm partition cho môi trường local
    
    # Tự động cấu hình Delta Lake
    spark = configure_spark_with_delta_pip(builder).getOrCreate()
    
    # Thiết lập log level để giảm noise
    spark.sparkContext.setLogLevel("ERROR")
    
    return spark

if __name__ == "__main__":
    # Test khởi tạo Spark
    print("Initializing Spark session...")
    spark = get_spark_session()
    print(f"Spark Version: {spark.version}")
    print("Spark Session initialized successfully!")
    spark.stop()
