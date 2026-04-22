# Big Data-driven Movies Recommendation System with MLOps

Dự án xây dựng hệ thống gợi ý phim quy mô lớn sử dụng kiến trúc Lakehouse (Delta Lake), Spark Streaming và quy trình MLOps hiện đại.

---

## 🚀 Hướng dẫn vận hành (Quick Start)

### 1. Chuẩn bị môi trường (Bắt buộc)
*   **Python:** Cài đặt **Python 3.11** (Tránh 3.12+ và 3.10- để đảm bảo tương thích thư viện AI).
*   **Java:** Cài đặt **JDK 11 hoặc 17**.
*   **Docker:** Docker Desktop phải đang chạy.
*   **Hadoop binaries:** Tải `winutils.exe` vào `C:\hadoop\bin`.

### 2. Thiết lập dự án
```powershell
# Tạo môi trường ảo bằng Python 3.11
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1

# Cài đặt thư viện
pip install -r requirements.txt
```

### 3. Khởi chạy toàn bộ hệ thống (End-to-End)
Thay vì chạy từng file thủ công, bạn chỉ cần thực hiện chu trình tự động:

1. **Bật hạ tầng:** `cd infra; docker-compose up -d`
2. **Chạy Pipeline E2E:** `python run_e2e_pipeline.py`

### 4. Kiểm tra thành quả
*   **Dashboard:** `streamlit run src/ui/main.py`
*   **MLflow UI:** `http://127.0.0.1:5000`
*   **MinIO UI:** `http://127.0.0.1:9001` (User: admin / Pass: password)

---

## 🛠 Xử lý lỗi thường gặp (Troubleshooting)
*   **Lỗi WinError 10054 (Spark crash):** Đã được xử lý tự động trong `spark_session.py` bằng cấu hình `--add-opens`.
*   **Lỗi ModuleNotFoundError (pkg_resources):** Hãy đảm bảo đã cài `setuptools<70`.
*   **Lỗi PATH_NOT_FOUND:** Thường do Spark Streaming chưa kịp ghi dữ liệu. Script E2E hiện tại đã được tăng thời gian chờ lên 120s để khắc phục.

---

## 🏗 Kiến trúc hệ thống
Chi tiết xem tại thư mục `docs/`:
1. [Kiến trúc Lakehouse & MLOps](docs/total_approach.md)
2. [Đặc tả kỹ thuật (Spec)](docs/technical_spec.md)
3. [Thiết kế Dashboard](docs/web_approach3.md)
4. [Kế hoạch phát triển Web App](docs/web_features.md)
