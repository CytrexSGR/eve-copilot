#!/bin/bash
# =============================================================================
# EVE Co-Pilot Microservices Health Check Script
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=================================================="
echo "  EVE Co-Pilot Health Check"
echo "=================================================="
echo

# Service endpoints
declare -A SERVICES=(
    ["api-gateway"]="http://localhost:8000/health"
    ["auth-service"]="http://localhost:8001/health"
    ["war-intel-service"]="http://localhost:8002/health"
    ["scheduler-service"]="http://localhost:8003/health"
    ["market-service"]="http://localhost:8004/health"
    ["production-service"]="http://localhost:8005/health"
    ["shopping-service"]="http://localhost:8006/health"
    ["character-service"]="http://localhost:8007/health"
)

HEALTHY=0
UNHEALTHY=0

for service in "${!SERVICES[@]}"; do
    url="${SERVICES[$service]}"
    if curl -sf "$url" > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓${NC} $service"
        ((HEALTHY++))
    else
        echo -e "  ${RED}✗${NC} $service"
        ((UNHEALTHY++))
    fi
done

echo
echo "=================================================="
TOTAL=$((HEALTHY + UNHEALTHY))

if [ $UNHEALTHY -eq 0 ]; then
    echo -e "  ${GREEN}All $TOTAL services healthy${NC}"
    exit 0
elif [ $HEALTHY -eq 0 ]; then
    echo -e "  ${RED}All $TOTAL services unhealthy${NC}"
    exit 2
else
    echo -e "  ${YELLOW}$HEALTHY/$TOTAL services healthy${NC}"
    exit 1
fi
