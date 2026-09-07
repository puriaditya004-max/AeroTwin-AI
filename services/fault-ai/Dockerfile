FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 curl && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml README.md ./
COPY app/ app/
COPY features/ features/
COPY models/ models/
COPY training/ training/
COPY configs/ configs/
COPY artifacts/ artifacts/
RUN pip install --no-cache-dir .
EXPOSE 8004
HEALTHCHECK --interval=10s --timeout=5s --start-period=20s --retries=5 CMD curl -f http://localhost:8004/health/ready || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8004"]
