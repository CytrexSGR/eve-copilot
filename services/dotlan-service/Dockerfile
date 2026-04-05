FROM python:3.11-slim

WORKDIR /app

# Install curl for healthcheck and build dependencies
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Install shared library first
COPY shared/ /shared/
RUN pip install --no-cache-dir /shared/

# Install service dependencies
COPY services/dotlan-service/pyproject.toml .
RUN pip install --no-cache-dir .

# Copy application
COPY services/dotlan-service/app/ ./app/

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
