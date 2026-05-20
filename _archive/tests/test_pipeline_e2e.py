import os
import time
import json
import pytest
import logging
from confluent_kafka import Producer
from src.utils.spark_session import get_spark_session
from pyspark.sql import functions as F
from dotenv import load_dotenv

# Tải biến môi trường
load_dotenv()

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Lấy cấu hình từ .env
KAFKA_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
KAFKA_TOPIC = os.getenv('KAFKA_TOPIC_NAME', 'movie_ratings')
S3_BUCKET = os.getenv('S3_BUCKET_PATH', 's3a://movie-data')
SILVER_PATH = f"{S3_BUCKET}/silver/ratings"

@pytest.fixture(scope="module")
def spark():
    """Khởi tạo Spark Session để kiểm tra dữ liệu trong Delta Lake."""
    spark_session = get_spark_session("E2E-Pipeline-Test")
    yield spark_session
    spark_session.stop()

def test_data_flow_kafka_to_silver(spark):
    """
    Kịch bản: Bắn tin nhắn vào Kafka -> Đợi Spark xử lý -> Kiểm tra Delta Lake.
    """
    # 1. Tạo dữ liệu Mock duy nhất (Sử dụng ID cực lớn dựa trên timestamp để tránh trùng dữ liệu thật)
    test_user_id = int(time.time()) 
    test_movie_id = 999999
    test_rating = 5.0
    
    payload = {
        'userId': test_user_id,
        'movieId': test_movie_id,
        'rating': test_rating,
        'timestamp': int(time.time())
    }
    
    # 2. Bắn tin nhắn vào Kafka
    logger.info(f"Step 1: Sending mock message to Kafka topic '{KAFKA_TOPIC}'...")
    producer_conf = {'bootstrap.servers': KAFKA_SERVERS}
    producer = Producer(producer_conf)
    
    try:
        producer.produce(
            KAFKA_TOPIC, 
            key=str(test_user_id), 
            value=json.dumps(payload)
        )
        producer.flush(timeout=10)
        logger.info(f"✅ Message sent: {payload}")
    except Exception as e:
        pytest.fail(f"Failed to send message to Kafka: {e}")

    # 3. Đợi Spark Streaming xử lý (Micro-batch trigger là 1 phút)
    # Chúng ta đợi 75 giây để đảm bảo Spark đã hoàn tất việc ghi xuống MinIO
    wait_time = 75
    logger.info(f"Step 2: Waiting {wait_time}s for Spark Streaming to process (1-min trigger)...")
    time.sleep(wait_time)

    # 4. Kiểm tra dữ liệu tại Silver Layer (Delta Table)
    logger.info(f"Step 3: Querying Delta Table at {SILVER_PATH}...")
    try:
        # Đọc Delta Table
        df_silver = spark.read.format("delta").load(SILVER_PATH)
        
        # Lọc tìm bản ghi chúng ta vừa bắn vào
        result = df_silver.filter(
            (F.col("userId") == test_user_id) & 
            (F.col("movieId") == test_movie_id)
        ).collect()
        
        # Assert (Xác nhận kết quả)
        assert len(result) > 0, f"❌ Test FAILED: Không tìm thấy userId {test_user_id} trong Silver Layer!"
        assert result[0]['rating'] == test_rating, "❌ Test FAILED: Giá trị rating không khớp!"
        
        logger.info(f"🚀 SUCCESS: Tìm thấy bản ghi trong Silver Layer. Data Flow hoạt động hoàn hảo!")
        
    except Exception as e:
        pytest.fail(f"❌ Error during Delta Lake assertion: {e}")

if __name__ == "__main__":
    # Cho phép chạy trực tiếp bằng python nếu không dùng pytest
    pytest.main([__file__, "-s"])
