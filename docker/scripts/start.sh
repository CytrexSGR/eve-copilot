#!/bin/bash
# =============================================================================
# EVE Co-Pilot Microservices Startup Script
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCKER_DIR="$(dirname "$SCRIPT_DIR")"

cd "$DOCKER_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=================================================="
echo "  EVE Co-Pilot Microservices Startup"
echo "=================================================="
echo

# Check for .env file
if [ ! -f .env ]; then
    echo -e "${YELLOW}Warning: .env file not found${NC}"
    echo "Creating from .env.example..."
    cp .env.example .env
    echo -e "${YELLOW}Please edit .env with your configuration before continuing.${NC}"
    exit 1
fi

# Validate required environment variables
echo "Checking environment configuration..."
source .env

REQUIRED_VARS=("POSTGRES_USER" "POSTGRES_PASSWORD" "POSTGRES_DB")
MISSING_VARS=()

for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        MISSING_VARS+=("$var")
    fi
done

if [ ${#MISSING_VARS[@]} -gt 0 ]; then
    echo -e "${RED}Error: Missing required environment variables:${NC}"
    printf '  - %s\n' "${MISSING_VARS[@]}"
    exit 1
fi

echo -e "${GREEN}✓ Environment configuration valid${NC}"
echo

# Start services
echo "Starting services..."
echo

if [ "$1" == "--build" ]; then
    echo "Building and starting all services..."
    docker compose up -d --build
else
    echo "Starting all services..."
    docker compose up -d
fi

echo
echo "Waiting for services to become healthy..."
echo

# Wait for services with timeout
TIMEOUT=120
ELAPSED=0
INTERVAL=5

while [ $ELAPSED -lt $TIMEOUT ]; do
    # Check api-gateway health (it depends on all other services)
    if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ API Gateway is healthy${NC}"
        break
    fi

    echo "  Waiting... ($ELAPSED/$TIMEOUT seconds)"
    sleep $INTERVAL
    ELAPSED=$((ELAPSED + INTERVAL))
done

if [ $ELAPSED -ge $TIMEOUT ]; then
    echo -e "${YELLOW}Warning: Timeout waiting for services${NC}"
    echo "Some services may still be starting. Check with: docker compose ps"
fi

echo
echo "=================================================="
echo "  Service Status"
echo "=================================================="
echo

docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"

echo
echo "=================================================="
echo "  Quick Health Check"
echo "=================================================="
echo

# Check aggregated health
HEALTH_RESPONSE=$(curl -sf http://localhost:8000/health/services 2>/dev/null || echo '{"status":"unavailable"}')
echo "Aggregated health: $HEALTH_RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    status = data.get('status', 'unknown')
    services = data.get('services', {})
    healthy = services.get('healthy', 0)
    total = services.get('total', 0)

    if status == 'healthy':
        print(f'\033[0;32m✓ All services healthy ({healthy}/{total})\033[0m')
    elif status == 'degraded':
        print(f'\033[1;33m⚠ Some services degraded ({healthy}/{total} healthy)\033[0m')
    else:
        print(f'\033[0;31m✗ Services unavailable\033[0m')
except:
    print('\033[0;31m✗ Could not check health\033[0m')
"

echo
echo "=================================================="
echo "  Access Points"
echo "=================================================="
echo
echo "  API Gateway:     http://localhost:8000"
echo "  API Docs:        http://localhost:8000/docs"
echo "  Health Check:    http://localhost:8000/health/services"
echo "  Grafana:         http://localhost:3200"
echo "  Prometheus:      http://localhost:9090"
echo
echo "=================================================="
echo
