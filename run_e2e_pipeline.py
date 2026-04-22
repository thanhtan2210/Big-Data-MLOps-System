import subprocess
import time
import os
import sys

LOG_FILE = "project_execution_report.log"
SPARK_LOG = "spark_streaming.log"
KAFKA_LOG = "kafka_producer.log"

def log_output(message, file):
    print(message)
    file.write(message + "\n")
    file.flush()

def run_command(command, description, log_file, background=False, duration=None):
    log_output(f"\n{'='*20} {description} {'='*20}", log_file)
    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    
    # ÉP BUỘC: Thay thế "python " bằng đường dẫn tuyệt đối của Python đang chạy (Venv)
    python_exe = sys.executable
    if command.startswith("python "):
        command = command.replace("python ", f'"{python_exe}" ', 1)
    
    if background:
        bg_log = open(KAFKA_LOG if "producer" in command else SPARK_LOG, "w")
        process = subprocess.Popen(command, shell=True, stdout=bg_log, stderr=bg_log, text=True, env=env)
        log_output(f"[INFO] Started {description} (PID: {process.pid}). Log: {bg_log.name}", log_file)
        
        if duration:
            for i in range(duration):
                if i % 20 == 0:
                    print(f"  ... {description} is running ({i}/{duration}s)")
                time.sleep(1)
            subprocess.run(f"taskkill /F /T /PID {process.pid}", shell=True, capture_output=True)
            bg_log.close()
            log_output(f"[INFO] Stopped {description}.", log_file)
        return process
    else:
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)
        for line in process.stdout:
            sys.stdout.write(line)
            log_file.write(line)
        process.wait()
        
        if process.returncode == 0:
            log_output(f"[SUCCESS] {description} completed.", log_file)
            return True
        else:
            log_output(f"[CRITICAL ERROR] {description} FAILED.", log_file)
            return False

def main():
    if os.path.exists(LOG_FILE): os.remove(LOG_FILE)

    with open(LOG_FILE, "w", encoding="utf-8") as f:
        log_output("STARTING FINAL E2E VALIDATION", f)
        
        if not run_command("python src/utils/setup_minio.py", "Step 1: MinIO Setup", f):
            return

        run_command("python src/ingestion/kafka_producer.py", "Step 2: Kafka Ingestion", f, background=True, duration=20)

        log_output("[WAIT] Spark is starting...", f)
        run_command("python src/pipelines/bronze_to_silver.py", "Step 3: Spark Streaming", f, background=True, duration=90)

        if not run_command("python src/pipelines/silver_to_gold.py", "Step 4: Silver -> Gold", f):
            return

        if not run_command("python src/models/train_retrieval.py", "Step 5: Training", f):
            return

        log_output("\nFINISHED: E2E PIPELINE COMPLETED SUCCESSFULLY.", f)

if __name__ == "__main__":
    main()
