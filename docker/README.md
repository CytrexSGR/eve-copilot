# EVE Co-Pilot Microservices

Docker Compose setup for the EVE Co-Pilot microservices architecture.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              API Gateway (:8000)                             │
│                    Routes requests to microservices                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
         ┌────────────────┬───────────┼───────────┬────────────────┐
         │                │           │           │                │
         ▼                ▼           ▼           ▼                ▼
┌──────────────┐  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│war-intel-svc │  │scheduler-svc │ │market-service│ │production-svc│ │shopping-svc  │
│   (:8002)    │  │   (:8003)    │ │   (:8004)    │ │   (:8005)    │ │   (:8006)    │
│              │  │              │ │              │ │              │ │              │
│• Battles     │  │• Cron jobs   │ │• Prices      │ │• Blueprints  │ │• Lists       │
│• Power Blocs │  │• Coalition   │ │• Arbitrage   │ │• PI          │ │• Materials   │
│• Intel       │  │• Corp Sync   │ │• Orders      │ │• Cost calc   │ │• Transport   │
└──────────────┘  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
         │                │           │           │                │
         ▼                ▼           ▼           ▼                ▼
┌──────────────┐  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│character-svc │  │auth-service  │ │ectmap-service│ │wormhole-svc  │ │zkillboard    │
│   (:8007)    │  │   (:8010)    │ │   (:8011)    │ │   (:8012)    │ │   (:8013)    │
│              │  │              │ │              │ │              │ │              │
│• Wallet      │  │• EVE SSO     │ │• Screenshots │ │• J-Space     │ │• RedisQ      │
│• Assets      │  │• Tokens      │ │• Playwright  │ │• Residents   │ │• Live Stream │
│• Skills      │  │• Characters  │ │• Maps        │ │• Threats     │ │• Detection   │
└──────────────┘  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
         │                │           │           │                │
         └────────────────┴───────────┼───────────┴────────────────┘
                                      │
         ┌────────────────────────────┼────────────────────────────┐
         │                            │                            │
         ▼                            ▼                            ▼
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│   PostgreSQL    │      │     Redis       │      │  ectmap (3001)  │
│    (:5432)      │      │    (:6379)      │      │                 │
│                 │      │                 │      │ • Next.js Map   │
│ • EVE SDE       │      │ • L1 Cache      │      │ • 501MB SDE     │
│ • Killmails     │      │ • Sessions      │      │ • Battle Layer  │
│ • Battles       │      │ • State         │      │ • Live Kills    │
└─────────────────┘      └─────────────────┘      └─────────────────┘
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| **api-gateway** | 8000 | Main entry point, routes to all services |
| war-intel-service | 8002 | Killmails, battles, intelligence, power blocs |
| scheduler-service | 8003 | Cron jobs, background tasks (coalition refresh, corp sync) |
| market-service | 8004 | Market prices, orders, arbitrage |
| production-service | 8005 | Blueprints, manufacturing costs, PI |
| shopping-service | 8006 | Shopping lists, materials |
| character-service | 8007 | Character data, wallet, assets, skills |
| auth-service | 8010 | EVE SSO OAuth, token management |
| ectmap-service | 8011 | Map screenshot generation (Playwright + Chromium) |
| wormhole-service | 8012 | Wormhole intel, resident detection, threat feed |
| zkillboard-service | 8013 | zkillboard RedisQ live stream, battle detection |
| ectmap (frontend) | 3001 | Next.js interactive map with SDE data |
| public-frontend | 5173 | React SPA (Vite + nginx, production build) |
| postgres | 5432 | PostgreSQL database (internal network) |
| redis | 6379 | Redis cache (internal network) |
| prometheus | 9090 | Metrics collection |
| grafana | 3200 | Dashboards & visualization |
| loki | 3100 | Log aggregation |

## Quick Start

### 1. Setup Environment

```bash
cd /home/cytrex/eve_copilot/docker

# Copy and configure environment
cp .env.example .env
nano .env  # Fill in your values
```

### 2. Start All Services

```bash
# Start everything
docker compose up -d

# Or start with build
docker compose up -d --build

# Check status
docker compose ps
```

### 3. Verify Health

```bash
# Gateway health
curl http://localhost:8000/health

# All services health
curl http://localhost:8000/health/services

# Individual service
curl http://localhost:8001/health  # auth-service
```

## API Routes

The API Gateway routes requests to the appropriate microservice:

| Path | Service |
|------|---------|
| `/api/auth/*` | auth-service |
| `/api/war/*` | war-intel-service |
| `/api/panoptikum/*` | war-intel-service |
| `/api/intelligence/*` | war-intel-service |
| `/api/scheduler/*` | scheduler-service |
| `/api/market/*` | market-service |
| `/api/production/*` | production-service |
| `/api/reactions/*` | production-service |
| `/api/shopping/*` | shopping-service |
| `/api/character/*` | character-service |

## Development

### View Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f api-gateway
docker compose logs -f market-service
```

### Restart Service

```bash
docker compose restart market-service
```

### Rebuild Service

```bash
docker compose up -d --build market-service
```

### Scale Service

```bash
# Run 3 instances of market-service
docker compose up -d --scale market-service=3
```

## Database

### Connect to PostgreSQL

```bash
docker compose exec postgres psql -U eve -d eve_sde
```

### Run Migrations

```bash
# Copy migration file into container
docker compose exec -T postgres psql -U eve -d eve_sde < ../migrations/XXX_migration.sql
```

## Monitoring

### Grafana

Access Grafana at http://localhost:3200

- Default user: `admin`
- Password: Set in `.env` (`GRAFANA_PASSWORD`)

### Prometheus

Access Prometheus at http://localhost:9090

All services expose `/metrics` endpoint for Prometheus scraping.

## Troubleshooting

### Service Won't Start

```bash
# Check logs
docker compose logs service-name

# Check resource usage
docker stats

# Restart with fresh build
docker compose up -d --build --force-recreate service-name
```

### Connection Refused

1. Check if service is running: `docker compose ps`
2. Check network: `docker network ls`
3. Verify environment variables in `.env`

### Database Connection Issues

```bash
# Test connection
docker compose exec postgres pg_isready -U eve -d eve_sde

# Check postgres logs
docker compose logs postgres
```

## Production Deployment

For production, consider:

1. **Secrets Management**: Use Docker secrets or external secret store
2. **Resource Limits**: Already configured in docker-compose.yml
3. **Logging**: Configure log rotation and external aggregation
4. **Backups**: Schedule PostgreSQL backups
5. **Load Balancing**: Use Traefik or nginx in front of api-gateway
6. **TLS**: Configure HTTPS termination

### Example Production Override

Create `docker-compose.prod.yml`:

```yaml
services:
  api-gateway:
    environment:
      LOG_LEVEL: WARN
    deploy:
      replicas: 2

  postgres:
    volumes:
      - /data/postgres:/var/lib/postgresql/data
```

Run with:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```
