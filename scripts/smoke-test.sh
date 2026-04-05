#!/usr/bin/env bash
# ============================================================================
# smoke-test.sh — Post-Deploy Smoke Tests fuer EVE Copilot
# Prueft Container-Health, Service-Endpoints, Auth/Security und Business-Logic.
# Usage: ./smoke-test.sh [--no-color]
# ============================================================================
set -uo pipefail

# --- Farben ----------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

if [[ "${1:-}" == "--no-color" ]]; then
    RED='' GREEN='' YELLOW='' CYAN='' BOLD='' DIM='' NC=''
fi

# --- Konfiguration ---------------------------------------------------------
COMPOSE_FILE="/home/cytrex/eve_copilot/docker/docker-compose.yml"
MIN_CONTAINERS=20

# JWT-Secret aus docker-compose.yml extrahieren (Default-Wert)
JWT_SECRET="8bGKMxz1NMDxDTXrjuXZ90ahVKTM7vp-XSbJXmoe9L0"

# --- Zaehler ---------------------------------------------------------------
TOTAL=0
PASSED=0
FAILED=0
WARNED=0
FAILURES=()

# --- Hilfsfunktionen -------------------------------------------------------
print_header() {
    local now
    now=$(date '+%Y-%m-%d %H:%M:%S')
    echo ""
    echo -e "${BOLD}${CYAN}==============================${NC}"
    echo -e "${BOLD}${CYAN} EVE Copilot Smoke Tests${NC}"
    echo -e "${BOLD}${CYAN} ${now}${NC}"
    echo -e "${BOLD}${CYAN}==============================${NC}"
}

# check LABEL URL EXPECTED_CODE [EXTRA_CURL_ARGS...]
# Fuehrt einen HTTP-Check aus und gibt formatierte Ausgabe.
check() {
    local label="$1"
    local url="$2"
    local expected="$3"
    shift 3
    local extra_args=("$@")

    TOTAL=$((TOTAL + 1))

    local start_ms end_ms duration_ms http_code
    start_ms=$(date +%s%N)

    http_code=$(curl -s -o /dev/null -w '%{http_code}' \
        --connect-timeout 5 --max-time 10 \
        "${extra_args[@]}" \
        "$url" 2>/dev/null) || http_code="000"

    end_ms=$(date +%s%N)
    duration_ms=$(( (end_ms - start_ms) / 1000000 ))

    # Formatierung: Label auf 42 Zeichen auffuellen
    local padded
    padded=$(printf "%-42s" "$label")

    if [[ ",$expected," == *",$http_code,"* ]]; then
        echo -e "  ${padded} ${GREEN}OK${NC}  (${http_code}, ${duration_ms}ms)"
        PASSED=$((PASSED + 1))
    else
        echo -e "  ${padded} ${RED}FAIL${NC} (got ${http_code}, expected ${expected}, ${duration_ms}ms)"
        FAILED=$((FAILED + 1))
        FAILURES+=("$label")
    fi
}

# check_warn — wie check(), aber WARN statt FAIL bei Fehlschlag
check_warn() {
    local label="$1"
    local url="$2"
    local expected="$3"
    shift 3
    local extra_args=("$@")

    TOTAL=$((TOTAL + 1))

    local start_ms end_ms duration_ms http_code
    start_ms=$(date +%s%N)

    http_code=$(curl -s -o /dev/null -w '%{http_code}' \
        --connect-timeout 5 --max-time 10 \
        "${extra_args[@]}" \
        "$url" 2>/dev/null) || http_code="000"

    end_ms=$(date +%s%N)
    duration_ms=$(( (end_ms - start_ms) / 1000000 ))

    local padded
    padded=$(printf "%-42s" "$label")

    if [[ ",$expected," == *",$http_code,"* ]]; then
        echo -e "  ${padded} ${GREEN}OK${NC}  (${http_code}, ${duration_ms}ms)"
        PASSED=$((PASSED + 1))
    else
        echo -e "  ${padded} ${YELLOW}WARN${NC} (got ${http_code}, expected ${expected}, ${duration_ms}ms)"
        WARNED=$((WARNED + 1))
    fi
}

# generate_jwt — erzeugt JWT Token mit PyJWT
generate_jwt() {
    python3 -c "
import jwt, time
now = int(time.time())
payload = {
    'sub': '2114350216',
    'name': 'Cytrex',
    'account_id': 2,
    'character_ids': [2114350216],
    'type': 'public_session',
    'exp': now + 3600,
    'iat': now,
}
print(jwt.encode(payload, '${JWT_SECRET}', algorithm='HS256'))
" 2>/dev/null
}

# --- Container Health Check ------------------------------------------------
check_containers() {
    echo ""
    echo -e "${BOLD}--- Container Health ---${NC}"

    TOTAL=$((TOTAL + 1))

    local output running healthy total_containers
    output=$(docker compose -f "$COMPOSE_FILE" ps --format '{{.Name}} {{.Status}}' 2>/dev/null) || {
        echo -e "  ${RED}FAIL${NC}  Docker Compose nicht erreichbar"
        FAILED=$((FAILED + 1))
        FAILURES+=("Container Health Check")
        return
    }

    total_containers=$(echo "$output" | wc -l)
    running=$(echo "$output" | grep -c "Up" || true)
    healthy=$(echo "$output" | grep -c "healthy" || true)

    local padded
    padded=$(printf "%-42s" "Container (${running} running, ${healthy} healthy)")

    if [[ "$running" -ge "$MIN_CONTAINERS" ]]; then
        echo -e "  ${padded} ${GREEN}OK${NC}  (${running}/${total_containers})"
        PASSED=$((PASSED + 1))
    else
        echo -e "  ${padded} ${RED}FAIL${NC} (${running}/${total_containers}, min ${MIN_CONTAINERS})"
        FAILED=$((FAILED + 1))
        FAILURES+=("Container Health Check (${running}/${total_containers})")

        # Zeige nicht laufende Container
        local stopped
        stopped=$(echo "$output" | grep -v "Up" || true)
        if [[ -n "$stopped" ]]; then
            echo -e "  ${DIM}Nicht laufend:${NC}"
            echo "$stopped" | while read -r line; do
                echo -e "    ${DIM}- ${line}${NC}"
            done
        fi
    fi
}

# --- Service Health Endpoints ----------------------------------------------
check_service_health() {
    echo ""
    echo -e "${BOLD}--- Service Health Endpoints ---${NC}"

    check "API Gateway"             "http://localhost:8000/health"  "200"
    check "Auth Service"            "http://localhost:8010/health"  "200"
    check "War-Intel Service"       "http://localhost:8002/health"  "200"
    check "Market Service"          "http://localhost:8004/health"  "200"
    check "Character Service"       "http://localhost:8007/health"  "200"
    check "Production Service"      "http://localhost:8005/health"  "200"
    check "Shopping Service"        "http://localhost:8006/health"  "200"
    check "Wormhole Service"        "http://localhost:8012/health"  "200"
    check "Scheduler Service"       "http://localhost:8003/health"  "200"
    check "Military Service"        "http://localhost:8020/health"  "200"
    check "Dotlan Service"          "http://localhost:8014/health"  "200"
    check "Public Frontend"         "http://localhost:5173/"        "200"
    check_warn "HR Service"         "http://localhost:8015/health"  "200"
    check_warn "Finance Service"    "http://localhost:8016/health"  "200"
    check "ECTMap Service"          "http://localhost:8011/health"  "200"
    check "MCP Service"             "http://localhost:8008/health"  "200"
    check "Zkillboard Service"      "http://localhost:8013/health"  "200"
}

# --- Auth & Security -------------------------------------------------------
check_auth_security() {
    echo ""
    echo -e "${BOLD}--- Auth & Security ---${NC}"

    # Pruefe PyJWT
    if ! python3 -c "import jwt" 2>/dev/null; then
        echo -e "  ${RED}SKIP${NC}  PyJWT nicht installiert — Auth-Tests uebersprungen"
        echo -e "  ${DIM}Installation: pip3 install PyJWT${NC}"
        return
    fi

    local token
    token=$(generate_jwt)

    if [[ -z "$token" ]]; then
        echo -e "  ${RED}SKIP${NC}  JWT-Generierung fehlgeschlagen"
        return
    fi

    # /me mit JWT — erwartet nicht-401 (404 = JWT gueltig, kein Customer-Record)
    TOTAL=$((TOTAL + 1))
    local start_ms end_ms duration_ms http_code padded
    start_ms=$(date +%s%N)
    http_code=$(curl -s -o /dev/null -w '%{http_code}' \
        --connect-timeout 5 --max-time 10 \
        -b "session=${token}" \
        "http://localhost:8000/api/auth/me" 2>/dev/null) || http_code="000"
    end_ms=$(date +%s%N)
    duration_ms=$(( (end_ms - start_ms) / 1000000 ))
    padded=$(printf "%-42s" "Auth /me (mit JWT)")

    if [[ "$http_code" != "401" && "$http_code" != "000" ]]; then
        echo -e "  ${padded} ${GREEN}OK${NC}  (${http_code}, ${duration_ms}ms)"
        PASSED=$((PASSED + 1))
    else
        echo -e "  ${padded} ${RED}FAIL${NC} (${http_code}, ${duration_ms}ms)"
        FAILED=$((FAILED + 1))
        FAILURES+=("Auth /me (mit JWT)")
    fi

    # Ohne JWT → muss 401 sein
    check "Auth /me (ohne JWT)"                "http://localhost:8000/api/auth/me" "401,404"

    # Ownership: eigener Character
    TOTAL=$((TOTAL + 1))
    start_ms=$(date +%s%N)
    http_code=$(curl -s -o /dev/null -w '%{http_code}' \
        --connect-timeout 5 --max-time 10 \
        -b "session=${token}" \
        -H "X-Character-Id: 2114350216" \
        "http://localhost:8000/api/auth/me" 2>/dev/null) || http_code="000"
    end_ms=$(date +%s%N)
    duration_ms=$(( (end_ms - start_ms) / 1000000 ))
    padded=$(printf "%-42s" "Ownership OK (eigener Char)")

    if [[ "$http_code" != "401" && "$http_code" != "403" && "$http_code" != "000" ]]; then
        echo -e "  ${padded} ${GREEN}OK${NC}  (${http_code}, ${duration_ms}ms)"
        PASSED=$((PASSED + 1))
    else
        echo -e "  ${padded} ${RED}FAIL${NC} (${http_code}, ${duration_ms}ms)"
        FAILED=$((FAILED + 1))
        FAILURES+=("Ownership OK (eigener Char)")
    fi

    # Ownership: fremder Character → 403
    check "Ownership REJECT (fremder Char)"  "http://localhost:8000/api/auth/me" "403" \
        -b "session=${token}" -H "X-Character-Id: 999999999"

    # Invalid Character-ID → 400
    check "Invalid Char-ID (non-numeric)"    "http://localhost:8000/api/auth/me" "400" \
        -b "session=${token}" -H "X-Character-Id: abc"
}

# --- Business Logic --------------------------------------------------------
check_business_logic() {
    echo ""
    echo -e "${BOLD}--- Business Logic ---${NC}"

    check "Fingerprints API"        "http://localhost:8000/api/fingerprints/?limit=1"  "200"
    check "War Battles (active)"    "http://localhost:8000/api/war/battles/active"     "200"
    check "War Summary"             "http://localhost:8000/api/war/summary"            "200"
    check "Fleet Doctrines"         "http://localhost:8000/api/fleet/doctrines"        "200"
    check "Character Summary"       "http://localhost:8000/api/character/summary/all"  "200"
    check "Dashboard Summary"       "http://localhost:8000/api/dashboard/characters/summary" "200"

    # JWT fuer authentifizierte Checks
    local token
    token=$(generate_jwt)
    if [[ -z "$token" ]]; then
        echo -e "  ${YELLOW}SKIP${NC}  JWT-Generierung fehlgeschlagen — Market/Production/Fittings-Tests uebersprungen"
        return
    fi

    # --- Market ---
    check "Market: Item Search"          "http://localhost:8000/api/items/search?q=tritanium" "200" -b "session=${token}"
    check "Market: Hot Items"            "http://localhost:8000/api/market/prices/hot-items" "200" -b "session=${token}"
    check "Market: Tritanium Price"      "http://localhost:8000/api/market/price/34" "200" -b "session=${token}"
    check "Market: Orders (aggregated)"  "http://localhost:8000/api/orders/aggregated" "200" -b "session=${token}"
    check "Market: Trading Opportunities" "http://localhost:8000/api/trading/opportunities" "200" -b "session=${token}"

    # --- Production ---
    check "Production: Economics"        "http://localhost:8000/api/production/economics/587" "200" -b "session=${token}"
    check "Production: Blueprint Chain"  "http://localhost:8000/api/production/chains/587" "200" -b "session=${token}"
    check "Production: Reactions List"   "http://localhost:8000/api/reactions" "200" -b "session=${token}"
    check "Production: PI Formulas"      "http://localhost:8000/api/pi/formulas" "200" -b "session=${token}"
    check "Production: Facilities"       "http://localhost:8000/api/production/facilities" "200" -b "session=${token}"

    # --- Fittings ---
    check "Fittings: Shared"             "http://localhost:8000/api/fittings/shared?limit=1" "200" -b "session=${token}"
    check "Fittings: Boost Presets"      "http://localhost:8000/api/fittings/boost-presets" "200" -b "session=${token}"
    check "Fittings: Boost Definitions"  "http://localhost:8000/api/fittings/boost-definitions" "200" -b "session=${token}"
    check "Fittings: Projected Presets"  "http://localhost:8000/api/fittings/projected-presets" "200" -b "session=${token}"
}

# --- Zusammenfassung -------------------------------------------------------
print_summary() {
    echo ""
    echo -e "${BOLD}${CYAN}==============================${NC}"
    local total_checked=$((PASSED + FAILED + WARNED))
    echo -e "${BOLD} Results: ${GREEN}${PASSED}${NC}/${BOLD}${total_checked} passed${NC}, ${RED}${FAILED} failed${NC}, ${YELLOW}${WARNED} warned${NC}"

    if [[ ${#FAILURES[@]} -gt 0 ]]; then
        echo -e " ${RED}Failed:${NC}"
        for f in "${FAILURES[@]}"; do
            echo -e "   ${RED}- ${f}${NC}"
        done
    fi
    echo -e "${BOLD}${CYAN}==============================${NC}"
    echo ""
}

# --- Hauptprogramm ---------------------------------------------------------
main() {
    print_header
    check_containers
    check_service_health
    check_auth_security
    check_business_logic
    print_summary

    if [[ "$FAILED" -gt 0 ]]; then
        exit 1
    else
        exit 0
    fi
}

main
