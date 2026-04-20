# Hệ thống Gợi ý Phim Big Data: Kiến trúc Lakehouse & Two-Tower (Retrieval & Ranking)

Tài liệu này tổng hợp toàn diện giải pháp hiện thực hệ thống gợi ý phim quy mô lớn, tập trung vào sức mạnh xử lý của **Kiến trúc Lakehouse (Medallion)** và mô hình **Two-Tower**. Đây là kiến trúc tối ưu cho hiệu suất thời gian thực, khả năng mở rộng (scalability) và quản trị dữ liệu chặt chẽ theo tiêu chuẩn công nghiệp.

---

## 1. Tổng quan Kiến trúc (High-Level Architecture)

Hệ thống sử dụng mô hình **Lakehouse** thống nhất trên nền tảng **Delta Lake**, loại bỏ sự tách biệt giữa Batch và Streaming (Lambda). Toàn bộ vòng đời dữ liệu được quản lý qua kiến trúc **Medallion**, đảm bảo tính nhất quán ACID và khả năng khôi phục (Time Travel).

### Các trụ cột công nghệ chính:
*   **Storage (Lakehouse):** MinIO + Delta Lake (Quản lý dữ liệu theo tầng Bronze, Silver, Gold).
*   **Processing:** Apache Spark (Unified Engine cho cả Batch, Streaming và Feature Engineering).
*   **Data Governance:** Kiểm soát chất lượng dữ liệu (Data Quality Gate) và truy xuất vết (Lineage).
*   **MLOps & Feature Store:** Feast (Online/Offline Store) + MLflow (Model Lifecycle).
*   **Vector Search:** LanceDB (Tối ưu hóa Indexing dựa trên Columnar Storage trên MinIO).

---

## 2. Chi tiết các lớp xử lý (Deep-dive into Big Data)

### 2.1 Lớp Thu thập & Quản trị (Ingestion & Medallion Architecture)
Hệ thống tổ chức dữ liệu thành 3 tầng để tối ưu hóa việc quản lý:
*   **Bronze (Raw Layer):** Lưu trữ dữ liệu thô từ **Kafka** (Clicks, Ratings, Views) dưới dạng Parquet/Delta. Giữ nguyên trạng dữ liệu để có khả năng tái xử lý (Reprocessing).
*   **Silver (Cleaned & Augmented Layer):** 
    *   **Data Quality Gate:** Sử dụng các bộ quy tắc (Expectations) để lọc bỏ dữ liệu lỗi, null hoặc sai định dạng. 
    *   **Schema Evolution:** Tự động cập nhật cấu trúc bảng khi dữ liệu đầu vào thay đổi.
*   **Gold (Aggregated Layer):** Các bảng đã được tối ưu hóa (Z-Order theo `userId`, `movieId`) để phục vụ việc huấn luyện mô hình và báo cáo với tốc độ cao nhất.

### 2.2 Lớp Xử lý Đặc trưng thời gian thực (Real-time Feature Engineering)
Sử dụng **Spark Structured Streaming** để tính toán đặc trưng động:
*   **Windowed Operations:** Tính toán các chỉ số trong cửa sổ thời gian (ví dụ: Xu hướng xem phim trong 15 phút, 1 giờ, 24 giờ).
*   **Watermarking:** Xử lý dữ liệu đến muộn (Late-arriving data) từ Kafka, đảm bảo tính chính xác của các phép hợp nhất (Aggregations).
*   **Feast Integration:** Các đặc trưng sau khi tính toán được đẩy đồng thời vào **Offline Store** (Delta Lake) để training và **Online Store** (Redis/Sqlite) để phục vụ dự đoán tức thì.

### 2.3 Mô hình Gợi ý 2 giai đoạn (Two-Stage Recommendation)
1.  **Giai đoạn 1 - Retrieval (Two-Tower Model):** 
    *   Huấn luyện User/Item Tower để tạo Embeddings.
    *   **LanceDB Indexing:** Sử dụng kỹ thuật **Disk-based Indexing (IVF-PQ)** trực tiếp trên MinIO. Cho phép truy xuất 100 ứng viên từ hàng triệu phim với độ trễ < 5ms mà không tốn nhiều RAM.
2.  **Giai đoạn 2 - Ranking (DeepFM/XGBoost):** 
    *   Sử dụng đặc trưng từ Feast để xếp hạng lại ứng viên dựa trên ngữ cảnh thực tế của người dùng.

### 2.4 Quản trị hệ thống (Data Operations & MLOps)
*   **Time Travel:** Tận dụng khả năng lưu trữ version của Delta Lake để quay ngược thời gian (Audit) hoặc tái hiện lại tập dữ liệu huấn luyện tại một thời điểm bất kỳ.
*   **Optimized Performance:** Thực hiện định kỳ các lệnh `OPTIMIZE` và `VACUUM` để dọn dẹp file nhỏ, tăng hiệu suất IO cho Big Data.

---

## 3. Quy trình luồng dữ liệu & Vòng đời MLOps (End-to-End Workflow)

Hệ thống không vận hành theo một đường thẳng mà theo một vòng lặp khép kín để tối ưu hóa hiệu suất Big Data:

1.  **Data Source (Nguồn):** Kafka (Real-time events) & CSV/Parquet (Historical data).
2.  **Ingestion & ETL (Medallion):** Spark xử lý dữ liệu qua các tầng Bronze (Raw), Silver (Cleaned), Gold (Aggregated).
3.  **Lakehouse & Feature Store:** 
    *   **Delta Lake:** Lưu trữ dữ liệu lớn bền vững, hỗ trợ ACID.
    *   **Feast:** Cung cấp đặc trưng "Point-in-time" cho Training và "Low-latency" cho Serving.
4.  **Model Lifecycle (MLOps):** 
    *   **Training:** Huấn luyện Two-Tower Model trên Spark/TensorFlow.
    *   **Tracking:** Ghi lại mọi thí nghiệm (Hyperparameters, Metrics) trên MLflow.
    *   **Registry:** Quản lý và phê duyệt phiên bản mô hình tốt nhất (Staging/Production).
5.  **Serving & AI:** Triển khai mô hình (BentoML/Ray Serve) kết hợp với **LanceDB** để phục vụ yêu cầu gợi ý thời gian thực.
6.  **Dashboard & Monitoring:** 
    *   Hiển thị kết quả gợi ý và các chỉ số hệ thống (Streamlit).
    *   Giám sát chất lượng dữ liệu và độ lệch mô hình (Drift Detection).
7.  **Feedback Loop:** Hành động của người dùng trên Dashboard (Click/Rate) được đẩy ngược lại **Kafka**, tạo thành dòng dữ liệu mới để cải thiện mô hình liên tục.

---

## 4. Tóm tắt Stack Công nghệ Big Data

1.  **Ingestion:** Kafka.
2.  **Lakehouse Storage:** MinIO + Delta Lake.
3.  **Unified Processing:** Apache Spark.
4.  **Feature Management:** Feast.
5.  **Vector Intelligence:** LanceDB.
6.  **Pipeline Orchestration:** MLflow + (Airflow/Prefect - tùy chọn).

---

## 5. So sánh ưu điểm về khía cạnh Big Data

| Thành phần | Kiến trúc truyền thống | Kiến trúc Big Data Lakehouse |
| :--- | :--- | :--- |
| **Tính nhất quán** | Dễ mất đồng bộ giữa Batch/Stream | ACID hoàn toàn trên Delta Lake |
| **Quản trị dữ liệu** | Khó kiểm soát chất lượng thô | Medallion (Bronze/Silver/Gold) + Quality Gate |
| **Xử lý đặc trưng** | Độ trễ cao (tính theo giờ) | Windowing & Watermarking (tính theo giây) |
| **Khả năng tái hiện** | Khó (Data Overwrite) | Time Travel (Version control cho Data) |
| **Hiệu suất lưu trữ** | Phụ thuộc vào RAM (Vector DB) | Disk-based Indexing (LanceDB trên MinIO) |
| **Mở rộng (Scaling)** | Khó khăn khi dữ liệu lớn | Tối ưu hóa file (Z-Order, Optimize) |
