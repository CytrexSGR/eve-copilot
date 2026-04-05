#!/bin/bash
# EVE Co-Pilot - Start All Services (Microservices + Monolith)
# Usage: ./start-all.sh

set -e

echo "=== EVE Co-Pilot Startup Script ==="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Base directory
BASE_DIR="/home/cytrex/eve_copilot"
LOG_DIR="$BASE_DIR/logs"

# Create logs directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Function to check if service is running
check_port() {
    curl -s http://localhost:$1/ > /dev/null 2>&1
    return $?
}

# Function to wait for service
wait_for_service() {
    local port=$1
    local name=$2
    local max_wait=30
    local waited=0

    while ! check_port $port; do
        sleep 1
        waited=$((waited + 1))
        if [ $waited -ge $max_wait ]; then
            echo -e "${RED}[FAIL]${NC} $name did not start within ${max_wait}s"
            return 1
        fi
    done
    echo -e "${GREEN}[OK]${NC} $name running on port $port"
    return 0
}

# 1. Docker Containers
echo -e "${BLUE}=== Docker Containers ===${NC}"
if ! docker ps | grep -q eve_db; then
    echo "Starting PostgreSQL (eve_db)..."
    echo '$SUDO_PASSWORD' | sudo -S docker start eve_db 2>/dev/null || echo "eve_db not found, skipping"
else
    echo -e "${YELLOW}[SKIP]${NC} PostgreSQL already running"
fi

if ! docker ps | grep -q redis; then
    echo "Starting Redis..."
    echo '$SUDO_PASSWORD' | sudo -S docker start redis 2>/dev/null || echo "redis not found, skipping"
else
    echo -e "${YELLOW}[SKIP]${NC} Redis already running"
fi

sleep 2

if docker ps | grep -q eve_db; then
    echo -e "${GREEN}[OK]${NC} PostgreSQL (eve_db)"
else
    echo -e "${RED}[FAIL]${NC} PostgreSQL (eve_db)"
fi

if docker ps | grep -q redis; then
    echo -e "${GREEN}[OK]${NC} Redis"
else
    echo -e "${RED}[FAIL]${NC} Redis"
fi

# 2. Backend Services
echo ""
echo -e "${BLUE}=== Backend Services ===${NC}"

# 2a. Backend API Monolith (Port 8000)
if check_port 8000; then
    echo -e "${YELLOW}[SKIP]${NC} Backend API already running on port 8000"
else
    echo "Starting Backend API (8000)..."
    cd "$BASE_DIR"
    nohup uvicorn main:app --host 0.0.0.0 --port 8000 --reload > "$LOG_DIR/backend-8000.log" 2>&1 &
    wait_for_service 8000 "Backend API"
fi

# 2b. war-intel-service (Port 8002)
if check_port 8002; then
    echo -e "${YELLOW}[SKIP]${NC} war-intel-service already running on port 8002"
else
    echo "Starting war-intel-service (8002)..."
    cd "$BASE_DIR/services/war-intel-service"
    nohup uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload > "$LOG_DIR/war-intel-8002.log" 2>&1 &
    wait_for_service 8002 "war-intel-service"
    cd "$BASE_DIR"
fi

# 2c. scheduler-service (Port 8003)
if check_port 8003; then
    echo -e "${YELLOW}[SKIP]${NC} scheduler-service already running on port 8003"
else
    echo "Starting scheduler-service (8003)..."
    cd "$BASE_DIR/services/scheduler-service"
    nohup uvicorn app.main:app --host 0.0.0.0 --port 8003 --reload > "$LOG_DIR/scheduler-8003.log" 2>&1 &
    wait_for_service 8003 "scheduler-service"
    cd "$BASE_DIR"
fi

# 2d. Copilot Server (Port 8009) - Optional, needs OPENAI_API_KEY
if check_port 8009; then
    echo -e "${YELLOW}[SKIP]${NC} Copilot Server already running on port 8009"
else
    if [ -f "/home/cytrex/Userdocs/.env" ] && grep -q "OPENAI_API_KEY" /home/cytrex/Userdocs/.env; then
        echo "Starting Copilot Server (8009)..."
        cd "$BASE_DIR"
        export $(grep OPENAI_API_KEY /home/cytrex/Userdocs/.env | xargs)
        nohup uvicorn copilot_server.main:app --host 0.0.0.0 --port 8009 --reload > "$LOG_DIR/copilot-8009.log" 2>&1 &
        wait_for_service 8009 "Copilot Server"
    else
        echo -e "${YELLOW}[SKIP]${NC} Copilot Server (OPENAI_API_KEY not found)"
    fi
fi

# 2e. MCP Service (Port 8008) - Optional AI Tool Server
cd "$BASE_DIR/docker"
if docker ps | grep -q eve-mcp-service; then
    echo -e "${GREEN}[OK]${NC} MCP Service (Docker) running on port 8008"
else
    echo "Starting MCP Service (Docker)..."
    docker compose up -d mcp-service
    wait_for_service 8008 "MCP Service"
fi
cd "$BASE_DIR"

# 3. Frontend Services
echo ""
echo -e "${BLUE}=== Frontend Services ===${NC}"

# 3a. Public Frontend (Port 5173) - Docker
cd "$BASE_DIR/docker"
if docker ps | grep -q eve-public-frontend; then
    echo -e "${GREEN}[OK]${NC} Public Frontend (Docker) running on port 5173"
else
    echo "Starting Public Frontend (Docker)..."
    docker compose up -d public-frontend
    sleep 3
    wait_for_service 5173 "Public Frontend"
fi
cd "$BASE_DIR"

# 3b. Unified Frontend (Port 3003) - systemd service
if check_port 3003; then
    echo -e "${GREEN}[OK]${NC} Unified Frontend running on port 3003"
else
    echo -e "${YELLOW}[INFO]${NC} Checking systemd service eve-unified-frontend..."
    if echo '$SUDO_PASSWORD' | sudo -S systemctl is-active --quiet eve-unified-frontend; then
        echo -e "${GREEN}[OK]${NC} eve-unified-frontend service is active"
    else
        echo -e "${YELLOW}[WARN]${NC} Starting eve-unified-frontend service..."
        echo '$SUDO_PASSWORD' | sudo -S systemctl start eve-unified-frontend
        sleep 3
        wait_for_service 3003 "Unified Frontend"
    fi
fi

# 4. Optional Services
echo ""
echo -e "${BLUE}=== Optional Services ===${NC}"

# 4a. ectmap-service (Port 8011) - Docker
cd "$BASE_DIR/docker"
if docker ps | grep -q eve-ectmap-service; then
    echo -e "${GREEN}[OK]${NC} ectmap-service (Docker) running on port 8011"
else
    echo "Starting ectmap-service (Docker)..."
    docker compose up -d ectmap-service
    wait_for_service 8011 "ectmap-service"
fi

# 4b. ectmap Frontend (Port 3001) - Docker
if docker ps | grep -q eve-ectmap-frontend; then
    echo -e "${GREEN}[OK]${NC} ectmap Frontend (Docker) running on port 3001"
else
    echo "Starting ectmap Frontend (Docker)..."
    docker compose up -d ectmap
    wait_for_service 3001 "ectmap Frontend"
fi

# 4c. zkillboard Stream (Port 8013) - Docker - CRITICAL for Battle Detection
if docker ps | grep -q eve-zkillboard-service; then
    echo -e "${GREEN}[OK]${NC} zkillboard Stream (Docker) running on port 8013"
else
    echo "Starting zkillboard Stream (Docker)..."
    docker compose up -d zkillboard-service
    sleep 3
    echo -e "${GREEN}[OK]${NC} zkillboard Stream started (check logs with: docker logs -f eve-zkillboard-service)"
fi
cd "$BASE_DIR"

# Summary
echo ""
echo -e "${BLUE}=== Service Status Summary ===${NC}"
echo ""
echo "Docker Containers:"
docker ps --format "  {{.Names}}: {{.Status}}" | grep -E "eve_db|redis" || echo "  No containers running"
echo ""
echo "Backend Services:"
check_port 8000 && echo -e "  Monolith API:      ${GREEN}http://localhost:8000${NC}" || echo -e "  Monolith API:      ${RED}NOT RUNNING${NC}"
check_port 8002 && echo -e "  war-intel-service: ${GREEN}http://localhost:8002${NC}" || echo -e "  war-intel-service: ${RED}NOT RUNNING${NC}"
check_port 8003 && echo -e "  scheduler-service: ${GREEN}http://localhost:8003${NC}" || echo -e "  scheduler-service: ${RED}NOT RUNNING${NC}"
check_port 8008 && echo -e "  MCP Service:       ${GREEN}http://localhost:8008${NC}" || echo -e "  MCP Service:       ${RED}NOT RUNNING${NC}"
check_port 8009 && echo -e "  Copilot Server:    ${GREEN}http://localhost:8009${NC}" || echo -e "  Copilot Server:    ${RED}NOT RUNNING${NC}"
echo ""
echo "Frontend Services:"
check_port 5173 && echo -e "  Public Frontend:   ${GREEN}http://localhost:5173${NC}" || echo -e "  Public Frontend:   ${RED}NOT RUNNING${NC}"
check_port 3003 && echo -e "  Unified Frontend:  ${GREEN}http://localhost:3003${NC}" || echo -e "  Unified Frontend:  ${RED}NOT RUNNING${NC}"
echo ""
echo "External Access:"
echo "  Production: https://eve.infinimind-creations.com"
echo "  Public:     http://localhost:5173"
echo "  Internal:   http://localhost:3003"
echo ""
echo "API Documentation:"
echo "  Monolith:   http://localhost:8000/docs"
echo ""
echo "Live Services:"
pgrep -f "listen_zkillboard" > /dev/null && echo -e "  zkillboard Stream: ${GREEN}RUNNING${NC}" || echo -e "  zkillboard Stream: ${RED}NOT RUNNING${NC}"
echo ""
echo "Logs:"
echo "  Backend:          tail -f $LOG_DIR/backend-8000.log"
echo "  war-intel:        tail -f $LOG_DIR/war-intel-8002.log"
echo "  scheduler:        tail -f $LOG_DIR/scheduler-8003.log"
echo "  copilot:          tail -f $LOG_DIR/copilot-8009.log"
echo "  zkillboard:       tail -f $LOG_DIR/zkillboard-stream.log"
echo ""
echo -e "${GREEN}=== Startup Complete ===${NC}"
