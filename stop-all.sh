#!/bin/bash
# EVE Co-Pilot - Stop All Services
# Usage: ./stop-all.sh

echo "=== EVE Co-Pilot Shutdown Script ==="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to stop process on port
stop_port() {
    local port=$1
    local name=$2
    local pid=$(lsof -ti:$port 2>/dev/null)

    if [ -z "$pid" ]; then
        echo -e "${YELLOW}[SKIP]${NC} $name (port $port) not running"
        return 0
    fi

    echo "Stopping $name (PID: $pid)..."
    kill $pid 2>/dev/null
    sleep 2

    # Force kill if still running
    if kill -0 $pid 2>/dev/null; then
        echo "Force killing $name (PID: $pid)..."
        kill -9 $pid 2>/dev/null
    fi

    echo -e "${GREEN}[OK]${NC} $name stopped"
}

# Stop Backend Services
echo -e "${BLUE}=== Stopping Backend Services ===${NC}"
stop_port 8000 "Backend API (Monolith)"
stop_port 8002 "war-intel-service"
stop_port 8003 "scheduler-service"
stop_port 8009 "Copilot Server"

# Stop MCP Service (Docker)
cd /home/cytrex/eve_copilot/docker

if docker ps | grep -q eve-mcp-service; then
    echo "Stopping MCP Service (Docker)..."
    docker compose stop mcp-service
    echo -e "${GREEN}[OK]${NC} MCP Service stopped"
else
    echo -e "${YELLOW}[SKIP]${NC} MCP Service not running"
fi

cd /home/cytrex/eve_copilot

# Stop Frontend Services
echo ""
echo -e "${BLUE}=== Stopping Frontend Services ===${NC}"

cd /home/cytrex/eve_copilot/docker

if docker ps | grep -q eve-public-frontend; then
    echo "Stopping Public Frontend (Docker)..."
    docker compose stop public-frontend
    echo -e "${GREEN}[OK]${NC} Public Frontend stopped"
else
    echo -e "${YELLOW}[SKIP]${NC} Public Frontend not running"
fi

cd /home/cytrex/eve_copilot

if echo '$SUDO_PASSWORD' | sudo -S systemctl is-active --quiet eve-unified-frontend; then
    echo "Stopping eve-unified-frontend..."
    echo '$SUDO_PASSWORD' | sudo -S systemctl stop eve-unified-frontend
    echo -e "${GREEN}[OK]${NC} Unified Frontend stopped"
else
    echo -e "${YELLOW}[SKIP]${NC} Unified Frontend not running"
fi

# Stop Optional Services
echo ""
echo -e "${BLUE}=== Stopping Optional Services ===${NC}"

# Docker Services - ectmap and zkillboard
cd /home/cytrex/eve_copilot/docker

if docker ps | grep -q eve-ectmap-service; then
    echo "Stopping ectmap-service (Docker)..."
    docker compose stop ectmap-service
    echo -e "${GREEN}[OK]${NC} ectmap-service stopped"
else
    echo -e "${YELLOW}[SKIP]${NC} ectmap-service not running"
fi

if docker ps | grep -q eve-ectmap-frontend; then
    echo "Stopping ectmap Frontend (Docker)..."
    docker compose stop ectmap
    echo -e "${GREEN}[OK]${NC} ectmap Frontend stopped"
else
    echo -e "${YELLOW}[SKIP]${NC} ectmap Frontend not running"
fi

if docker ps | grep -q eve-zkillboard-service; then
    echo "Stopping zkillboard Stream (Docker)..."
    docker compose stop zkillboard-service
    echo -e "${GREEN}[OK]${NC} zkillboard Stream stopped"
else
    echo -e "${YELLOW}[SKIP]${NC} zkillboard Stream not running"
fi

cd /home/cytrex/eve_copilot

# Docker Containers (optional - comment out if you want to keep them running)
echo ""
echo -e "${BLUE}=== Docker Containers ===${NC}"
echo -e "${YELLOW}[INFO]${NC} Docker containers (PostgreSQL, Redis) are still running"
echo -e "${YELLOW}[INFO]${NC} To stop them, run: sudo docker stop eve_db redis"

echo ""
echo -e "${GREEN}=== Shutdown Complete ===${NC}"
