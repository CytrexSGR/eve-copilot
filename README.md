# EVE Co-Pilot

![Alpha](https://img.shields.io/badge/Status-Alpha-yellow?style=for-the-badge) ![Under Development](https://img.shields.io/badge/Under-Development-orange?style=for-the-badge)

Comprehensive intelligence, industry, fitting analysis, and alliance management platform for EVE Online. 17 microservices, 111+ database migrations, 3,029+ unit tests, full Dogma engine v4. Public combat intelligence dashboard + SaaS management suite.

> ⚠️ **Alpha Software**: This project is in active development. Features may be incomplete, data may be inaccurate, and breaking changes can occur. Use at your own risk!

## 🌐 Live Public Dashboard (Alpha)

**[🚀 https://eve.infinimind-creations.com](https://eve.infinimind-creations.com)** ⚠️ Alpha Version

Free real-time combat intelligence dashboard with:
- ⚡ **Live Battle Tracking** - Real-time battle detection & updates every 5 seconds
- 🗺️ **ectmap Integration** - Full EVE universe map with live battle overlays
- 📊 **24-Hour Battle Reports** - Track combat activity across New Eden
- 💰 **War Profiteering** - Most destroyed items and market opportunities
- ⚔️ **Alliance Wars** - Active conflicts and combat statistics
- 🛣️ **Trade Route Safety** - Danger analysis for cargo routes

**No login required. Updates daily from zKillboard + ESI.**

## 📱 Live Telegram Alerts

**[📢 Join: t.me/infinimind_eve](https://t.me/infinimind_eve)**

Get real-time combat intelligence delivered directly to your phone:

### 🚨 Combat Hotspot Alerts (Real-time)
Instant notifications when combat spikes are detected (5+ kills in 5 minutes):
- 📍 System location with security status and region
- 🔥 Kill count and activity rate
- 💰 Total ISK destroyed with ship breakdowns
- 🎯 Intelligent danger level (🟢 LOW → 🔴 EXTREME)
- ⚔️ Attacking forces (alliances/corps involved)
- 💀 Top 5 most expensive ship losses
- 🚨 Gate camp detection with confidence rating

### 📊 Scheduled Reports
- **Battle Reports** - Every hour: 24h combat statistics, hot zones, peak activity
- **Alliance Wars** - Every 30 minutes: Active conflicts, K/D ratios, efficiency ratings
- **War Profiteering** - Every 6 hours: Most destroyed items, market opportunities

**Alert cooldown:** 10 minutes per system to prevent spam during extended battles.

---

![Status](https://img.shields.io/badge/Status-Alpha-yellow)
![EVE Online](https://img.shields.io/badge/EVE-Online-orange)
![Python](https://img.shields.io/badge/Python-3.11+-blue)
![React](https://img.shields.io/badge/React-19-61DAFB)
![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6)
![License](https://img.shields.io/badge/License-MIT-green)
![Website](https://img.shields.io/website?url=https%3A%2F%2Feve.infinimind-creations.com&label=Live)
![Telegram](https://img.shields.io/badge/Telegram-Join%20Alerts-2CA5E0?logo=telegram)

---

## 🎮 Core Features

### 🏭 Production & Manufacturing
- **Production Planner** - Calculate manufacturing costs with ME/TE bonuses, regional pricing
- **Material Chain Analysis** - Full recursive breakdown of all materials needed (raw → components → final product)
- **Regional Economics** - Compare profitability across all regions, identify best manufacturing locations
- **Production Workflow** - Track multiple production jobs, batch processing, job status management
- **Material Classifier** - Difficulty scoring for material acquisition (market availability, price volatility)

### 💰 Market Intelligence
- **Arbitrage Finder** - Cross-region price differences with route planning and profit calculations
- **Market Hunter** - Automated scanning of 2000+ T1 items for profitable manufacturing opportunities
- **Live Market Data** - Real-time ESI API integration with order depth analysis and market spread
- **Price History** - Historical price tracking, trend analysis, volatility scoring
- **Market Gaps** - Identify supply shortages and high-demand items

### 📦 Shopping & Logistics
- **Shopping Wizard** - Guided list creation with automatic best-price finding across regions
- **Multi-Region Price Comparison** - Compare prices for entire shopping lists across trade hubs
- **Route Optimization** - A* pathfinding for multi-stop shopping routes with jump/distance calculations
- **Cargo Calculator** - Volume calculations, transport ship recommendations (Iterons, DST, Freighters)
- **Build vs Buy Analysis** - Automatic comparison of manufacturing vs purchasing with material recursion
- **Material Expansion** - Recursive blueprint breakdown with option to build or buy sub-components

### ⚔️ Combat Intelligence (Public Dashboard)
- **Live Battle Tracking** - Real-time battle detection from zkillboard stream (5+ kills/5min threshold)
- **ectmap Integration** - Full EVE universe map with live battle overlays, interactive tooltips, click navigation
- **Battle Detail Pages** - Individual battle analytics with kill timeline, ship class breakdown, ISK tracking
- **24-Hour Battle Reports** - Total kills, ISK destroyed, peak activity hours, regional breakdown
- **War Profiteering** - Track most destroyed items, market opportunities from combat losses
- **Alliance Wars** - Active conflicts, kill/loss statistics, efficiency ratings, war zones
- **Trade Route Safety** - Danger scoring based on recent kills along trade corridors
- **Telegram Integration** - Real-time battle alerts mirrored in dashboard feed
- **Data Consistency** - Transactional integrity (battles only updated if kills successfully stored)
- **Automatic Cleanup** - Old battles (>2h) removed every 30 minutes via cron job
- **Doctrine Detection** - Automatic fleet composition recognition via DBSCAN clustering
  - Real-time fleet snapshot collection (5-minute windows)
  - DBSCAN clustering with cosine similarity for pattern detection
  - Automatic derivation of items of interest (ammunition, fuel, modules)
  - Market intelligence for war profiteering and supply chain optimization
- **Reshipment Analysis** - Battle logistics strength assessment
  - Track pilot reshipments (deaths → new ship → return)
  - Alliance reship ratios indicate staging proximity and SRP strength


### 🌍 Planetary Industry (PI)
- **Production Chain Analysis** - Full P0→P4 material chain visualization
- **Profitability Calculator** - ROI analysis with real-time market prices
- **Colony Management** - ESI sync for character colonies, pins, and routes
- **Project Management** - Create and track PI production projects
- **Material Assignments** - Auto-assign materials to colonies based on planet types
- **SOLL Planning** - Target vs actual output comparison (German: SOLL vs IST)
- **Multi-Character Aggregation** - Aggregate PI data across multiple characters
- **Planet Recommendations** - Suggest optimal planet types for target products
- **Make-or-Buy Analysis** - Compare market prices vs production costs for PI products

### 📈 War Economy Intelligence
- **Fuel Market Tracking** - Isotope volume/price anomalies for capital movement prediction
- **Market Manipulation Detection** - Z-score analysis (>3σ triggers alerts)
- **Supercapital Timer Tracking** - Intel on supercap construction
- **Timezone Analysis** - Alliance activity heatmaps by UTC hour
- **Critical Item Monitoring** - Price history for strategic commodities

### 🏢 Alliance Management Suite
- **HR & Vetting** - Red list management, 5-stage risk scoring engine (0-100), corp history analysis, application portal with status workflow
- **Finance** - Wallet sync, mining tax calculation, invoice generation, financial reports, buyback program (Janice API)
- **SRP & Doctrine** - Doctrine CRUD with EFT/DNA import, killmail matching, SRP claim workflow, pricing engine
- **Industry Calculator** - Invention cost calculator, structure bonuses, facility comparison, system cost index tracking
- **Logistics** - Freight pricing (Blockade Runner to Jump Freighter), transport route optimization
- **Military Ops** - D-Scan parser, Local Scan, Fleet PAP tracking, Discord relay (configurable webhooks), timerboard
- **Sovereignty & Equinox** - System topology (4,358 systems), workforce graph (BFS), skyhook telemetry, Metenox drill tracking, sov simulator, asset snapshots with delta analysis
- **ESI Notifications** - Automated notification pipeline, timer-relevant classification, auto-processing into structure timers with jitter windows

### 💎 SaaS Platform
- **Tier System** - public < free < pilot < corporation < alliance < coalition
- **Feature Gating** - Middleware-based per-endpoint tier enforcement (350+ endpoints)
- **ISK Payment** - In-game currency payment with wallet journal polling and auto-activation
- **Corp Registration** - ESI role detection with automatic platform role mapping
- **Tier-Aware Rate Limiting** - Redis-based, scales from 30 req/min (public) to 2,000 req/min (coalition)
- **Monitoring** - Prometheus metrics + Grafana dashboards for SaaS revenue, subscriptions, gate decisions

### 🔫 Fitting System & Dogma Engine v4
- **Dogma Engine v4** - Full EVE modifier pipeline (ItemModifier, LocationGroupModifier, OwnerRequiredSkillModifier) with stacking penalty, T3D modes, Triglavian spool-up, fighter DPS, fleet boosts, projected effects
- **Module States** - Per-module offline/online/active/overheated with smart state cycling
- **Fitting Stats** - DPS, EHP, capacitor, navigation, targeting, repairs, applied DPS, warp time, scanability — all calculated from SDE + Dogma modifiers
- **Character Skill Integration** - Use actual trained skill levels or default All Skills V, with character selector dropdown and implant support
- **Market Tree Browser** - 4-tab browser (Hulls, Modules, Charges, Drones) with ship compatibility filters
- **Constraint Validation** - CPU/PG/Calibration limits, maxGroupFitted, maxTypeFitted, 1-cloak rule
- **Interactive Ship Display** - Visual slot layout with click-to-fit, charge selection, drone management
- **EFT Import/Export** - Paste EFT format, parse, preview, import to editor; export to clipboard
- **Fit Comparison** - Side-by-side comparison of 2-4 fittings
- **Custom Fittings** - Save, share, tag, browse shared fittings

### 🏢 Doctrine Engine
- **Doctrine Stats** - Full Dogma-powered stats for corporation doctrines
- **Readiness Check** - Character skill compliance per doctrine fitting
- **Compliance Scoring** - Dual scoring: fuzzy killmail matching + Dogma engine verification
- **Bill of Materials** - Aggregated shopping list with Jita prices for doctrine fittings

### 🌙 Moon Mining Operations
- **Extraction Calendar** - Active and upcoming moon extraction timers
- **Structure Performance** - Moon mining structure efficiency tracking
- **Ore Analytics** - Moon ore composition and value analysis

### 📋 Production Projects
- **Multi-Item Projects** - Group items into named manufacturing projects
- **Buy/Make Decisions** - Per-material buy vs manufacture decision tracking
- **Shopping Lists** - Aggregated material lists with live Jita prices and copy-to-multibuy
- **Fitting Integration** - Create project directly from fitting (hull + all modules)

### 📊 CEO Command Center
- **Strategic Dashboard** - Corporation-level KPIs and operational overview
- **Operational Deep-Dive** - Detailed metrics across all management areas

### 🚀 Ship Mastery
- **Mastery Calculation** - Calculate mastery level (0-4) for any ship
- **Flyable Ships** - List all ships a character can fly at mastery 1+
- **Multi-Character Comparison** - Compare mastery across all characters
- **Skill Gap Analysis** - Identify missing skills for higher mastery

### 🗺️ LiveMap Intelligence Overlays
- **Hunting Heatmap** - Systems colored by hunting score (deaths + ADM + capitals)
- **Capital Threat Zones** - Orange/red circles for capital ship sightings
- **Logistics Strength** - Cyan indicators for logistics ship presence
- **Entity Live Map** - Corp/Alliance/PowerBloc activity visualization on map

### 👤 Character Management
- **EVE SSO OAuth2** - Secure authentication with multiple character support
- **Multi-Character Portfolio** - Aggregate view of wallets, assets, skills across all characters
- **Wallet Tracking** - Real-time balance monitoring, transaction history
- **Asset Management** - View all character/corp assets with location filtering
- **Industry Jobs** - Monitor manufacturing, research, copying, invention jobs
- **Corporation Support** - Corp wallet divisions, member lists, roles
- **Skill Planning** - Required skills for items, training time calculations, skill recommendations

### 🗺️ Navigation & Routes
- **A* Route Calculator** - Optimal pathfinding between any two systems
- **Trade Hub Routes** - Pre-calculated distances to major hubs (Jita, Amarr, Dodixie, Rens, Hek)
- **Danger Scoring** - Route safety based on recent combat activity (kills/hour, ship types destroyed)
- **Shopping Routes** - Optimized multi-stop paths for shopping lists
- **System Search** - Fast lookup of systems, regions, constellations

---

## 🤖 AI Agent (Conversational Interface)

Natural language interface to 600+ EVE tools through Claude AI (14 semantic MCP tools + auto-generated from OpenAPI):

**Features:**
- Multi-turn conversations with full session history
- Automatic tool selection for EVE operations
- Plan detection for complex multi-step workflows
- Configurable autonomy levels (L0-L3)
- Real-time WebSocket event streaming
- Full audit trail and replay capability

**Example:**
```
User: "What profitable items can I manufacture in Jita?"
Agent: [Analyzes market data, production costs, returns recommendations]

User: "Create shopping list for 10 Caracals"
Agent: [Detects multi-tool plan, requests approval based on autonomy level]
```

See [Agent Documentation](docs/agent/) for details.

---

## 🏗️ Tech Stack

**Backend (17 Microservices):**
- FastAPI 0.104+ with async/await, Docker Compose orchestration
- PostgreSQL 16 (EVE SDE + 111+ application migrations, 136+ tables)
- Redis (L1 cache, session storage, rate limiting, 4 uvicorn workers per service)
- Shared ESI client with circuit breaker, distributed lock, ETag cache, token encryption
- Dogma Engine v4 (modifier parser, stacking penalty, skill bonuses, T3D modes, spool-up, fleet boosts, projected effects)
- MCP (Model Context Protocol) - 609 dynamic tools
- Prometheus + Grafana monitoring (HTTP, DB, cache, SaaS metrics)
- 3,029+ unit tests across 15 services (<5s runtime)

**Public Frontend** (`/public-frontend`):
- React 19 + TypeScript 5
- Vite 7 - Build tooling
- TanStack Query v5 - Data caching
- ectmap integration (iframe, port 3001)
- Auto-refresh every 60s

**ectmap** (`/ectmap` - Port 3001):
- Next.js 16 (Turbopack)
- Canvas-based EVE Online universe map
- Live battle overlay with 5s refresh
- Interactive tooltips & click navigation

**Internal Unified Frontend** (`/unified-frontend` - Port 3003):
- React 18 + TypeScript 5
- TanStack Query v5 - Data caching
- Lazy-loaded pages with code splitting
- Fitting system (EVE Workbench-style)

---

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Node.js 18+ (for frontend development with HMR)

### Setup

```bash
# Clone repository
git clone https://github.com/CytrexSGR/Eve-Online-Copilot.git
cd Eve-Online-Copilot

# Start all 17 microservices + infrastructure
cd docker
docker compose up -d
docker compose ps                  # Verify all services healthy

# Or use startup script
./start-all.sh

# Frontend development (fast HMR mode)
cd public-frontend
./dev.sh                           # Vite dev server, ~200ms reload
# Access: http://localhost:5175
```

### Access Points
- **API Gateway:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs
- **Public Frontend (Dev HMR):** http://localhost:5175
- **Public Frontend (Prod):** http://localhost:5173
- **ectmap (Universe Map):** http://localhost:3001
- **Internal Tools (Unified Frontend):** http://localhost:3003

See [OPERATIONS.md](OPERATIONS.md) for full operational documentation.

---

## 🔧 Self-Hosted Setup

### EVE SSO Application

1. Go to [EVE Developer Portal](https://developers.eveonline.com)
2. Create a new application
3. Set callback URL to `http://localhost:8000/api/auth/callback` (or your domain)
4. Copy Client ID and Secret to your `.env` file (see `.env.example`)

### Database

The project uses PostgreSQL 16 with the EVE Static Data Export (SDE). On first startup, migrations in `migrations/` set up the application schema. You'll need to import the SDE separately — see [EVE SDE Downloads](https://developers.eveonline.com/resource/resources).

### Configuration

Copy `.env.example` to `.env` and fill in your values. At minimum you need:
- Database credentials
- EVE SSO Client ID and Secret

---

## 📊 Data Sources

- **zKillboard RedisQ** - Real-time combat stream for live battle tracking
- **zKillboard API** - Historical combat data (daily killmail downloads)
- **ESI API** - EVE Online official API
- **EVE SDE** - Static Data Export (PostgreSQL)
- **DOTLAN EveMaps** - System activity (NPC kills, jumps, ship/pod kills), sovereignty campaigns, alliance rankings, ADM history
- **Telegram Bot API** - Real-time battle alerts and scheduled reports
- **Janice API** - Item appraisal for buyback pricing

---

## 📚 Documentation

| Topic | Location |
|-------|----------|
| **Architecture** | [ARCHITECTURE.md](ARCHITECTURE.md) |
| **Microservices** | [ARCHITECTURE.microservices.md](ARCHITECTURE.microservices.md) |
| **Deployment** | [ARCHITECTURE.deployment.md](ARCHITECTURE.deployment.md) |
| **Operations Guide** | [OPERATIONS.md](OPERATIONS.md) |
| **Docker Setup** | [docker/README.md](docker/README.md) |

---

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Submit a pull request

---

## 📝 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## 🔗 Links

- **Live Dashboard:** https://eve.infinimind-creations.com
- **Telegram Alerts:** https://t.me/infinimind_eve
- **GitHub Issues:** https://github.com/CytrexSGR/Eve-Online-Copilot/issues
- **EVE Online:** https://www.eveonline.com

---

**Built by capsuleers, for capsuleers.** 🚀
