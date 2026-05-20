# Troubleshooting: Hướng dẫn xử lý lỗi hệ thống

Tài liệu này tổng hợp các vấn đề kỹ thuật phát sinh trong quá trình phát triển và vận hành dự án, kèm theo các giải pháp đã được thực hiện. Đây là cẩm nang cực kỳ hữu ích cho người mới khi setup dự án trên môi trường Windows.

---

## 1. Lỗi PySpark trên Windows

### Vấn đề: HADOOP_HOME and winutils.exe
*   **Triệu chứng:** Khi chạy code Spark, console báo lỗi đỏ rực `java.io.FileNotFoundException: HADOOP_HOME and hadoop.home.dir are unset`.
*   **Nguyên nhân:** PySpark cần các công cụ nhị phân của Hadoop (`winutils.exe`, `hadoop.dll`) để hoạt động và giả lập quyền truy cập file trên môi trường Windows. (Bản chất Spark được sinh ra cho hệ sinh thái Linux).
*   **Giải pháp:** Dự án đã thiết lập tự động chèn thư mục Hadoop ảo qua file `.env` hoặc bạn cần tự tải `winutils.exe` tương ứng và cấu hình HADOOP_HOME.

### Vấn đề: ConnectionResetError [WinError 10054]
*   **Triệu chứng:** Khi Spark Session đang khởi tạo thì bị ngắt kết nối đột ngột, Py4J (Cầu nối giữa Python và Java) báo lỗi Network.
*   **Nguyên nhân:** Khi sử dụng Java 17+, JVM thắt chặt quyền truy cập bộ nhớ nội bộ, khiến Spark không thể giao tiếp bình thường.
*   **Giải pháp:** Đã thêm dòng cấu hình `--add-opens=java.base/sun.nio.ch=ALL-UNNAMED` vào thiết lập `spark.driver.extraJavaOptions` trong file `src/utils/spark_session.py`.

---

## 2. Lỗi MLflow & BentoML Backend

### Vấn đề: RESOURCE_DOES_NOT_EXIST khi BentoML khởi động
*   **Triệu chứng:** Khi chạy BentoServer, log hiển thị lỗi: `mlflow.exceptions.RestException: RESOURCE_DOES_NOT_EXIST: Registered Model with name=user_tower_model not found`. Hệ thống Backend không thể start hoàn toàn.
*   **Nguyên nhân:** File `service.py` của BentoML được lập trình để ưu tiên kéo mô hình đã được đăng ký (Registered Model) có tên `user_tower_model` từ thư viện MLflow. Tuy nhiên, nếu bạn vừa tải dự án về, trên MLflow chưa có mô hình nào tồn tại.
*   **Giải pháp:** Bạn phải chạy script huấn luyện ít nhất 1 lần để hệ thống train và đẩy mô hình lên MLflow trước:
    ```bash
    python src/models/train_retrieval.py
    ```

### Vấn đề: Lỗi gõ phím / UnicodeEncodeError
*   **Triệu chứng:** Khi chạy BentoML hoặc các script có log ra terminal của Windows, app bị crash với lỗi liên quan đến Unicode (ví dụ: `UnicodeEncodeError: 'charmap' codec can't encode character...`).
*   **Nguyên nhân:** Mặc định Command Prompt hoặc Powershell trên một số máy Windows (sử dụng mã hóa cp1252) không hỗ trợ in các ký tự Emoji (✅, ⚠️, 🚀) hoặc tiếng Việt có dấu.
*   **Giải pháp:** Các file log (như `service.py`) đã được chỉnh sửa để xóa bỏ emoji và thay bằng tiếng Anh thuần ASCII để đảm bảo an toàn và tính tương thích trên mọi nền tảng.

---

## 3. Lỗi Data Pipeline (Dữ liệu bị rỗng)

### Vấn đề: PATH_NOT_FOUND (Delta Lake)
*   **Triệu chứng:** Khi chạy script tự động `run_e2e_pipeline.py`, console báo lỗi không tìm thấy bảng ở tầng Silver hoặc Gold.
*   **Nguyên nhân:** Xảy ra hiện tượng "Chạy đua" (Race condition). Script yêu cầu đọc bảng Silver/Gold trong khi công nhân Spark Streaming chưa kịp lấy dữ liệu từ Kafka và ghi batch dữ liệu đầu tiên xuống ổ cứng MinIO.
*   **Giải pháp:** Script `run_e2e_pipeline.py` đã được nâng cấp. Thay vì chạy nối tiếp từng bước, nó khởi chạy các dịch vụ dưới dạng Background Processes (chạy ngầm). Kafka producer sẽ liên tục đẩy dữ liệu, giúp Spark có thời gian xử lý và tạo file vật lý ổn định. Mọi thứ vận hành đồng bộ và chịu lỗi tốt hơn.