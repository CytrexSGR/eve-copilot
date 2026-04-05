# EVE Co-Pilot - Microservices Architecture

> **Back to:** [ARCHITECTURE.md](ARCHITECTURE.md) | **See also:** [Data Layer](ARCHITECTURE.data.md) | [Deployment](ARCHITECTURE.deployment.md)

---

## Architecture Overview

```
                         ┌─────────────────────────────────────────┐
                         │           External Data Sources         │
                         │  EVE ESI API │ zKillboard │ EVE Ref     │
                         │  DOTLAN EveMaps │ anoik.is │ Janice     │
                         └───────────────────┬─────────────────────┘
                                             │
                         ┌───────────────────▼─────────────────────┐
                         │            API Gateway (:8000)          │
                         │  Route → Feature Gate → Rate Limit      │
                         │  CORS │ Security Headers │ Health       │
                         └───────────────────┬─────────────────────┘
                                             │
    ┌──────────┬──────────┬─────────┬────────┼────────┬─────────┬──────────┐
    │          │          │         │        │        │         │          │
    ▼          ▼          ▼         ▼        ▼        ▼         ▼          ▼
┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
│  war   │ │ sched  │ │ market │ │  prod  │ │  shop  │ │  char  │ │  auth  │ │ ectmap │
│ :8002  │ │ :8003  │ │ :8004  │ │ :8005  │ │ :8006  │ │ :8007  │ │ :8010  │ │ :8011  │
└────┬───┘ └────┬───┘ └────┬───┘ └────┬───┘ └────┬───┘ └────┬───┘ └────┬───┘ └────┬───┘
     │          │          │          │          │          │          │          │
     │   ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐                 │
     │   │wormhole│ │zkill   │ │dotlan  │ │   hr   │ │finance │ ┌────────┐      │
     │   │ :8012  │ │ :8013  │ │ :8014  │ │ :8015  │ │ :8016  │ │  mcp   │      │
     │   └────┬───┘ └────┬───┘ └────┬───┘ └────┬───┘ └────┬───┘ │ :8008  │      │
     │        │          │          │          │          │     └────┬───┘       │
     └──────────┴──────────┴──────────┴────┬─────┴──────────┴──────────┴──────────┘
                                           │
                    ┌──────────────────────┼──────────────────────┐
                    │                      │                      │
                    ▼                      ▼                      ▼
             ┌───────────┐          ┌───────────┐          ┌───────────┐
             │ PostgreSQL│          │   Redis   │          │Observabil.│
             │  (:5432)  │          │  (:6379)  │          │ Prometheus│
             │  eve_sde  │          │  L1 Cache │          │  Grafana  │
             │ 132+ tbl  │          │ Rate Limit│          │   Loki    │
             └───────────┘          └───────────┘          └───────────┘
```

### Service Overview

| Service | Port | Status | Responsibility |
|---------|------|--------|----------------|
| **api-gateway** | 8000 | 🐳 Docker | Request routing, feature gating (tier_map.yaml), tier-aware rate limiting, CORS, security headers |
| war-intel-service | 8002 | 🐳 Docker | Combat intel, battles, alliances, power blocs, sovereignty, military ops, MCP tools, Dogma tank analysis, killmail intelligence (threats, capital radar, logi score, hunting, pilot risk, corp health) |
| scheduler-service | 8003 | 🐳 Docker | 48 cron jobs (sync, aggregation, snapshots, reports), APScheduler, legacy monolith scripts |
| market-service | 8004 | 🐳 Docker | Market prices, orders, arbitrage (with fees), trading, route planning, bookmarks |
| production-service | 8005 | 🐳 Docker | Blueprints, manufacturing, reactions, PI (advisor, chains, profitability, empire analysis), mining, supply chain |
| shopping-service | 8006 | 🐳 Docker | Shopping lists, materials calculation, freight pricing (BR to JF) |
| character-service | 8007 | 🐳 Docker | Character data, ESI sync, fittings, Dogma engine, fitting stats, SDE browser, skill analysis, mastery, fleet readiness, skill plans |
| mcp-service | 8008 | 🐳 Docker | MCP server (609 dynamic tools from OpenAPI), AI agent interface (optional) |
| copilot-server | 8009 | Manual | AI Agent with Claude (optional) |
| auth-service | 8010 | 🐳 Docker | EVE SSO OAuth, token management, Fernet encryption, tier subscriptions, platform accounts, ISK payments, org management |
| ectmap-service | 8011 | 🐳 Docker | Map screenshot generation (Playwright, Chromium) |
| ectmap (frontend) | 3001 | 🐳 Docker | Next.js map frontend with 501MB SDE data, live battle overlay, sov campaigns, entity activity heatmap |
| wormhole-service | 8012 | 🐳 Docker | Wormhole intel, market analysis, threat detection, resident tracking, Thera routing |
| zkillboard-service | 8013 | 🐳 Docker | zkillboard RedisQ live stream, battle detection, hotspot tracking |
| dotlan-service | 8014 | 🐳 Docker | DOTLAN EveMaps scraping (system activity, sovereignty, alliance rankings, ADM history) |
| hr-service | 8015 | 🐳 Docker | Red list, vetting engine (5-stage risk scoring), role sync, activity tracking, applications |
| finance-service | 8016 | 🐳 Docker | Wallet sync, mining tax, invoicing, financial reports, SRP, doctrine management (clone, auto-pricing, changelog), buyback (Janice API) |
| redis | 6379 | 🐳 Docker | L1 cache, session storage, rate limiting, market stats cache |
| PostgreSQL | 5432 | 🐳 Docker | Database (eve_sde, 103 migrations, 132+ tables) |

### API Gateway Routes

**nginx routes ALL `/api/*` to api-gateway (8000), which routes internally by prefix:**

| Path Prefix | Target Service | Host Port |
|-------------|----------------|-----------|
| `/api/auth/*`, `/api/settings/*` | auth-service | 8010 |
| `/api/tier/*` | auth-service | 8010 |
| `/api/war/*`, `/api/reports/*`, `/api/intelligence/*` | war-intel-service | 8002 |
| `/api/powerbloc/*`, `/api/alliances/*`, `/api/sovereignty/*` | war-intel-service | 8002 |
| `/api/dps/*`, `/api/dogma/*`, `/api/risk/*` | war-intel-service | 8002 |
| `/api/fingerprints/*`, `/api/events/*`, `/api/fleet/*` | war-intel-service | 8002 |
| `/api/contracts/*`, `/api/corp-contracts/*`, `/api/wallet/*` | war-intel-service | 8002 |
| `/api/jump/*`, `/api/timers/*`, `/api/moon/*`, `/api/fuel/*` | war-intel-service | 8002 |
| `/api/military/*`, `/api/sov/*`, `/api/notifications/*` | war-intel-service | 8002 |
| `/api/mcp/*` (AI tools) | war-intel-service | 8002 |
| `/api/scheduler/*`, `/api/jobs/*` | scheduler-service | 8003 |
| `/api/market/*`, `/api/orders/*`, `/api/hunter/*`, `/api/trading/*` | market-service | 8004 |
| `/api/alerts/*`, `/api/goals/*`, `/api/history/*`, `/api/portfolio/*` | market-service | 8004 |
| `/api/items/*`, `/api/materials/*`, `/api/route/*`, `/api/bookmarks/*` | market-service | 8004 |
| `/api/production/*`, `/api/reactions/*`, `/api/pi/*` | production-service | 8005 |
| `/api/mining/*`, `/api/supply-chain/*` | production-service | 8005 |
| `/api/shopping/*` | shopping-service | 8006 |
| `/api/character/*`, `/api/account-groups/*` | character-service | 8007 |
| `/api/fittings/*`, `/api/sde/*` | character-service | 8007 |
| `/api/mastery/*`, `/api/skills/*`, `/api/research/*` | character-service | 8007 |
| `/mcp/*` | mcp-service | 8008 |
| `/api/wormhole/*` | wormhole-service | 8012 |
| `/api/dotlan/*` | dotlan-service | 8014 |
| `/api/hr/*` | hr-service | 8015 |
| `/api/finance/*`, `/api/srp/*`, `/api/doctrine/*`, `/api/buyback/*` | finance-service | 8016 |
| `/ectmap` | ectmap (frontend) | 3001 |
| `/` | public-frontend (Docker) | 5173 |

**Background Services (not HTTP routed):**
- zkillboard-service (8013): RedisQ live stream → writes directly to PostgreSQL

### Directory Structure

```
services/
├── api-gateway/          # Request routing, feature gate, rate limiting (host: 8000) 🐳
├── war-intel-service/    # Combat intel, alliances, power blocs, sovereignty (host: 8002) 🐳
├── scheduler-service/    # 48 cron jobs + legacy monolith/ scripts (host: 8003) 🐳
│   └── monolith/         # Active legacy code (src/, jobs/, config.py, services/)
├── market-service/       # Market data, arbitrage, trading (host: 8004) 🐳
├── production-service/   # Manufacturing, PI, reactions, mining (host: 8005) 🐳
├── shopping-service/     # Shopping lists, freight pricing (host: 8006) 🐳
├── character-service/    # Characters, fittings, Dogma, SDE browser (host: 8007) 🐳
├── mcp-service/          # MCP AI tools (609 dynamic, host: 8008) 🐳
├── auth-service/         # EVE SSO, tiers, payments (host: 8010) 🐳
├── ectmap-service/       # Map screenshots (Playwright, host: 8011) 🐳
├── wormhole-service/     # Wormhole intel (host: 8012) 🐳
├── zkillboard/           # RedisQ live stream (host: 8013) 🐳
│   └── legacy/           # Shared src/ modules (database.py, auth.py, character.py)
├── dotlan-service/       # DOTLAN scraping (host: 8014) 🐳
├── hr-service/           # HR, vetting, applications (host: 8015) 🐳
├── finance-service/      # Wallets, tax, SRP, buyback (host: 8016) 🐳
ectmap/
└── (Next.js frontend)    # Interactive map with SDE data (host: 3001) 🐳
shared/
└── eve_shared/           # Shared library (database, redis, ESI client, constants, middleware)
docker/
├── docker-compose.yml    # Service orchestration (22 containers)
├── grafana/              # Dashboard provisioning (JSON)
└── prometheus/           # Metrics scrape config
```

---

## Service Details

### 1. API Gateway (Port 8000)

**Location:** `services/api-gateway/`

Routes all `/api/*` requests to microservices. Also provides:

| Feature | File | Description |
|---------|------|-------------|
| Feature Gating | `middleware/feature_gate.py` | Tier-based access control (tier_map.yaml, 350+ endpoints) |
| Rate Limiting | `middleware/rate_limit.py` | Tier-aware Redis rate limiting |
| Tier Config | `middleware/tier_config.py` | Config loader for tier/module maps |
| Gate Helpers | `middleware/gate_helpers.py` | JWT decode, pattern matching |
| Redis Pool | `middleware/redis_pool.py` | Shared Redis connection |

**Rate Limits (req/min):**

| Tier | Limit |
|------|-------|
| public | 30 |
| free | 60 |
| pilot | 200 |
| corporation | 500 |
| alliance | 1000 |
| coalition | 2000 |

**Feature Gate Flow:** Extract JWT → check module_map.yaml → fall back to tier_map.yaml → allow/403/401

**Prometheus Metrics:** `saas_feature_gate_decisions`, `saas_tier_resolutions`

### 2. War-Intel Service (Port 8002)

**Location:** `services/war-intel-service/` | **Tests:** 501

Largest service. Handles all combat intelligence, alliance/corporation/power bloc analysis, sovereignty, and military operations.

**Router Structure:**
```
app/routers/
├── economy/              # Fuel, manipulation, prices, profiteering, trade routes
├── intelligence/
│   ├── alliances/        # Capsuleers, defensive, offensive, summary, dashboard
│   ├── corporations/     # Same structure, shared via EntityContext
│   ├── entity_context.py # Shared SQL parameterization (Corp/Alliance/PB)
│   ├── shared_queries.py # Geography + capitals (deduplicated)
│   ├── shared_defensive.py # 16 defensive sections (deduplicated)
│   ├── threats.py        # Threat composition (who attacks us, damage profiles)
│   ├── capital_radar.py  # Capital escalation radar (sightings + escalation timeline)
│   ├── logi_score.py     # Logi shield score (enemy logistics strength 0-100)
│   ├── hunting_intel.py  # Hunting scoreboard (killmail + DOTLAN ADM fusion)
│   ├── capsuleer_risk.py # Pilot risk assessment (AWOX detection)
│   ├── corp_health.py    # Corp health dashboard (activity, efficiency, trends)
│   └── map_intel.py      # LiveMap overlays (hunting heatmap, capital activity, logi presence)
├── military/             # Fleet sessions, military ops (D-Scan, local scan, PAPs)
├── mcp/                  # 14 semantic AI tools (alliance, economy, ops, strategic)
├── powerbloc/            # 13 modules (offensive, defensive, capitals, hunting, etc.)
├── reports/              # Battle reports, power blocs, stored reports
├── war/battles/          # Battle CRUD, sides (BFS), loadouts, context, dogma
├── alliances.py          # Alliance info, search
├── contracts.py          # Corp contract tracking
├── dogma.py              # Dogma tank analysis (killmail fitting)
├── dps.py                # DPS calculator
├── notifications.py      # ESI notification pipeline
├── sovereignty.py        # Sov tracking, sov resources, sov assets
├── structure_timers.py   # Timer board with state machine
└── ... (40+ router files total)
```

**Key Features:**
- EntityContext deduplication: Corp/Alliance/PB share geography, capitals, defensive queries
- Redis caching (5-10min TTL) on all PB endpoints, geography, capitals
- Prometheus instrumentation (cache hits, DB query duration)
- BFS 2-coloring for battle side detection
- Doctrine detection via DBSCAN clustering

### 3. Scheduler Service (Port 8003)

**Location:** `services/scheduler-service/` | **Tests:** 130

APScheduler-based job runner with 48 scheduled jobs.

**Executor Structure:**
```
app/jobs/executors/
├── _helpers.py           # _call_service() DRY httpx helper
├── aggregation.py        # Hourly stats aggregation
├── characters.py         # Character sync, skill snapshots
├── dotlan.py             # DOTLAN scraper triggers
├── intelligence.py       # Killmail fetch, doctrine clustering, fingerprints
├── market.py             # Prices, arbitrage, batch calculator
├── reports.py            # Report generation (4 reports via monolith/src/core shim)
├── saas.py               # Payment polling, subscription expiry
├── sovereignty.py        # Sov tracker, FW tracker, sov snapshots
├── wormhole.py           # WH data sync, stats refresh
```

**Legacy Code:** `monolith/` directory contains active `src/`, `jobs/`, `config.py` still used by 5 remaining subprocess calls (report generators, doctrine clustering).

**Internal Endpoint Pattern:** Most jobs call `POST /api/internal/<job>` on target services.

### 4. Market Service (Port 8004)

**Location:** `services/market-service/` | **Tests:** 260

Market data, trading, arbitrage, route planning.

**Routers:** market, orders, hunter, trading, alerts, goals, history, portfolio, items, materials, route, bookmarks, cargo

**Key Features:**
- Arbitrage with net profit/fees (broker 1.5% + tax 3.6%)
- Regional price comparison across all trade hubs
- A* pathfinding for route planning
- Market history sync with ESI

### 5. Production Service (Port 8005)

**Location:** `services/production-service/` | **Tests:** 112

Manufacturing, PI, reactions, mining.

**Router Structure:**
```
app/routers/
├── pi/                   # Planetary Industry (9 routers: colonies, empire, formulas, profitability, alerts, advisor, chain_planner, multi_character, recommendations)
├── chains.py             # Production chain analysis
├── economics.py          # Manufacturing economics + daily volume
├── invention.py          # Blueprint invention calculator
├── mining.py             # Mining operations
├── reaction_requirements.py  # Recursive reaction chain builder
├── reactions.py          # Reaction economics
├── simulation.py         # Production cost simulation
├── supply_chain.py       # Supply chain intelligence
├── workflow.py           # Production job tracking
└── ... (18 router files total)
```

**Key Features:**
- PI Advisor: skill-aware profitability, optimal planet combinations, production layouts
- PI Empire Overview: multi-character production aggregation, P4 feasibility analysis with make-or-buy
- PI Chain Browser: interactive SVG DAG visualization (P0→P4), profitability overlay, plan creation
- Reaction requirements: recursive chain (composite → simple → moon goo)
- Batch calculator: manufacturing opportunities with liquidity/risk scoring
- Manufacturing economics with ME/TE bonuses, structure bonuses, system cost index

### 6. Shopping Service (Port 8006)

**Location:** `services/shopping-service/` | **Tests:** 41

Shopping list management and freight pricing.

**Features:** List CRUD, multi-region price comparison, freight pricing (Blockade Runner → DST → Jump Freighter), build-vs-buy analysis

### 7. Character Service (Port 8007)

**Location:** `services/character-service/` | **Tests:** 287

Character data, fittings, Dogma engine, SDE browser.

**Router Structure:**
```
app/routers/
├── character.py          # 19 endpoints: info, wallet, assets, skills, summary/all
├── corporation.py        # Corp data
├── fittings.py           # 7 endpoints: ESI fittings, custom CRUD, stats
├── account_summary.py    # Aggregated multi-char account summary (Phase 5)
├── mastery.py            # Ship mastery levels (0-4)
├── research.py           # Skill recommendations
├── sde_browser.py        # 8 endpoints: ships, modules, market tree (4-tab browser)
├── skill_analysis.py     # Skill gap analysis
├── skill_plans.py        # Skill plan management
├── skills.py             # Skill browser
├── sync.py               # Character ESI sync trigger
├── doctrine_stats.py     # Fleet readiness analysis (per doctrine per corp)
└── skill_export.py       # Skill plan export (EVEMon XML format)
```

**Key Services:**
```
app/services/
├── fitting_stats/        # Modular package (was 1,451-line monolith)
│   ├── models.py         # 12 Pydantic models
│   ├── constants.py      # 60 SDE attribute IDs, flags, effects
│   ├── calculations.py   # Pure functions: capacitor, align, weapon/drone DPS
│   ├── offense.py        # DPS calculation with Dogma modifiers
│   ├── defense.py        # EHP with resist stacking
│   ├── navigation.py     # Speed, align, propmod (Acceleration Control skill)
│   ├── resources.py      # CPU/PG/Cal usage, slot counting
│   ├── validation.py     # Constraint validation (maxGroupFitted, maxTypeFitted, 1-cloak)
│   └── service.py        # Orchestrator + ship info loader
├── dogma/                # Dogma modifier engine
│   ├── engine.py         # DogmaEngine (YAML effects → attribute modifications)
│   ├── models.py         # ItemModifier, LocationGroupModifier, stacking penalty
│   └── ...
├── fitting_service.py    # ESI fitting CRUD, custom fittings
└── repository.py         # SDE queries, character data
```

**SDE Browser Features:**
- 4-tab market tree: Hulls (root 4), Modules (root 9), Charges (root 11), Drones (root 157)
- Ship compatibility filters: weapon size, canFitShipGroup/Type, hardpoint limits, rig size
- CTE pruning: empty categories hidden when filters active
- Character skill integration: actual `trained_skill_level` from DB or default All Skills V

### 8. MCP Service (Port 8008)

**Location:** `services/mcp-service/` | **Tests:** 73 | **Optional**

Model Context Protocol server for AI agent integration.

**Architecture:**
- Generates 609 tools dynamically from microservice OpenAPI schemas
- SSE-based tool execution with 30s timeout
- 14 semantic MCP tools (hand-crafted) + auto-generated from all service APIs

**Endpoints:** `POST /mcp/list-tools`, `POST /mcp/call-tool`, `POST /mcp/list-prompts`

### 9. Auth Service (Port 8010)

**Location:** `services/auth-service/` | **Tests:** 167

Authentication, tier management, payments.

**Routers:**
| Router | Endpoints | Purpose |
|--------|-----------|---------|
| `auth.py` | 6 | EVE SSO OAuth flow, token refresh, rekey |
| `public_auth.py` | 5 | Public auth (login, callback, logout) |
| `tier.py` | 9 | Tier resolution, ISK payment processing |
| `subscription.py` | 3 | Subscription management |
| `admin.py` | 4 | Admin operations |
| `settings.py` | 3 | User settings |
| `character_management.py` | 3 | Token health, primary switch, alt removal (Phase 5) |
| `org_management.py` | 8 | Corp member/role/permission management, audit log (Phase 2) |

**Key Features:**
- EVE SSO OAuth2 with PKCE
- Fernet token encryption (with scheduled re-keying)
- JWT session cookies with enriched claims (tier, character_id, org info)
- ISK payment: PAY-XXXXX code → wallet journal polling (1min) → auto-activation
- Director detection: ESI role → platform role auto-mapping
- Platform accounts with multi-character linking
- Character management: token health (13 scope groups), primary switching, alt removal
- character_scope_consents table for ESI scope tracking
- Org management: member listing, role updates, permission matrix, audit log (Phase 2)
- org_permissions + org_audit_log tables for corp governance

### 10. Wormhole Service (Port 8012)

**Location:** `services/wormhole-service/` | **Tests:** 189

Wormhole intelligence and Thera routing.

**Routers:** types, systems, residents, activity, evictions, stats, threats, opportunities, market, thera

**Data Sources:** SDE (invTypes groupID=988), Pathfinder CSVs, anoik.is (system effects), killmails (60k+ J-Space)

### 11. zkillboard Service (Port 8013)

**Location:** `services/zkillboard/` | **Type:** Background stream (not HTTP API)

Real-time killmail ingestion from zkillboard RedisQ.

- Long-polling with 0.5s minimum interval, own queue ID
- Writes killmails + attackers + items directly to PostgreSQL
- Battle detection: 5 kills in 300 seconds = battle
- Hotspot tracking via Redis state manager
- Legacy code in `legacy/` directory (shared `src/database.py`, `auth.py`, `character.py`)

### 12. DOTLAN Service (Port 8014)

**Location:** `services/dotlan-service/` | **Tests:** 66

Scrapes data from evemaps.dotlan.net not available via ESI.

**Scrapers:**
| Scraper | Data | Schedule |
|---------|------|----------|
| Activity Region | NPC/ship/pod kills, jumps | Every 2h |
| Activity Detail | Top 200 active systems, 7-day history | Every 6h |
| Sov Campaigns | Active campaigns with defender, score | Every 10min |
| Sov Changes | Ownership transfers | Daily |
| Alliance Rankings | Systems, members, corps | Every 12h |
| ADM History | ADM levels from chart data | Every 6h |

**Technical:** Token-bucket rate limiter (1 req/sec), BeautifulSoup + lxml, JS chart data extraction

### 13. HR Service (Port 8015)

**Location:** `services/hr-service/` | **Tests:** 178

HR and vetting operations.

**Routers:** vetting, red_list, roles, activity, applications

**Vetting Engine (5 stages):**
1. Red list check
2. Character age scoring
3. Wallet heuristics
4. Skill injection detection
5. Corp history analysis (hopping, short tenure, NPC cycling)

### 14. Finance Service (Port 8016)

**Location:** `services/finance-service/` | **Tests:** 139

Corporation financial operations.

**Routers:** wallet, mining, invoices, reports, srp, buyback

**Features:** Wallet journal sync, mining tax calculation, invoice generation, SRP claims (killmail matching + doctrine pricing), buyback contracts (Janice API)

**Doctrine Management Extensions:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/finance/doctrine/{id}/clone` | Clone doctrine with new name |
| GET | `/api/finance/doctrine/{id}/price` | Auto-calculate price from Jita market |
| GET | `/api/finance/doctrine/{id}/changelog` | Doctrine-level changelog |
| GET | `/api/finance/corp/{corp_id}/changelog` | Corp-wide doctrine changelog |

**New Tables:** `doctrine_changelog` (action, changes JSONB, actor)
**New Column:** `fleet_doctrines.category` (doctrine categorization)

### 15. ECTMap (Ports 8011 + 3001)

**Backend** (`services/ectmap-service/`): Playwright-based map screenshot generation

**Frontend** (`ectmap/`): Next.js 16 with Turbopack
- Canvas-based EVE universe map with 501MB SDE data
- Live battle overlay (5s refresh) with status filters (Gank/Brawl/Battle/Hellcamp)
- Sov campaign markers (IHUB/TCU/Station)
- **Entity Activity mode** (`colorMode=entity_activity`): Corp/Alliance/PowerBloc system heatmap (blue→red), golden home system rings, entity-filtered kills/battles, auto-zoom to active systems
- API route `/api/entity-geography` proxies to intelligence service Geography Extended API (300s cache)
- URL parameter support for iframe embedding

---

## ⛔ Monolith Architecture (DECOMMISSIONED - 2026-02-10)

> **Fully replaced by microservices.** ~72,000 lines removed from project root.
>
> **Active legacy code** moved to:
> - `services/scheduler-service/monolith/` — Active `src/`, `jobs/`, `config.py` (19 of 24 subprocess calls converted to API, 5 remaining)
> - `services/zkillboard/legacy/` — Shared `src/database.py`, `auth.py`, `character.py`

---

## Database Schema

**Container:** `eve_db` | **Database:** `eve_sde` | **103 migrations, 132+ tables**

### Combat Intelligence Tables

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
| ship_class                |     +---------------------------+
| ship_category             |              |
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
| started_at / ended_at     |
| total_kills / total_isk   |
| capital_kills / status    |
+---------------------------+

+---------------------------+     +---------------------------+
| intelligence_hourly_stats |     | corporation_hourly_stats  |
+---------------------------+     +---------------------------+
| alliance_id, bucket (PK)  |     | corp_id, bucket (PK)      |
| kills, deaths, isk_*     |     | kills, deaths, isk_*     |
| solo_kills, solo_ratio    |     | avg/max_kill_value        |
+---------------------------+     +---------------------------+
```

### Coalition & Sovereignty Tables

```
+---------------------------+     +---------------------------+
| alliance_fight_together   |     | alliance_fight_against    |
+---------------------------+     +---------------------------+
| alliance_a, alliance_b    |     | alliance_a, alliance_b    |
| fights_together, last_seen|     | fights_against, last_seen |
+---------------------------+     +---------------------------+

+---------------------------+     +---------------------------+     +---------------------------+
| sovereignty_map_cache     |     | structure_timers          |     | sov_asset_snapshots       |
+---------------------------+     +---------------------------+     +---------------------------+
| system_id (PK)            |     | id (PK)                   |     | id (PK)                   |
| alliance_id               |     | system_id, type           |     | alliance_id               |
| corporation_id            |     | state (FSM), jitter       |     | snapshot_data (JSONB)     |
+---------------------------+     | timer_window_start/end    |     | created_at                |
                                  +---------------------------+     +---------------------------+
```

### SaaS & Auth Tables

```
+---------------------------+     +---------------------------+     +---------------------------+
| tier_subscriptions        |     | platform_accounts         |     | tier_payments             |
+---------------------------+     +---------------------------+     +---------------------------+
| id (PK)                   |     | id (PK)                   |     | id (PK)                   |
| entity_type, entity_id    |     | main_character_id         |     | subscription_id (FK)      |
| tier, status              |     | created_at                |     | amount_isk                |
| started_at, expires_at    |     +---------------------------+     | payment_code (PAY-XXXXX)  |
+---------------------------+              |                         | status                    |
                                           v                         +---------------------------+
                                  +---------------------------+
                                  | account_characters        |
                                  +---------------------------+
                                  | account_id (FK)           |
                                  | character_id              |
                                  | is_primary                |
                                  +---------------------------+
                                           |
                                  +---------------------------+
                                  | character_scope_consents  |
                                  +---------------------------+
                                  | character_id (PK, FK)     |
                                  | granted_scopes TEXT[]     |
                                  | requested_scopes TEXT[]   |
                                  | last_auth_at, revoked_at  |
                                  +---------------------------+

+---------------------------+     +---------------------------+
| org_permissions           |     | org_audit_log             |
+---------------------------+     +---------------------------+
| id (PK)                   |     | id (PK)                   |
| corporation_id            |     | corporation_id            |
| role                      |     | actor_character_id        |
| permissions JSONB         |     | action, target_id         |
| updated_at, updated_by    |     | details JSONB, created_at |
+---------------------------+     +---------------------------+
```

### Character & Fitting Tables

```
+---------------------------+     +---------------------------+     +---------------------------+
| characters                |     | character_skills          |     | character_orders          |
+---------------------------+     +---------------------------+     +---------------------------+
| character_id (PK)         |     | character_id, skill_id PK |     | character_id, order_id PK |
| name, corp_id, alliance_id|     | trained_skill_level       |     | type_id, price, volume    |
| wallet_balance            |     | skillpoints_in_skill      |     | is_buy_order, location    |
| last_sync                 |     +---------------------------+     +---------------------------+
+---------------------------+
                                  +---------------------------+
                                  | custom_fittings           |
                                  +---------------------------+
                                  | id (PK)                   |
                                  | character_id, ship_type_id|
                                  | name, description         |
                                  | items (JSONB), tags (GIN) |
                                  | is_public                 |
                                  +---------------------------+
```

### Industry & Market Tables

```
+---------------------------+     +---------------------------+     +---------------------------+
| manufacturing_            |     | arbitrage_opportunities   |     | market_prices             |
| opportunities             |     +---------------------------+     +---------------------------+
+---------------------------+     | id (PK)                   |     | type_id, region_id (PK)   |
| type_id (PK)              |     | type_id                   |     | lowest_sell, highest_buy  |
| profit, roi               |     | net_profit, net_margin    |     | avg_daily_volume          |
| avg_daily_volume          |     | fees, buy/sell region     |     | updated_at                |
| risk_score, net_profit    |     +---------------------------+     +---------------------------+
+---------------------------+
```

### DOTLAN & Wormhole Tables

```
+---------------------------+     +---------------------------+     +---------------------------+
| dotlan_system_activity    |     | dotlan_sov_campaigns      |     | dotlan_adm_history        |
+---------------------------+     +---------------------------+     +---------------------------+
| system_id, timestamp (PK) |     | campaign_id (PK)          |     | system_id, timestamp (PK) |
| npc_kills, ship_kills     |     | type, defender, score     |     | adm_level                 |
| pod_kills, jumps          |     | system_id                 |     +---------------------------+
+---------------------------+     +---------------------------+

+---------------------------+     +---------------------------+
| wormhole_residents        |     | wh_sov_threats            |
+---------------------------+     +---------------------------+
| id (PK)                   |     | alliance_id (PK)          |
| system_id, corp_id        |     | total_wh_systems/kills    |
| alliance_id, kills        |     | critical/high/mod/low     |
| first_seen, last_seen     |     | top_attackers (JSONB)     |
+---------------------------+     +---------------------------+
```

### HR & Management Tables

```
+---------------------------+     +---------------------------+     +---------------------------+
| vetting_snapshots         |     | hr_applications           |     | esi_notifications         |
+---------------------------+     +---------------------------+     +---------------------------+
| id (PK)                   |     | id (PK)                   |     | notification_id (PK)      |
| character_id, risk_score  |     | character_id, corp_id     |     | character_id, type        |
| stages (JSONB)            |     | status (workflow)         |     | text, processed           |
+---------------------------+     +---------------------------+     +---------------------------+
```

### Doctrine Management Tables

```
+---------------------------+     +---------------------------+
| fleet_doctrines           |     | doctrine_changelog        |
+---------------------------+     +---------------------------+
| id (PK)                   |     | id (PK)                   |
| corporation_id            |     | doctrine_id (FK)          |
| name, ship_type_id        |     | corporation_id            |
| fitting_eft, category     |     | action (enum)             |
| priority, is_active       |     | changes (JSONB)           |
| created_at                |     | actor_character_id        |
+---------------------------+     | actor_name, created_at    |
                                  +---------------------------+
```

---

## Public Frontend

**Location:** `/home/cytrex/eve_copilot/public-frontend/`
**Framework:** Vite + React 19 + TypeScript 5
**Port:** 5173 (Docker) / 5175 (Dev HMR)

### Pages (42 routes)

| Category | Route | Page | Tier |
|----------|-------|------|------|
| **Public** | `/` | Home (auth-conditional landing) | public |
| | `/pricing` | Pricing page | public |
| | `/how-it-works` | User guide | public |
| | `/auth/callback` | ESI OAuth callback | public |
| **Intel (Free)** | `/battle-report` | Battle list with power blocs | free |
| | `/battle/:id` | Tactical battle analysis | free |
| | `/battle-map` | Interactive 2D battle map | free |
| | `/conflicts/:conflictId` | Conflict tracking | free |
| | `/war-economy` | War economy dashboard | free |
| | `/wormhole` | Wormhole intelligence | free |
| | `/alliance/:allianceId` | Alliance intel (10 tabs, incl. Live Map) | free |
| | `/powerbloc/:leaderAllianceId` | Coalition intel (13 modules, incl. Live Map tab) | free |
| | `/corporation/:corpId` | Corporation intel (incl. Live Map tab) | free |
| | `/supply-chain/:allianceId?` | Supply chain analysis | free |
| | `/doctrines` | Doctrine intelligence | free |
| | `/ectmap` | Interactive EVE map | free |
| | `/system/:systemId` | System detail | free |
| | `/route/:origin/:destination` | Route detail | free |
| | `/ships` | Ship browser | free |
| **Pilot** | `/dashboard` | Character dashboard | pilot |
| | `/characters` | Multi-character management | pilot |
| | `/market` | Market suite (tabs: overview, orders, arbitrage, history) | pilot |
| | `/production` | Production suite (tabs: manufacturing, PI, reactions) | pilot |
| | `/production/pi/:typeId` | PI advisor detail | pilot |
| | `/fittings` | Fitting browser (ESI + custom + shared) | pilot |
| | `/fittings/new` | Fitting editor (Dogma stats, market tree) | pilot |
| | `/fittings/esi/:fittingId` | ESI fitting detail | pilot |
| | `/fittings/custom/:fittingId` | Custom fitting detail | pilot |
| | `/navigation` | Route planner | pilot |
| | `/shopping` | Shopping list manager | pilot |
| | `/subscription` | Subscription management | pilot |
| | `/account` | Account settings | pilot |
| **Corporation** | `/intel` | Military intel (D-Scan, local scan) | corporation |
| | `/corp/finance` | Corp finance dashboard | corporation |
| | `/corp/hr` | HR & vetting | corporation |
| | `/corp/srp` | SRP claims | corporation |
| | `/corp/fleet` | Fleet PAP tracking | corporation |
| | `/corp/timers` | Timer board | corporation |
| | `/corp/tools` | Corp tools | corporation |

All routes use `React.lazy()` for code-splitting.

---

## Unified Frontend (Legacy Internal)

**Location:** `/home/cytrex/eve_copilot/unified-frontend/`
**Port:** 3003 (systemd)

Internal development frontend, mostly superseded by public-frontend. Contains legacy pages for PI empire management, skill browser, admin dashboard.

---

## Cron Jobs (48 scheduled)

### High Frequency (1-15 min)

| Job | Schedule | Service | Purpose |
|-----|----------|---------|---------|
| payment_poll | 1 min | auth | ISK payment wallet journal polling |
| batch_calculator | 5 min | production | Manufacturing opportunity scanning |
| wallet_poll | 5 min | war-intel | Corp wallet sync |
| timer_expiry_check | 5 min | war-intel | Structure timer state transitions |
| notification_sync | 10 min | war-intel | ESI notification pipeline |
| dotlan_sov_campaigns | 10 min | dotlan | Sovereignty campaign scrape |
| token_refresh | 15 min | auth | ESI token refresh |
| character_sync | 15 min | character | Full character ESI sync |
| economy_manipulation_scanner | 15 min | market | Market manipulation (Z-score) |
| market_undercut_checker | 15 min | market | Order undercut detection |

### Medium Frequency (30 min)

| Job | Schedule | Purpose |
|-----|----------|---------|
| aggregate_hourly_stats | 30 min | Alliance hourly stats (kills, ISK, solo) |
| aggregate_corp_hourly_stats | 30 min | Corporation hourly stats |
| regional_prices | 30 min | Regional market price update |
| sov_tracker | 30 min | Sovereignty campaigns (ESI) |
| fw_tracker | 30 min | Faction Warfare system status |
| economy_fuel_poller | 30 min | Fuel market anomaly detection |
| economy_price_snapshotter | 30 min | Critical item price snapshots |
| coalition_refresh | 30 min | Coalition membership refresh |
| battle_cleanup | 30 min | End old battles (>2h inactivity) |
| pi_monitor | 30 min | PI colony monitoring |
| portfolio_snapshotter | 30 min | Trading portfolio snapshots |
| arbitrage_calculator | 30 min | Cross-region arbitrage scanning |
| contract_sync | 30 min | Corp contract status tracking |

### Hourly+

| Job | Schedule | Purpose |
|-----|----------|---------|
| telegram_report | 1h | Telegram battle report |
| alliance_wars | 1h | Alliance war report |
| subscription_expiry | 1h | SaaS subscription expiry check |
| dotlan_activity_region | 2h | DOTLAN region activity scan |
| war_profiteering | 6h | War profiteering report |
| report_generator | 6h | Stored report generation |
| wormhole_stats_refresh | 6h | WH resident + activity refresh |
| dotlan_activity_detail | 6h | DOTLAN detail scan (top 200 systems) |
| sov_asset_snapshot | 6h | Sov asset snapshots with delta |
| dotlan_alliance_rankings | 12h | Alliance ranking stats |

### Daily

| Job | Schedule | Purpose |
|-----|----------|---------|
| wormhole_data_sync | 03:00 | Pathfinder CSV sync |
| dotlan_cleanup | 03:30 | Data retention cleanup |
| dotlan_sov_changes | 04:15 | Sov ownership changes |
| corporation_sync | 05:45 | Corporation ESI sync (6,500+ corps) |
| wh_sov_threats | 05:45 | WH threats to sovereignty |
| killmail_fetcher | 06:00 | Previous day killmails (legacy) |
| everef_importer | 07:00 | EVE Ref killmail dumps with items |
| token_rekey | 03:00 | Re-encrypt all tokens with current key |
| capability_sync | Daily | Character capability refresh |
| market_history_sync | Daily | Market price history |
| skill_snapshot | Daily | Skill progress snapshots |
| alliance_fingerprints | Daily | Alliance ship fingerprint analysis |
| pilot_skill_estimates | Daily | Batch skill estimation |
| doctrine_clustering | Daily | DBSCAN fleet composition clustering |

---

**Last Updated:** 2026-02-22 (18 Services, 112 Migrations, 2,400+ Tests, SaaS, Dogma Engine, Killmail Intelligence System, Character Management Phase 1, Org Management Phase 2, Monolith Decommissioned, Doctrine Management Extensions)
