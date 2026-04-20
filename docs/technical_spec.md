# Technical Specification: Hệ thống Gợi ý Phim Big Data Lakehouse

Tài liệu này định nghĩa chi tiết các thành phần kỹ thuật, cấu trúc dữ liệu và quy trình xử lý cho hệ thống gợi ý phim.

---

## 1. Mô hình Thực thể Dữ liệu (Data Entities)

Hệ thống xoay quanh 3 thực thể chính:
*   **User:** `user_id`, `gender`, `age`, `occupation`, `zip_code`.
*   **Movie:** `movie_id`, `title`, `genres` (dạng list), `release_year`, `embeddings` (vector 128-dim).
*   **Interaction (Event):** `user_id`, `movie_id`, `rating`, `timestamp`, `event_type` (click, view, rate).

---

## 2. Chi tiết kiến trúc Medallion (Delta Lake)

### 2.1 Tầng Bronze (Raw Data)
*   **Nguồn:** Kafka topic `movie_ratings`.
*   **Định dạng:** Delta Table (Append-only).
*   **Schema:** `raw_payload` (JSON), `ingestion_timestamp`, `kafka_offset`.
*   **Mục tiêu:** Lưu trữ nguyên bản dữ liệu để có thể Replay pipeline khi cần.

### 2.2 Tầng Silver (Cleaned Data)
*   **Logic xử lý:** 
    *   Parse JSON từ Bronze.
    *   **Data Quality Gate:** Loại bỏ bản ghi có `user_id` hoặc `movie_id` bị NULL; `rating` phải nằm trong khoảng [0, 5].
    *   Ép kiểu dữ liệu (Casting types).
*   **Schema:** `user_id` (Long), `movie_id` (Long), `rating` (Float), `timestamp` (Timestamp), `is_processed` (Boolean).

### 2.3 Tầng Gold (Feature/Aggregated Data)
Đây là nguồn dữ liệu cho Feature Store và Training:
*   **User_Stats_Gold:** `user_id`, `avg_rating_24h`, `favorite_genre`, `total_interactions_1h`.
*   **Movie_Stats_Gold:** `movie_id`, `avg_rating_global`, `trending_score` (tính bằng Windowing 15 phút).
*   **Optimization:** Thực hiện `Z-ORDER BY (user_id)` để tăng tốc truy vấn theo User.

---

## 3. Định nghĩa Đặc trưng (Feast Feature Store)

Hệ thống quản lý đặc trưng tập trung để tránh lệch dữ liệu (Training-Serving Skew):

### 3.1 User Features (Batch & Stream)
*   `user_recent_ratings`: Trung bình rating của user trong 7 ngày gần nhất.
*   `user_genre_preference`: Vector trọng số các thể loại phim user thường xem.

### 3.2 Movie Features (Batch)
*   `movie_metadata`: Thể loại, năm sản xuất, đạo diễn.
*   `movie_embeddings`: Vector đặc trưng trích xuất từ mô hình Item-Tower.

---

## 4. Pipeline xử lý dòng (Spark Streaming)

*   **Windowing:** Sử dụng `Tumbling Window` 15 phút để tính `trending_score` cho phim.
*   **Watermarking:** Đặt ngưỡng `10 minutes` cho dữ liệu đến muộn. Nếu event trễ hơn 10 phút so với thời gian hệ thống, nó sẽ bị loại bỏ khỏi tính toán window nhưng vẫn lưu vào Bronze.
*   **Checkpointing:** Lưu trạng thái pipeline trên MinIO để đảm bảo khả năng phục hồi lỗi (Fault-tolerance).

---

## 5. Quy trình Gợi ý (Inference Workflow)

### Bước 1: Retrieval (Candidate Generation)
1.  Nhận `user_id` từ Request.
2.  Lấy `user_embedding` từ Feast Online Store.
3.  Truy vấn **LanceDB** (Vector Search) để tìm Top 100 phim có khoảng cách Cosine gần nhất với `user_embedding`.

### Bước 2: Ranking (Scoring)
1.  Lấy danh sách 100 phim từ Bước 1.
2.  Lấy thêm các đặc trưng ngữ cảnh (Context) như: thời gian hiện tại, thiết bị.
3.  Đưa toàn bộ vào mô hình **DeepFM** (được lưu trên MLflow) để tính xác suất Click/Rate.
4.  Trả về Top 10 phim có điểm cao nhất.

---

## 6. Giám sát và Chất lượng (Observability)

*   **Data Quality Monitoring:** Theo dõi số lượng bản ghi bị loại bỏ tại tầng Silver.
*   **Model Performance Monitoring:** Theo dõi chỉ số `Recall@100` (Retrieval) và `NDCG@10` (Ranking) trên MLflow.
*   **System Health:** RAM/CPU của Spark Cluster và tốc độ phản hồi (Latency) của LanceDB.

---

## 7. Danh sách Công nghệ & Phiên bản (Dự kiến)

*   **Apache Spark:** 3.4+
*   **Delta Lake:** 2.4+
*   **Feast:** 0.31+
*   **LanceDB:** 0.1.x
*   **MLflow:** 2.x
*   **BentoML:** 1.0+

---

## 8. Model Serving & Feedback Loop (MLOps)

### 8.1 Model Serving Layer
*   **Framework:** BentoML (Đóng gói mô hình thành Docker Container).
*   **Endpoint:** `/v1/recommend/{user_id}`.
*   **Caching:** Sử dụng **Redis** để cache kết quả Top 10 của các User tích cực nhất nhằm giảm tải cho hệ thống Retrieval.

### 8.2 Feedback Loop Mechanism
*   **Event Capture:** Khi người dùng click vào phim trên Dashboard, một sự kiện `click_event` được gửi về `/v1/events`.
*   **Kafka Producer:** API nhận sự kiện và đẩy ngay vào Kafka topic `user_feedback`.
*   **Online Training (Tùy chọn):** Spark Streaming tiêu thụ `user_feedback` để cập nhật đặc trưng người dùng trong Feast Online Store ngay lập tức, giúp kết quả gợi ý tiếp theo thay đổi theo thời gian thực.
