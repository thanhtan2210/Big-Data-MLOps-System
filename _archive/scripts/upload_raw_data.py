import boto3
import os
from dotenv import load_dotenv

# Tải thông tin cấu hình từ file .env
load_dotenv()

# Khởi tạo kết nối tới Cloudflare R2 (tương thích API S3)
s3 = boto3.client('s3',
                  endpoint_url=os.getenv('AWS_ENDPOINT_URL'),
                  aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                  aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
                  )

bucket_name = os.getenv('S3_BUCKET_NAME', 'movie-mlops')

# Danh sách các file thô cần đẩy lên R2 Data Lake
files_to_upload = {
    'dataset/ml-25m/movies.csv': 'raw/movies.csv',
    'dataset/ml-25m/links.csv': 'raw/links.csv',
    'dataset/ml-25m/tags.csv': 'raw/tags.csv',
    'dataset/ml-25m/ratings.csv': 'raw/ratings.csv',            # Đã mở comment
    'dataset/ml-25m/genome-scores.csv': 'raw/genome-scores.csv',  # Thêm mới
    'dataset/ml-25m/genome-tags.csv': 'raw/genome-tags.csv'
}

print("BẮT ĐẦU ĐẨY DỮ LIỆU THÔ LÊN CLOUDFLARE R2 DATA LAKE...")
print("-" * 50)

for local_file, s3_key in files_to_upload.items():
    if os.path.exists(local_file):
        print(f"⏳ Đang đẩy {local_file} lên {bucket_name}/{s3_key}...")
        # Lệnh upload file
        s3.upload_file(local_file, bucket_name, s3_key)
        print(f"✅ Hoàn tất tải lên {local_file}!")
    else:
        print(f"❌ LỖI: Không tìm thấy file {local_file} ở máy local. Bỏ qua.")

print("-" * 50)
print("🎉 Quá trình tải dữ liệu thô lên R2 đã xong! Colab của bạn giờ đã có thể tải chúng xuống an toàn.")
