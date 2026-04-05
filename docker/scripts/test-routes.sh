#!/bin/bash
# =============================================================================
# EVE Co-Pilot API Gateway Route Testing Script
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

GATEWAY_URL="${GATEWAY_URL:-http://localhost:8000}"

echo "=================================================="
echo "  EVE Co-Pilot API Gateway Route Tests"
echo "=================================================="
echo "  Gateway URL: $GATEWAY_URL"
echo "=================================================="
echo

PASSED=0
FAILED=0

test_route() {
    local name="$1"
    local method="$2"
    local path="$3"
    local expected_status="$4"

    response=$(curl -sf -o /dev/null -w "%{http_code}" -X "$method" "${GATEWAY_URL}${path}" 2>/dev/null || echo "000")

    if [ "$response" == "$expected_status" ]; then
        echo -e "  ${GREEN}✓${NC} $name (${method} ${path}) -> $response"
        ((PASSED++))
    else
        echo -e "  ${RED}✗${NC} $name (${method} ${path}) -> $response (expected $expected_status)"
        ((FAILED++))
    fi
}

# Gateway
echo -e "${BLUE}Gateway Endpoints${NC}"
test_route "Root" "GET" "/" "200"
test_route "Health" "GET" "/health" "200"
test_route "Services Health" "GET" "/health/services" "200"

# Auth Service
echo
echo -e "${BLUE}Auth Service (/api/auth)${NC}"
test_route "Auth Characters" "GET" "/api/auth/characters" "200"

# War Intel Service
echo
echo -e "${BLUE}War Intel Service (/api/war)${NC}"
test_route "War Summary" "GET" "/api/war/summary" "200"

# Market Service
echo
echo -e "${BLUE}Market Service (/api/market)${NC}"
test_route "Market Stats" "GET" "/api/market/stats/10000002/34" "200"

# Production Service
echo
echo -e "${BLUE}Production Service (/api/production)${NC}"
test_route "Production Cost" "GET" "/api/production/cost/648" "200"

# Shopping Service
echo
echo -e "${BLUE}Shopping Service (/api/shopping)${NC}"
test_route "Shopping Lists" "GET" "/api/shopping/lists" "200"

# Character Service
echo
echo -e "${BLUE}Character Service (/api/character)${NC}"
test_route "Character Info (Public)" "GET" "/api/character/1117367444/info" "200"

echo
echo "=================================================="
TOTAL=$((PASSED + FAILED))

if [ $FAILED -eq 0 ]; then
    echo -e "  ${GREEN}All $TOTAL routes passed${NC}"
    exit 0
else
    echo -e "  ${YELLOW}$PASSED/$TOTAL routes passed, $FAILED failed${NC}"
    exit 1
fi
