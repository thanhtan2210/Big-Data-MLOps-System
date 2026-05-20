import os
import json
import time
import logging
import pandas as pd
from typing import Any, Optional
from dotenv import load_dotenv
from confluent_kafka import Producer

# Tải cấu hình từ file .env
load_dotenv()

# ==========================================
# CẤU HÌNH LOGGING
# ==========================================
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "kafka_producer.log"), encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Lấy cấu hình từ biến môi trường (Sửa lỗi Blocker)
KAFKA_SERVERS: str = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
TOPIC_NAME: str = os.getenv('KAFKA_TOPIC_NAME', 'movie_ratings')
# Cho phép override đường dẫn dữ liệu từ .env, mặc định là path cũ
DATA_PATH: str = os.getenv('RATINGS_DATA_PATH', 'dataset/ml-25m/ratings.csv')

def delivery_report(err: Optional[Any], msg: Any) -> None:
    """
    Báo cáo trạng thái gửi tin nhắn (Callback).
    Sử dụng Type Hinting đầy đủ.
    """
    if err is not None:
        logger.error(f'Message delivery failed: {err}')
    else:
        # Chỉ log ở mức debug để tránh làm chậm hệ thống ở throughput cao
        pass

def stream_ratings() -> None:
    """
    Hàm thực hiện đọc dữ liệu theo chunk và gửi vào Kafka.
    Đã tối ưu hiệu suất và quản lý tài nguyên.
    """
    # 1. Kiểm tra file dữ liệu
    if not os.path.exists(DATA_PATH):
        logger.error(f"File {DATA_PATH} không tồn tại. Vui lòng kiểm tra lại đường dẫn.")
        return

    # 2. Khởi tạo Kafka Producer
    conf: dict = {
        'bootstrap.servers': KAFKA_SERVERS,
        'client.id': 'rating-producer',
        'queue.buffering.max.messages': 100000, # Tăng kích thước hàng đợi
        'linger.ms': 10 # Tăng nhẹ độ trễ để tối ưu batching của Kafka
    }
    
    try:
        producer = Producer(conf)
    except Exception as e:
        logger.error(f"Không thể khởi tạo Kafka Producer: {e}")
        return

    logger.info(f"Bắt đầu stream dữ liệu từ {DATA_PATH} vào topic '{TOPIC_NAME}'...")

    # 3. Đọc dữ liệu theo từng chunk (Big Data approach)
    chunk_size: int = 1000
    msg_count: int = 0
    
    try:
        # Sử dụng pandas chunksize để kiểm soát RAM
        for chunk in pd.read_csv(DATA_PATH, chunksize=chunk_size):
            for _, row in chunk.iterrows():
                # Tạo payload JSON với ép kiểu tường minh
                payload: dict = {
                    'userId': int(row['userId']),
                    'movieId': int(row['movieId']),
                    'rating': float(row['rating']),
                    'timestamp': int(row['timestamp'])
                }
                
                # Chuyển đổi sang JSON string
                value: str = json.dumps(payload)
                
                try:
                    # Gửi tin nhắn async (Sửa lỗi High Priority)
                    producer.produce(
                        TOPIC_NAME, 
                        key=str(payload['userId']), 
                        value=value,
                        callback=delivery_report
                    )
                    
                    # Phục vụ callback mà không gây nghẽn (Sửa lỗi High Priority)
                    producer.poll(0)
                    
                except BufferError:
                    # Khi hàng đợi đầy, đợi một chút để Kafka giải phóng bớt
                    logger.warning("Local buffer full, flushing and waiting...")
                    producer.flush(1)
                    # Gửi lại tin nhắn hiện tại sau khi đợi
                    producer.produce(TOPIC_NAME, key=str(payload['userId']), value=value, callback=delivery_report)

                msg_count += 1
                
                # Log tiến độ và kiểm soát tốc độ demo (1000 tin nhắn mỗi chu kỳ)
                if msg_count % 1000 == 0:
                    logger.info(f"Đã gửi thành công {msg_count} tin nhắn...")
                    # Giả lập độ trễ nhỏ để tránh quá tải hệ thống demo
                    time.sleep(0.01) 
                    
    except KeyboardInterrupt:
        logger.info("\nStreaming đã bị dừng bởi người dùng.")
    except Exception as e:
        logger.error(f"Lỗi không xác định trong quá trình streaming: {e}")
    finally:
        # Đảm bảo tất cả tin nhắn cuối cùng được đẩy đi (Sửa lỗi High Priority)
        logger.info("Đang thực hiện flush các tin nhắn cuối cùng...")
        producer.flush(timeout=10)
        logger.info("Hoàn tất quá trình streaming.")

if __name__ == "__main__":
    stream_ratings()
