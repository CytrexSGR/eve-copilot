FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for Playwright and healthcheck
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    # Playwright Chromium dependencies
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libatspi2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install eve_shared library first
COPY shared/ /shared/
RUN pip install --no-cache-dir /shared/

# Copy and install service dependencies
COPY services/ectmap-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (Chromium)
# Note: --with-deps removed because we already installed system dependencies above
RUN playwright install chromium

# Copy application code
COPY services/ectmap-service/app/ ./app/

# Create snapshots directory
RUN mkdir -p /app/snapshots

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8011/health || exit 1

EXPOSE 8011

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8011"]
