import os
import boto3
import pandas as pd
from datetime import datetime

class HealthService:
    def __init__(self):
        self.bucket = os.environ.get('S3_BUCKET_NAME', 'movie-mlops')
        self.s3 = boto3.client('s3',
            endpoint_url=os.environ.get('AWS_ENDPOINT_URL'),
            aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY')
        )

    def get_pipeline_status(self):
        """Kiểm tra sự tồn tại của các file cốt lõi."""
        files = ['raw/movies.csv', 'raw/ratings.csv', 'lancedb_movies.zip']
        status = {}
        for f in files:
            try:
                self.s3.head_object(Bucket=self.bucket, Key=f)
                status[f] = "✅ OK"
            except:
                status[f] = "❌ Missing"
        return status

    def get_data_quality(self):
        """Mock data quality metrics."""
        return {
            "Total Movies": "27,278",
            "Schema Valid": "✅ Yes",
            "Poster Coverage": "98%",
            "Last Vectorized": "2026-05-19"
        }

    def get_system_metrics(self):
        """Mock observability metrics."""
        return {
            "R2 Latency": "45ms",
            "TMDB Quota": "85%",
            "Search p95": "12ms"
        }
