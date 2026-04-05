FROM python:3.11-slim

WORKDIR /app

# Install curl for healthcheck and build dependencies
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Install shared library first
COPY shared/ /shared/
RUN pip install --no-cache-dir /shared/

# Install service dependencies
COPY services/war-intel-service/pyproject.toml .
RUN pip install --no-cache-dir .

# Copy application
COPY services/war-intel-service/app/ ./app/

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000
# 4 workers — Redis shared cache enables multi-worker scaling
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
