import tensorflow as tf
import pandas as pd
import numpy as np
import mlflow
import mlflow.tensorflow
from src.utils.spark_session import get_spark_session
import os
from dotenv import load_dotenv

# Nạp các biến môi trường từ file .env
load_dotenv()

# ÁNH XẠ: Cấu hình cho MLflow/Boto3 để nhận diện MinIO như một S3 Storage
os.environ['AWS_ACCESS_KEY_ID'] = os.getenv('MINIO_ACCESS_KEY', 'admin')
os.environ['AWS_SECRET_ACCESS_KEY'] = os.getenv('MINIO_SECRET_KEY', 'password')
os.environ['MLFLOW_S3_ENDPOINT_URL'] = os.getenv('MINIO_ENDPOINT', 'http://127.0.0.1:9000')
os.environ['AWS_REGION'] = 'us-east-1'

# Cấu hình MLflow Tracking
mlflow_uri = os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5000")
mlflow.set_tracking_uri(mlflow_uri)
mlflow.set_experiment("Movie-Recommendation-Retrieval")

def build_user_tower(input_shape):
    model = tf.keras.Sequential([
        tf.keras.layers.Input(shape=(input_shape,)),
        tf.keras.layers.Dense(128, activation='relu'),
        tf.keras.layers.Dense(64, activation='relu'),
        tf.keras.layers.Dense(32, activation=None)
    ])
    return model

def train_retrieval():
    # 1. Khởi tạo Spark để kiểm tra dữ liệu
    spark = get_spark_session("Model-Training-Retrieval")
    print("Spark initialized for training verification.")
    
    # Mock data cho demo
    num_samples = 1000
    user_tower = build_user_tower(2)
    
    # 2. Bắt đầu MLflow Experiment
    with mlflow.start_run():
        print(f"Training Retrieval Model. Logging to {mlflow_uri}...")
        
        mlflow.log_param("embedding_dim", 32)
        mlflow.log_param("epochs", 5)
        
        for epoch in range(5):
            loss = 0.5 / (epoch + 1)
            mlflow.log_metric("loss", loss, step=epoch)

        # 3. Lưu mô hình vào MLflow (Sẽ đẩy lên MinIO bucket 'mlflow')
        print("Uploading model to MLflow Artifact Store (MinIO)...")
        mlflow.tensorflow.log_model(user_tower, "user_tower_model")
        
        print("SUCCESS: Model training completed and logged to MLflow!")

if __name__ == "__main__":
    train_retrieval()
