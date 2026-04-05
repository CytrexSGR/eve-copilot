# Backend Development Guide

> **Back to:** [00_INDEX.md](00_INDEX.md) | **Related:** [Architecture](03_ARCHITECTURE.md)
>
> **Last Updated:** 2026-02-26

---

## Project Structure

```
/home/cytrex/eve_copilot/
├── services/                    # 17 Microservices (each with app/ structure)
│   ├── api-gateway/            # Port 8000 — request routing
│   ├── auth-service/           # Port 8010 — EVE SSO, tokens, SaaS
│   ├── war-intel-service/      # Port 8002 — killmails, battles, intel
│   ├── scheduler-service/      # Port 8003 — 40+ cron jobs
│   ├── market-service/         # Port 8004 — prices, arbitrage
│   ├── production-service/     # Port 8005 — manufacturing, PI
│   ├── shopping-service/       # Port 8006 — shopping lists
│   ├── character-service/      # Port 8007 — characters, Dogma engine
│   ├── mcp-service/            # Port 8008 — 609 MCP tools
│   ├── ectmap-service/         # Port 8011 — map data
│   ├── wormhole-service/       # Port 8012 — J-Space intel
│   ├── zkillboard/             # Port 8013 — live kill stream
│   ├── dotlan-service/         # Port 8014 — DOTLAN scraping
│   ├── hr-service/             # Port 8015 — HR, vetting
│   ├── finance-service/        # Port 8016 — SRP, doctrines
│   ├── military-service/       # Port 8017 — D-Scan, PAPs
│   └── public-frontend/        # Port 5173 — nginx
│
├── eve_shared/                  # Shared library
│   ├── db.py                   # DB: cursor() = RealDictCursor, connection() = raw
│   ├── redis_client.py         # Redis: set(key, val, ex=N)
│   ├── constants/              # trade_hubs.py, ship_groups.py
│   ├── utils/error_handling.py # @handle_endpoint_errors() decorator
│   ├── middleware/              # Global exception handler
│   └── esi/                    # Shared ESI client (circuit breaker, token lock)
│
├── migrations/                  # SQL migrations (001-111+)
├── public-frontend/             # React 19 + TypeScript 5 + Vite 7
├── ectmap/                      # Next.js universe map (Port 3001)
└── copilot_server/              # AI Agent runtime (Port 8009)
```

### Service Internal Structure

Each service follows the same pattern:
```
services/<name>/
├── app/
│   ├── main.py              # FastAPI app, router registration
│   ├── config.py            # ServiceConfig (pydantic Settings)
│   ├── database.py          # DB connection (or imports eve_shared)
│   ├── routers/             # API endpoints
│   │   ├── __init__.py
│   │   └── *.py
│   ├── services/            # Business logic
│   ├── models/              # Pydantic models
│   └── tests/               # Unit tests
│       ├── conftest.py      # MockCursor fixtures
│       └── test_*.py
├── Dockerfile
├── pyproject.toml
└── pytest.ini
```

---

## Database

**PostgreSQL 16** (Docker: `eve_db`, internal network only)

```bash
# Connect
echo '<SUDO_PASSWORD>' | sudo -S docker exec eve_db psql -U eve -d eve_sde

# Run migration
cat migrations/111_xxx.sql | sudo -S docker exec -i eve_db psql -U eve -d eve_sde
```

### DB Access Patterns

| Service | Pattern | Notes |
|---------|---------|-------|
| Most services | `from eve_shared.db import get_db` → `db.cursor()` | RealDictCursor, auto-commit |
| war-intel | `from app.database import db_cursor` | DatabasePool singleton, NOT request.app.state.db |
| production | Uses both cursor types | Row access must match cursor type! |

### Key Tables

| Table | Purpose |
|-------|---------|
| `market_prices` | Regional prices (type_id, region_id, lowest_sell, highest_buy) |
| `killmails`, `killmail_attackers`, `killmail_items` | Combat data |
| `battles`, `battle_participants` | Battle tracking |
| `intelligence_hourly_stats` | Pre-aggregated alliance/corp combat stats |
| `corporation_hourly_stats` | Corporation-level combat stats |
| `custom_fittings` | Saved fittings (JSONB items, charges) |
| `production_projects`, `project_items` | Multi-item manufacturing projects |
| `pi_colonies`, `pi_pins`, `pi_routes` | Planetary Industry |
| `dotlan_system_activity`, `dotlan_sov_campaigns` | DOTLAN data |
| `dotlan_adm_history`, `dotlan_alliance_stats` | ADM + rankings |
| `esi_notifications` | ESI notification pipeline |
| `hr_applications` | HR application portal |
| `sov_asset_snapshots` | Sovereignty asset tracking |
| `platform_accounts`, `platform_subscriptions` | SaaS platform |
| `invTypes`, `invGroups`, `mapSolarSystems` | EVE SDE data |
| `dgmTypeAttributes`, `dgmTypeEffects`, `dgmEffects` | Dogma SDE |

### Key DB Gotchas

- `character_skills`: columns are `skill_id`, `trained_skill_level` (NOT `type_id`, `trained_level`)
- `market_prices`: column is `lowest_sell` NOT `sell_price`; PK is `(type_id, region_id)`
- `dgmEffects."effectCategory"`: is NULL for ALL 3,272 effects — Dogma engine derives from durationAttrID/effectName
- `invGroups.published`: is `smallint`, not `boolean` — use `1` not `true`

### Common Queries

```sql
-- Item info
SELECT "typeID", "typeName" FROM "invTypes" WHERE "typeID" = 648;

-- Blueprint materials
SELECT m."materialTypeID", t."typeName", m.quantity
FROM "industryActivityMaterials" m
JOIN "invTypes" t ON m."materialTypeID" = t."typeID"
WHERE m."typeID" = 649 AND m."activityID" = 1;

-- Recent killmails
SELECT k.killmail_id, k.ship_type_id, t."typeName", k.ship_value
FROM killmails k
JOIN "invTypes" t ON k.ship_type_id = t."typeID"
WHERE k.killmail_time > NOW() - INTERVAL '7 days'
ORDER BY k.ship_value DESC LIMIT 20;
```

---

## Unit Tests (~3,029 total, <5s runtime)

| Service | Tests |
|---------|-------|
| character-service | 898 |
| war-intel-service | 529 |
| market-service | 260 |
| wormhole-service | 189 |
| hr-service | 178 |
| finance-service | 176 |
| auth-service | 167 |
| api-gateway | 162 |
| production-service | 145 |
| scheduler-service | 130 |
| eve_shared | 89 |
| mcp-service | 73 |
| dotlan-service | 66 |
| shopping-service | 60 |
| ectmap-service | 40 |

**Run tests:**
```bash
cd services/<name> && python3 -m pytest app/tests/ -v --override-ini="addopts="
```

**Pattern:** Pure function tests, MockCursor fixtures, no DB dependency.

---

## Cron Jobs (Scheduler Service, 40+ Jobs)

| Category | Key Jobs | Schedule |
|----------|----------|----------|
| Market | price fetcher, market hunter, hot items | */4-30 min |
| Combat | killmail importer, battle cleanup, hourly stats | */5-30 min |
| Character | character sync (API-based) | */15 min |
| Doctrine | DBSCAN clustering | */30 min |
| Economy | fuel poller, manipulation scanner | */15-30 min |
| DOTLAN | activity, sov campaigns, ADM, rankings | */30 min - 2h |
| Reports | report generator, Telegram alerts | Various |
| Infra | token re-key, notification sync, sov snapshots | Daily/6h/10min |

---

## EVE Online Data

### Regions (Trade Hubs)

| Key | Region ID | Hub |
|-----|-----------|-----|
| `the_forge` | 10000002 | Jita |
| `domain` | 10000043 | Amarr |
| `heimatar` | 10000030 | Rens |
| `sinq_laison` | 10000032 | Dodixie |
| `metropolis` | 10000042 | Hek |

### Characters

| Name | ID |
|------|-----|
| Cytrex | 1117367444 |
| Artallus | 526379435 |
| Cytricia | 110592475 |
| Mind Overmatter | 2124063958 |

### Corporation

- **Name:** Minimal Industries [MINDI]
- **ID:** 98785281
- **Home:** Isikemi (0.78, 3j from Jita)

---

## API Patterns

### Router Structure (Microservice)

```python
from fastapi import APIRouter, HTTPException, Query
from eve_shared.utils.error_handling import handle_endpoint_errors

router = APIRouter(prefix="/api/example", tags=["example"])

@router.get("/items/{item_id}")
@handle_endpoint_errors()
async def get_item(item_id: int):
    with db.cursor() as cur:
        cur.execute("SELECT * FROM items WHERE type_id = %s", (item_id,))
        item = cur.fetchone()
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    return item
```

### Register in main.py

```python
from app.routers.example import router as example_router
app.include_router(example_router)
```

---

## Critical Patterns

### 1. Parameterized Queries (ALWAYS)

```python
# CORRECT
cur.execute("SELECT * FROM items WHERE type_id = %s", (type_id,))

# WRONG - SQL Injection!
cur.execute(f"SELECT * FROM items WHERE type_id = {type_id}")
```

### 2. Batch Operations

```python
# CORRECT - Single query
cur.execute("SELECT * FROM market_prices WHERE type_id = ANY(%s)", (type_ids,))

# WRONG - N+1 queries
for type_id in type_ids:
    cur.execute("SELECT * FROM market_prices WHERE type_id = %s", (type_id,))
```

### 3. Redis Caching

```python
from eve_shared.redis_client import RedisClient

redis = RedisClient()
redis.set("key", value, ex=300)  # 5min TTL
# NOTE: Use set(key, val, ex=N), NOT setex()
```

### 4. Error Handling

```python
from eve_shared.utils.error_handling import handle_endpoint_errors

@router.get("/endpoint")
@handle_endpoint_errors()  # Maps exceptions to HTTP status codes
async def endpoint():
    ...
```

### 5. Material Efficiency

```python
me_factor = 1 - (me_level / 100)  # ME 10 = 0.9
adjusted_quantity = max(1, int(base_quantity * me_factor))
```

---

## SDE Management

**Source:** https://www.fuzzwork.co.uk/dump/

```bash
cd /home/cytrex/eve_data

# Download & extract
curl -L -o sqlite-latest.sqlite.bz2 "https://www.fuzzwork.co.uk/dump/sqlite-latest.sqlite.bz2"
bunzip2 -f sqlite-latest.sqlite.bz2

# Migrate
python3 migrate_sde.py
```

---

## Troubleshooting

### Service won't start

```bash
cd /home/cytrex/eve_copilot/docker
docker compose logs <service-name>
docker compose restart <service-name>
```

### Database connection failed

```bash
echo '<SUDO_PASSWORD>' | sudo -S docker ps | grep eve_db
echo '<SUDO_PASSWORD>' | sudo -S docker start eve_db
```

### Token expired

```bash
curl http://localhost:8010/api/auth/characters
curl -X POST http://localhost:8010/api/auth/refresh/1117367444
```

### Rebuild service after code change

```bash
cd /home/cytrex/eve_copilot/docker
docker compose build --no-cache <service-name>
docker compose up -d <service-name>
```
