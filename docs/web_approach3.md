# Mối quan hệ giữa Giao diện (web_approach3) và Kiến trúc (total_approach)

Tài liệu này giải thích cách thức bản thiết kế giao diện Streamlit (`web_approach3.md`) hiện thực hóa và bổ trợ cho kiến trúc hệ thống tổng thể (`total_approach.md`), đảm bảo tính thống nhất cho dự án của team 2 người.

---

## 1. Sự đồng nhất về Kỹ thuật (Chìa khóa & Ổ khóa)

`web_approach3.md` không làm thay đổi kế hoạch trong `total_approach.md` mà đóng vai trò là "Bảng điều khiển" (Dashboard) để trình diễn "Bộ máy" (Engine) bên dưới:

*   **Hệ thống AI:** 
    *   `total_approach.md` chọn **Two-Tower + Ranking**.
    *   `web_approach3.md` thiết kế Trang 2 để trình diễn đúng quy trình 2 giai đoạn này: Lấy 50-100 phim ứng viên (Retrieval) và xếp hạng lại chọn ra Top 10 (Ranking).
*   **Hạ tầng Big Data:** 
    *   `total_approach.md` sử dụng **Kafka, Spark, Delta Lake**.
    *   `web_approach3.md` tạo Trang 4 (Monitoring) để soi trực tiếp vào dòng dữ liệu thời gian thực và trạng thái lưu trữ ACID trên MinIO.
*   **Lưu trữ Vector:** 
    *   `total_approach.md` chọn **LanceDB**.
    *   `web_approach3.md` hiện thực hóa nó thành tính năng "Tìm kiếm thông minh" dựa trên ngữ nghĩa (Semantic Search) ở Trang 2.

---

## 2. Điểm nhấn về quy trình Two-Tower + Ranking

Mô hình Two-Tower và Ranking xuất hiện xuyên suốt trong cả hai tài liệu vì đây là linh hồn của hệ thống:

1.  **Giai đoạn 1 - Retrieval (Two-Tower):** Dùng để tìm nhanh các phim "có vẻ" liên quan từ hàng triệu phim trong LanceDB. Đầu ra này sẽ được hiển thị ở Trang 2 dưới dạng danh sách ứng viên.
2.  **Giai đoạn 2 - Ranking (DeepFM/XGBoost):** Dùng để soi xét kỹ danh sách ứng viên và chọn ra Top 10 phim "đỉnh nhất". Đây là kết quả cuối cùng mà người dùng nhìn thấy trên giao diện.

Việc trình diễn cả 2 bước này giúp giảng viên thấy bạn đang xây dựng một hệ thống gợi ý đa tầng đúng chuẩn công nghiệp (Netflix, YouTube).

---

## 3. Vai trò của Chatbot AI (Trang 3)

Trong `total_approach.md`, Chatbot được coi là một phần của **Serving Layer**. 
*   `web_approach3.md` cụ thể hóa thành một trang riêng biệt để bạn dễ dàng triển khai các kỹ thuật NLP (LLM, Function Calling) mà không làm phức tạp hóa các trang khác.
*   Điều này giúp "showcase" năng lực AI của bạn một cách tập trung và ấn tượng nhất.

---

## 4. Tổng kết sự tương quan

| Thành phần | total_approach.md (Bộ máy - The Engine) | web_approach3.md (Bảng điều khiển - The Dashboard) |
| :--- | :--- | :--- |
| **Nhiệm vụ** | Quy định hệ thống chạy bằng gì, dữ liệu đi đâu. | Quy định người dùng nhìn thấy gì và cách bạn demo. |
| **Dữ liệu** | Định nghĩa luồng Kafka -> Spark -> Delta Lake. | Hiển thị trực tiếp các thành phần này để chứng minh. |
| **Mô hình** | Chọn Two-Tower & Ranking Model. | Trình diễn quy trình Retrieval & Ranking 2 giai đoạn. |
| **AI Nâng cao** | Nhắc đến Serving Layer & LLM. | Hiện thực hóa thành Trang Chatbot & Semantic Search. |

**Kết luận:** Hai tài liệu này bổ trợ hoàn hảo cho nhau. Bạn có thể yên tâm giữ nguyên `total_approach.md` làm khung kiến trúc, và dùng `web_approach3.md` làm hướng dẫn để bắt tay vào code giao diện.