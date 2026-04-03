# Hệ thống Gợi ý Phim Big Data: Kiến trúc Lakehouse & Two-Tower (Retrieval & Ranking)

Tài liệu này tổng hợp toàn diện giải pháp hiện thực hệ thống gợi ý phim quy mô lớn, chuyển dịch từ kiến trúc Lambda và mô hình GNN truyền thống sang mô hình **Two-Tower** chạy trên nền tảng **Lakehouse**. Đây là kiến trúc tối ưu cho hiệu suất thời gian thực và sát với thực tế công nghiệp (Netflix, YouTube).

---

## 1. Tổng quan Kiến trúc (High-Level Architecture)

Thay vì tách biệt hoàn toàn Batch và Streaming (Lambda), hệ thống sử dụng mô hình **Lakehouse** thống nhất trên nền tảng **Delta Lake**, giúp đơn giản hóa việc quản lý dữ liệu và đảm bảo tính nhất quán ACID cho toàn bộ Pipeline.

### Các trụ cột công nghệ chính:
*   **Storage (Lakehouse):** MinIO + Delta Lake (thay thế PostgreSQL cho dữ liệu trung gian).
*   **Processing:** Apache Spark (Unified Batch & Streaming).
*   **MLOps & Feature Store:** Feast (Quản lý đặc trưng) + MLflow (Quản lý mô hình).
*   **Recommendation Engine:** Quy trình 2 giai đoạn (Retrieval & Ranking).
*   **Vector Search:** LanceDB (Serverless Vector DB lưu trên MinIO).

---

## 2. Chi tiết các lớp xử lý

### 2.1 Lớp Thu thập & Lưu trữ (Ingestion & Storage)
*   **Kafka (Confluent):** Thu thập các sự kiện Click, View, Rating từ người dùng theo thời gian thực.
*   **MinIO + Delta Lake:** 
    *   Sử dụng thay cho kiến trúc Lambda truyền thống. Toàn bộ dữ liệu "Bronze" (thô), "Silver" (làm sạch), "Gold" (đặc trưng) đều nằm trên MinIO dưới dạng các bảng Delta.
    *   **Lý do:** Cho phép Spark đọc/ghi dữ liệu đồng thời với tính chất ACID, loại bỏ "silos" dữ liệu và giảm chi phí vận hành server DB riêng.

### 2.2 Lớp Xử lý & Đặc trưng (Feature Engineering & Feature Store)
*   **Apache Spark:** Thực hiện tính toán các đặc trưng (Features) như:
    *   *User Features:* Trung bình rating 24h/7 ngày, thể loại yêu thích nhất, xu hướng tương tác gần đây.
    *   *Movie Features:* Độ phổ biến, điểm đánh giá trung bình, metadata nhúng.
*   **Feast (Feature Store):** 
    *   Đóng vai trò là kho lưu trữ đặc trưng trung tâm. 
    *   **Lý do:** Giải quyết vấn đề "Training-Serving Skew" (sai lệch dữ liệu giữa lúc huấn luyện và dự đoán thực tế). Đảm bảo mô hình luôn truy cập được đặc trưng mới nhất với độ trễ thấp.

### 2.3 Mô hình Gợi ý 2 giai đoạn (Two-Stage Recommendation)
Thay thế GNN (MARGO) phức tạp bằng quy trình 2 giai đoạn tiêu chuẩn:

1.  **Giai đoạn 1 - Retrieval (Truy xuất - Two-Tower Model):**
    *   **Cơ chế:** Gồm User Tower và Item Tower (TensorFlow/PyTorch). Biến User và Movie thành các Vector Embedding.
    *   **LanceDB:** Lưu trữ Item Embeddings trực tiếp trên MinIO. Đây là Vector DB serverless, cho phép tìm ra 100 ứng viên từ hàng triệu phim trong < 5ms.

2.  **Giai đoạn 2 - Ranking (Xếp hạng - DeepFM/XGBoost):**
    *   **Cơ chế:** Lấy 100 ứng viên từ giai đoạn 1, kết hợp với đặc trưng ngữ cảnh (thời gian, thiết bị, lịch sử 5 phim gần nhất) để tính điểm số chính xác nhất cho Top 10.

### 2.4 Lớp Phục vụ & MLOps (Serving & Model Management)
*   **BentoML hoặc Ray Serve:** Đóng gói mô hình Retrieval và Ranking thành các API hiệu năng cao, hỗ trợ tự động scale.
*   **MLflow:** 
    *   **Experiment Tracking:** Theo dõi các phiên bản huấn luyện, lưu lại các chỉ số (Recall, Precision, NDCG).
    *   **Model Registry:** Quản lý vòng đời mô hình (Staging, Production) và lưu trữ Artifacts.

---

## 3. Quy trình luồng dữ liệu (Data Flow)

1.  **User Action:** Người dùng tương tác (Rate/Like) -> Đẩy sự kiện vào **Kafka**.
2.  **Streaming & Storage:** **Spark Streaming** xử lý tin nhắn từ Kafka và ghi trực tiếp vào **Delta Lake (MinIO)**.
3.  **Feature Sync:** **Spark** định kỳ tính toán đặc trưng từ Delta Lake và cập nhật vào **Feast**.
4.  **Inference (Dự đoán):**
    *   Backend nhận yêu cầu -> Lấy đặc trưng User/Context từ **Feast**.
    *   **Retrieval:** Tìm 100 phim gần nhất trong **LanceDB**.
    *   **Ranking:** Xếp hạng lại 100 phim đó bằng mô hình **DeepFM** và trả về Top 10.

---

## 4. Tóm tắt Stack Công nghệ Đề xuất

1.  **Ingestion:** Kafka.
2.  **Storage:** MinIO + Delta Lake.
3.  **Processing:** Apache Spark.
4.  **Feature Store:** Feast.
5.  **Vector Search:** LanceDB.
6.  **Model Management:** MLflow.
7.  **Serving:** BentoML hoặc Ray Serve.

---

## 5. So sánh ưu điểm so với kiến trúc cũ (Báo cáo)

| Thành phần | Bài báo cáo cũ (Lambda) | Kiến trúc mới (Lakehouse) |
| :--- | :--- | :--- |
| **Kiến trúc** | Lambda (Batch + Stream riêng) | Lakehouse (Delta Lake thống nhất) |
| **Quản lý dữ liệu** | Phức tạp (S3 + PostgreSQL) | Tối ưu (Tận dụng Object Storage MinIO) |
| **Mô hình AI** | GNN (MARGO - Khó vận hành) | Two-Tower + Ranking (Công nghiệp) |
| **Vector DB** | Milvus (Cần Server riêng) | LanceDB (Serverless trên MinIO) |
| **MLOps** | MLflow Tracking cơ bản | Feast + MLflow (Full MLOps Lifecycle) |
| **Độ trễ** | Trung bình | Cực thấp (< 5ms cho Retrieval) |