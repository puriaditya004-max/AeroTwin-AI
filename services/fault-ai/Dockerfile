FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy pyproject.toml and install Python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Copy application source code
COPY app/ app/
COPY features/ features/
COPY models/ models/
COPY training/ training/
COPY configs/ configs/

# Expose service port
EXPOSE 8004

# Healthcheck
HEALTHCHECK --interval=10s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8004/health/live || exit 1

# Run model training on boot if artifacts missing, then launch FastAPI service
CMD python -m training.train && uvicorn app.main:app --host 0.0.0.0 --port 8004
