import boto3
from botocore.client import Config
import os
from dotenv import load_dotenv

load_dotenv()

def setup_minio():
    minio_endpoint = os.getenv('MINIO_ENDPOINT', "http://localhost:9000")
    minio_access_key = os.getenv('MINIO_ACCESS_KEY', "admin")
    minio_secret_key = os.getenv('MINIO_SECRET_KEY', "password")

    print(f"Connecting to MinIO at {minio_endpoint}...")
    
    # Khởi tạo client kết nối MinIO
    s3 = boto3.resource('s3',
        endpoint_url=minio_endpoint,
        aws_access_key_id=minio_access_key,
        aws_secret_access_key=minio_secret_key,
        config=Config(signature_version='s3v4'),
        region_name='us-east-1'
    )

    bucket_name = 'movie-data'

    # Kiểm tra và tạo bucket
    try:
        if s3.Bucket(bucket_name).creation_date is None:
            print(f"Bucket '{bucket_name}' not found. Creating...")
            s3.create_bucket(Bucket=bucket_name)
            print("Successfully created bucket!")
        else:
            print(f"Bucket '{bucket_name}' already exists.")
            
        # Tạo thêm bucket cho MLflow nếu chưa có
        if s3.Bucket('mlflow').creation_date is None:
            s3.create_bucket(Bucket='mlflow')
            print("Successfully created 'mlflow' bucket!")
            
    except Exception as e:
        print(f"Error connecting to MinIO: {e}")

if __name__ == "__main__":
    setup_minio()
