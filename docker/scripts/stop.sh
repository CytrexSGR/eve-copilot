#!/bin/bash
# =============================================================================
# EVE Co-Pilot Microservices Stop Script
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCKER_DIR="$(dirname "$SCRIPT_DIR")"

cd "$DOCKER_DIR"

echo "Stopping EVE Co-Pilot microservices..."
echo

if [ "$1" == "--clean" ]; then
    echo "Stopping and removing containers, networks, and volumes..."
    docker compose down -v
else
    echo "Stopping containers..."
    docker compose down
fi

echo
echo "Services stopped."
