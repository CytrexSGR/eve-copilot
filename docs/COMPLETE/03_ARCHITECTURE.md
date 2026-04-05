# EVE Co-Pilot Architecture

> **Back to:** [CLAUDE.md](CLAUDE.md)
>
> **Last Updated:** 2026-02-26

---

## System Overview

EVE Co-Pilot is a comprehensive intelligence, industry, fitting analysis, and alliance management platform for EVE Online. 17 microservices, 111+ database migrations, 3,029+ unit tests, full Dogma Engine v4. Public combat intelligence dashboard + SaaS management suite.

## Architecture

All services run as Docker containers orchestrated via Docker Compose. The monolith was **decommissioned on 2026-02-10** (~73,000 lines removed). Legacy code that is still needed by scheduler and zkillboard services is preserved in `services/scheduler-service/monolith/` and `services/zkillboard/legacy/`.

---

## Microservices Architecture

> **Documentation:** [docker/README.md](docker/README.md)

### Microservices Overview

```
                         ┌─────────────────────────────────────────┐
                         │           External Data Sources         │
                         │  EVE ESI API │ zKillboard │ EVE Ref     │
                         └───────────────────┬─────────────────────┘
                                             │
                         ┌───────────────────▼─────────────────────┐
                         │            API Gateway (:8000)          │
                         │     Routes requests to microservices    │
                         │     CORS │ Rate Limiting │ Health       │
                         └───────────────────┬─────────────────────┘
                                             │
    ┌──────────┬──────────┬─────────┬────────┼────────┬─────────┬──────────┐
    │          │          │         │        │        │         │          │
    ▼          ▼          ▼         ▼        ▼        ▼         ▼          ▼
┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
│  auth  │ │  war   │ │ sched  │ │ market │ │  prod  │ │  shop  │ │  char  │
│ :8001  │ │ :8002  │ │ :8003  │ │ :8004  │ │ :8005  │ │ :8006  │ │ :8007  │
└────┬───┘ └────┬───┘ └────┬───┘ └────┬───┘ └────┬───┘ └────┬───┘ └────┬───┘
     │          │          │          │          │          │          │
     │          │          │          │          │          │          │
     └──────────┴──────────┴──────────┴────┬─────┴──────────┴──────────┘
                                           │
                    ┌──────────────────────┼──────────────────────┐
                    │                      │                      │
                    ▼                      ▼                      ▼
             ┌───────────┐          ┌───────────┐          ┌───────────┐
             │ PostgreSQL│          │   Redis   │          │Observabil.│
             │  (:5432)  │          │  (:6379)  │          │ Prometheus│
             │  eve_sde  │          │  L1 Cache │          │  Grafana  │
             └───────────┘          └───────────┘          │   Loki    │
                                                           └───────────┘
```

### Service Overview

| Service | Port | Responsibility |
|---------|------|----------------|
| **api-gateway** | 8000 | Request routing, CORS, health aggregation |
| auth-service | 8010 | EVE SSO OAuth, token management |
| war-intel-service | 8002 | Killmails, battles, intelligence, reports |
| scheduler-service | 8003 | Cron jobs, APScheduler integration |
| market-service | 8004 | Market prices, orders, arbitrage |
| production-service | 8005 | Blueprints, manufacturing, reactions, PI |
| shopping-service | 8006 | Shopping lists, materials, transport |
| character-service | 8007 | Character data, wallet, assets, skills, Dogma engine |
| mcp-service | 8008 | 609 dynamic MCP tools for AI agent |
| ectmap-service | 8011 | Map data service for universe map |
| wormhole-service | 8012 | J-Space intelligence, wormhole tracking |
| zkillboard | 8013 | Live kill stream (RedisQ) |
| dotlan-service | 8014 | DOTLAN EveMaps scraping (activity, sov, ADM) |
| hr-service | 8015 | HR, vetting, applications, risk scoring |
| finance-service | 8016 | SRP, doctrines, buyback, invoices |
| military-service | 8017 | D-Scan parser, fleet PAPs, timerboard |
| public-frontend | 5173 | Public dashboard (nginx, React 19) |

**Infrastructure:** Redis 7, PostgreSQL 16 (eve_db container), Prometheus, Grafana, Loki, Alertmanager

### API Gateway Routes

| Path Prefix | Target Service |
|-------------|----------------|
| `/api/auth/*` | auth-service |
| `/api/war/*`, `/api/intelligence/*`, `/api/powerbloc/*`, `/api/reports/*` | war-intel-service |
| `/api/scheduler/*` | scheduler-service |
| `/api/market/*` | market-service |
| `/api/production/*`, `/api/reactions/*`, `/api/pi/*` | production-service |
| `/api/shopping/*` | shopping-service |
| `/api/character/*`, `/api/fittings/*`, `/api/sde/*`, `/api/mastery/*` | character-service |
| `/api/wormhole/*` | wormhole-service |
| `/api/dotlan/*` | dotlan-service |
| `/api/hr/*` | hr-service |
| `/api/finance/*`, `/api/srp/*`, `/api/doctrines/*` | finance-service |
| `/api/military/*` | military-service |

### Quick Start (Docker)

```bash
cd /home/cytrex/eve_copilot/docker
cp .env.example .env
# Edit .env with your configuration
docker compose up -d --build

# Verify
curl http://localhost:8000/health/services
```

### Directory Structure

```
/home/cytrex/eve_copilot/
├── services/                    # 17 Microservices
│   ├── api-gateway/            # Port 8000
│   ├── auth-service/           # Port 8010
│   ├── war-intel-service/      # Port 8002
│   ├── scheduler-service/      # Port 8003 (+ monolith/ legacy code)
│   ├── market-service/         # Port 8004
│   ├── production-service/     # Port 8005
│   ├── shopping-service/       # Port 8006
│   ├── character-service/      # Port 8007 (+ Dogma engine)
│   ├── mcp-service/            # Port 8008
│   ├── ectmap-service/         # Port 8011
│   ├── wormhole-service/       # Port 8012
│   ├── zkillboard/             # Port 8013 (+ legacy/ shared code)
│   ├── dotlan-service/         # Port 8014
│   ├── hr-service/             # Port 8015
│   ├── finance-service/        # Port 8016
│   ├── military-service/       # Port 8017
│   └── public-frontend/        # Port 5173 (nginx)
├── eve_shared/                  # Shared library (DB, Redis, constants, middleware)
├── public-frontend/             # React 19 + TypeScript 5 + Vite 7
├── ectmap/                      # Next.js universe map (Port 3001)
├── copilot_server/              # AI Agent runtime (Port 8009)
├── docker/
│   ├── docker-compose.yml      # Service orchestration
│   └── .env.example            # Environment template
├── migrations/                  # Database migrations (001-111+)
└── docs/                        # Documentation
```

---

## Components

### 1. Backend (17 Microservices)

Each service is an independent FastAPI application running in its own Docker container with 4 uvicorn workers.

**Key Service Capabilities:**

| Service | Key Features |
|---------|-------------|
| **war-intel-service** | Killmails, battles, alliance/corp/powerbloc intelligence, doctrine detection, DOTLAN overlays, reports |
| **character-service** | Character sync, skills, wallets, assets, Dogma Engine v4, fitting stats, SDE browser, ship mastery |
| **production-service** | Blueprints, manufacturing, reactions, PI (chains, colonies, projects, empire), production projects |
| **market-service** | Market prices, orders, arbitrage, market hunter, price history |
| **finance-service** | SRP claims, doctrine CRUD (EFT/DNA), buyback (Janice), invoices, mining tax |
| **hr-service** | Vetting engine (5-stage risk scoring), red list, applications, corp history analysis |
| **scheduler-service** | APScheduler with 40+ cron jobs, legacy monolith code for active jobs |
| **auth-service** | EVE SSO OAuth2, token management, platform accounts, SaaS subscriptions |
| **shopping-service** | Shopping lists, freight pricing, route optimization |
| **wormhole-service** | Wormhole system DB, resident tracking, Thera routes, eviction analysis |
| **dotlan-service** | DOTLAN scraping (activity, sov campaigns, ADM, alliance rankings) |
| **military-service** | D-Scan parser, local scan, fleet PAPs, Discord relay, timerboard |

### 2. Shared Libraries (eve_shared)

**Location:** `/home/cytrex/eve_copilot/eve_shared/`

| Module | Purpose |
|--------|---------|
| `db.py` | Database connection: `db.cursor()` (RealDictCursor, auto-commit), `db.connection()` (raw conn) |
| `redis_client.py` | Redis client: `set(key, val, ex=N)`, prefix-based clearing |
| `constants/trade_hubs.py` | JITA_REGION_ID, trade hub definitions |
| `constants/ship_groups.py` | CAPITAL_GROUP_IDS (8 groups), ship classification |
| `utils/error_handling.py` | `@handle_endpoint_errors()` decorator for all endpoints |
| `middleware/exception_handler.py` | Global exception handler registered in all 12 services |
| `esi/client.py` | Shared ESI client with circuit breaker, token lock, pagination |

### 3. Data Layer (Repository Pattern)

**Architecture:** Three-tier hybrid caching with automatic fallback:
```
┌─────────────────────────────────────────────────────────────────────────┐
│                    UNIFIED DATA LAYER (Repository Pattern)              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   Business Logic (Routers, Services)                                    │
│           │                                                             │
│           v                                                             │
│   ┌───────────────────────────────────────────────────────────────┐     │
│   │  UnifiedMarketRepository / KillmailRepository / CharacterRepo │     │
│   │  (Single interface - caller doesn't know data source)         │     │
│   └───────────────────────────────────────────────────────────────┘     │
│           │                                                             │
│           v                                                             │
│   ┌───────────────┐   ┌───────────────┐   ┌───────────────┐             │
│   │  L1: Redis    │ → │  L2: Postgres │ → │  L3: ESI API  │             │
│   │  (5 min TTL)  │   │  (1 hour TTL) │   │  (Fallback)   │             │
│   │  Hot items    │   │  Persistent   │   │  Fresh data   │             │
│   └───────────────┘   └───────────────┘   └───────────────┘             │
│           ↑                   ↑                   │                     │
│           └───────────────────┴───────────────────┘                     │
│                    Write-through on cache miss                          │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**Market Data (market-service):**
- 3-tier caching: Redis L1 (5min TTL) → PostgreSQL L2 → ESI API L3
- 56 hot items proactively refreshed every 4 minutes
- Regional price tracking, arbitrage with fee engine

**Character Data (character-service):**
- Per-data-type TTLs (wallet: 5m, skills: 1h, assets: 30m)
- Dogma Engine v4 for fitting stats calculation
- Auto-sync every 15 minutes via scheduler

**Combat Intelligence (war-intel-service):**
- Real-time killmail processing via zKillboard RedisQ
- Battle detection (5+ kills in 5min window)
- Alliance/Corp/PowerBloc analytics with dual efficiency (ISK + K/D)
- Doctrine detection via DBSCAN clustering
- DOTLAN integration (activity, sov campaigns, ADM history)

### 4. Database (PostgreSQL)

**Container:** `eve_db`
**Database:** `eve_sde`

#### Schema Overview

**SDE & Market Tables:**
```
+-------------------+     +-------------------+     +-------------------+
| invTypes          |     | market_prices     |     | shopping_lists    |
| (EVE SDE)         |     | (App Data)        |     | (App Data)        |
+-------------------+     +-------------------+     +-------------------+
| typeID (PK)       |     | type_id           |     | id (PK)           |
| typeName          |     | region_id         |     | name              |
| groupID           |     | lowest_sell       |     | created_at        |
| volume            |     | highest_buy       |     +-------------------+
+-------------------+     | sell_volume       |              |
        |                 | updated_at        |              |
        v                 +-------------------+              v
+-------------------+                              +-------------------+
| industryActivity  |                              | shopping_list_    |
| Materials         |                              | items             |
+-------------------+                              +-------------------+
| typeID            |                              | id (PK)           |
| materialTypeID    |                              | list_id (FK)      |
| quantity          |                              | type_id           |
+-------------------+                              | quantity          |
                                                   +-------------------+
```

**Combat Intelligence Tables (Real-Time):**
```
+---------------------------+     +---------------------------+
| killmails                 |     | killmail_attackers        |
+---------------------------+     +---------------------------+
| killmail_id (PK)          |     | id (PK)                   |
| killmail_time             |     | killmail_id (FK)          |
| solar_system_id           |     | character_id              |
| region_id                 |     | corporation_id            |
| ship_type_id              |     | alliance_id               |
| ship_value                |     | ship_type_id              |
| victim_character_id       |     | weapon_type_id            |
| victim_corporation_id     |     | damage_done               |
| victim_alliance_id        |     | is_final_blow             |
| final_blow_alliance_id    |     +---------------------------+
| ship_class                |              |
| ship_category             |              v
| battle_id (FK)            |     +---------------------------+
+---------------------------+     | killmail_items            |
           |                      +---------------------------+
           v                      | id (PK)                   |
+---------------------------+     | killmail_id (FK)          |
| battles                   |     | type_id                   |
+---------------------------+     | quantity_dropped          |
| battle_id (PK)            |     | quantity_destroyed        |
| solar_system_id           |     +---------------------------+
| region_id                 |
| started_at                |
| last_kill_at              |
| ended_at                  |
| total_kills               |
| total_isk_destroyed       |
| capital_kills             |
| status (active/ended)     |
| telegram_message_id       |
+---------------------------+
           |
           v
+---------------------------+
| battle_participants       |
+---------------------------+
| id (PK)                   |
| battle_id (FK)            |
| alliance_id               |
| corporation_id            |
| kills                     |
| losses                    |
| isk_destroyed             |
| isk_lost                  |
+---------------------------+
```

**Sovereignty & Legacy Tables:**
```
+-------------------+     +-------------------+     +-------------------+
| combat_ship_      |     | system_region_    |     | fw_system_        |
| losses (Legacy)   |     | map               |     | status            |
+-------------------+     +-------------------+     +-------------------+
| id (PK)           |     | system_id (PK)    |     | system_id (PK)    |
| type_id           |     | region_id         |     | faction_id        |
| region_id         |     | system_name       |     | contested_percent |
| system_id         |     | security          |     | updated_at        |
| quantity          |     +-------------------+     +-------------------+
| kill_date         |
+-------------------+
```

**War Economy Tables:**
```
+---------------------------+     +---------------------------+     +---------------------------+
| war_economy_fuel_         |     | war_economy_price_        |     | war_economy_manipulation_ |
| snapshots                 |     | history                   |     | alerts                    |
+---------------------------+     +---------------------------+     +---------------------------+
| id (PK)                   |     | id (PK)                   |     | id (PK)                   |
| region_id                 |     | type_id                   |     | type_id                   |
| type_id                   |     | region_id                 |     | region_id                 |
| volume                    |     | price                     |     | alert_type                |
| price                     |     | volume                    |     | z_score                   |
| snapshot_time             |     | snapshot_time             |     | detected_at               |
+---------------------------+     +---------------------------+     +---------------------------+

+---------------------------+
| war_economy_supercap_     |
| timers                    |
+---------------------------+
| id (PK)                   |
| type_id (ship type)       |
| region_id                 |
| system_id                 |
| alliance_id               |
| estimated_completion      |
| confidence                |
| status                    |
+---------------------------+
```

**Doctrine Detection Tables:**
```
+---------------------------+     +---------------------------+     +---------------------------+
| doctrine_fleet_           |     | doctrine_templates        |     | doctrine_items_of_        |
| snapshots                 |     |                           |     | interest                  |
+---------------------------+     +---------------------------+     +---------------------------+
| id (PK)                   |     | id (PK)                   |     | id (PK)                   |
| battle_id                 |     | name                      |     | doctrine_template_id (FK) |
| alliance_id               |     | alliance_id               |     | type_id                   |
| snapshot_time             |     | ship_composition (JSONB)  |     | category                  |
| ship_composition (JSONB)  |     | confidence                |     | priority                  |
| total_pilots              |     | created_at                |     +---------------------------+
+---------------------------+     +---------------------------+

+---------------------------+     +---------------------------+
| doctrine_predefined_      |     | detected_doctrines        |
| templates                 |     |                           |
+---------------------------+     +---------------------------+
| id (PK)                   |     | id (PK)                   |
| name                      |     | battle_id                 |
| description               |     | template_id (FK)          |
| ship_composition (JSONB)  |     | alliance_id               |
| created_by                |     | confidence                |
+---------------------------+     | detected_at               |
                                  +---------------------------+
```

**Character Data Tables:**
```
+---------------------------+     +---------------------------+
| character_capabilities    |     | character_skill_          |
|                           |     | snapshots                 |
+---------------------------+     +---------------------------+
| id (PK)                   |     | id (PK)                   |
| character_id              |     | character_id              |
| capability_type           |     | skill_id                  |
| capability_value          |     | level                     |
| updated_at                |     | skill_points              |
+---------------------------+     | snapshot_time             |
                                  +---------------------------+
```

**Industry Module Tables:**
```
+---------------------------+     +---------------------------+     +---------------------------+
| tax_profiles              |     | facility_profiles         |     | system_cost_indices       |
+---------------------------+     +---------------------------+     +---------------------------+
| id (PK)                   |     | id (PK)                   |     | system_id (PK)            |
| name                      |     | name                      |     | activity (PK)             |
| character_id (nullable)   |     | character_id (nullable)   |     | cost_index                |
| broker_fee_buy (%)        |     | structure_type            |     | updated_at                |
| broker_fee_sell (%)       |     | me_bonus (%)              |     +---------------------------+
| sales_tax (%)             |     | te_bonus (%)              |
| is_default                |     | cost_reduction (%)        |
| created_at                |     | system_id                 |
+---------------------------+     | is_default                |
                                  +---------------------------+

+---------------------------+     +---------------------------+
| character_asset_cache     |     | production_ledger         |
+---------------------------+     +---------------------------+
| id (PK)                   |     | id (PK)                   |
| character_id              |     | character_id              |
| type_id                   |     | name                      |
| quantity                  |     | target_type_id            |
| location_id               |     | target_quantity           |
| cached_at                 |     | status (planning/active/  |
+---------------------------+     |        completed/cancelled)|
                                  | created_at                |
                                  +---------------------------+
                                           |
           +-------------------------------+-------------------------------+
           |                               |                               |
           v                               v                               v
+---------------------------+     +---------------------------+     +---------------------------+
| ledger_stages             |     | ledger_jobs               |     | ledger_materials          |
+---------------------------+     +---------------------------+     +---------------------------+
| id (PK)                   |     | id (PK)                   |     | id (PK)                   |
| ledger_id (FK)            |     | stage_id (FK)             |     | job_id (FK)               |
| name                      |     | type_id                   |     | type_id                   |
| order_index               |     | runs                      |     | quantity_required         |
| status                    |     | status (pending/running/  |     | quantity_available        |
+---------------------------+     |        completed)         |     +---------------------------+
                                  | started_at                |
                                  | completed_at              |
                                  +---------------------------+

+---------------------------+     +---------------------------+     +---------------------------+
| reaction_formulas         |     | reaction_formula_inputs   |     | moon_material_prices      |
+---------------------------+     +---------------------------+     +---------------------------+
| id (PK)                   |     | id (PK)                   |     | type_id (PK)              |
| output_type_id            |     | formula_id (FK)           |     | buy_price                 |
| output_quantity           |     | input_type_id             |     | sell_price                |
| duration_seconds          |     | input_quantity            |     | updated_at                |
| reaction_type             |     +---------------------------+     +---------------------------+
| imported_at               |
+---------------------------+

+---------------------------+     +---------------------------+     +---------------------------+
| pi_colonies               |     | pi_pins                   |     | pi_routes                 |
+---------------------------+     +---------------------------+     +---------------------------+
| id (PK)                   |     | id (PK)                   |     | id (PK)                   |
| character_id              |     | colony_id (FK)            |     | colony_id (FK)            |
| planet_id                 |     | pin_id                    |     | route_id                  |
| planet_type               |     | type_id                   |     | source_pin_id             |
| solar_system_id           |     | schematic_id              |     | destination_pin_id        |
| upgrade_level             |     | product_type_id           |     | content_type_id           |
| num_pins                  |     | expiry_time               |     | quantity                  |
| last_update               |     | qty_per_cycle             |     +---------------------------+
| last_sync                 |     | cycle_time                |
+---------------------------+     +---------------------------+
```

### 5. Public Frontend (React 19 + TypeScript 5)

**Location:** `/home/cytrex/eve_copilot/public-frontend/`
**Framework:** Vite 7 + React 19 + TypeScript 5
**Port:** 5173 (Docker nginx) / 5175 (Vite dev server)

#### Key Pages

| Page | Route | Purpose |
|------|-------|---------|
| Home | `/` | Auth-conditional: hero/CTA (unauthenticated) or dashboard (logged in) |
| Battle Report | `/battles` | 24h battle report with ectmap integration |
| Battle Detail | `/battle/:id` | Individual battle analytics with attacker loadouts, tank analysis |
| Ectmap | `/ectmap` | Interactive universe map with intel overlays |
| Alliance Detail | `/alliance/:id` | Alliance intelligence (offensive, defensive, geography, capitals, pilots) |
| Corporation Detail | `/corporation/:id` | Corporation intelligence (same tabs as alliance) |
| PowerBloc Detail | `/powerbloc/:id` | Coalition intelligence (same tabs as alliance) |
| Fitting Browser | `/fittings` | ESI + shared fittings browser with ship class filter |
| Fitting Editor | `/fittings/new` | Interactive fitting editor with live Dogma stats |
| Fitting Detail | `/fittings/:type/:id` | Fitting stats, slots, resist profile, EFT export |
| Fitting Comparison | `/fittings/compare` | Side-by-side 2-4 fitting comparison |
| Production | `/production` | Production planner, projects, PI chain browser, PI empire |
| Shopping | `/shopping` | Shopping wizard, shopping lists, route optimization |
| Market | `/market` | Market suite with hub selector, arbitrage |
| Wormhole | `/wormhole` | Wormhole intel, Thera router |
| Corp Management | `/corp/*` | HR, Finance, SRP, Military, Sovereignty tabs |
| Character Dashboard | `/characters` | Multi-character portfolio (wallets, assets, skills, implants) |
| Pricing | `/pricing` | SaaS tier comparison and upgrade flow |
| War Economy | `/war-economy` | Fuel tracking, manipulation detection |

#### Component Structure

```
src/components/
├── alliance/           # Alliance intelligence views (7 tabs)
├── corporation/        # Corporation intelligence views (7 tabs)
├── powerbloc/          # PowerBloc intelligence views
├── battle/             # Battle detail panels (12 components)
├── fittings/           # Fitting browser, editor, stats panels
├── production/         # Production planner, PI chain browser, PI empire
├── war-intel/          # War economy, doctrines
├── shared/             # LiveMapView, Spinner, etc.
└── ...                 # 34+ component directories
```

### 6. ECTMap (Next.js Universe Map)

**Location:** `/home/cytrex/eve_copilot/ectmap/`
**Framework:** Next.js 16 (Turbopack)
**Port:** 3001

Canvas-based EVE Online universe map with:
- Color modes: Region, Security, FW, Sovereignty, ADM, Hunting
- DOTLAN overlays: NPC kills, ship kills, jumps, ADM, IHUB campaigns
- Intel overlays: Hunting heatmap, capital threat zones, logistics strength
- Entity activity mode: Corp/Alliance/PowerBloc system heatmap
- Live battle icons with status filters (Gank/Brawl/Battle/Hellcamp)
- Live kill skulls with 5s refresh

### 7. Scheduler Service (40+ Cron Jobs)

All cron jobs run inside the scheduler-service container via APScheduler. Key jobs:

| Category | Jobs | Schedule |
|----------|------|----------|
| **Market** | Price fetcher, market hunter, hot items refresh | */4-30 min |
| **Combat** | Killmail importer, battle cleanup, hourly stats aggregation | */5-30 min |
| **Character** | Character sync (API-based, not direct DB) | */15 min |
| **Doctrine** | DBSCAN clustering, fleet snapshot collection | */30 min |
| **Economy** | Fuel poller, manipulation scanner, price snapshots | */15-30 min |
| **DOTLAN** | Activity scraper, sov campaigns, ADM, rankings | */30 min - 2h |
| **Reports** | Report generator, Telegram alerts | Various |
| **Infrastructure** | Token re-key, notification sync, sov asset snapshots | Daily/6h/10min |
| **Real-time** | zKillboard RedisQ listener | Daemon |

---

## Data Flows

### 1. Market Price Flow (Hybrid Caching)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    MARKET PRICE DATA FLOW                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   Application (Router/Service)                                          │
│           │                                                             │
│           v                                                             │
│   UnifiedMarketRepository.get_price(type_id)                           │
│           │                                                             │
│           ├── 1. Check L1 Redis ──→ HIT? Return (source=REDIS)         │
│           │                                                             │
│           ├── 2. Check L2 PostgreSQL ──→ HIT? Promote to L1, Return    │
│           │                               (source=CACHE)                │
│           │                                                             │
│           └── 3. Fetch from ESI ──→ Write to L1+L2, Return             │
│                                      (source=ESI)                       │
│                                                                         │
│   Background: market_hot_items_refresher.py (*/4 min)                  │
│           │                                                             │
│           └── Proactively refresh 56 hot items before TTL expires      │
│               (minerals, isotopes, fuel blocks, moon materials)         │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘

Legacy flow (deprecated):
ESI Market API → regional_price_fetcher.py → market_prices table
```

### 2. Authentication Flow

```
User → /api/auth/login → EVE SSO → /api/auth/callback → tokens.json
                                                              ↓
                                                        ESI API calls
                                                        (wallet, assets, etc.)
```

### 3. War Room Data Flow (Batch)

```
EVE Ref → killmail_fetcher.py → combat_ship_losses + combat_item_losses
                                            ↓
ESI Sov → sov_tracker.py → sovereignty_campaigns
                                            ↓
ESI FW → fw_tracker.py → fw_system_status
                                            ↓
                                    war_analyzer.py
                                            ↓
                                    /api/war/* endpoints
```

### 4. Real-Time Battle Tracking Flow

```
zKillboard RedisQ → redisq_client.py → live_service.py
                                              |
                    +-------------------------+-------------------------+
                    |                         |                         |
                    v                         v                         v
           +---------------+          +---------------+          +---------------+
           | Redis         |          | PostgreSQL    |          | Notifications |
           | (Hot Storage) |          | killmails     |          |               |
           | 24h TTL       |          | battles       |          | Telegram Bot  |
           +---------------+          | battle_       |          | Discord       |
                    |                 | participants  |          +---------------+
                    v                 +---------------+
           +---------------+                  |
           | Hotspot       |                  v
           | Detection     |          +---------------+
           | (5 kills/5min)|          | /api/war/*    |
           +---------------+          | endpoints     |
                                      +---------------+
```

**Battle Detection Logic:**
1. Killmail received via RedisQ polling (10s interval)
2. Check for active battle in same system (30min window)
3. Create new battle or update existing
4. Update battle_participants (alliance/corp stats)
5. Send Telegram alert at milestones (10, 25, 50, 100+ kills)
6. End battle after 30min inactivity

### 5. Shopping List Flow

```
User selects item → /api/production/optimize/{type_id} → Material list
                                                              ↓
                                            /api/shopping/lists/{id}/add-production
                                                              ↓
                                                    shopping_list_items
```

### 6. War Economy Data Flow

```
ESI Market API → economy_fuel_poller.py → war_economy_fuel_snapshots
                                                    ↓
                                         Anomaly Detection (volume spikes)
                                                    ↓
                                         Capital Movement Prediction
                                                    ↓
                                         /api/war/economy/* endpoints

ESI Market API → economy_price_snapshotter.py → war_economy_price_history
                                                         ↓
                              economy_manipulation_scanner.py
                                                         ↓
                              Z-Score Analysis (>3σ = manipulation)
                                                         ↓
                              war_economy_manipulation_alerts
```

### 7. Doctrine Detection Flow

```
zkillboard → killmails → doctrine_clustering.py (every 30min)
                                    |
                    +---------------+---------------+
                    |               |               |
                    v               v               v
           Fleet Snapshots   DBSCAN Clustering   Template Matching
           (5-min windows)   (cosine similarity) (known doctrines)
                    |               |               |
                    +-------+-------+---------------+
                            |
                            v
                   doctrine_templates
                            |
                            v
                   doctrine_items_of_interest
                            |
                            v
                   War Profiteering / Supply Chain Intelligence
```

### 8. Planetary Industry (PI) Data Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        PI PROJECT MANAGEMENT                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   User creates project → pi_projects                                    │
│           │                                                             │
│           v                                                             │
│   GET /api/pi/chain/{type_id} → PISchematicService.get_production_chain│
│           │                                                             │
│           v                                                             │
│   Production chain tree (P0→P4) with quantities                         │
│           │                                                             │
│           v                                                             │
│   POST /api/pi/projects/{id}/assignments/auto                           │
│           │                                                             │
│           v                                                             │
│   PIAssignmentService.auto_assign() → pi_material_assignments          │
│           │                                                             │
│           ├── P0 materials → Match to planet type (barren, gas, etc.)   │
│           └── P1-P4 materials → Assign to factory colonies              │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                        ESI OUTPUT TRACKING                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   ESI API → pi_colonies → pi_pins (qty_per_cycle, cycle_time)          │
│                                  │                                      │
│                                  v                                      │
│   GET /api/pi/projects/{id}/assignments                                │
│           │                                                             │
│           v                                                             │
│   PIRepository.calculate_material_outputs()                            │
│           │                                                             │
│           ├── P0: SUM(qty_per_cycle * 3600/cycle_time) WHERE           │
│           │       product_type_id = material_type_id                    │
│           │                                                             │
│           └── P1-P4: SUM(...) WHERE schematic outputs material         │
│                                                                         │
│           v                                                             │
│   Response includes:                                                    │
│           • actual_output_per_hour (from pi_pins)                       │
│           • expected_output_per_hour (from chain)                       │
│           • output_percentage (actual/expected * 100)                   │
│           • status: active|planned|unassigned                           │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**PI Database Tables:**
| Table | Purpose |
|-------|---------|
| `pi_colonies` | ESI-synced character colonies |
| `pi_pins` | Buildings with production data (qty_per_cycle, cycle_time) |
| `pi_routes` | Material flow routes between pins |
| `pi_projects` | Production projects with target product |
| `pi_project_colonies` | Colonies assigned to projects |
| `pi_material_assignments` | Material-to-colony assignments with tracking |

---

## External Dependencies

### EVE Online APIs

| API | Purpose | Rate Limit |
|-----|---------|------------|
| ESI (esi.evetech.net) | Official game API | ~400/min |
| EVE Ref (data.everef.net) | Killmail bulk data | No limit |
| EVE Image Server | Item icons | No limit |
| zKillboard RedisQ | Real-time killmail stream | Pull-based |
| zKillboard API | Alliance/corporation stats | ~20/10sec |

### Infrastructure

| Service | Container | Port |
|---------|-----------|------|
| PostgreSQL | eve_db | 5432 |
| Redis | (host) | 6379 |
| Backend | (host) | 8000 |
| Frontend | (host) | 5173 |
| Public Frontend | (host) | 5173 |
| ectmap | (host) | 3001 |

---

## Security Considerations

### Token Storage

- OAuth2 tokens stored in `tokens.json`
- Tokens include refresh tokens for long-term access
- Character IDs used to isolate data access

### API Access

- CORS configured for frontend origin
- No authentication required for public endpoints
- Character-specific endpoints require valid token

### Database

- Credentials in `config.py` (not in git)
- Docker container network isolation
- No external access to database port

---

## Performance Characteristics

### Caching

**Hybrid Cache Architecture (New):**
| Data Type | L1 Redis | L2 PostgreSQL | L3 ESI | Background Refresh |
|-----------|----------|---------------|--------|-------------------|
| Market Prices (Hot) | 5 min | 1 hour | Fallback | */4 min (proactive) |
| Market Prices (Other) | 5 min | 1 hour | Fallback | On-demand |
| Killmails | 24 hour | Permanent | Fallback | Real-time (RedisQ) |
| Character Data | 5-60 min | Sync | Fallback | */30 min (auto-sync) |

**Hot Items (56 items proactively cached):**
- Minerals (8): Tritanium, Pyerite, Mexallon, Isogen, Nocxium, Zydrine, Megacyte, Morphite
- Isotopes (4): Oxygen, Nitrogen, Hydrogen, Helium
- Fuel Blocks (4): All racial fuel blocks
- Moon Materials (20): Common R4-R64 materials
- Production Materials (20): Common T2/T3 components

**Backend (Legacy):**
- ESI responses cached in `esi_client.py` (TTL: varies by endpoint)
- Regional prices cached in `market_prices` table (30 min refresh)
- Manufacturing opportunities pre-calculated (5 min refresh)

**Frontend:**
- React Query caching (5 min staleTime, 10 min gcTime)
- Optimistic updates for mutations
- No refetch on window focus (reduces load)
- Code splitting via lazy loading for all pages

### Rate Limiting

- ESI client implements exponential backoff
- Bulk operations batched to avoid rate limits
- Price fetcher uses parallel requests with throttling

### Database Queries

- Complex queries use indexed columns
- SDE tables pre-indexed (EVE provides)
- App tables indexed on type_id, region_id

### Frontend Optimization

- **Code Splitting:** All pages lazy-loaded with React.lazy()
- **Bundle Size:** Reduced by dynamic imports
- **React Query:** Aggressive caching reduces API calls
- **Keyboard Shortcuts:** Efficient navigation without mouse

---

## Future Considerations

### Completed (Previously Planned)

- ✅ **Git Repository** - Version control on GitHub
- ✅ **Route Safety in Shopping** - Danger warnings implemented
- ✅ **2D Galaxy Map** - ectmap with live battle overlays
- ✅ **Production Timing Warnings** - War economy alerts

### Planned Improvements

1. **Docker Containerization** - Package entire application in Docker
2. **Mobile-Responsive Dashboard** - Better mobile experience
3. **Push Notifications** - Browser push for critical alerts
4. **API Rate Limiting** - Public API access controls
5. **Multi-Language Support** - UI translations beyond EN/DE

### Technical Debt

**Resolved (January 2026):**
- ✅ Consolidated 2 ESI clients → `src/integrations/esi/client.py` (primary)
- ✅ Consolidated 2 Market services → `src/services/market/repository.py` (primary)
- ✅ Unified caching strategy → L1 Redis → L2 PostgreSQL → L3 ESI
- ✅ Added 116+ tests for new repository layer
- ✅ Killmail deduplication via Redis sets
- ✅ Character auto-sync (*/30 min)

**Remaining:**
- `services.py` contains legacy code that could be split
- Some endpoints in `main.py` should move to routers
- Frontend could benefit from more TypeScript interfaces
- Test coverage could be improved for new features
- Legacy files (`src/esi_client.py`, `src/market_service.py`) marked deprecated, remove in v2.0

---

## Quick Reference

### Start Application

```bash
# Backend
cd /home/cytrex/eve_copilot
/home/cytrex/.local/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Frontend
cd /home/cytrex/eve_copilot/frontend
npm run dev -- --host 0.0.0.0
```

### Database Access

```bash
echo '<SUDO_PASSWORD>' | sudo -S docker exec eve_db psql -U eve -d eve_sde
```

### Logs

```bash
tail -f /home/cytrex/eve_copilot/logs/*.log
```

---

**Last Updated:** 2026-01-23

---

## API Documentation

Detailed service and module documentation:

- **[docs/api/](docs/api/README.md)** - Complete API documentation
  - [Backend Services](docs/api/services/) - 10 core services (~20,500 LOC)
  - [Microservices](docs/api/microservices/) - 9 Docker services (~29,800 LOC)
  - [Copilot Server](docs/api/copilot-server.md) - AI Agent Runtime (~5,000 LOC)
  - [Routers](docs/api/routers/) - API endpoints (~13,500 LOC)

**Total documented:** ~68,800 LOC
