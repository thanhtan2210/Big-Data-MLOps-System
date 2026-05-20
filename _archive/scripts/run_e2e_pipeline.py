import subprocess
import time
import os
import sys
import signal
import socket
import shutil
from typing import List

# ==========================================
# CẤU HÌNH & TÊN FILE LOG
# ==========================================
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

PROCESSES: List[subprocess.Popen] = []


def log_header(msg: str):
    print(f"\n{'='*20} {msg} {'='*20}")


def is_port_open(port: int, host: str = "127.0.0.1") -> bool:
    """Kiểm tra xem một cổng đã sẵn sàng nhận kết nối chưa."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((host, port)) == 0


def wait_for_model_ready():
    """Kiểm tra health check để đảm bảo model đã sẵn sàng."""
    print("[WAIT] Đang kiểm tra trạng thái model trong BentoML...")
    url = "http://127.0.0.1:3000/health"
    for i in range(30):
        try:
            import requests
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get("model_loaded") is True:
                    print("✅ Model đã load thành công và sẵn sàng.")
                    return True
        except:
            pass
        print(f"  ... model đang load ({i+1}/30)...")
        time.sleep(5)
    raise RuntimeError("❌ Model không load được sau 30 lần thử!")


def cleanup_processes(sig=None, frame=None):
    """Đảm bảo tất cả các tiến trình con được đóng khi thoát."""
    print("\n[INFO] Đang đóng toàn bộ các tiến trình đang chạy ngầm...")
    for p in PROCESSES:
        try:
            # Gửi tín hiệu đóng cho Windows (taskkill) hoặc Unix (terminate)
            if os.name == 'nt':
                subprocess.run(
                    f"taskkill /F /T /PID {p.pid}", shell=True, capture_output=True)
            else:
                p.terminate()
        except:
            pass
    print("[INFO] Đã dọn dẹp xong. Tạm biệt!")
    sys.exit(0)


# Đăng ký signal handler
signal.signal(signal.SIGINT, cleanup_processes)
signal.signal(signal.SIGTERM, cleanup_processes)


def start_background_service(command: str, name: str, log_filename: str):
    """Khởi động một dịch vụ chạy ngầm và lưu log."""
    log_path = os.path.join(LOG_DIR, log_filename)
    log_file = open(log_path, "w", encoding="utf-8")

    env = os.environ.copy()
    env["PYTHONPATH"] = "."

    print(f"[STARTING] {name}...")
    process = subprocess.Popen(
        command,
        shell=True,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        env=env,
        text=True
    )
    PROCESSES.append(process)
    return process


def run_synchronous_task(command: str, name: str):
    """Chạy một tác vụ và đợi cho đến khi hoàn thành."""
    print(f"[RUNNING] {name}...")
    env = os.environ.copy()
    env["PYTHONPATH"] = "."

    result = subprocess.run(command, shell=True, env=env)
    if result.returncode == 0:
        print(f"[SUCCESS] {name} đã hoàn thành.")
        return True
    else:
        print(f"[ERROR] {name} thất bại với mã lỗi {result.returncode}.")
        return False


def cleanup_delta_transaction_logs():
    """Xóa các thư mục log dở dang của Delta Lake để tránh xung đột transaction."""
    log_paths = [
        "dataset/delta_lake/silver/ratings/_delta_log",
        "dataset/delta_lake/bronze/ratings/_delta_log"  # Thêm nếu có đường dẫn bronze
    ]
    for path in log_paths:
        if os.path.exists(path):
            print(f"[INFO] Đang dọn dẹp transaction log tại: {path}")
            shutil.rmtree(path)
        else:
            print(f"[INFO] Không tìm thấy log tại {path}, bỏ qua.")


def main():
    cleanup_delta_transaction_logs()
    log_header("BẮT ĐẦU QUY TRÌNH HỢP NHẤT (BƯỚC 3, 4, 5)")
    python_exe = sys.executable

    # --- BƯỚC 3: KHỞI ĐỘNG CÁC CỖ MÁY (Duy trì chạy ngầm) ---
    log_header("BƯỚC 3: Khởi động Dịch vụ")

    # 1. Khởi động Spark Streaming
    start_background_service(
        f'"{python_exe}" -m src.pipelines.bronze_to_silver',
        "Spark Streaming Pipeline",
        "bronze_to_silver.log"
    )

    # 2. Khởi động BentoML Serving qua Docker
    print("[STARTING] BentoML Serving (Docker)...")
    run_synchronous_task(
        f'"{python_exe}" -m bentoml build -f bentofile.yaml .',
        "BentoML Build Image"
    )
    # Tag image để map với docker-compose
    run_synchronous_task(
        f'"{python_exe}" -m bentoml containerize movie_recommender_service:latest -t bentoml_service:latest',
        "BentoML Containerize"
    )
    run_synchronous_task(
        "docker compose -f infra/docker-compose.yml up -d bentoml",
        "Docker Compose Up BentoML"
    )

    print("[WAIT] Đang chờ các dịch vụ khởi động (60 giây)...")
    # Kiểm tra cổng 3000 (BentoML) xem đã mở chưa
    for i in range(60):
        time.sleep(1)
        if is_port_open(3000):
            print(f"✅ BentoML đã sẵn sàng tại cổng 3000 sau {i} giây.")
            break
        if i % 10 == 0:
            print(f"  ... vẫn đang đợi BentoML khởi động ({i}/60s)")

    wait_for_model_ready()

    # --- BƯỚC 4: KÍCH HOẠT LUỒNG DỮ LIỆU ---
    log_header("BƯỚC 4: Đổ dữ liệu vào Kafka")
    # Chúng ta chạy producer trong background vì nó stream liên tục
    start_background_service(
        f'"{python_exe}" -m src.ingestion.kafka_producer',
        "Kafka Producer",
        "kafka_producer.log"
    )
    print("[INFO] Dữ liệu đang được stream vào Kafka.")

    # --- BƯỚC 5: KIỂM THỬ & SỬ DỤNG ---
    log_header("BƯỚC 5: Kiểm thử & Giao diện")

    # 1. Chạy Master E2E Test
    test_success = run_synchronous_task(
        f'pytest tests/test_master_e2e.py -s',
        "Master E2E Integration Test"
    )

    if test_success:
        # 2. Nếu test thành công, khởi động Streamlit
        print(
            "\n[INFO] Hệ thống hoạt động tốt! Đang khởi động giao diện người dùng...")
        start_background_service(
            f'streamlit run app.py',
            "Streamlit UI",
            "streamlit_ui.log"
        )
        print("\n🚀 GIAO DIỆN ĐÃ SẴN SÀNG!")
        print("👉 Truy cập: http://localhost:8501")
        print("\n[BẤM CTRL+C ĐỂ DỪNG TOÀN BỘ HỆ THỐNG]")

        # Giữ script sống để duy trì các dịch vụ background
        while True:
            time.sleep(1)
    else:
        print("\n❌ KIỂM THỬ THẤT BẠI. Hệ thống sẽ dừng để bạn kiểm tra log.")
        cleanup_processes()


if __name__ == "__main__":
    main()
