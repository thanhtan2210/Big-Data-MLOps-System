# Thiết kế chi tiết cho Giao diện Web Người dùng (User Web Application)

Tài liệu này phác thảo các thành phần và tính năng cần thiết để phát triển một ứng dụng Web gợi ý phim chuyên nghiệp, kết nối trực tiếp với hệ thống Big Data Backend.

---

## 1. Cấu trúc trang Web (Web Architecture)

*   **Frontend:** React.js / Next.js (Cho hiệu năng cao và SEO tốt).
*   **Backend API:** FastAPI / Node.js (Để truy xuất thông tin chi tiết phim từ metadata DB).
*   **AI Serving:** BentoML (Hệ thống gợi ý mà chúng ta đã xây dựng).
*   **Event Collector:** Một API nhỏ để đẩy hành động của người dùng (clicks, views) vào Kafka.

---

## 2. Các trang chức năng chính (Main Pages)

### 2.1 Trang Chủ (Home Page)
*   **Hero Section:** Các bộ phim đang thịnh hành (Trending) lấy từ Gold Layer của Delta Lake.
*   **Personalized Carousel:** Các dải phim gợi ý riêng cho từng User (Gọi API từ BentoML).
*   **Genre Explorer:** Tìm kiếm phim theo thể loại (Action, Sci-Fi, ...).

### 2.2 Trang Chi tiết Phim (Movie Detail Page)
*   **Thông tin chi tiết:** Tên phim, đạo diễn, năm sản xuất, mô tả nội dung.
*   **Trailer:** Tích hợp video trailer từ YouTube API.
*   **Similar Movies:** Danh sách các phim tương tự (Gọi Vector Search từ LanceDB).

### 2.3 Trang Tìm kiếm (Search Page)
*   **Semantic Search:** Cho phép người dùng tìm kiếm bằng ngôn ngữ tự nhiên (Ví dụ: "Phim về vũ trụ nhưng phải có yếu tố hài hước").

---

## 3. Các thành phần Big Data & MLOps (The "Magic" Part)

### 3.1 Tracking System (Feedback Loop)
Đây là phần biến trang Web thành một hệ thống Big Data:
*   Mỗi khi người dùng click vào một bộ phim, Frontend sẽ gửi một sự kiện `movie_click` kèm theo `user_id` và `movie_id` về hệ thống.
*   Dữ liệu này được đẩy vào **Kafka topic `user_interactions`**.
*   Spark Streaming sẽ ngay lập tức tính toán lại sở thích người dùng và cập nhật vào Feature Store (Feast).

### 3.2 Cold Start Handling
*   Đối với người dùng mới (chưa có lịch sử), trang Web sẽ hiển thị form khảo sát nhanh sở thích (thể loại phim yêu thích) để nạp dữ liệu ban đầu cho Feast.

### 3.3 A/B Testing
*   Trang Web có thể phân chia người dùng thành 2 nhóm: Nhóm A nhận gợi ý từ mô hình cũ, Nhóm B nhận gợi ý từ mô hình mới để so sánh tỷ lệ Click-Through Rate (CTR).

---

## 4. Công nghệ đề xuất cho Frontend
*   **Framework:** Next.js (Dễ dàng tích hợp SSR - Server Side Rendering).
*   **Styling:** Tailwind CSS (Nhanh và hiện đại).
*   **State Management:** Redux Toolkit / React Query (Quản lý dữ liệu từ API).
*   **Analytics:** Mixpanel / Google Analytics (Để giám sát hành vi người dùng).
