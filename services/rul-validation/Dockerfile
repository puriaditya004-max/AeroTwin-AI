
FROM python:3.12-slim

# =========================================================
# M5 RUL Validation Service
# =========================================================

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# M5 application
COPY app/ app/

# M5 training artifacts
COPY training/ training/

# M5 API port
EXPOSE 8005

# Healthcheck
HEALTHCHECK --interval=10s \
    --timeout=5s \
    --start-period=20s \
    --retries=5 \
    CMD curl -f http://localhost:8005/health || exit 1

# Start FastAPI
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8005"]
