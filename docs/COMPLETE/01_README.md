# EVE Co-Pilot

![Alpha](https://img.shields.io/badge/Status-Alpha-yellow?style=for-the-badge) ![Under Development](https://img.shields.io/badge/Under-Development-orange?style=for-the-badge)

Comprehensive intelligence and industry platform for EVE Online. Two frontends: public combat intelligence dashboard and internal production tools.

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
![React](https://img.shields.io/badge/React-18-61DAFB)
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

### 🔫 DPS & Fitting Analysis
- **Weapon DPS Calculator** - Calculate DPS for any weapon/ammo combination
- **Ammo Comparison** - Compare performance across ammo types
- **Fitting Analysis** - Analyze saved fittings with all modifiers (damage mods, Bastion)
- **Ship Bonuses** - Include ship damage bonuses in calculations
- **Skill Integration** - Factor in character skills for accurate DPS

### 🚀 Ship Mastery
- **Mastery Calculation** - Calculate mastery level (0-4) for any ship
- **Flyable Ships** - List all ships a character can fly at mastery 1+
- **Multi-Character Comparison** - Compare mastery across all characters
- **Skill Gap Analysis** - Identify missing skills for higher mastery


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

Natural language interface to all 143 EVE tools through Claude AI:

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

**Backend:**
- FastAPI 0.104+ with async/await
- PostgreSQL 16 (EVE SDE data + application state)
- Redis (session cache, ESI name resolution)
- ESI API integration with rate limiting
- MCP (Model Context Protocol) - 143 tools

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
- Keyboard shortcuts

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 16
- Redis (optional, for agent sessions)

### Setup

```bash
# Clone repository
git clone https://github.com/CytrexSGR/Eve-Online-Copilot.git
cd Eve-Online-Copilot

# Backend setup
pip install -r requirements.txt
cp config.example.py config.py
# Edit config.py with your database credentials

# Start backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Public frontend setup (separate terminal)
cd public-frontend
npm install
npm run dev -- --host 0.0.0.0

# ectmap setup (separate terminal)
cd ectmap
npm install
npm run dev

# Internal frontend setup (separate terminal)
cd frontend
npm install
npm run dev -- --host 0.0.0.0
```

### Production Server (Systemd Services)

On the production server, frontends are managed by systemd:

```bash
# Check status
sudo systemctl status eve-public-frontend    # Port 5173
sudo systemctl status eve-unified-frontend   # Port 3003
sudo systemctl status eve-intelligence-api   # Port 8001

# Restart services
sudo systemctl restart eve-public-frontend
sudo systemctl restart eve-unified-frontend
```

See [OPERATIONS.md](OPERATIONS.md) for full operational documentation.

### Access Points
- **Public Dashboard:** http://localhost:5173
- **ectmap (Universe Map):** http://localhost:3001
- **Internal Tools (Unified Frontend):** http://localhost:3003
- **API Docs:** http://localhost:8000/docs

---

## 📊 Data Sources

- **zKillboard RedisQ** - Real-time combat stream for live battle tracking
- **zKillboard API** - Historical combat data (daily killmail downloads)
- **ESI API** - EVE Online official API
- **EVE SDE** - Static Data Export (PostgreSQL)
- **Telegram Bot API** - Real-time battle alerts and scheduled reports

---

## 📚 Documentation

| Topic | Location |
|-------|----------|
| **Development Guide** | [CLAUDE.md](CLAUDE.md) |
| **Architecture** | [ARCHITECTURE.md](ARCHITECTURE.md) |
| **Agent Runtime** | [docs/agent/](docs/agent/) |
| **Backend Development** | [CLAUDE.backend.md](CLAUDE.backend.md) |
| **Frontend Development** | [CLAUDE.frontend.md](CLAUDE.frontend.md) |
| **Doctrine Detection Engine** | [docs/doctrine-detection-engine.md](docs/doctrine-detection-engine.md) |
| **War Economy Dashboard** | [docs/war-economy-dashboard.md](docs/war-economy-dashboard.md) |
| **Cron Setup** | [docs/cron-setup.md](docs/cron-setup.md) |
| **Operations Guide** | [OPERATIONS.md](OPERATIONS.md) |

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
