# EVE Co-Pilot - Deployment Guide

**Version:** 3.0.0
**Date:** 2026-02-26

Complete deployment guide for the EVE Co-Pilot platform with Docker Compose.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Configuration](#configuration)
4. [Service Architecture](#service-architecture)
5. [Production Deployment](#production-deployment)
6. [Monitoring & Maintenance](#monitoring--maintenance)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required

- **Docker** 24.0+ with Docker Compose V2
- **Git** (to clone repository)
- **EVE SSO Application** (Client ID + Secret)

### Optional

- **Anthropic API Key** (for AI Copilot agent)
- **Node.js 18+** (for frontend development with HMR)

### System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 4 cores | 8+ cores |
| RAM | 8 GB | 16+ GB |
| Storage | 20 GB | 40+ GB |
| Network | 10 Mbps | 100+ Mbps |

---

## Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/CytrexSGR/Eve-Online-Copilot.git
cd Eve-Online-Copilot
```

### 2. Configure Environment

```bash
cd docker
cp .env.example .env
nano .env
```

**Required Configuration:**

```env
# Database
POSTGRES_DB=eve_sde
POSTGRES_USER=eve
POSTGRES_PASSWORD=<your_password>

# Redis
REDIS_PASSWORD=<your_redis_password>

# EVE SSO
EVE_CLIENT_ID=your_client_id
EVE_CLIENT_SECRET=your_client_secret
EVE_CALLBACK_URL=http://localhost:8010/api/auth/callback
```

### 3. Start Services

```bash
docker compose up -d
docker compose ps       # Verify all services healthy
```

### 4. Access Application

- **Public Frontend:** http://localhost:5173
- **API Gateway:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs
- **ECTMap (Universe Map):** http://localhost:3001

---

## Service Architecture

### 17 Microservices + Infrastructure

```
                         ┌─────────────────────────────────────────┐
                         │           External Data Sources         │
                         │  EVE ESI API │ zKillboard │ DOTLAN      │
                         └───────────────────┬─────────────────────┘
                                             │
                         ┌───────────────────▼─────────────────────┐
                         │            API Gateway (:8000)          │
                         │     Routes requests to microservices    │
                         │     CORS │ Rate Limiting │ Health       │
                         └───────────────────┬─────────────────────┘
                                             │
    ┌──────────┬──────────┬─────────┬────────┼────────┬─────────┬──────────┐
    ▼          ▼          ▼         ▼        ▼        ▼         ▼          ▼
┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
│  auth  │ │  war   │ │ sched  │ │ market │ │  prod  │ │  shop  │ │  char  │
│ :8010  │ │ :8002  │ │ :8003  │ │ :8004  │ │ :8005  │ │ :8006  │ │ :8007  │
└────────┘ └────────┘ └────────┘ └────────┘ └────────┘ └────────┘ └────────┘
    + mcp(:8008), ectmap(:8011), wormhole(:8012), zkill(:8013)
    + dotlan(:8014), hr(:8015), finance(:8016), military(:8017)
                                           │
                    ┌──────────────────────┼──────────────────────┐
                    ▼                      ▼                      ▼
             ┌───────────┐          ┌───────────┐          ┌───────────┐
             │ PostgreSQL│          │   Redis   │          │Monitoring │
             │  (eve_db) │          │  (:6379)  │          │ Prometheus│
             │  Internal │          │  L1 Cache │          │  Grafana  │
             └───────────┘          └───────────┘          │   Loki    │
                                                           └───────────┘
```

### Service Ports

| Port | Service | Purpose |
|------|---------|---------|
| 5173 | public-frontend | Public dashboard (nginx) |
| 3001 | ectmap | Universe map (Next.js) |
| 8000 | api-gateway | Main API entry point |
| 8002 | war-intel-service | Combat intelligence, battles |
| 8003 | scheduler-service | 40+ cron jobs |
| 8004 | market-service | Market prices, arbitrage |
| 8005 | production-service | Manufacturing, PI |
| 8006 | shopping-service | Shopping lists |
| 8007 | character-service | Characters, Dogma engine |
| 8008 | mcp-service | 609 dynamic MCP tools |
| 8010 | auth-service | EVE SSO OAuth |
| 8011 | ectmap-service | Map data |
| 8012 | wormhole-service | J-Space intelligence |
| 8013 | zkillboard | Live kill stream |
| 8014 | dotlan-service | DOTLAN scraping |
| 8015 | hr-service | HR, vetting |
| 8016 | finance-service | SRP, doctrines |
| 8017 | military-service | D-Scan, fleet PAPs |

### Infrastructure Services

| Service | Purpose |
|---------|---------|
| Redis 7 | L1 cache, rate limiting, sessions |
| PostgreSQL 16 | Database (internal network only) |
| Prometheus | Metrics collection |
| Grafana | Dashboards and visualization |
| Loki + Promtail | Log aggregation |
| Alertmanager | Alert routing |

---

## Docker Compose Commands

```bash
cd /home/cytrex/eve_copilot/docker

# Start all services
docker compose up -d

# Check health
docker compose ps

# View logs
docker compose logs -f <service-name>

# Restart a service
docker compose restart <service-name>

# Rebuild after code change
docker compose build --no-cache <service-name>
docker compose up -d <service-name>

# Stop all
docker compose down

# Database backup
docker exec eve_db pg_dump -U eve eve_sde | gzip > backup-$(date +%Y%m%d).sql.gz
```

---

## Production Deployment

### Current Production Setup

| Component | Value |
|-----------|-------|
| **Domain** | `eve.infinimind-creations.com` |
| **Server** | Proxmox VM, Debian Linux |
| **SSL** | Cloudflare Full (Strict) |
| **CDN** | Cloudflare (WAF, Bot Fight Mode) |

### Nginx Reverse Proxy

```nginx
server {
    listen 443 ssl http2;
    server_name eve.infinimind-creations.com;

    # Cloudflare origin certificate
    ssl_certificate /etc/ssl/cloudflare/cert.pem;
    ssl_certificate_key /etc/ssl/cloudflare/key.pem;

    # API Gateway
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # ECTMap
    location /ectmap {
        proxy_pass http://localhost:3001;
        proxy_set_header Host $host;
    }

    # Frontend
    location / {
        proxy_pass http://localhost:5173;
        proxy_set_header Host $host;
    }
}
```

### Security Layers

| Layer | Protection |
|-------|------------|
| **Cloudflare** | WAF, Bot Fight Mode, Rate Limit (100 req/10s) |
| **Nginx** | Blocks non-Cloudflare IPs, waiting room (50 conn max) |
| **SaaS Rate Limiter** | Tier-aware: public=30 to coalition=2,000 req/min |
| **Database** | Internal Docker network only (NOT exposed to host) |

---

## Monitoring & Maintenance

### Health Monitoring

```bash
# Check all services
docker compose ps

# API health aggregation
curl http://localhost:8000/health/services

# Grafana dashboards
# http://localhost:3000 (Grafana port in Docker)
```

### Prometheus Metrics

- HTTP request latency and error rates per service
- Database query performance
- Redis cache hit/miss ratios
- SaaS subscription metrics

### Log Management

All services use structured JSON logging via Loki + Promtail:

```bash
# View service logs
docker compose logs -f war-intel-service

# Log rotation configured in docker-compose.yml
# max-size: 10m, max-file: 3
```

### Database Maintenance

```bash
# Connect to database
echo '<SUDO_PASSWORD>' | sudo -S docker exec eve_db psql -U eve -d eve_sde

# Run migration
cat migrations/111_xxx.sql | sudo -S docker exec -i eve_db psql -U eve -d eve_sde

# Backup
docker exec eve_db pg_dump -U eve eve_sde | gzip > backup.sql.gz
```

---

## Troubleshooting

### Service Won't Start

```bash
docker compose logs <service-name>
docker compose restart <service-name>

# Full rebuild
docker compose build --no-cache <service-name>
docker compose up -d <service-name>
```

### Database Connection Failed

```bash
docker ps | grep eve_db
docker start eve_db
docker exec eve_db pg_isready -U eve
```

### Token Expired

```bash
curl http://localhost:8010/api/auth/characters
curl -X POST http://localhost:8010/api/auth/refresh/<character_id>
```

### Frontend Not Updating

```bash
# Rebuild Docker container (serves cached JS bundle)
docker compose build --no-cache public-frontend
docker compose up -d public-frontend
```

### Redis Issues

```bash
docker exec eve-redis redis-cli -a $REDIS_PASSWORD ping
docker exec eve-redis redis-cli -a $REDIS_PASSWORD INFO memory
```

---

## Appendix

### Unit Tests

3,029+ tests across 15 services, <5s runtime:

```bash
cd services/<name> && python3 -m pytest app/tests/ -v --override-ini="addopts="
```

### Key Directories

| Path | Purpose |
|------|---------|
| `docker/docker-compose.yml` | Service orchestration |
| `docker/.env` | Environment configuration |
| `migrations/` | Database migrations (001-111+) |
| `data/tokens.json` | EVE SSO tokens (bind-mounted) |
| `services/` | 17 microservice directories |
| `eve_shared/` | Shared library |
| `public-frontend/` | React frontend source |
| `ectmap/` | Next.js universe map source |

---

**Last Updated:** 2026-02-26
**Maintainer:** Cytrex
