FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir 'redis>=5,<9' 'httpx>=0.27,<1'
COPY worker.py .
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=5 CMD python -c "import pathlib,time; assert time.time()-float(pathlib.Path('/tmp/worker-heartbeat').read_text()) < 45"
CMD ["python", "worker.py"]
