import os
import logging
from dotenv import load_dotenv
from pyspark.sql import functions as F
from pyspark.sql.types import StructType, StructField, LongType, FloatType
from src.utils.spark_session import get_spark_session

# Tải biến môi trường từ file .env
load_dotenv(override=True)

# ==========================================
# CẤU HÌNH LOGGING
# ==========================================
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "bronze_to_silver.log"), encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ==========================================
# CẤU HÌNH TỪ BIẾN MÔI TRƯỜNG (Sửa lỗi Blocker)
# ==========================================
KAFKA_SERVERS: str = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
KAFKA_TOPIC: str = os.getenv('KAFKA_TOPIC_NAME', 'movie_ratings')
S3_BUCKET: str = os.getenv('S3_BUCKET_PATH', 's3a://movie-data')

SILVER_TABLE_PATH: str = f"{S3_BUCKET}/silver/ratings"
CHECKPOINT_PATH: str = f"{S3_BUCKET}/checkpoints/bronze_to_silver"

# Định nghĩa Schema cho dữ liệu JSON từ Kafka
json_schema = StructType([
    StructField("userId", LongType(), True),
    StructField("movieId", LongType(), True),
    StructField("rating", FloatType(), True),
    StructField("timestamp", LongType(), True)
])

def process_bronze_to_silver() -> None:
    """
    Spark Streaming Pipeline: Đọc dữ liệu từ Kafka (Bronze) và ghi vào Delta Lake (Silver).
    Đã sửa lỗi Small File Problem, tối ưu tài nguyên và cấu hình mạng Docker.
    """
    # 1. Khởi tạo Spark Session
    spark = get_spark_session("Bronze-to-Silver-Pipeline")
    
    # Sửa lỗi High Priority: Tối ưu số lượng partition cho streaming (mặc định 200 là quá lớn)
    spark.conf.set("spark.sql.shuffle.partitions", "4")
    
    logger.info(f"Đang khởi động Pipeline. Đang kết nối Kafka tại: {KAFKA_SERVERS}")

    try:
        # 2. Đọc dữ liệu từ Kafka (Sửa lỗi 🔴: Thêm failOnDataLoss để ổn định hệ thống)
        df_kafka = spark.readStream \
            .format("kafka") \
            .option("kafka.bootstrap.servers", KAFKA_SERVERS) \
            .option("subscribe", KAFKA_TOPIC) \
            .option("startingOffsets", "earliest") \
            .option("failOnDataLoss", "false") \
            .load()

        # 3. Parse JSON và ép kiểu dữ liệu
        df_parsed = df_kafka.selectExpr("CAST(value AS STRING)") \
            .select(F.from_json("value", json_schema).alias("data")) \
            .select("data.*")

        # 4. Data Quality Gate (Làm sạch dữ liệu)
        df_cleaned = df_parsed \
            .filter(F.col("userId").isNotNull() & F.col("movieId").isNotNull()) \
            .filter((F.col("rating") >= 0) & (F.col("rating") <= 5)) \
            .withColumn("ingestion_timestamp", F.current_timestamp())

        # 5. Ghi dữ liệu vào Silver Layer (Sửa lỗi 🔴: Chống Small File Problem bằng Trigger)
        # Sử dụng trigger 1 phút để Spark gom dữ liệu thành các file lớn hơn trên MinIO
        query = df_cleaned.writeStream \
            .format("delta") \
            .outputMode("append") \
            .option("checkpointLocation", CHECKPOINT_PATH) \
            .trigger(processingTime='1 minute') \
            .start(SILVER_TABLE_PATH)

        logger.info(f"Pipeline đang chạy. Dữ liệu đang được ghi vào: {SILVER_TABLE_PATH}")
        
        # Duy trì job chạy cho đến khi gặp lỗi hoặc bị dừng
        query.awaitTermination()

    except Exception as e:
        logger.error(f"Lỗi nghiêm trọng trong Pipeline: {e}")
    finally:
        # Đảm bảo đóng Spark Session khi dừng
        spark.stop()
        logger.info("Spark Session đã được đóng.")

if __name__ == "__main__":
    process_bronze_to_silver()
