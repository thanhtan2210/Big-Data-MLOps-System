# Troubleshooting: Hướng dẫn xử lý lỗi hệ thống Big Data

Tài liệu này tổng hợp các vấn đề kỹ thuật phát sinh trong quá trình phát triển dự án và giải pháp đã thực hiện.

---

## 1. Lỗi Spark & Windows (Java Compatibility)

### Vấn đề: ConnectionResetError [WinError 10054]
*   **Triệu chứng:** Spark Session đang khởi tạo thì bị ngắt kết nối đột ngột, Py4J báo lỗi Network.
*   **Nguyên nhân:** Java 17+ thắt chặt quyền truy cập bộ nhớ (reflection), khiến Spark không thể truy cập một số vùng nhớ nội bộ của JVM.
*   **Giải pháp:** Thêm cấu hình `--add-opens` vào `spark.driver.extraJavaOptions` trong file `src/utils/spark_session.py`.

### Vấn đề: HADOOP_HOME and winutils.exe
*   **Triệu chứng:** Lỗi `java.io.FileNotFoundException: HADOOP_HOME and hadoop.home.dir are unset`.
*   **Nguyên nhân:** Windows thiếu các file nhị phân của Hadoop để giả lập quyền hạn Linux.
*   **Giải pháp:** Tải `winutils.exe` và nạp tự động qua file `.env` và `os.environ` trong code.

---

## 2. Lỗi MLOps (Library Conflicts)

### Vấn đề: Pydantic 2.x Incompatibility
*   **Triệu chứng:** Lỗi `@root_validator` khi import `mlflow`.
*   **Nguyên nhân:** MLflow (bản ổn định) vẫn dùng Pydantic v1, trong khi môi trường mới tự động cài v2.
*   **Giải pháp:** Khóa phiên bản `pydantic<2.0.0` trong `requirements.txt`.

### Vấn đề: ModuleNotFoundError: No module named 'pkg_resources'
*   **Triệu chứng:** Không thể chạy training.
*   **Nguyên nhân:** `setuptools` phiên bản mới (>70) đã loại bỏ `pkg_resources`.
*   **Giải pháp:** Hạ cấp xuống `setuptools<70`.

---

## 3. Lỗi Data Pipeline (Data Residency)

### Vấn đề: PATH_NOT_FOUND (Delta Lake)
*   **Triệu chứng:** Bước 4 không tìm thấy thư mục `silver/ratings`.
*   **Nguyên nhân:** Race condition - Spark Streaming bị giết (kill) trước khi kịp ghi batch dữ liệu đầu tiên xuống MinIO.
*   **Giải pháp:** Tăng thời gian chờ cho Spark Streaming lên 120 giây và thêm log thời gian thực để giám sát.

---

## 4. Lỗi hiển thị Windows
*   **Vấn đề:** UnicodeEncodeError (Emoji lỗi).
*   **Giải pháp:** Thay thế toàn bộ Emoji bằng text thuần túy trong các file log và script chạy terminal.
