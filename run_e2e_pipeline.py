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
    
    # Thiết lập PYTHONPATH để nhận diện thư mục src
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
        process = subprocess.run(command, shell=True, capture_output=True, text=True, env=env)
        log_file.write(process.stdout)
        if process.returncode == 0:
            log_output(f"[SUCCESS] {description} completed successfully.", log_file)
        else:
            log_output(f"[ERROR] {description} failed with return code {process.returncode}.", log_file)
            log_file.write(process.stderr)
        return process

def main():
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        log_output("🚀 STARTING END-TO-END PROJECT VALIDATION", f)
        start_time = time.time()

        # 1. Setup MinIO Buckets
        run_command("python src/utils/setup_minio.py", "Step 1: MinIO Infrastructure Setup", f)

        # 2. Run Kafka Producer (Background)
        # Chúng ta chạy trong 15 giây để đẩy một lượng dữ liệu mẫu
        run_command("python src/ingestion/kafka_producer.py", "Step 2: Data Ingestion (Kafka)", f, background=True, duration=15)

        # 3. Run Spark Streaming Bronze to Silver (Background)
        # Chạy trong 20 giây để Spark kịp quét dữ liệu từ Kafka và ghi vào Delta Lake
        run_command("python src/pipelines/bronze_to_silver.py", "Step 3: Spark Streaming (Bronze -> Silver)", f, background=True, duration=25)

        # 4. Run Spark Batch Silver to Gold
        run_command("python src/pipelines/silver_to_gold.py", "Step 4: Feature Engineering (Silver -> Gold)", f)

        # 5. Run Model Training
        run_command("python src/models/train_retrieval.py", "Step 5: Model Training & MLflow Logging", f)

        # 6. Run Unit Tests
        run_command("python -m pytest tests/test_pipelines.py", "Step 6: System Validation (Unit Tests)", f)

        end_time = time.time()
        log_output(f"\n{'='*50}", f)
        log_output(f"✅ ALL STEPS COMPLETED IN {round(end_time - start_time, 2)} SECONDS", f)
        log_output(f"📄 Full report saved to: {LOG_FILE}", f)

if __name__ == "__main__":
    main()
