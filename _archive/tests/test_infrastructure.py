import os
import logging
import boto3
import requests
import lancedb
from confluent_kafka.admin import AdminClient
from dotenv import load_dotenv

# Tải cấu hình từ .env
load_dotenv()

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def test_kafka():
    """Kiểm tra kết nối tới Kafka Broker."""
    bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
    try:
        admin_client = AdminClient({'bootstrap.servers': bootstrap_servers})
        # Lấy metadata để thực sự kiểm tra kết nối
        metadata = admin_client.list_topics(timeout=5)
        logger.info(f"✅ [OK] Kafka: Reachable at {bootstrap_servers}. Found {len(metadata.topics)} topics.")
        return True
    except Exception as e:
        logger.error(f"❌ [FAILED] Kafka: Cannot connect to {bootstrap_servers}. Error: {e}")
        return False

def test_minio():
    """Kiểm tra kết nối tới MinIO/S3."""
    endpoint = os.getenv('MINIO_ENDPOINT', 'http://localhost:9000')
    access_key = os.getenv('MINIO_ACCESS_KEY', 'admin')
    secret_key = os.getenv('MINIO_SECRET_KEY', 'password')
    
    try:
        s3 = boto3.resource(
            's3',
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name='us-east-1'
        )
        # Thử liệt kê các bucket
        buckets = [bucket.name for bucket in s3.buckets.all()]
        logger.info(f"✅ [OK] MinIO: Connected at {endpoint}. Buckets: {buckets}")
        return True
    except Exception as e:
        logger.error(f"❌ [FAILED] MinIO: Connection error at {endpoint}. Error: {e}")
        return False

def test_mlflow():
    """Kiểm tra kết nối tới MLflow Tracking Server."""
    tracking_uri = os.getenv('MLFLOW_TRACKING_URI', 'http://localhost:5000')
    try:
        # Kiểm tra endpoint /health hoặc đơn giản là GET trang chủ
        response = requests.get(f"{tracking_uri}/health", timeout=5)
        if response.status_code == 200:
            logger.info(f"✅ [OK] MLflow: Server is up at {tracking_uri}")
            return True
        else:
            logger.warning(f"⚠️ [WARN] MLflow: Server at {tracking_uri} returned status {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"❌ [FAILED] MLflow: Connection refused at {tracking_uri}. Error: {e}")
        return False

def test_lancedb():
    """Kiểm tra quyền truy cập vào LanceDB (Local storage)."""
    db_uri = os.getenv('LANCEDB_URI', 'dataset/lancedb_store')
    try:
        db = lancedb.connect(db_uri)
        tables = db.table_names()
        logger.info(f"✅ [OK] LanceDB: Storage access at '{db_uri}'. Tables: {tables}")
        return True
    except Exception as e:
        logger.error(f"❌ [FAILED] LanceDB: Cannot access storage at '{db_uri}'. Error: {e}")
        return False

def run_all_tests():
    logger.info("="*50)
    logger.info("HYBRID ARCHITECTURE INFRASTRUCTURE CHECK")
    logger.info("="*50)
    
    results = [
        test_kafka(),
        test_minio(),
        test_mlflow(),
        test_lancedb()
    ]
    
    logger.info("="*50)
    if all(results):
        logger.info("🚀 TẤT CẢ HỆ THỐNG ĐÃ SẴN SÀNG ĐỂ CHẠY PIPELINE!")
    else:
        logger.error("🚨 MỘT SỐ DỊCH VỤ CHƯA SẴN SÀNG. VUI LÒNG KIỂM TRA DOCKER-COMPOSE.")
    logger.info("="*50)

if __name__ == "__main__":
    run_all_tests()
