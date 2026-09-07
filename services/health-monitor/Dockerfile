FROM python:3.12-slim
WORKDIR /app/services/health-monitor
COPY services/health-monitor/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY packages/schemas/python/ /app/packages/schemas/python/
COPY services/health-monitor/ .
HEALTHCHECK --interval=10s --timeout=5s --retries=5 CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8003/health')"
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8003"]
