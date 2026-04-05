FROM python:3.11-slim

WORKDIR /app

# Install curl for healthcheck
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Install shared library first
COPY shared/ /shared/
RUN pip install --no-cache-dir /shared/

# Install service dependencies
COPY services/zkillboard/pyproject.toml .
RUN pip install --no-cache-dir .

# Copy legacy src/ for imports (zkillboard uses "from src.database import...")
COPY services/zkillboard/legacy/src/ ./src/

# Copy config.py for DB_CONFIG
COPY services/zkillboard/legacy/config.py ./config.py

# Copy entire zkillboard service directory structure
COPY services/zkillboard/*.py ./services/zkillboard/
COPY services/zkillboard/live/ ./services/zkillboard/live/
COPY services/zkillboard/reports/ ./services/zkillboard/reports/

# Copy the FastAPI app
COPY services/zkillboard/app/ ./app/

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
