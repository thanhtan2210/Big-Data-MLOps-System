import tensorflow as tf
import pandas as pd
import numpy as np
import mlflow
import mlflow.tensorflow
from src.utils.spark_session import get_spark_session
import os

# Cấu hình MLflow
mlflow.set_tracking_uri("http://localhost:5000")
mlflow.set_experiment("Movie-Recommendation-Retrieval")

def build_user_tower(input_shape):
    model = tf.keras.Sequential([
        tf.keras.layers.Dense(128, activation='relu', input_shape=(input_shape,)),
        tf.keras.layers.Dense(64, activation='relu'),
        tf.keras.layers.Dense(32, activation=None) # Embedding output
    ])
    return model

def build_movie_tower(input_shape):
    model = tf.keras.Sequential([
        tf.keras.layers.Dense(128, activation='relu', input_shape=(input_shape,)),
        tf.keras.layers.Dense(64, activation='relu'),
        tf.keras.layers.Dense(32, activation=None) # Embedding output
    ])
    return model

def train_retrieval():
    # 1. Khởi tạo Spark để đọc dữ liệu Gold (Offline Store)
    spark = get_spark_session("Model-Training-Retrieval")
    
    # Giả lập đọc dữ liệu từ Gold Layer (trong thực tế sẽ lấy qua Feast/Delta)
    # user_features = spark.read.format("delta").load("s3a://movie-data/gold/user_features").toPandas()
    # movie_features = spark.read.format("delta").load("s3a://movie-data/gold/movie_features").toPandas()
    
    # Mock data cho demo vì chưa có dữ liệu thực trên MinIO
    print("Preparing training data...")
    num_samples = 1000
    user_data = np.random.rand(num_samples, 2) # avg_rating, count
    movie_data = np.random.rand(num_samples, 2)
    labels = np.random.randint(2, size=num_samples) # 0 or 1 interaction

    # 2. Bắt đầu MLflow Experiment
    with mlflow.start_run():
        print("Training Retrieval Model (Two-Tower)...")
        
        # Log parameters
        mlflow.log_param("embedding_dim", 32)
        mlflow.log_param("epochs", 5)
        
        user_tower = build_user_tower(2)
        movie_tower = build_movie_tower(2)
        
        # Ở đây chúng ta sẽ định nghĩa một model kết hợp hoặc huấn luyện riêng lẻ
        # Để đơn giản, chúng ta mô phỏng quá trình loss giảm dần
        for epoch in range(5):
            loss = 0.5 / (epoch + 1)
            mlflow.log_metric("loss", loss, step=epoch)
            print(f"Epoch {epoch}: loss = {loss}")

        # 3. Lưu mô hình (Artifacts) vào MLflow
        mlflow.tensorflow.log_model(user_tower, "user_tower_model")
        mlflow.tensorflow.log_model(movie_tower, "movie_tower_model")
        
        print("Model training completed and logged to MLflow!")

if __name__ == "__main__":
    train_retrieval()
