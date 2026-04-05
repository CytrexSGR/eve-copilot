# EVE Co-Pilot - Production Deployment

> **Back to:** [ARCHITECTURE.md](ARCHITECTURE.md) | **See also:** [Microservices](ARCHITECTURE.microservices.md) | [Data Layer](ARCHITECTURE.data.md)

---

## Production Environment

| Service | Value |
|---------|-------|
| **Domain** | `eve.infinimind-creations.com` |
| **Server IP** | `your-server-ip` |
| **Cloudflare** | ✅ Active (Proxied) |
| **SSL** | Cloudflare Full (Strict) |
| **VM** | Proxmox VM 100 |

---

## External Dependencies

### EVE Online APIs

| API | Purpose | Rate Limit |
|-----|---------|------------|
| ESI (esi.evetech.net) | Official game API | ~400/min |
| EVE Ref (data.everef.net) | Killmail bulk data | No limit |
| EVE Image Server | Item/ship/alliance/corp icons | No limit |
| zKillboard RedisQ | Real-time killmail stream | Pull-based |
| zKillboard API | Alliance/corporation stats | ~20/10sec |
| DOTLAN EveMaps | Activity, sovereignty, ADM, rankings | Respectful scraping |
| Janice API | Item appraisal for buyback pricing | No limit |
| Pathfinder (GitHub) | Wormhole static connections | Static CSVs |
| anoik.is | Wormhole system effects | Static data |

### Infrastructure (22 Containers)

| Service | Container | Host Port | Status |
|---------|-----------|-----------|--------|
| PostgreSQL | eve_db | internal only | 🐳 Docker |
| Redis | eve-redis | internal only | 🐳 Docker |
| API Gateway | eve-api-gateway | 8000 | 🐳 Docker |
| War-Intel Service | eve-war-intel-service | 8002 | 🐳 Docker |
| Scheduler | eve-scheduler-service | 8003 | 🐳 Docker |
| Market Service | eve-market-service | 8004 | 🐳 Docker |
| Production Service | eve-production-service | 8005 | 🐳 Docker |
| Shopping Service | eve-shopping-service | 8006 | 🐳 Docker |
| Character Service | eve-character-service | 8007 | 🐳 Docker |
| MCP Service | eve-mcp-service | 8008 | 🐳 Docker (optional) |
| Copilot Server | (host) | 8009 | Manual (optional) |
| Auth Service | eve-auth-service | 8010 | 🐳 Docker |
| ectmap Service | eve-ectmap-service | 8011 | 🐳 Docker |
| Wormhole Service | eve-wormhole-service | 8012 | 🐳 Docker |
| zkillboard Service | eve-zkillboard-service | 8013 | 🐳 Docker |
| DOTLAN Service | eve-dotlan-service | 8014 | 🐳 Docker |
| HR Service | eve-hr-service | 8015 | 🐳 Docker |
| Finance Service | eve-finance-service | 8016 | 🐳 Docker |
| ectmap Frontend | eve-ectmap | 3001 | 🐳 Docker |
| Public Frontend | eve-public-frontend | 5173 | 🐳 Docker (nginx) |
| Unified Frontend | (systemd) | 3003 | systemd |
| Grafana | eve-grafana | 3200 | 🐳 Docker |
| Prometheus | eve-prometheus | 9090 | 🐳 Docker |

---

## Security Considerations

### Production Security

| Layer | Protection |
|-------|------------|
| **Cloudflare** | WAF, Bot Fight Mode, Rate Limit (100 req/10s for `/api/`) |
| **Nginx** | Blocks non-Cloudflare IPs, LAN allowed (`cloudflare-allow.conf`) |
| **Waiting Room** | Max 50 conn (server), 30 conn (per IP) → 429 on overload |
| **SSL** | Cloudflare Full (Strict) |

### Token Storage

- OAuth2 tokens stored in `data/tokens.json` (bind-mounted into auth-service Docker container)
- Tokens encrypted with Fernet (symmetric encryption)
- Daily re-keying via scheduler job (03:00 UTC)
- Manual re-key: `POST /api/auth/rekey-tokens`
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

**Hybrid Cache Architecture:**
| Data Type | L1 Redis | L2 PostgreSQL | L3 ESI | Background Refresh |
|-----------|----------|---------------|--------|-------------------|
| Market Prices (Hot) | 5 min | 1 hour | Fallback | */4 min (proactive) |
| Market Prices (Other) | 5 min | 1 hour | Fallback | On-demand |
| Killmails | 24 hour | Permanent | Fallback | Real-time (RedisQ) |
| Character Data | 5-60 min | Sync | Fallback | */30 min (auto-sync) |
| ESI Responses | ETag cache | - | 304 Not Modified | On-demand |

**Hot Items (56 items proactively cached):**
- Minerals (8): Tritanium, Pyerite, Mexallon, Isogen, Nocxium, Zydrine, Megacyte, Morphite
- Isotopes (4): Oxygen, Nitrogen, Hydrogen, Helium
- Fuel Blocks (4): All racial fuel blocks
- Moon Materials (20): Common R4-R64 materials
- Production Materials (20): Common T2/T3 components

**ESI Scaling (100+ Characters):**
- SharedRateState: Redis-based global error budget across all services
- ETag Cache: 304 Not Modified support reduces bandwidth
- Staggered Sync: 25-minute window with jitter
- Delta-Sync: Skip recently updated data

**Frontend:**
- React Query caching (5 min staleTime, 10 min gcTime)
- Optimistic updates for mutations
- No refetch on window focus (reduces load)
- Code splitting via lazy loading for all pages

### Rate Limiting

- ESI client implements exponential backoff
- Bulk operations batched to avoid rate limits
- Price fetcher uses parallel requests with throttling
- SharedRateState coordinates rate limits across microservices

### Database Queries

- Complex queries use indexed columns
- SDE tables pre-indexed (EVE provides)
- App tables indexed on type_id, region_id
- Materialized views for coalition detection

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
- ✅ **2D Galaxy Map** - ectmap with live battle overlays + IHUB markers + battle filters
- ✅ **Production Timing Warnings** - War economy alerts
- ✅ **Docker Containerization** - 18 microservices in Docker Compose
- ✅ **Wormhole Intelligence** - Dedicated service with Thera router, residents, threats
- ✅ **Coalition Detection** - 3-truth behavioral analysis
- ✅ **Doctrine Detection** - DBSCAN clustering + template matching
- ✅ **Alliance Intelligence** - 9-tab analysis dashboard with DOTLAN geography
- ✅ **Corporation Intelligence** - 8-tab analysis dashboard
- ✅ **PowerBloc Intelligence** - 10-tab coalition analytics with Redis caching
- ✅ **ESI Scaling** - SharedRateState, ETag cache, staggered sync
- ✅ **DOTLAN Integration** - Activity scraping, sovereignty, ADM, rankings
- ✅ **HR & Vetting** - Red list, 5-stage risk scoring, applications
- ✅ **Finance** - Wallets, mining tax, invoicing, SRP, doctrine, buyback
- ✅ **Sovereignty** - Skyhook telemetry, Metenox drills, sov simulator
- ✅ **Military Ops** - D-Scan parser, fleet PAP, Discord relay, timerboard
- ✅ **Battle Intelligence** - Attacker loadouts, victim tank, sov context, BFS sides
- ✅ **Dogma Engine** - Killmail fitting analysis, EHP calculation
- ✅ **Unit Tests** - 821 tests across 5 services (<1.1s runtime)
- ✅ **Monitoring** - Grafana + Prometheus dashboards

### Planned Improvements

1. **Mobile-Responsive Dashboard** - Better mobile experience
2. **Push Notifications** - Browser push for critical alerts
3. **Management Suite Frontend** - Separate React app for HR/Finance/Industry tools

### Technical Debt

**Resolved (February 2026):**
- ✅ 14 MCP tool endpoints implemented (alliance, strategic, economy, operations)
- ✅ Hourly stats: solo_kills/ratio + avg/max_kill_value columns
- ✅ DPS skill integration via httpx to character-service
- ✅ Data consistency overhaul: 53 bugs fixed across all War Intelligence tabs
- ✅ ISK deduplication via DISTINCT killmail queries
- ✅ War-intel-service refactoring: 3,839-line file → 13 modules, Redis cache, 4 workers

**Resolved (January 2026):**
- ✅ Consolidated ESI clients → shared `eve_shared/esi/` (circuit breaker, distributed lock, ETag cache)
- ✅ Unified caching → L1 Redis → L2 PostgreSQL → L3 ESI
- ✅ Character auto-sync via service APIs (not direct DB)
- ✅ ESI scaling to 100+ characters
- ✅ 821 unit tests, 0 failures

**Remaining:**
- Legacy monolith `main.py` endpoints could be migrated to microservices
- Frontend TypeScript type coverage could be expanded
- Activity tab for Alliance detail page (daily patterns, timezone analysis)

---

