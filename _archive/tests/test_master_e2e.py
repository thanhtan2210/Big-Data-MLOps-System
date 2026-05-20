import os
import logging
# Sửa lỗi 🔴: Đưa torch lên đầu để tránh OpenMP DLL conflict trên Windows
try:
    import torch
except ImportError:
    pass

import time
import json
import pytest
import requests
from typing import Dict, Any
from confluent_kafka import Producer
from src.utils.spark_session import get_spark_session
from dotenv import load_dotenv

# Tải cấu hình
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
        logging.FileHandler(os.path.join(LOG_DIR, "master_test.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Cấu hình từ .env
KAFKA_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
KAFKA_TOPIC = os.getenv('KAFKA_TOPIC_NAME', 'movie_ratings')
S3_BUCKET = os.getenv('S3_BUCKET_PATH', 's3a://movie-data')
SILVER_PATH = f"{S3_BUCKET}/silver/ratings"
BENTO_URL = "http://localhost:3000/chat"

class MasterPipelineTest:
    def __init__(self):
        self.test_user_id = int(time.time())
        self.test_movie_id = 777888 
        self.spark = None

    def setup_spark(self):
        """Khởi tạo kết nối Spark để query Delta Lake."""
        try:
            self.spark = get_spark_session("Master-E2E-Check")
            return True
        except Exception as e:
            logger.error(f"❌ Không thể kết nối Spark: {e}")
            return False

    def stage_1_ingest_kafka(self):
        """Bước 1: Bơm dữ liệu vào Kafka."""
        logger.info("🚀 [STAGE 1] Injecting mock rating into Kafka...")
        conf = {'bootstrap.servers': KAFKA_SERVERS}
        producer = Producer(conf)
        
        payload = {
            'userId': self.test_user_id,
            'movieId': self.test_movie_id,
            'rating': 5.0,
            'timestamp': int(time.time())
        }
        
        try:
            producer.produce(KAFKA_TOPIC, key=str(self.test_user_id), value=json.dumps(payload))
            producer.flush(timeout=10)
            logger.info(f"✅ Data injected into Kafka: {payload}")
        except Exception as e:
            logger.error(f"❌ Kafka Ingestion Failed: {e}")
            raise e

    def stage_2_poll_delta_lake(self, timeout_sec=120):
        """Bước 2: Polling Delta Lake chờ Spark xử lý."""
        logger.info(f"⏳ [STAGE 2] Waiting for Spark to write to Delta Lake (Timeout: {timeout_sec}s)...")
        start_time = time.time()
        
        while time.time() - start_time < timeout_sec:
            try:
                # Đọc Delta Table từ đường dẫn tuyệt đối để tránh sai lệch path
                absolute_silver_path = os.path.abspath(SILVER_PATH)
                df = self.spark.read.format("delta").load(absolute_silver_path)
                # Kiểm tra sự hiện diện của bản ghi (Sử dụng count để confirm)
                match_count = df.filter(df.userId == self.test_user_id).count()
                
                if match_count > 0:
                    logger.info(f"✅ [OK] Record found in Delta Lake after {int(time.time() - start_time)}s!")
                    return True
            except Exception as e:
                # Table có thể chưa tồn tại ở những giây đầu tiên, bỏ qua lỗi
                pass
            
            time.sleep(10) 
            
        logger.error("❌ [FAILED] Timeout: Data did not appear in Delta Lake.")
        return False

    def stage_3_test_ai_serving(self):
        """Bước 3: Kiểm tra AI Chatbot API."""
        logger.info("🤖 [STAGE 3] Testing AI Chatbot Response via BentoML...")
        
        payload = {
            "request": {
                "message": "Tôi vừa xem một bộ phim mới, hệ thống của bạn có ghi nhận được không?",
                "session_id": f"e2e_test_{self.test_user_id}"
            }
        }
        
        try:
            # Tăng timeout cho request đầu tiên vì model Gemini/BentoML có thể cần warm-up
            response = requests.post(BENTO_URL, json=payload, timeout=60)
            response.raise_for_status()
            res_json = response.json()
            
            bot_text = res_json.get('response', '')
            logger.info(f"✅ [OK] AI Response received: {bot_text[:100]}...")
            return True
        except Exception as e:
            logger.error(f"❌ [FAILED] AI Serving Error: {e}")
            return False

@pytest.fixture(scope="module")
def pipeline_tester():
    tester = MasterPipelineTest()
    # Khởi động Spark một lần duy nhất cho toàn bộ module test
    if not tester.setup_spark():
        pytest.fail("Could not initialize Spark session for E2E test.")
    yield tester
    if tester.spark:
        tester.spark.stop()

def test_full_pipeline_master(pipeline_tester):
    """Hàm chạy test chính theo trình tự Stage 1 -> 2 -> 3."""
    # Stage 1: Ingest
    pipeline_tester.stage_1_ingest_kafka()
    
    # Stage 2: Processing (Polling)
    assert pipeline_tester.stage_2_poll_delta_lake() is True
    
    # Stage 3: Serving
    assert pipeline_tester.stage_3_test_ai_serving() is True

    logger.info("="*60)
    logger.info("🎉 CONGRATULATIONS: FULL END-TO-END PIPELINE IS FUNCTIONAL!")
    logger.info("="*60)

if __name__ == "__main__":
    # Cho phép chạy trực tiếp: python tests/test_master_e2e.py
    pytest.main([__file__, "-s"])
