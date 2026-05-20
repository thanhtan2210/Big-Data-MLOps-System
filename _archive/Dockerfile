# syntax=docker/dockerfile:1
# Sử dụng hình ảnh uv để copy binary sang cho nhanh
FROM ghcr.io/astral-sh/uv:latest AS uv_bin

FROM python:3.11-slim

# ============================================
# OPTIMIZED DOCKERFILE - Extreme Performance
# ============================================

# 1. Thiết lập biến môi trường tối ưu
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    UV_SYSTEM_PYTHON=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    MALLOC_ARENA_MAX=2

WORKDIR /app

# Copy uv binary từ stage trước
COPY --from=uv_bin /uv /usr/local/bin/uv

# 2. Cài đặt system dependencies với Cache Mount
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 3. Copy các file config dependencies
COPY requirements-serving.txt pyproject.toml bentofile.yaml ./

# 4. Cài đặt toàn bộ dependencies cho Serving (đảm bảo CPU-only)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install -r requirements-serving.txt

# Loại bỏ package gây lỗi (nếu lỡ bị kéo theo)
RUN uv pip uninstall tensorflow-io-gcs-filesystem || true

# 6. Copy Source Code
COPY src/ ./src/

# Tạo .env nếu chưa có
RUN test -f .env || echo "# Runtime config" > .env

# 7. Cài đặt project và biên dịch Bytecode (giúp startup nhanh hơn)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install -e . && \
    python -m compileall src/

# Health Check & Expose
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000/health || exit 1

EXPOSE 3000

# Khởi chạy service
ENTRYPOINT ["bentoml", "serve"]
CMD ["src.serving.service:MovieRecommenderService", "--port", "3000", "--host", "0.0.0.0"]