from pyspark.sql import functions as F
from src.utils.spark_session import get_spark_session
import os

# Cấu hình đường dẫn trên MinIO (S3)
SILVER_TABLE_PATH = "s3a://movie-data/silver/ratings"
GOLD_USER_FEATURES_PATH = "s3a://movie-data/gold/user_features"
GOLD_MOVIE_FEATURES_PATH = "s3a://movie-data/gold/movie_features"

def process_silver_to_gold():
    # Khởi tạo Spark Session
    spark = get_spark_session("Silver-to-Gold-Pipeline")
    
    print("Starting Silver to Gold Feature Engineering Pipeline...")

    # 1. Đọc dữ liệu từ Silver Layer
    df_silver = spark.read.format("delta").load(SILVER_TABLE_PATH)

    # 2. Tính toán User Features (Gold Layer)
    user_features = df_silver.groupBy("userId").agg(
        F.avg("rating").alias("user_avg_rating"),
        F.count("rating").alias("user_rating_count"),
        F.max("timestamp").alias("user_last_interaction_timestamp")
    ).withColumn("updated_at", F.current_timestamp())

    # 3. Tính toán Movie Features (Gold Layer)
    movie_features = df_silver.groupBy("movieId").agg(
        F.avg("rating").alias("movie_avg_rating"),
        F.count("rating").alias("movie_rating_count")
    ).withColumn("updated_at", F.current_timestamp())

    # 4. Ghi dữ liệu vào Gold Layer (Delta Table)
    print(f"Writing User Features to {GOLD_USER_FEATURES_PATH}...")
    user_features.write.format("delta").mode("overwrite").save(GOLD_USER_FEATURES_PATH)

    print(f"Writing Movie Features to {GOLD_MOVIE_FEATURES_PATH}...")
    movie_features.write.format("delta").mode("overwrite").save(GOLD_MOVIE_FEATURES_PATH)

    print("Feature Engineering completed successfully!")

if __name__ == "__main__":
    process_silver_to_gold()
