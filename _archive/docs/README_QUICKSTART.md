# Movie Recommender System - Module Overview

Hệ thống gợi ý phim tích hợp AI (Gemini), Vector Search (LanceDB) và MLOps Pipeline (Spark, Delta Lake, MLflow, BentoML).

## 📂 Danh sách các file Python và Chức năng

### 1. Ingestion & Pipelines (`src/ingestion/`, `src/pipelines/`)
- `kafka_producer.py`: Giả lập nguồn dữ liệu streaming, gửi các event đánh giá phim (ratings) vào Kafka.
- `bronze_to_silver.py`: (Spark Streaming) Đọc dữ liệu từ Kafka, làm sạch và lưu vào Delta Lake (Silver Layer) trên MinIO.
- `silver_to_gold.py`: (Spark Batch) Tổng hợp dữ liệu từ Silver Layer để tạo ra các tập đặc trưng (features) cho User và Movie, lưu vào Gold Layer.

### 2. Feature Engineering & Embedding (`src/features/`)
- `feature_definition.py`: (Dự kiến) Định nghĩa các feature view cho Feast Feature Store.
- `generate_text_embeddings.py`: Lấy metadata từ TMDB API, kết hợp với dữ liệu MovieLens và sử dụng `SentenceTransformer` để sinh vector embeddings cho mô tả phim.

### 3. Model Training (`src/models/`)
- `train_retrieval.py`: Huấn luyện mô hình Two-Tower (User Tower) để thực hiện tác vụ Retrieval, quản lý và lưu trữ mô hình bằng MLflow.

### 4. Serving Layer (`src/serving/`)
- `semantic_search.py`: Engine tìm kiếm ngữ nghĩa sử dụng LanceDB. Cho phép tìm kiếm phim dựa trên vector similarity từ mô tả văn bản.
- `chatbot.py`: AI Chatbot sử dụng Google Gemini. Tích hợp Function Calling để tự động gọi các công cụ tìm kiếm và gợi ý phim.
- `service.py`: (BentoML Service) API Gateway chính của hệ thống, expose các endpoint `/recommend` và `/chat`, kết nối với MLflow và Chatbot.

### 5. User Interface & Utils (`src/ui/`, `src/utils/`)
- `main.py`: Giao diện người dùng web xây dựng bằng Streamlit, cho phép người dùng chat với AI và nhận gợi ý phim.
- `spark_session.py`: Utility để cấu hình và khởi tạo Spark Session kết nối với MinIO và Delta Lake.
- `setup_minio.py`: Script khởi tạo các bucket cần thiết trên MinIO (bronze, silver, gold, mlflow).

---
*Ghi chú: Hệ thống yêu cầu các dịch vụ nền (Docker Compose) như Kafka, MinIO, MLflow và LanceDB phải đang chạy.*
