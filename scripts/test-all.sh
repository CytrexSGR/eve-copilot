#!/usr/bin/env bash
# ============================================================================
# test-all.sh — Pre-Deploy Test-Runner für EVE Copilot
# Führt alle Unit-Tests in allen Service-Containern aus.
# Usage: ./test-all.sh [--verbose]
# ============================================================================
set -euo pipefail

# --- Farben ----------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m' # No Color

# --- Flags -----------------------------------------------------------------
VERBOSE=0
if [[ "${1:-}" == "--verbose" || "${1:-}" == "-v" ]]; then
    VERBOSE=1
fi

# --- Docker Compose Verzeichnis --------------------------------------------

# --- Service-Definitionen --------------------------------------------------
# Format: "container_name|test_command|label"
PYTHON_SERVICES=(
    "eve-api-gateway|python -m pytest app/tests --tb=short -q|API Gateway"
    "eve-auth-service|python -m pytest app/tests --tb=short -q|Auth Service"
    "eve-character-service|python -m pytest app/tests --tb=short -q|Character Service"
    "eve-dotlan-service|python -m pytest app/tests --tb=short -q|Dotlan Service"
    "eve-ectmap-service|python -m pytest app/tests --tb=short -q|ECTMap Service"
    "eve-finance-service|python -m pytest app/tests --tb=short -q|Finance Service"
    "eve-hr-service|python -m pytest app/tests --tb=short -q|HR Service"
    "eve-market-service|python -m pytest app/tests --tb=short -q|Market Service"
    "eve-mcp-service|python -m pytest app/tests --tb=short -q|MCP Service"
    "eve-production-service|python -m pytest app/tests --tb=short -q|Production Service"
    "eve-scheduler-service|python -m pytest app/tests --tb=short -q|Scheduler Service"
    "eve-shopping-service|python -m pytest app/tests --tb=short -q|Shopping Service"
    "eve-war-intel-service|python -m pytest app/tests --tb=short -q|War Intel Service"
    "eve-wormhole-service|python -m pytest app/tests --tb=short -q|Wormhole Service"
)

FRONTEND_SERVICES=(
    "eve-public-frontend|npx vitest run|Public Frontend"
)

# --- Zähler ----------------------------------------------------------------
TOTAL=0
PASSED=0
FAILED=0
SKIPPED=0
ERRORS=()

# --- Hilfsfunktionen -------------------------------------------------------
print_header() {
    echo ""
    echo -e "${BOLD}${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}${CYAN}║       EVE Copilot — Pre-Deploy Test-Runner              ║${NC}"
    echo -e "${BOLD}${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
    echo -e "${DIM}$(date '+%Y-%m-%d %H:%M:%S')${NC}"
    echo ""
}

is_container_running() {
    local container="$1"
    docker inspect -f '{{.State.Running}}' "$container" 2>/dev/null | grep -q 'true'
}

# Extrahiert aus pytest-Ausgabe: "X passed" / "X failed" etc.
parse_pytest_summary() {
    local output="$1"
    # Die letzte Zeile mit "passed" oder "failed" oder "error" enthält die Summary
    local summary_line
    summary_line=$(echo "$output" | grep -E '[0-9]+ (passed|failed|error)' | tail -1)
    echo "$summary_line"
}

run_test() {
    local container="$1"
    local test_cmd="$2"
    local label="$3"
    local type="$4"  # "pytest" oder "vitest"

    TOTAL=$((TOTAL + 1))

    # Prüfe ob Container läuft
    if ! is_container_running "$container"; then
        echo -e "  ${YELLOW}⊘ SKIP${NC}  ${label} ${DIM}(Container nicht gestartet)${NC}"
        SKIPPED=$((SKIPPED + 1))
        return
    fi

    # Prüfe ob Test-Tool verfügbar ist
    if [[ "$type" == "pytest" ]]; then
        local check_output
        check_output=$(docker exec "$container" python -m pytest --version 2>&1) || true
        if echo "$check_output" | grep -q "No module named pytest"; then
            echo -e "  ${YELLOW}⊘ SKIP${NC}  ${label} ${DIM}(pytest nicht installiert)${NC}"
            SKIPPED=$((SKIPPED + 1))
            return
        fi
    elif [[ "$type" == "vitest" ]]; then
        local check_output
        check_output=$(docker exec "$container" sh -c "which npx" 2>&1) || true
        if [[ -z "$check_output" ]]; then
            echo -e "  ${YELLOW}⊘ SKIP${NC}  ${label} ${DIM}(npx/vitest nicht verfügbar)${NC}"
            SKIPPED=$((SKIPPED + 1))
            return
        fi
    fi

    # Tests ausführen
    local output
    local exit_code=0
    output=$(docker exec "$container" sh -c "$test_cmd" 2>&1) || exit_code=$?

    if [[ $exit_code -eq 0 ]]; then
        # Erfolg — Zusammenfassung extrahieren
        local summary
        if [[ "$type" == "pytest" ]]; then
            summary=$(parse_pytest_summary "$output")
        else
            summary=$(echo "$output" | grep -E 'Tests? (Files? )?' | tail -1)
        fi
        echo -e "  ${GREEN}✔ PASS${NC}  ${label}  ${DIM}${summary}${NC}"
        PASSED=$((PASSED + 1))

        if [[ $VERBOSE -eq 1 ]]; then
            echo "$output" | sed 's/^/         /'
            echo ""
        fi
    else
        # Fehler — Fehlerzeilen anzeigen
        echo -e "  ${RED}✘ FAIL${NC}  ${label}"
        FAILED=$((FAILED + 1))
        ERRORS+=("$label")

        if [[ $VERBOSE -eq 1 ]]; then
            echo "$output" | sed 's/^/         /'
        else
            # Kompakt: nur FAILED-Zeilen + Summary
            echo "$output" | grep -E '(FAILED|ERROR|assert|Error)' | head -10 | sed 's/^/         /'
            local summary
            summary=$(parse_pytest_summary "$output")
            if [[ -n "$summary" ]]; then
                echo -e "         ${DIM}${summary}${NC}"
            fi
        fi
        echo ""
    fi
}

# --- Hauptprogramm ---------------------------------------------------------
print_header

if [[ $VERBOSE -eq 1 ]]; then
    echo -e "${DIM}Modus: verbose${NC}"
else
    echo -e "${DIM}Modus: compact (--verbose für Details)${NC}"
fi

# Python-Services testen
echo ""
echo -e "${BOLD}Python-Services (pytest):${NC}"
echo -e "${DIM}─────────────────────────────────────────────────────────${NC}"

for entry in "${PYTHON_SERVICES[@]}"; do
    IFS='|' read -r container cmd label <<< "$entry" || true
    run_test "$container" "$cmd" "$label" "pytest"
done

# Frontend testen
echo ""
echo -e "${BOLD}Frontend (vitest):${NC}"
echo -e "${DIM}─────────────────────────────────────────────────────────${NC}"

for entry in "${FRONTEND_SERVICES[@]}"; do
    IFS='|' read -r container cmd label <<< "$entry" || true
    run_test "$container" "$cmd" "$label" "vitest"
done

# --- Summary ---------------------------------------------------------------
echo ""
echo -e "${BOLD}${CYAN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}  Ergebnis:${NC}  ${GREEN}${PASSED} bestanden${NC}  ${RED}${FAILED} fehlgeschlagen${NC}  ${YELLOW}${SKIPPED} übersprungen${NC}  ${DIM}(${TOTAL} gesamt)${NC}"

if [[ ${#ERRORS[@]} -gt 0 ]]; then
    echo ""
    echo -e "${RED}  Fehlgeschlagene Services:${NC}"
    for err in "${ERRORS[@]}"; do
        echo -e "    ${RED}→ ${err}${NC}"
    done
fi

echo -e "${BOLD}${CYAN}═══════════════════════════════════════════════════════════${NC}"
echo ""

# Exit-Code
if [[ $FAILED -gt 0 ]]; then
    exit 1
else
    exit 0
fi
