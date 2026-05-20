import os
import boto3
import lancedb
import logging
import datetime
import shutil
from typing import Dict, Any

logger = logging.getLogger("health_monitor")

def get_s3_client():
    return boto3.client('s3',
                        endpoint_url=os.environ.get('AWS_ENDPOINT_URL'),
                        aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
                        aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY')
                        )

def ensure_lancedb_ready():
    """Tải và giải nén database từ R2 nếu chưa tồn tại local."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    # Thư mục giải nén mặc định từ zip
    db_path = os.path.join(base_dir, 'lancedb_movies') 
    zip_path = os.path.join(base_dir, 'lancedb_movies_monitor.zip')
    
    if not os.path.exists(db_path):
        logger.info(f"Đang tải LanceDB từ R2 về...")
        try:
            s3 = get_s3_client()
            bucket = os.environ.get('S3_BUCKET_NAME', 'movie-mlops')
            s3.download_file(bucket, 'lancedb_movies.zip', zip_path)
            shutil.unpack_archive(zip_path, base_dir)
            os.remove(zip_path)
            logger.info("Đã giải nén database thành công.")
        except Exception as e:
            logger.error(f"Lỗi khi tải/giải nén từ R2: {e}")
            raise e
    return db_path

def get_db_table(table_name: str):
    lancedb_uri = ensure_lancedb_ready()
    db = lancedb.connect(lancedb_uri)
    return db.open_table(table_name)

def get_overall_health() -> Dict[str, Any]:
    """Kiểm tra tổng quan hệ thống dựa trên sự tồn tại của bảng 'movies'."""
    try:
        tbl = get_db_table("movies")
        count = tbl.count_rows()
        status = "green" if count > 0 else "red"
        return {
            "overall_status": status, 
            "movies_count": count, 
            "timestamp": datetime.datetime.now().isoformat()
        }
    except Exception as e:
        return {"overall_status": "red", "error": str(e)}

def get_quality_report() -> Dict[str, Any]:
    """Báo cáo chất lượng dữ liệu từ bảng 'movies'."""
    try:
        tbl = get_db_table("movies")
        count = tbl.count_rows()
        schema = tbl.schema
        
        dim = 0
        if count > 0:
            row = tbl.head(1)
            vector_data = row['vector'].to_pylist()
            if vector_data and len(vector_data[0]) > 0:
                dim = len(vector_data[0])
        
        return {
            "status": "passed" if count > 0 else "failed",
            "total_movies": count,
            "columns": schema.names,
            "vector_dimension": dim
        }
    except Exception as e:
        return {"status": "failed", "error": str(e)}

def get_pipeline_status() -> Dict[str, Any]:
    """Kiểm tra trạng thái pipeline thông qua file trên S3/R2."""
    try:
        s3 = get_s3_client()
        bucket = os.environ.get('S3_BUCKET_NAME', 'movie-mlops')
        res = s3.head_object(Bucket=bucket, Key='lancedb_movies.zip')
        return {
            "status": "operational", 
            "last_updated": res['LastModified'].strftime('%Y-%m-%d %H:%M:%S')
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
