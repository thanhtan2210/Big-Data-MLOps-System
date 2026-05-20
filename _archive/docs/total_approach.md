# Tổng quan Kiến trúc: Hệ thống Gợi ý Phim Big Data (Dành cho người mới)

Chào mừng bạn đến với dự án Hệ thống Gợi ý Phim! Tài liệu này sẽ giúp bạn hiểu bức tranh toàn cảnh về cách các công nghệ Big Data và AI kết hợp với nhau trong thực tế.

## 1. Mục tiêu của dự án
Hệ thống này không chỉ là một ứng dụng gợi ý phim đơn giản, mà là một **Data Pipeline (Đường ống dữ liệu)** hoàn chỉnh. Chúng ta sẽ thu thập dữ liệu (ratings), lưu trữ khối lượng lớn, làm sạch, huấn luyện AI, và cuối cùng phục vụ (serve) qua một giao diện web trực quan.

## 2. Các thành phần công nghệ chính (Tech Stack)

Dự án sử dụng các công nghệ tiêu chuẩn trong ngành Data Engineering và MLOps:
*   **Thu thập dữ liệu (Ingestion):** `Kafka`. Giả lập dòng sự kiện đánh giá phim (ratings) liên tục.
*   **Lưu trữ dữ liệu (Lakehouse):** `MinIO` (Lưu trữ Object tương tự Amazon S3) + `Delta Lake` (Định dạng bảng đặc biệt cho phép cập nhật, xóa, và quay ngược thời gian).
*   **Xử lý dữ liệu (Processing):** `Apache Spark`. Xử lý hàng triệu dòng dữ liệu từ Kafka, làm sạch và lưu vào MinIO.
*   **Cơ sở dữ liệu Vector (Vector Database):** `LanceDB`. Lưu trữ các vector ngữ nghĩa (embeddings) của phim để AI có thể tìm kiếm nhanh chóng dựa trên nội dung.
*   **Quản lý Vòng đời AI (MLOps):** `MLflow`. Theo dõi quá trình huấn luyện mô hình, lưu lại các chỉ số và đóng vai trò như một kho chứa (Registry) cho mô hình tốt nhất.
*   **Phục vụ Mô hình (Model Serving):** `BentoML`. Đóng gói mô hình AI và Chatbot thành các API (Endpoint) để giao diện có thể gọi đến dễ dàng.
*   **Giao diện Người dùng (UI):** `Streamlit`. Xây dựng trang web tương tác, tích hợp Chatbot AI và danh sách phim gợi ý bằng Python.

## 3. Kiến trúc luồng dữ liệu (Data Flow)

Dự án áp dụng mô hình **Medallion Architecture (Bronze - Silver - Gold)** vô cùng phổ biến trong Data Engineering:

1.  **Tầng Bronze (Raw Data):** Dữ liệu thô từ Kafka được Spark Streaming đọc và lưu ngay lập tức vào MinIO. Mục đích là giữ lại bản gốc không chỉnh sửa để có thể dùng lại (Replay) sau này nếu cần.
2.  **Tầng Silver (Cleaned Data):** Spark đọc dữ liệu từ Bronze, tiến hành làm sạch (bỏ dữ liệu trống, lọc rating từ 0-5), và lưu thành bảng Silver. Đây là dữ liệu sạch sẵn sàng để phân tích.
3.  **Tầng Gold (Aggregated Data):** Dữ liệu từ Silver được tổng hợp (Ví dụ: tính điểm trung bình của mỗi user, của mỗi bộ phim) để làm dữ liệu chuẩn bị cho việc huấn luyện mô hình.
4.  **AI & Gợi ý (Serving):** Giao diện Streamlit gửi yêu cầu (kèm User ID) tới API BentoML. BentoML tải mô hình từ MLflow để tính toán, sau đó trả về danh sách các phim phù hợp nhất với người dùng đó.

## 4. Tại sao lại dùng kiến trúc này?
*   **Tách biệt (Decoupling):** MinIO chỉ lo lưu trữ, Spark chỉ lo tính toán. Điều này giúp hệ thống dễ dàng mở rộng (Scale).
*   **Dễ quản lý (MLOps):** Việc dùng MLflow và BentoML giúp mô hình AI không bị gắn chết vào code hệ thống. Team AI có thể độc lập huấn luyện và đẩy mô hình mới lên MLflow, và BentoML sẽ tự động lấy về chạy.
*   **Thời gian thực (Streaming):** Dùng Kafka và Spark Streaming giúp hệ thống có thể phản ứng với dữ liệu mới liên tục thay vì phải đợi chạy file tổng hợp vào cuối ngày.