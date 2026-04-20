import pandas as pd
import json
import time
from confluent_kafka import Producer
import sys
import os

# Cấu hình Kafka
KAFKA_CONF = {
    'bootstrap.servers': 'localhost:9092',
    'client.id': 'rating-producer'
}

TOPIC_NAME = 'movie_ratings'
DATA_PATH = 'dataset/ml-25m/ratings.csv'

def delivery_report(err, msg):
    """ Báo cáo trạng thái gửi tin nhắn """
    if err is not None:
        print(f'Message delivery failed: {err}')
    else:
        # print(f'Message delivered to {msg.topic()} [{msg.partition()}]')
        pass

def stream_ratings():
    # Kiểm tra file dữ liệu
    if not os.path.exists(DATA_PATH):
        print(f"Error: File {DATA_PATH} not found!")
        return

    # Khởi tạo Kafka Producer
    producer = Producer(KAFKA_CONF)

    print(f"Starting to stream data from {DATA_PATH} to Kafka topic '{TOPIC_NAME}'...")

    # Đọc dữ liệu theo từng chunk để tiết kiệm RAM (Big Data approach)
    chunk_size = 1000
    try:
        for chunk in pd.read_csv(DATA_PATH, chunksize=chunk_size):
            for index, row in chunk.iterrows():
                # Tạo payload JSON
                payload = {
                    'userId': int(row['userId']),
                    'movieId': int(row['movieId']),
                    'rating': float(row['rating']),
                    'timestamp': int(row['timestamp'])
                }
                
                # Gửi tin nhắn vào Kafka
                producer.produce(
                    TOPIC_NAME, 
                    key=str(payload['userId']), 
                    value=json.dumps(payload),
                    callback=delivery_report
                )
                
                # Để demo mượt mà, chúng ta gửi 100 tin nhắn mỗi giây
                if index % 100 == 0:
                    producer.flush()
                    # print(f"Sent {index} messages...")
                    time.sleep(0.1) 
                    
    except KeyboardInterrupt:
        print("\nStreaming stopped by user.")
    finally:
        producer.flush()
        print("Done.")

if __name__ == "__main__":
    stream_ratings()
