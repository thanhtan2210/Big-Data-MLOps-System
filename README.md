# Big Data-driven Movies Recommendation System with MLOps

Dự án xây dựng hệ thống gợi ý phim quy mô lớn sử dụng kiến trúc Lakehouse (Delta Lake), Spark Streaming và quy trình MLOps hiện đại.

---

## 🚀 Hướng dẫn vận hành (Quick Start)

### 1. Chuẩn bị môi trường
*   Cài đặt **Python 3.10+**.
*   Cài đặt **Java 11** (JDK 11) và thiết lập `JAVA_HOME`.
*   Cài đặt **Docker Desktop**.
*   Tải `winutils.exe` vào `C:\hadoop\bin` (đối với Windows).

### 2. Cài đặt thư viện
```powershell
pip install -r requirements.txt
pip install python-dotenv setuptools wheel
```

### 3. Khởi chạy hạ tầng (Infrastructure)
```powershell
cd infra
docker-compose up -d
```

### 4. Khởi tạo dữ liệu & Bucket
```powershell
$env:PYTHONPATH="."
python src/utils/setup_minio.py
```

### 5. Chạy luồng dữ liệu (Data Pipeline)
Mở các Terminal riêng biệt cho mỗi lệnh:
*   **Producer:** `python src/ingestion/kafka_producer.py` (Đẩy dữ liệu vào Kafka).
*   **Streaming Pipeline:** `python src/pipelines/bronze_to_silver.py` (Làm sạch dữ liệu vào Delta Lake).
*   **Feature Engineering:** `python src/pipelines/silver_to_gold.py` (Tính toán đặc trưng).

### 6. Khởi chạy Dashboard & API
*   **BentoML Serving:** `bentoml serve src/serving/service.py:svc --reload`
*   **Streamlit UI:** `streamlit run src/ui/main.py`

---

## 🛠 Công nghệ sử dụng
*   **Processing:** Apache Spark, Spark Structured Streaming.
*   **Storage:** MinIO (S3), Delta Lake (Medallion Architecture).
*   **MLOps:** Feast (Feature Store), MLflow (Model Registry).
*   **Serving:** BentoML, LanceDB (Vector Search).
*   **UI:** Streamlit.
