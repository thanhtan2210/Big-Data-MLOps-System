# Mối quan hệ giữa Giao diện (Streamlit) và Kiến trúc Big Data (Lakehouse)

Tài liệu này giải thích cách thức giao diện Streamlit (`web_approach3.md`) hiện thực hóa và trình diễn sức mạnh của kiến trúc Big Data Lakehouse (`total_approach.md`). Giao diện không chỉ là nơi hiển thị kết quả mà còn là một **Trung tâm điều hành (Control Tower)** để giám sát toàn bộ luồng dữ liệu.

---

## 1. Sự đồng nhất về Kỹ thuật (Chìa khóa & Ổ khóa)

`web_approach3.md` đóng vai trò là "Bảng điều khiển trực quan" cho các thành phần Big Data phức tạp:

*   **Hệ thống AI (Two-Stage Funnel):** 
    *   `total_approach.md`: Định nghĩa quy trình Retrieval & Ranking.
    *   `web_approach3.md`: Trình diễn hiệu ứng "Phễu lọc" (Funnel). Người dùng thấy được danh sách 100 ứng viên từ Retrieval trước khi mô hình Ranking chọn ra Top 10.
*   **Hạ tầng Big Data (Medallion Monitoring):** 
    *   `total_approach.md`: Sử dụng Bronze, Silver, Gold trên Delta Lake.
    *   `web_approach3.md`: Trang 4 hiển thị trực tiếp số lượng bản ghi và trạng thái của từng tầng dữ liệu trên MinIO.
*   **Quản trị dữ liệu (Data Governance):** 
    *   `total_approach.md`: Thiết lập Data Quality Gate.
    *   `web_approach3.md`: Hiển thị báo cáo về dữ liệu lỗi (Dead Letter Queue) và tỷ lệ dữ liệu sạch.

---

## 2. Chi tiết các Trang Dashboard theo hướng Big Data

### Trang 2: Recommendation Engine (Trái tim của hệ thống)
*   **Visual Retrieval:** Hiển thị kết quả từ LanceDB (Vector Search). Chứng minh khả năng tìm kiếm ngữ nghĩa với độ trễ cực thấp (< 5ms).
*   **Ranking Insight:** Hiển thị điểm số dự đoán của mô hình Ranking (DeepFM) cho từng phim.
*   **AI Explanation (Bonus):** Tích hợp LLM để giải thích lý do gợi ý dựa trên đặc trưng người dùng (lấy từ Feast).

### Trang 3: AI Chatbot & Semantic Search
*   **Context-Aware Chat:** Chatbot truy vấn trực tiếp vào Feature Store (Feast) để biết sở thích hiện tại của người dùng.
*   **Multi-modal Search:** Demo khả năng tìm kiếm phim bằng mô tả tự nhiên (ví dụ: "Phim về du hành thời gian có cái kết buồn").

### Trang 4: Big Data & System Monitor (Trọng tâm kỹ thuật)
Đây là trang quan trọng nhất để trình diễn năng lực Big Data của dự án:
*   **Real-time Stream:** Biểu đồ hiển thị tốc độ dữ liệu từ Kafka (Throughput) và các cửa sổ thời gian (Windowing) của Spark.
*   **Medallion Health:** 
    *   *Bronze Status:* Dữ liệu thô vừa cập nhật.
    *   *Silver Status:* Kết quả sau khi chạy Quality Gate (số bản ghi hợp lệ/lỗi).
    *   *Gold Status:* Các bảng đặc trưng đã được tối ưu hóa (Z-Order).
*   **Delta Lake Insights:** Hiển thị lịch sử phiên bản (Time Travel) và hiệu quả của việc chạy `OPTIMIZE`.

---

## 3. Vai trò của Feast Feature Store trên UI

Trên giao diện, sự hiện diện của Feast được cụ thể hóa qua:
*   **User Profile Live:** Hiển thị các đặc trưng thực tế của người dùng đang đăng nhập (ví dụ: "Thể loại yêu thích 7 ngày qua: Sci-Fi (80%)").
*   **Training-Serving Alignment:** Một phần nhỏ so sánh giá trị đặc trưng lúc huấn luyện và lúc dự đoán thực tế để chứng minh tính nhất quán của hệ thống.

---

## 4. Tổng kết sự tương quan

| Thành phần Big Data | total_approach.md (Engine) | web_approach3.md (Visual) |
| :--- | :--- | :--- |
| **Medallion Architecture** | Pipeline Bronze -> Silver -> Gold | Dashboard theo dõi từng tầng dữ liệu |
| **Data Quality** | Bộ quy tắc Great Expectations | Báo cáo tỷ lệ dữ liệu sạch/lỗi |
| **Streaming** | Spark Windowing & Watermarking | Biểu đồ lưu lượng thời gian thực |
| **Vector DB** | LanceDB Columnar Indexing | Tính năng Semantic Search tốc độ cao |
| **Time Travel** | Versioning trên Delta Lake | Nút bấm "Xem dữ liệu trong quá khứ" |

**Kết luận:** Với cách tiếp cận này, dự án của bạn không chỉ là một ứng dụng gợi ý phim đơn thuần mà là một bài toán **Data Engineering** thực thụ, đáp ứng đầy đủ các tiêu chuẩn vận hành dữ liệu lớn hiện nay.
