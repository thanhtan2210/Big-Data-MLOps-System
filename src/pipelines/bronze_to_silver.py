from pyspark.sql import functions as F
from pyspark.sql.types import StructType, StructField, LongType, FloatType, StringType
from src.utils.spark_session import get_spark_session
import os

# Cấu hình đường dẫn trên MinIO (S3)
SILVER_TABLE_PATH = "s3a://movie-data/silver/ratings"
CHECKPOINT_PATH = "s3a://movie-data/checkpoints/bronze_to_silver"

# Định nghĩa Schema cho dữ liệu JSON từ Kafka
json_schema = StructType([
    StructField("userId", LongType(), True),
    StructField("movieId", LongType(), True),
    StructField("rating", FloatType(), True),
    StructField("timestamp", LongType(), True)
])

def process_bronze_to_silver():
    # Khởi tạo Spark Session
    spark = get_spark_session("Bronze-to-Silver-Pipeline")
    
    print("Starting Bronze to Silver Streaming Pipeline...")

    # 1. Đọc dữ liệu từ Kafka (Bronze Layer)
    df_kafka = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", "localhost:9092") \
        .option("subscribe", "movie_ratings") \
        .option("startingOffsets", "earliest") \
        .load()

    # 2. Parse JSON và ép kiểu dữ liệu
    df_parsed = df_kafka.selectExpr("CAST(value AS STRING)") \
        .select(F.from_json("value", json_schema).alias("data")) \
        .select("data.*")

    # 3. Data Quality Gate (Làm sạch dữ liệu)
    df_cleaned = df_parsed \
        .filter(F.col("userId").isNotNull() & F.col("movieId").isNotNull()) \
        .filter((F.col("rating") >= 0) & (F.col("rating") <= 5)) \
        .withColumn("ingestion_timestamp", F.current_timestamp())

    # 4. Ghi dữ liệu vào Silver Layer (Delta Table)
    query = df_cleaned.writeStream \
        .format("delta") \
        .outputMode("append") \
        .option("checkpointLocation", CHECKPOINT_PATH) \
        .start(SILVER_TABLE_PATH)

    print(f"Pipeline is running. Data is being written to {SILVER_TABLE_PATH}")
    query.awaitTermination()

if __name__ == "__main__":
    process_bronze_to_silver()
