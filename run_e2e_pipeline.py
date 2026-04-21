import subprocess
import time
import os
import sys

# Cấu hình file log
LOG_FILE = "project_execution_report.log"

def log_output(message, file):
    print(message)
    file.write(message + "\n")
    file.flush()

def run_command(command, description, log_file, background=False, duration=None):
    log_output(f"\n{'='*20} {description} {'='*20}", log_file)
    
    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    
    if background:
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)
        log_output(f"[INFO] Started {description} in background (PID: {process.pid})", log_file)
        
        if duration:
            time.sleep(duration)
            process.terminate()
            log_output(f"[INFO] Stopped {description} after {duration} seconds.", log_file)
        return process
    else:
        # SỬA ĐỔI: Chạy và đẩy log ra màn hình thời gian thực
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)
        
        for line in process.stdout:
            sys.stdout.write(line) # Đẩy ra terminal
            log_file.write(line)   # Ghi vào file log
            log_file.flush()
            
        process.wait()
        if process.returncode == 0:
            log_output(f"[SUCCESS] {description} completed successfully.", log_file)
        else:
            log_output(f"[ERROR] {description} failed with return code {process.returncode}.", log_file)
        return process

def main():
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        log_output("🚀 STARTING END-TO-END PROJECT VALIDATION", f)
        start_time = time.time()

        # 1. Setup MinIO
        run_command("python src/utils/setup_minio.py", "Step 1: MinIO Infrastructure Setup", f)

        # 2. Kafka Producer (Tăng lên 20s để có nhiều dữ liệu hơn)
        run_command("python src/ingestion/kafka_producer.py", "Step 2: Data Ingestion (Kafka)", f, background=True, duration=20)

        # 3. Spark Streaming (Tăng lên 40s để đảm bảo dữ liệu đã ghi vào Silver)
        run_command("python src/pipelines/bronze_to_silver.py", "Step 3: Spark Streaming (Bronze -> Silver)", f, background=True, duration=45)

        # 4. Spark Batch Silver to Gold (Bây giờ bạn sẽ thấy log Spark hiện ra ngay)
        run_command("python src/pipelines/silver_to_gold.py", "Step 4: Feature Engineering (Silver -> Gold)", f)

        # 5. Model Training
        run_command("python src/models/train_retrieval.py", "Step 5: Model Training & MLflow Logging", f)

        # 6. Unit Tests
        run_command("python -m pytest tests/test_pipelines.py", "Step 6: System Validation (Unit Tests)", f)

        end_time = time.time()
        log_output(f"\n{'='*50}", f)
        log_output(f"✅ ALL STEPS COMPLETED IN {round(end_time - start_time, 2)} SECONDS", f)
        log_output(f"📄 Full report saved to: {LOG_FILE}", f)

if __name__ == "__main__":
    main()
