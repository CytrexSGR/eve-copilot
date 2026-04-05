# EVE Co-Pilot Architecture

> **Documentation Suite:** [Microservices](ARCHITECTURE.microservices.md) | [Deployment](ARCHITECTURE.deployment.md)

> **Quick Start:** [README](README.md) | [Self-Hosted Setup](README.md#-self-hosted-setup)

---

## System Overview

EVE Co-Pilot is a production, trading, **real-time combat intelligence**, **alliance management**, and **SaaS** platform for EVE Online. It combines market data, manufacturing calculations, live battle tracking, alliance analysis, HR vetting, financial operations, sovereignty monitoring, and a full Dogma fitting engine to provide strategic dominance.

**Current Architecture:** **18 Microservices** (Docker Compose) - Production since 2026-01-31

**Scale:** 111 database migrations, 136+ tables, ~3,029 unit tests across 15 services

**Monolith:** ⛔ Fully decommissioned (2026-02-10) — ~72,000 lines removed

---

## Quick Start

### Start All Services

```bash
cd /home/cytrex/eve_copilot
./start-all.sh                     # Start Docker services + zkillboard stream

# Or manually:
cd docker
docker compose up -d               # Start all microservices
docker compose ps                  # Check status
docker compose logs -f api-gateway # View logs
```

### Access Points

- **API Gateway:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs
- **Public Frontend (Dev HMR):** http://localhost:5175 ⚡ **← Use for development**
- **Public Frontend (Prod):** http://localhost:5173
- **Unified Frontend (Internal):** http://localhost:3003

### Service Status

```bash
cd docker
docker compose ps                  # All service status
docker compose logs -f <service>   # View logs
```

### Database Access

```bash
echo '<SUDO_PASSWORD>' | sudo -S docker exec eve_db psql -U eve -d eve_sde
```

---

## Architecture Components

### Core Services (Docker)

| Service | Port | Purpose | Documentation |
|---------|------|---------|---------------|
| **api-gateway** | 8000 | Request routing to all microservices | [Microservices](ARCHITECTURE.microservices.md#api-gateway) |
| war-intel-service | 8002 | Combat intelligence, battles, power blocs, sovereignty, military ops | [Microservices](ARCHITECTURE.microservices.md#war-intel-service) |
| scheduler-service | 8003 | 40+ cron jobs (sync, aggregation, snapshots), legacy monolith scripts | [Microservices](ARCHITECTURE.microservices.md#scheduler-service) |
| market-service | 8004 | Market prices, trading | [Microservices](ARCHITECTURE.microservices.md#market-service) |
| production-service | 8005 | Manufacturing, PI (incl. empire analysis), mining, industry calc, production projects | [Microservices](ARCHITECTURE.microservices.md#production-service) |
| shopping-service | 8006 | Shopping lists, materials, freight pricing | [Microservices](ARCHITECTURE.microservices.md#shopping-service) |
| character-service | 8007 | Character data, ESI sync, fittings, Dogma engine, SDE browser, **account summary**, fleet readiness, skill plans | [Microservices](ARCHITECTURE.microservices.md#character-service) |
| auth-service | 8010 | EVE SSO OAuth, token management, encryption, **character management**, **org management** | [Microservices](ARCHITECTURE.microservices.md#auth-service) |
| ectmap-service | 8011 | Map screenshot generation (Playwright) | [Microservices](ARCHITECTURE.microservices.md#ectmap-service) |
| wormhole-service | 8012 | Wormhole intel, market analysis, threat detection | [Microservices](ARCHITECTURE.microservices.md#wormhole-service) |
| zkillboard-service | 8013 | zkillboard RedisQ live stream, battle detection | [Microservices](ARCHITECTURE.microservices.md#zkillboard-service) |
| dotlan-service | 8014 | DOTLAN EveMaps scraping (activity, sovereignty, alliances) | [Microservices](ARCHITECTURE.microservices.md#dotlan-service) |
| hr-service | 8015 | Red list, vetting engine (5-stage scoring), role sync, applications | — |
| finance-service | 8016 | Wallet sync, mining tax, moon mining dashboard, invoicing, SRP, doctrine management (clone, auto-pricing, changelog), buyback (Janice API) | — |
| ectmap (frontend) | 3001 | Next.js map frontend with SDE data | [Microservices](ARCHITECTURE.microservices.md#ectmap-frontend) |

### Data Layer

| Component | Purpose | Documentation |
|-----------|---------|---------------|
| PostgreSQL (eve_db) | Primary database (SDE + 106 migrations, 136+ tables) | PostgreSQL |
| Redis | L1 cache, session storage, rate limiting, market stats cache | Redis |

### Monitoring

| Component | Port | Purpose |
|-----------|------|---------|
| Prometheus | 9090 | Metrics collection (HTTP, DB, cache, SaaS) |
| Grafana | 3200 | Dashboards (service overview, HTTP perf, DB/cache, SaaS revenue) |

### Support Services

| Service | Port | Type | Purpose |
|---------|------|------|---------|
| **mcp-service** | 8008 | Docker | AI Tool Server (MCP protocol, 600+ dynamic tools) |
| copilot-server | 8009 | Manual | AI Agent (optional) |
| **Public Frontend (Dev)** | 5175 | Native | **Vite HMR (~200ms reload) ⚡** |
| Public Frontend (Prod) | 5173 | Docker | React SPA (nginx, 103MB) |
| Unified Frontend | 3003 | systemd | React dev server |

---

## Traffic Flow

```
User → Cloudflare → nginx → api-gateway:8000
                              ↓
        ┌─────────────────────┴──────────────────────────────┐
        ↓                     ↓                              ↓
   war-intel:8002      market:8004               auth:8010
   scheduler:8003      production:8005           character:8007
   wormhole:8012       shopping:8006             dotlan:8014
   hr:8015             finance:8016              ectmap:8011
        ↓                     ↓                              ↓
        └─────────────────────┬──────────────────────────────┘
                              ↓
                    PostgreSQL + Redis
                              ↑
                              │
                    zkillboard-service:8013
                    (Background Stream)
```

---

## Frontend Development Architecture

### Development vs Production

| Mode | Port | Technology | Reload Time | Use Case |
|------|------|------------|-------------|----------|
| **Development (HMR)** | 5175 | Vite (native) | **~200ms** ⚡ | Active development |
| Production (Docker) | 5173 | nginx + static build | N/A | Final testing, deployment |

### Development Workflow (Fast Mode)

**Start Dev Server:**
```bash
cd /home/cytrex/eve_copilot/public-frontend
./dev.sh
# Access: http://localhost:5175
```

**Architecture:**
```
Source Files (src/)
      ↓
  Vite Dev Server (Native Process)
      ↓
  Hot Module Replacement (HMR)
      ↓
  Browser Auto-Reload (~200ms)
```

**Features:**
- ✅ **Hot Module Replacement (HMR)** - React components re-render without page reload
- ✅ **State Preservation** - Component state survives updates
- ✅ **Instant Feedback** - Changes appear in <1 second
- ✅ **Source Maps** - Full debugging in browser DevTools
- ✅ **TypeScript Errors** - Instant in terminal + browser overlay

**Speed Comparison:**
```
Docker Build:  Edit → build (15s) → deploy (5s) → test = ~20s ❌
HMR Dev Mode:  Edit → HMR (200ms) → test = <1s ⚡
```

### Production Build (Docker)

**When to use:**
- Final verification before git push
- Testing nginx routing
- Production bundle size checks
- Performance profiling

**Build Process:**
```bash
cd /home/cytrex/eve_copilot/docker
docker compose build public-frontend    # Multi-stage Docker build
docker compose up -d public-frontend     # Deploy to nginx
```

**Build Details:**
- Stage 1: Node.js 20 Alpine (build)
- Stage 2: nginx Alpine (serve)
- Output: 103MB image, 9MB RAM usage
- Gzip compression enabled
- 1-year cache for static assets

### Best Practices

1. **Use Dev Mode for Development** (5175)
   - All code changes during active work
   - Instant feedback loop
   - Fast iteration

2. **Use Production Mode for Testing** (5173)
   - Before committing major changes
   - Verify bundle size
   - Test nginx routing

3. **Parallel Setup Recommended**
   - Keep both servers running
   - Dev on 5175, verify on 5173
   - Switch tabs for quick comparison

**Documentation:** `public-frontend/DEVELOPMENT.md`

---

## Dynamic OpenAPI Router (MCP Service)

**Port:** 8008 (Optional Service)

**Purpose:** AI-native API layer that exposes **609 MCP tools** from all microservices with zero manual configuration.

### Architecture Innovation

**Problem:** Traditional API integration for AI agents requires manual wrapper functions for each endpoint.
- 8 microservices × ~76 endpoints each = 608 manual wrapper functions
- Maintenance nightmare: API changes require updating wrappers
- Schema drift: Manual parameter definitions get out of sync

**Solution:** Dynamic OpenAPI Router
- **Zero manual wrappers** - All tools auto-generated from OpenAPI specs
- **Self-documenting** - Tool schemas extracted from FastAPI definitions
- **Always in sync** - Endpoint changes automatically reflected in tools
- **Domain-based activation** - Prevent tool overload via scoped contexts

### Data Flow

```
┌──────────────────────────────────────────────────────────────┐
│ STARTUP: Auto-Discovery of 609 Tools                        │
└──────────────────────────────────────────────────────────────┘

DomainManager.initialize()
      │
      ├─► Fetch: http://market-service:8000/openapi.json
      ├─► Fetch: http://war-intel-service:8000/openapi.json
      ├─► ... (8 microservices)
      │
      ▼
OpenAPIParser.parse_endpoints()
      │
      ├─► Extract: paths, methods, parameters, descriptions
      ├─► Parse: path params, query params, request bodies
      │
      ▼
OpenAPIConverter.endpoint_to_mcp_tool()
      │
      ├─► Generate tool name: GET /api/market/price/{type_id} → get_api_market_price_type_id
      ├─► Build inputSchema from OpenAPI parameters
      ├─► Attach metadata: {service: "market", method: "GET", path: "/api/market/price/{type_id}"}
      │
      ▼
Store in domain_tools = {
    'market': [71 tools],
    'war_intel': [260 tools],
    'production': [100 tools],
    'character': [71 tools],
    'auth': [33 tools],
    'shopping': [32 tools],
    'wormhole': [28 tools],
    'scheduler': [14 tools]
}

┌──────────────────────────────────────────────────────────────┐
│ RUNTIME: Domain Activation & Tool Execution                 │
└──────────────────────────────────────────────────────────────┘

AI Agent: "Enable war intel tools"
      │
      ▼
enable_war_intel_tools()
      │
      ▼
DomainManager.active_domain = "war_intel"
      └─► Returns: 260 war-intel tools available
      │
      ▼
AI Agent: "What battles are active?"
      │
      ▼
get_war_battles_active()
      │
      ▼
GenericAPIHandler.call_endpoint(
    service="war_intel",
    method="GET",
    path="/api/war/battles/active",
    arguments={}
)
      │
      ├─► Build URL: http://war-intel-service:8000/api/war/battles/active
      ├─► Replace path params: {type_id} → 44992
      ├─► Add query params: ?region_id=10000002
      ├─► Execute HTTP request
      │
      ▼
Return response.json() to AI agent
```

### Tool Generation Examples

**Example 1: Simple GET**
```yaml
# OpenAPI Spec
GET /api/market/price/{type_id}
  parameters:
    - name: type_id (path, required, integer)
    - name: region_id (query, optional, integer, default: 10000002)

# Generated MCP Tool
{
  "name": "get_api_market_price_type_id",
  "description": "Get market price for item in region",
  "inputSchema": {
    "type": "object",
    "properties": {
      "type_id": {"type": "integer", "description": "Item type ID"},
      "region_id": {"type": "integer", "default": 10000002}
    },
    "required": ["type_id"]
  },
  "_metadata": {
    "service": "market",
    "method": "GET",
    "path": "/api/market/price/{type_id}"
  }
}
```

**Example 2: POST with Body**
```yaml
# OpenAPI Spec
POST /api/shopping/list
  requestBody:
    application/json:
      schema:
        properties:
          name: string (required)
          description: string (optional)

# Generated MCP Tool
{
  "name": "post_api_shopping_list",
  "inputSchema": {
    "type": "object",
    "properties": {
      "name": {"type": "string"},
      "description": {"type": "string"}
    },
    "required": ["name"]
  },
  "_metadata": {
    "service": "shopping",
    "method": "POST",
    "path": "/api/shopping/list"
  }
}
```

### Component Structure

```
services/mcp-service/app/
├── openapi/                   # OpenAPI Processing
│   ├── parser.py              # Fetch & parse specs (httpx)
│   │   └── OpenAPIParser      # load_service_spec(), parse_endpoints()
│   └── converter.py           # OpenAPI → MCP conversion
│       └── Functions          # endpoint_to_mcp_tool(), generate_tool_name()
│
├── domains/                   # Domain Management
│   └── manager.py             # Domain activation & tool registry
│       └── DomainManager      # initialize(), enable_domain(), get_active_tools()
│
├── handlers/                  # HTTP Proxy
│   └── generic_api.py         # Generic API caller
│       └── GenericAPIHandler  # call_endpoint(service, method, path, args)
│
└── routers/                   # FastAPI Routes
    └── tools.py               # /mcp/tools/* endpoints
        ├── GET  /tools/list-dynamic
        └── POST /tools/call-dynamic
```

### Service Registration

**domains/manager.py:**
```python
SERVICES = {
    'market': 'http://market-service:8000/openapi.json',
    'war_intel': 'http://war-intel-service:8000/openapi.json',
    'production': 'http://production-service:8000/openapi.json',
    'shopping': 'http://shopping-service:8000/openapi.json',
    'character': 'http://character-service:8000/openapi.json',
    'auth': 'http://auth-service:8000/openapi.json',
    'scheduler': 'http://scheduler-service:8000/openapi.json',
    'wormhole': 'http://wormhole-service:8000/openapi.json',
}
```

**handlers/generic_api.py:**
```python
SERVICE_URLS = {
    'market': 'http://market-service:8000',
    'war_intel': 'http://war-intel-service:8000',
    # ... (8 services)
}
```

**Adding a new service:** Just add 2 lines (one in each dict) and restart the container.

### Domain-Based Activation

**Problem:** 609 tools at once overwhelms AI agents with choices.

**Solution:** Domain-based scoping
- Initial state: 8 domain switcher tools
- After activation: Only active domain's tools visible
- AI agent sees manageable tool count (~50-260 tools per domain)

**Workflow:**
1. Agent starts → sees 8 domain switchers (enable_X_tools)
2. Agent calls enable_war_intel_tools()
3. Agent now sees 260 war-intel tools
4. Agent executes get_war_battles_active(), get_system_danger(), etc.

### Performance Metrics

| Metric | Value | Notes |
|--------|-------|-------|
| **Startup Time** | ~10 seconds | Fetches + parses 8 OpenAPI specs |
| **Memory Usage** | <256MB | Tool definitions in memory |
| **Tool Count** | 609 | Auto-updates when endpoints change |
| **Manual Wrappers** | 0 | 100% auto-generated |
| **Code Maintenance** | 2 lines per new service | Add to SERVICES + SERVICE_URLS dicts |

### Use Cases

**AI Agent Integration:**
- Claude Desktop with MCP protocol
- Custom AI assistants via MCP SDK
- Automated trading/production bots

**Not For:**
- Web application (use api-gateway directly)
- Direct API integrations (use microservice APIs)
- High-frequency trading (use direct service calls)

### Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| OpenAPI Fetching | httpx | Async HTTP client |
| Spec Parsing | Python dict traversal | Extract paths, methods, params |
| Schema Validation | Pydantic | OpenAPIEndpoint model |
| Tool Generation | Pure Python | Dict transformation |
| HTTP Proxy | httpx | Route calls to microservices |
| API Framework | FastAPI | /mcp/tools/* endpoints |

### Benefits

1. **Zero Maintenance** - Endpoint changes automatically reflected
2. **Always Accurate** - Tool schemas extracted from source of truth
3. **Rapid Scaling** - New service = 2 lines of code
4. **Type Safety** - Pydantic models ensure correctness
5. **Self-Documenting** - Descriptions pulled from OpenAPI
6. **Testable** - Each component independently testable

### Future Enhancements

- **Parallel Fetching** - asyncio.gather() for faster startup
- **Tool Caching** - Redis cache for tool definitions
- **Versioning** - Support multiple API versions per service
- **Access Control** - Per-domain authentication
- **Rate Limiting** - Per-domain rate limits

---

## MCP (Model Context Protocol) Architecture

**Status:** ✅ Production (2026-01-31) - AI-Agent-Friendly API Layer

### Purpose

Transform granular frontend APIs into flexible, semantic tools for AI agents (Claude Desktop, custom agents). Reduces API complexity and provides contextual aggregation.

**Problem:** 609 granular frontend endpoints (256 in war-intel alone) require multiple calls for simple agent queries.

**Solution:** 50 semantic MCP tools with flexible scope parameters (summary/detailed/complete).

### Implementation Pattern

MCP endpoints live in each microservice at `/api/mcp/*` and combine multiple frontend endpoints with flexible parameters.

**Example:** `mcp_analyze_alliance`

```python
# Old: 6+ API calls
GET /api/intelligence/fast/{id}/summary
GET /api/intelligence/fast/{id}/corps-ranking
GET /api/intelligence/fast/{id}/top-ships
GET /api/intelligence/fast/{id}/geography
GET /api/intelligence/fast/{id}/activity-timeline
GET /api/intelligence/fast/{id}/top-enemies

# New: 1 API call with scope parameter
GET /api/mcp/alliance/{id}?scope=complete&include_threats=true
```

### War-Intel MCP Tools (14 Implemented)

| Category | Tool | Status | Description |
|----------|------|--------|-------------|
| **Alliance Intelligence** | `mcp_analyze_alliance` | ✅ | 3 scopes (summary/detailed/complete), combines 5-15 endpoints |
| | `mcp_assess_threats` | ✅ | Top attackers with danger scores |
| | `mcp_get_fleet_readiness` | ✅ | Doctrine compliance, fleet composition, pilot counts |
| **Battle Intelligence** | `mcp_get_battles` | ✅ | Flexible filters (active/recent/all, by alliance/region) |
| | `mcp_analyze_battle` | ✅ | Deep battle analysis with optional details |
| **Strategic Tools** | `mcp_assess_threat` | ✅ | System/constellation/region danger scoring |
| | `mcp_find_conflicts` | ✅ | Sov vulnerability, constellation danger, conflict trends |
| | `mcp_get_sovereignty_intel` | ✅ | Vulnerable systems, sov campaigns |
| **Operations** | `mcp_calculate_jump_route` | ✅ | Capital jump planning with fatigue |
| | `mcp_get_structure_timers` | ✅ | Upcoming vulnerability timers with state machine |
| **Economy** | `mcp_get_market_intel` | ✅ | War supply analysis, consumption |
| | `mcp_analyze_mining_ops` | ✅ | Moon mining intel summary |
| **Hourly Stats** | `mcp_alliance_hourly` | ✅ | Solo kills, solo ratio per bucket |
| | `mcp_corp_hourly` | ✅ | Avg/max kill value per bucket |

**Status:** All 14 MCP tools implemented and tested

### Endpoint Reduction

| Service | Frontend APIs | MCP Tools | Reduction |
|---------|---------------|-----------|-----------|
| **war-intel** | 256 | 12 | 95% |
| market | 69 | ~8 (planned) | 88% |
| character | 71 | ~10 (planned) | 86% |
| production | 91 | ~10 (planned) | 89% |
| **Total** | 609 | ~50 (target) | 92% |

### MCP Service (Port 8008)

**Purpose:** AI Tool Server exposing microservice APIs via MCP protocol

**Architecture:**
- **Domain Manager:** Loads OpenAPI specs from all services at startup
- **Tool Registry:** Converts OpenAPI → MCP tool definitions
- **Dynamic Loading:** 361 tools from 8 microservices (after mcp_only filtering)
- **Protocol:** SSE-based MCP server for Claude Desktop integration

**OpenAPI Filtering:**

```python
# services/mcp-service/app/openapi/parser.py
def parse_endpoints(service_name: str, mcp_only: bool = False):
    """Filter to /api/mcp/* endpoints only for specific services"""
    if mcp_only and not path.startswith('/api/mcp/'):
        continue
    # ...
```

**Configuration:**

```python
# services/mcp-service/app/domains/manager.py
SERVICES = {
    'war_intel': 'http://war-intel-service:8000/openapi.json',
    'market': 'http://market-service:8000/openapi.json',
    # ... 8 services total
}

# Apply mcp_only filter for war_intel
mcp_only = (service_name == 'war_intel')
endpoints = self.parser.parse_endpoints(service_name, mcp_only=mcp_only)
```

### Technical Patterns

**Scope Parameters:**

```python
@router.get("/alliance/{alliance_id}")
async def mcp_analyze_alliance(
    alliance_id: int,
    scope: Literal["summary", "detailed", "complete"] = "summary",
    days: int = Query(7, ge=1, le=90),
    include_threats: bool = False
):
    if scope == "summary":
        # Single fast query (50ms)
        return await _get_alliance_summary(alliance_id, days)
    elif scope == "detailed":
        # Parallel 4-5 queries (300ms)
        return await _get_alliance_detailed(alliance_id, days)
    else:  # complete
        # Full dashboard (2-3s)
        return await get_dashboard(alliance_id, days)
```

**Reuses Existing Logic:**
- MCP endpoints call existing service functions
- No code duplication
- Maintains performance optimizations (caching, indexes)

**Common Fixes:**
- SQL: `make_interval(days => %s)` for parameterized intervals
- DB Access: Dictionary keys for RealDictCursor (`row['name']`)
- Pydantic: `.model_dump()` before `.get()` access
- FastAPI: Explicit parameters to avoid Query object leakage

### Integration

**Claude Desktop:**
1. MCP service exposes tools via SSE protocol
2. Claude Desktop discovers 361 tools (war_intel filtered to 12)
3. Agent selects appropriate tool based on user query
4. Single API call retrieves aggregated data

**Future Expansion:**
- Apply pattern to remaining services (Market, Character, Production)
- Target: 50 total MCP tools replacing 609 frontend APIs
- Maintain backwards compatibility (frontend APIs unchanged)

---

## Documentation Index

### Architecture Documentation

| Document | Content |
|----------|---------|
| **[ARCHITECTURE.microservices.md](ARCHITECTURE.microservices.md)** | Microservices architecture, service details, Docker setup, API routing |
| **[ARCHITECTURE.deployment.md](ARCHITECTURE.deployment.md)** | Production deployment, security, monitoring |

### Development Guides

| Document | Content |
|----------|---------|
| **[README.md](README.md)** | Project overview, features, getting started |
| **[ARCHITECTURE.microservices.md](ARCHITECTURE.microservices.md)** | All 15 services with endpoints and test counts |
| **[ARCHITECTURE.deployment.md](ARCHITECTURE.deployment.md)** | Production deployment and security |
| **[public-frontend/README.md](public-frontend/README.md)** | Public frontend overview, tech stack |

---

## Key Features

### Combat Intelligence (Real-Time)
- **Live Battle Tracking** - 5-second updates, ectmap integration, battle detection
- **Alliance Intelligence** - 9 specialized tabs (Overview, Offensive, Defensive, Capitals, Corps, Pilots, Wormhole, Activity, Hunting)
- **Corporation Intelligence** - 6 detailed tabs with 11-panel deep analysis
- **Power Bloc Analytics** - Coalition rankings, Redis caching (100x faster)
- **System Danger Scores** - 0-100 threat assessment, route safety analysis
- **Battle Intelligence** - Attacker loadout profiling, fleet size estimation, victim tank analysis, BFS side detection
- **Killmail Intelligence System** - Multi-source threat analysis fusing killmail data with DOTLAN ADM:
  - **Threat Composition** — Top attackers by alliance with kill bars, ISK destroyed, ship diversity, weighted damage profiles (EM/Thermal/Kinetic/Explosive)
  - **Capital Escalation Radar** — Capital ship sightings by system with escalation timeline (avg/min time from subcap to capital arrival)
  - **Logi Shield Score** — Enemy logistics strength scored 0-100 via kill suppression, logi ratio, kill asymmetry (STRONG/MODERATE/WEAK badges)
  - **Hunting Scoreboard** — Ranked system opportunities fusing player deaths + DOTLAN ADM + capital umbrella detection (500 systems analyzed)
  - **Pilot Risk Assessment** — AWOX detection via friendly-fire scoring with risk badges (Normal/Trainable/Liability/AWOX Risk)
  - **Corp Health Dashboard** — Member count, activity rate, ISK efficiency, member trend sparkline
  - **LiveMap Intelligence Overlays** — 4 ECTMap visualizations (Hunting Heatmap ColorMode, Capital Threat Zones overlay, Logi Strength overlay, Hunting Scoreboard top-10 markers) with compact INTEL filter panel. 3 global map endpoints (`/api/intelligence/map/hunting-heatmap`, `capital-activity`, `logi-presence`).

### Military Operations
- **D-Scan Parser** - Paste d-scan output, get ship classification and fleet composition
- **Local Scan** - Analyze local chat for hostile counts and threat assessment
- **Fleet PAP Tracking** - Participation tracking with fleet operations management
- **Structure Timers** - State machine (pending/reinforced/vulnerable/active/completed), jitter windows
- **Discord Relay** - Configurable webhooks with filter matching (region, alliance, ISK threshold)
- **Timerboard** - Structure vulnerability timer management

### Management Suite
- **CEO Command Center** - Strategic landing dashboard at `/corp` with 8 KPI tiles, action item alerts, 6 section preview cards (Treasury, Military, Personnel, Ship Replacement, Infrastructure, Logistics)
- **CEO Cockpit** - Operational deep-dive at `/corp/finance` with 20+ panels across Finance, Military, Personnel, and Production sections (sparklines, mini-charts, drill-down tables)
- **Corp Page Header** - Shared `CorpPageHeader` component across all 7 corp pages — ESI corp logo, name resolution, consistent styling
- **HR Service** - Red list management, 5-stage vetting engine (risk scoring 0-100), role sync, activity tracking, application portal
- **Finance Service** - Wallet sync, mining tax calculation, moon mining dashboard (extraction calendar, structure performance, ore analytics), invoice generation, financial reports
- **SRP & Doctrine** - Doctrine CRUD with EFT/DNA import, killmail matching, SRP workflow (dual scoring: fuzzy + Dogma compliance), pricing engine, Doctrine Engine integration (stats, readiness, BOM, shopping list bridge)
- **Industry Calculator** - Invention cost calculator, structure bonuses, facility comparison, system cost index
- **Logistics** - Freight pricing (6 endpoints), buyback with Janice API, jump planner
- **Sovereignty & Equinox** - System topology (4,358 systems), workforce graph (BFS), skyhook telemetry, Metenox drill tracking, sov simulator
- **Moon Mining Operations** - Mining observer dashboard, extraction calendar (ESI sync), structure ISK/day performance, ore breakdown by rarity (R4-R64), top miners ranking
- **ESI Notifications** - Automated notification sync, timer-relevant classification, auto-processing into structure timers

### Fitting System & Dogma Engine
- **Dogma Engine** - Full modifier pipeline: ItemModifier, LocationGroupModifier, OwnerRequiredSkillModifier
- **Stacking Penalty** - EVE-accurate `e^(-((n/2.67)^2))` for ops 4/5/6, with correct exemptions:
  - **Module bonuses**: Stacking penalized (e.g., 2x Gyrostabilizer II)
  - **Skill bonuses**: NOT stacking penalized (`is_skill` flag, applied as independent multipliers)
  - **Rig bonuses/drawbacks**: NOT stacking penalized (`is_rig`/`is_drawback` flags)
  - **Ship role bonuses**: NOT stacking penalized (applied in step 5.5)
- **Dogma Pipeline** (11 steps):
  1. Load module/ship attrs from SDE
  1.5. Supplement invTypes attrs + load skill virtual modules
  3.5. Apply compensation skills (LocationGroupModifier on resist attrs)
  4. Load modifiers from fitted module effects
  5. Separate by func type (ItemModifier, LocationGroup, OwnerRequired, etc.)
  5.5. Ship role bonuses (per-level + flat)
  5.7. T3D mode modifiers (PostDiv)
  5.8. Self-modifiers (overheating)
  5.95. Rig drawback reduction (pre-apply rigging skill bonus to attr 1138)
  6. Apply location modifiers to module attrs (stacking penalized, skill-exempt)
  7. Apply ship-targeting modifiers (stacking penalized, skill-exempt)
  8. Apply OwnerRequiredSkillModifier (stacking penalized, skill-exempt)
  9. Apply attribute caps (maxAttributeID mechanism)
- **Fitting Stats** - DPS, EHP, capacitor, navigation, targeting, repairs, applied DPS, warp time, scanability — all from SDE data + Dogma modifiers
- **Module States** - Per-module offline/online/active/overheated with effectCategory filtering (0=passive, 1=active, 4=online, 5=overload)
- **Overheating** - Heat bonus calculation from SDE overload attributes, overheated DPS/rep stats
- **Combat Boosters** - Slot 1-3 drugs with togglable side effects, integrated into Dogma modifier pipeline
- **Sustainable Tank** - Cap-limited repair rates (cap stable = full rep, unstable = proportional)
- **Applied DPS** - Turret tracking, missile application, drone sig reduction against 7 target profiles (frigate→structure)
- **Passive Defense** - Shield peak regen, EHP/s sustained tank, 11 NPC damage profiles for EHP calculation
- **Fit Comparison** - Side-by-side comparison of 2-4 fittings with best/worst highlighting
- **Character Skills** - Use actual trained skill levels (from `character_skills` DB) or default All Skills V
- **Implant Support** - ESI sync, Dogma engine integration, include_implants toggle
- **T3D Mode Switching** - Tactical Destroyer modes (Defense/Propulsion/Sharpshooter), PostDiv modifiers from group 1306
- **Triglavian Spool-Up** - Min/avg/max DPS for Entropic Disintegrators, ramping damage calculation
- **Fighter DPS** - Squadron size × damage/cycle, FighterInput model, SDE attribute loading
- **Fleet Boosts** - Pre-calculated buff values, 16 warfareBuffID definitions, 4 presets (Shield/Armor/Skirmish/Information)
- **Projected Effects** - Webs/paints (stacking penalized), neuts/reps (rates), 7 presets
- **Constraint Validation** - CPU/PG/Calibration limits, maxGroupFitted, maxTypeFitted, 1-cloak rule
- **Market Tree Browser** - 4-tab browser (Hulls, Modules, Charges, Drones) with ship compatibility filters and charge search
- **Ship Compatibility** - Weapon size matching, canFitShipGroup/Type, hardpoint limits, rig size filter
- **Visual Ship Display** - Interactive slot layout with module state toggle (right-click cycle), colored state indicators
- **Verified Accuracy** - Jackdaw: agility exact match (3.2400), align exact (27.4s), resists exact (PyFA), velocity exact, shield HP within 1

### Economic Intelligence
- **Manufacturing Optimization** - Production chains, material calculations, PI profitability, reaction requirements
- **Production Projects** - Multi-item manufacturing project management with per-material buy/make decisions, aggregated shopping lists with Jita prices, copy-to-multibuy, and fitting integration (create project from any fitting)
- **Market Analysis** - Price tracking, arbitrage detection (with net profit/fees), trade route optimization
- **PI Advisor** - Skill-aware profitability analysis, optimal planet combinations, production layouts
- **War Economy** - Market opportunities driven by combat activity
- **Buyback Program** - Janice API integration for fair pricing

### Strategic Intelligence
- **Coalition Detection** - Power bloc tracking, alliance relationships
- **War Tracking** - Conflict analysis, efficiency trends (dual ISK + K/D efficiency)
- **Sovereignty Monitoring** - Territory control, SOV threats, asset snapshots with delta analysis
- **Capital Fleet Tracking** - Carriers, Dreads, FAX, Supers, Titans (9 intelligence categories)

### Doctrine Systems (Two Separate Systems)

**Important:** The codebase has two independent systems that both use the term "Doctrines":

| System | Route | Backend | Purpose |
|--------|-------|---------|---------|
| **Doctrine Intel** | `/doctrines` | war-intel-service (`/api/fingerprints`) | Passive — "What are enemies flying?" |
| **Corp Doctrine Management** | `/corp/srp` → Doctrines tab | finance-service (CRUD) + character-service (Dogma Engine via `/api/doctrines`) | Active — "What should our pilots fly?" |

**Doctrine Intel** (`/doctrines`):
- zKillboard killmail fingerprinting → fleet composition detection
- Tabs: Live-Ops, Intel, Trends
- Data source: `getLiveOpsData()` → war-intel-service
- Shows: active doctrines in universe, fleet sizes, counter-matrix, hotspots

**Corp Doctrine Management** (`/corp/srp` → Doctrines):
- Corporation-managed fittings with EFT import, SRP payouts, Dogma-powered stats
- Sub-tabs in expanded doctrine: [Fitting | Readiness | Fleet BOM]
- Readiness: character skill check (CAN FLY/CANNOT FLY, DPS/EHP ratio vs All V)
- Fleet BOM: bill of materials for N ships, copy multibuy, → Shopping List integration
- Data source: `doctrineApi` → finance-service (CRUD), `doctrineStatsApi` → character-service/Doctrine Engine

**No shared code or data between the two systems.** Could be connected in the future (e.g., enemy doctrine detection → suggest counter-doctrine from corp fittings).

### SaaS Platform
- **Tier Hierarchy** - public < free < pilot < corporation < alliance < coalition
- **Feature Gating** - FeatureGateMiddleware with tier_map.yaml (350+ endpoints)
- **ISK Payment** - PAY-XXXXX code → wallet journal polling → auto-activation
- **Corp Registration** - ESI role → platform role auto-mapping (CEO/Director→admin)
- **Rate Limiting** - Tier-aware Redis rate limiting (public=30 to coalition=2000 req/min)

### Character Management (Phase 5)
- **Multi-Character Accounts** - Platform accounts with primary + alt linking
- **Token Health Monitoring** - Per-character ESI token validity, expiry, scope completeness
- **13 Scope Groups** - Skills, Wallet, Assets, Industry, Fittings, Location, Contacts, Contracts, Mail, Clones, Blueprints, Killmails, Corp Roles
- **Account Summary** - Aggregated ISK, SP, locations, skill queues across all characters
- **Character Switcher** - Navigation dropdown for switching active character context
- **Primary Management** - Switch primary character, remove alts with protection

### Org Management (Phase 2)
- **Corp Member Management** - List corp members with roles and join dates, role updates (member/officer/director/admin), member removal
- **Permission Matrix** - Configurable role-based permissions per corp (JSONB), view and update permission mappings
- **Audit Log** - Full audit trail for org actions (role changes, kicks, permission updates), filterable by actor/action/date, CSV export
- **8 API Endpoints** - Under `/api/auth/public/org/` with JWT-based corp/role authorization
- **Database** - `org_permissions` (role→permissions mapping) + `org_audit_log` (governance trail)

### Doctrine Management Extensions
- **Doctrine Clone** - Clone existing doctrines with new name, preserving fitting and ship type
- **Auto-Pricing** - Real-time doctrine cost calculation from Jita market prices (item-level breakdown)
- **Doctrine Changelog** - Full audit trail for doctrine changes (created, updated, cloned, deleted) with JSONB diffs
- **Corp Changelog** - Corp-wide changelog across all doctrines
- **Doctrine Categories** - Categorization field (Mainline DPS, Logistics, Tackle, etc.) for filtering and organization
- **Fleet Readiness** - Per-doctrine, per-corp readiness analysis (can fly / cannot fly, DPS/EHP ratios, missing skills)
- **Skill Plan Export** - EVEMon-compatible XML skill plan export for missing doctrine skills
- **Database** - `doctrine_changelog` table + `category` column on `fleet_doctrines`

### Technical Features
- **18 Microservices** - Docker Compose orchestration, 106 database migrations, 136+ tables
- **~3,029 Unit Tests** - Pure function tests across 15 services, <5s runtime
- **14 MCP Tools** - Semantic AI agent interface replacing 600+ granular endpoints
- **Shared ESI Client** - Circuit breaker, distributed lock, ETag cache, token encryption
- **Prometheus + Grafana** - HTTP metrics, DB query duration, cache hit rates, SaaS revenue
- **19 Intelligence Pages** - Complete combat analytics suite
- **50+ Reusable Components** - React component library
- **Code Splitting** - All pages lazy-loaded
- **HMR Dev Mode** - ~200ms reload time for development

---

**Last Updated:** 2026-02-22 (18 Services, 112 Migrations, ~3,037 Tests, SaaS Complete, Character Management Phase 1, Org Management Phase 2, Killmail Intelligence System, Dogma Engine v4 + Doctrine Engine Integration, Dual Doctrine Systems documented, Skill Stacking Fix, T3D Modes, Spool-Up, Fighters, Fleet Boosts, Projected Effects, Module States, Overheating, Boosters, Fit Comparison, Production Projects, Doctrine Management Extensions)
