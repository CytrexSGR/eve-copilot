FROM python:3.11-slim

WORKDIR /app

# Install curl for healthcheck
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Install shared library first
COPY shared/ /shared/
RUN pip install --no-cache-dir /shared/

# Install service dependencies
COPY services/scheduler-service/pyproject.toml .
RUN pip install --no-cache-dir .

# Copy application
COPY services/scheduler-service/app/ ./app/

# Copy legacy monolith code (used by subprocess jobs)
COPY services/scheduler-service/monolith/jobs/ ./jobs/
COPY services/scheduler-service/monolith/src/ ./src/
COPY services/scheduler-service/monolith/config.py ./config.py
COPY services/scheduler-service/monolith/services/ ./services/

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
