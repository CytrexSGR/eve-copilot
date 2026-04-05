# EVE Co-Pilot - Complete Documentation (2026-02-26)

This is the complete, up-to-date documentation collection for the EVE Co-Pilot project.

## Quick Navigation

| Document | Purpose | Size |
|----------|---------|------|
| **[01_README.md](01_README.md)** | Project overview, features, tech stack, quick start | 12 KB |
| **[02_QUICKSTART.md](02_QUICKSTART.md)** | Development setup, credentials, commands, links | 6 KB |
| **[03_ARCHITECTURE.md](03_ARCHITECTURE.md)** | System architecture, microservices, database schema, data flows | 58 KB |
| **[04_BACKEND_GUIDE.md](04_BACKEND_GUIDE.md)** | Backend development, APIs, database patterns, cron jobs | 12 KB |
| **[05_FRONTEND_GUIDE.md](05_FRONTEND_GUIDE.md)** | Frontend development, components, pages, patterns | 31 KB |

**Total:** ~119 KB of documentation

---

## Project Summary

**EVE Co-Pilot** is a comprehensive intelligence and industry platform for EVE Online with:

- 17 **microservices** (FastAPI, Docker Compose orchestrated)
- 111+ **database migrations**, 136+ tables
- 3,029+ **unit tests** across 15 services (<5s runtime)
- **Dogma Engine v4** — full EVE modifier pipeline with T3D modes, spool-up, fleet boosts, projected effects
- **Real-time combat tracking** from zKillboard (5s refresh)
- **Production & manufacturing** with material chains, projects, PI empire
- **Market intelligence** with arbitrage, profit engine, shopping
- **Universe map** with live battle overlays, intel heatmaps (ectmap)
- **War economy analysis** with fuel tracking, manipulation detection
- **609 dynamic MCP tools** for AI agent integration
- **SaaS platform** with tier gating, ISK payments, rate limiting

**Status:** Alpha (actively developed, Dec 2025 - Feb 2026)
**Live:** https://eve.infinimind-creations.com

---

## Key Technologies

| Layer | Technology |
|-------|-----------|
| **Backend** | FastAPI 0.104+, Python 3.11+ |
| **Database** | PostgreSQL 16 (EVE SDE + 111+ app migrations) |
| **Cache** | Redis 7 (L1 cache, rate limiting, sessions) |
| **Frontend (Public)** | React 19, TypeScript 5, Vite 7 |
| **Map Service** | Next.js 16, Canvas-based universe map |
| **Monitoring** | Prometheus, Grafana, Loki, Alertmanager |
| **Deployment** | Docker Compose, Nginx, Cloudflare |

---

## Project Structure

```
/home/cytrex/eve_copilot/
├── services/                    # 17 Microservices (Docker)
│   ├── api-gateway/            # Port 8000 — Request routing, CORS, health
│   ├── auth-service/           # Port 8010 — EVE SSO OAuth, token mgmt
│   ├── war-intel-service/      # Port 8002 — Killmails, battles, intelligence
│   ├── scheduler-service/      # Port 8003 — Cron jobs, APScheduler
│   ├── market-service/         # Port 8004 — Prices, orders, arbitrage
│   ├── production-service/     # Port 8005 — Blueprints, manufacturing, PI
│   ├── shopping-service/       # Port 8006 — Shopping lists, transport
│   ├── character-service/      # Port 8007 — Characters, skills, Dogma engine
│   ├── mcp-service/            # Port 8008 — 609 dynamic MCP tools
│   ├── ectmap-service/         # Port 8011 — Map data service
│   ├── wormhole-service/       # Port 8012 — J-Space intelligence
│   ├── zkillboard/             # Port 8013 — Live kill stream
│   ├── dotlan-service/         # Port 8014 — DOTLAN scraping
│   ├── hr-service/             # Port 8015 — HR, vetting, applications
│   ├── finance-service/        # Port 8016 — SRP, doctrines, buyback
│   ├── military-service/       # Port 8017 — D-Scan, fleet PAPs
│   └── public-frontend/        # Port 5173 — Public dashboard (nginx)
│
├── eve_shared/                  # Shared library (DB, Redis, constants, middleware)
├── public-frontend/             # React 19 + TypeScript 5 + Vite 7
├── ectmap/                      # Next.js universe map (Port 3001)
├── copilot_server/              # AI Agent runtime (Port 8009)
├── docker/                      # Docker Compose orchestration
├── migrations/                  # Database migrations (001-111+)
├── docs/                        # Documentation
│   ├── COMPLETE/               # THIS COLLECTION
│   ├── plans/                  # Implementation plans
│   └── sessions/               # Session records
└── data/                        # Runtime data (tokens.json)
```

---

## Getting Started

### 1. Read First
- Start with **[02_QUICKSTART.md](02_QUICKSTART.md)** for setup
- Review **[01_README.md](01_README.md)** for feature overview

### 2. System Architecture
- **[03_ARCHITECTURE.md](03_ARCHITECTURE.md)** covers the complete system design
- Understand microservices layout, database schema, data flows

### 3. Development
- **[04_BACKEND_GUIDE.md](04_BACKEND_GUIDE.md)** for backend development
- **[05_FRONTEND_GUIDE.md](05_FRONTEND_GUIDE.md)** for frontend development

### 4. Live Resources
- **API Docs:** http://localhost:8000/docs
- **Production:** https://eve.infinimind-creations.com
- **GitHub:** https://github.com/CytrexSGR/Eve-Online-Copilot

---

## Key Services & Ports

| Port | Service | Purpose |
|------|---------|---------|
| 5173 | public-frontend | Public combat intel dashboard |
| 3001 | ectmap | Universe map with live overlays |
| 8000 | api-gateway | Main API entry point |
| 8002 | war-intel-service | Combat intelligence, battles, reports |
| 8003 | scheduler-service | Cron jobs, background tasks |
| 8004 | market-service | Market prices, orders, arbitrage |
| 8005 | production-service | Blueprints, manufacturing, PI |
| 8006 | shopping-service | Shopping lists, transport |
| 8007 | character-service | Characters, skills, Dogma engine |
| 8008 | mcp-service | 609 dynamic MCP tools |
| 8010 | auth-service | EVE SSO OAuth |
| 8011 | ectmap-service | Map data service |
| 8012 | wormhole-service | J-Space intelligence |
| 8013 | zkillboard | Live kill stream |
| 8014 | dotlan-service | DOTLAN scraping |
| 8015 | hr-service | HR, vetting, applications |
| 8016 | finance-service | SRP, doctrines, buyback |
| 8017 | military-service | D-Scan, fleet PAPs |

---

## Key Features

### Combat Intelligence
- Real-time battle tracking (zKillboard RedisQ)
- Battle detail pages with kill timeline, attacker loadouts, victim tank analysis
- War profiteering analysis
- Doctrine detection (DBSCAN clustering)
- Alliance/powerbloc intelligence with dual efficiency (ISK + K/D)
- LiveMap intelligence overlays (hunting heatmap, capital threats, logi strength)

### Fitting System & Dogma Engine v4
- Full EVE modifier pipeline with stacking penalty
- Module states (offline/online/active/overheated)
- T3D mode switching, Triglavian spool-up, fighter DPS
- Fleet boosts, projected effects (webs, paints, neuts)
- Applied DPS, warp time, scanability, fit comparison
- EFT import/export, custom fittings, market tree browser

### Production & Trading
- Production planner with ME/TE bonuses
- Production projects (multi-item, buy/make decisions, shopping lists)
- Material chain analysis (recursive)
- Arbitrage finder with fee engine and route optimization
- PI chain browser (DAG visualization), PI empire overview
- Moon mining operations (extraction calendar, ore analytics)

### War Economy
- Fuel market tracking (capital movement prediction)
- Market manipulation detection (Z-score)
- Doctrine engine (stats, readiness, compliance, BOM)
- CEO command center + operational cockpit

### Alliance Management Suite
- HR & vetting (5-stage risk scoring, application portal)
- Finance (wallet sync, mining tax, invoices, buyback)
- SRP & doctrines (EFT/DNA import, killmail matching, pricing)
- Sovereignty & Equinox (workforce graph, skyhook telemetry, Metenox)
- ESI notification pipeline with timer auto-processing

### SaaS Platform
- Tier system (public < free < pilot < corporation < alliance < coalition)
- Feature gating middleware (350+ endpoints)
- ISK payment with wallet journal polling
- Tier-aware rate limiting (30-2,000 req/min)

### Character Management
- EVE SSO OAuth2 with multi-character support
- Wallet, assets, skills, industry jobs, implants
- Character auto-sync (every 15 min)
- Ship mastery calculation

---

## Recent Changes (February 2026)

| Date | Change |
|------|--------|
| 2026-02-22 | Ectmap iframe URL fix, overlay cleanup, ADM tooltip |
| 2026-02-21 | LiveMap Intelligence Overlays (hunting, capitals, logi) |
| 2026-02-21 | Pilots Tab — Active Pilots Timeline + Fleet Overview |
| 2026-02-20 | Entity Live Map (Corp/Alliance/PowerBloc) |
| 2026-02-20 | PI Empire Overview (multi-character production analysis) |
| 2026-02-18 | Doctrine Engine (stats, readiness, compliance, BOM) |
| 2026-02-18 | Dogma Engine refactoring (17 tasks, pipeline stages, 865 tests) |
| 2026-02-18 | PI Chain Browser DAG redesign |
| 2026-02-16 | Dogma Engine v4 (T3D, spool-up, fighters, fleet boosts, projected) |
| 2026-02-16 | Fitting Engine v3 (module states, overheating, boosters, comparison) |
| 2026-02-15 | Dogma Engine v2 (align, lock time, applied DPS, warp time, EHP/s) |
| 2026-02-14 | Production Projects (multi-item, buy/make, shopping lists) |
| 2026-02-14 | CEO Command Center + Cockpit |
| 2026-02-14 | Moon Mining Operations |
| 2026-02-10 | Monolith decommission (~73,000 lines removed) |
| 2026-02-10 | Backend refactoring Phase 3 (tests for 7 services, shared constants) |
| 2026-02-09 | Backend refactoring Phase 1-2 (dedup, error handling, eve_shared) |
| 2026-02-09 | SaaS Phases 4-5 (rate limiting, Prometheus, landing page) |
| 2026-02-08 | SaaS feature gating (5 phases), frontend roadmap (10 phases) |
| 2026-02-06 | Fitting System (5 phases complete + browser tested) |
| 2026-02-06 | Battle intelligence features (8 enhancements) |
| 2026-02-05 | DOTLAN scraping service, ECTMap sov campaigns |
| 2026-02-04 | War-Intel-Service major refactoring (6 phases) |

---

## Important Credentials & Links

### Development
- **Sudo Password:** See CLAUDE.md
- **Database:** eve_sde / eve
- **GitHub Token:** /home/cytrex/Userdocs/.env
- **EVE SSO Client ID:** <EVE_CLIENT_ID>

### Production
- **Domain:** eve.infinimind-creations.com
- **Server IP:** your-server-ip
- **SSL:** Cloudflare Full (Strict)
- **Nameservers:** Cloudflare (kristina.ns.cloudflare.com, rocco.ns.cloudflare.com)

---

## Navigation Tips

1. **New to the project?** Start with **[02_QUICKSTART.md](02_QUICKSTART.md)**
2. **Want to understand the system?** Read **[03_ARCHITECTURE.md](03_ARCHITECTURE.md)**
3. **Building a feature?** Check **[04_BACKEND_GUIDE.md](04_BACKEND_GUIDE.md)** or **[05_FRONTEND_GUIDE.md](05_FRONTEND_GUIDE.md)**
4. **Need specific info?** Use the table of contents in each document

---

**Last Updated:** 2026-02-26 (Project Documentation v2.0)
**Maintained By:** Claude AI
**Repository:** https://github.com/CytrexSGR/Eve-Online-Copilot
