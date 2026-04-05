# EVE Co-Pilot - Combat Intelligence Dashboard

**Real-time combat intelligence, battle tracking, and strategic analytics for EVE Online.**

Live battle visualization, alliance/corporation intelligence, and strategic insights powered by zkillboard live stream.

---

## Quick Start

### Development (Fast Iteration - Recommended)

```bash
cd /home/cytrex/eve_copilot/public-frontend

# Start Vite dev server with Hot Module Replacement (HMR)
./dev.sh

# Access: http://localhost:5175
# Changes auto-reload in ~200ms ⚡
```

### Production (Docker)

```bash
cd /home/cytrex/eve_copilot/docker

# Build and deploy
docker compose build public-frontend
docker compose up -d public-frontend

# Access: http://localhost:5173
```

**Speed Comparison:**
- Dev Mode (HMR): **<1 second** per change ⚡
- Docker Build: **~20 seconds** per change

---

## Tech Stack

| Technology | Version | Purpose |
|------------|---------|---------|
| React | 19 | UI Framework |
| TypeScript | 5.9 | Type safety |
| Vite | 7 | Build tool, dev server with HMR |
| React Router | 7 | Client-side routing |
| TanStack Query | v5 | Server state management |
| Axios | 1.13 | HTTP client |

---

## What's Inside

### 📊 19 Intelligence Pages

| Category | Pages | Features |
|----------|-------|----------|
| **Battle Intelligence** | Home, Battle Report, Battle Map, Battle Detail | Live battles, 24h reports, ectmap integration, attacker loadouts, victim tank analysis |
| **Alliance Intelligence** | Alliance Detail | 9 tabs: Overview, Offensive, Defensive, Capitals, Corps, Pilots, Wormhole, Geography, Hunting |
| **Corporation Intelligence** | Corporation Detail | 8 tabs: Overview, Offensive, Defensive, Capitals, Pilots, Hunting, Geography, Wormhole |
| **Strategic Intelligence** | Power Bloc Detail, Conflict Detail | 10+ coalition tabs, alliance wars |
| **Operational Intelligence** | System Detail, Route Detail, Trade Routes | Danger scores, route safety |
| **Economic Intelligence** | War Economy, Supply Chain | Market opportunities, logistics |
| **Specialized Intelligence** | Wormhole Intel, Doctrines | W-space (4 tabs: Thera Router, Hunters, Market, Residents) |

**Total Intelligence Tabs:** 9 (Alliance) + 8 (Corp) + 10 (PowerBloc) = **27 specialized intelligence views**

### 🎯 Key Features

- **Real-time battle tracking** (5s updates, BFS side detection)
- **Battle intelligence** (Attacker loadouts, victim tank analysis, sov context, significance scoring)
- **Alliance/Corporation deep intelligence** (27 intelligence tabs)
- **Capital fleet tracking** (Carriers, Dreads, FAX, Supers, Titans)
- **Power bloc analytics** (10 tabs, Redis-cached, 60s TTL)
- **DOTLAN geography** (Live activity, sov campaigns, ADM, territorial changes)
- **Wormhole intel** (Thera router with route visualization, hunters, market, residents)
- **System danger assessment** (0-100 threat scores)
- **Route safety analysis** (Jump route danger mapping)
- **ectmap integration** (Full EVE universe map, IHUB markers, battle status filters)
- **Optimized icons** (64/128/256px, 99% smaller)

---

## Project Structure

```
public-frontend/
├── src/
│   ├── App.tsx                      # Root component, 19 routes
│   ├── main.tsx                     # Entry point
│   ├── index.css                    # Global dark mode styles
│   │
│   ├── pages/                       # 19 pages (all lazy-loaded)
│   │   ├── Home.tsx                        # Battle map dashboard
│   │   ├── BattleReport.tsx                # 24h report + ectmap
│   │   ├── BattleMap2D.tsx                 # 2D battle map
│   │   ├── BattleDetail.tsx                # Battle analysis (9 panels)
│   │   ├── AllianceDetail.tsx              # Alliance intel (9 tabs)
│   │   ├── CorporationDetail.tsx           # Corp intel (6 tabs)
│   │   ├── PowerBlocDetail.tsx             # Coalition analytics
│   │   ├── SystemDetail.tsx                # System danger scores
│   │   ├── ConflictDetail.tsx              # Alliance wars
│   │   ├── RouteDetail.tsx                 # Route safety
│   │   ├── WormholeIntel.tsx               # W-space intel
│   │   ├── Doctrines.tsx                   # Fleet doctrines
│   │   ├── WarEconomy.tsx                  # Market opportunities
│   │   ├── SupplyChain.tsx                 # Logistics analysis
│   │   ├── Ectmap.tsx                      # Standalone map
│   │   ├── Impressum.tsx                   # Legal notice
│   │   ├── Datenschutz.tsx                 # Privacy policy
│   │   └── NotFound.tsx                    # 404 page
│   │
│   ├── components/                  # 80+ reusable components
│   │   ├── alliance/                       # 9 alliance tab views
│   │   │   ├── OverviewView.tsx                  # Overview tab
│   │   │   ├── OffensiveView.tsx                 # Offensive operations
│   │   │   ├── DefensiveView.tsx                 # Defensive analysis
│   │   │   ├── CapitalsView.tsx                  # Capital intel (9 panels)
│   │   │   ├── CorpsView.tsx                     # Corp rankings (6 panels)
│   │   │   ├── CapsuleersView.tsx                # Pilot intel (6 panels)
│   │   │   ├── WormholeView.tsx                  # W-space empire
│   │   │   ├── GeographyView.tsx                 # DOTLAN geography + zKillboard
│   │   │   └── HuntingView.tsx                   # Hunting patterns
│   │   │
│   │   ├── corporation/                    # 8 corp tab views
│   │   │   ├── OverviewView.tsx                  # Corp overview
│   │   │   ├── OffensiveView.tsx                 # Corp offensive (11 panels)
│   │   │   ├── DefensiveView.tsx                 # Corp defensive (11 panels)
│   │   │   ├── CapitalsView.tsx                  # Corp capitals (6 panels)
│   │   │   ├── PilotsView.tsx                    # Corp pilots (6 panels)
│   │   │   ├── HuntingView.tsx                   # Corp hunting
│   │   │   ├── GeographyView.tsx                 # DOTLAN geography
│   │   │   ├── CorporationWormholeView.tsx       # Corp W-space
│   │   │   └── geography/                        # Shared geography panels
│   │   │       ├── LiveActivityPanel.tsx          # System activity + heat badges
│   │   │       ├── SovDefensePanel.tsx            # Sov campaigns + ADM
│   │   │       ├── TerritorialChangesPanel.tsx    # Sov ownership changes
│   │   │       └── AlliancePowerPanel.tsx         # Alliance rankings + deltas
│   │   │
│   │   ├── powerbloc/                      # 10 power bloc tab views
│   │   │   ├── PBOffensiveView.tsx               # Coalition offensive + victim tank
│   │   │   ├── PBDefensiveView.tsx               # Coalition defensive
│   │   │   ├── PBCapitalsView.tsx                # Coalition capitals
│   │   │   ├── PBGeographyView.tsx               # Coalition DOTLAN geography
│   │   │   ├── PBAlliancesView.tsx               # Member alliance rankings
│   │   │   ├── PBCapsuleersView.tsx              # Coalition pilots
│   │   │   ├── PBDetailsView.tsx                 # Coalition details
│   │   │   ├── PBHuntingView.tsx                 # Coalition hunting
│   │   │   ├── PBWormholeView.tsx                # Coalition W-space
│   │   │   └── PBPilotsView.tsx                  # Coalition pilot intel
│   │   │
│   │   ├── battle/                         # 12 battle detail components
│   │   │   ├── BattleHeader.tsx                  # + SOV holder badge
│   │   │   ├── BattleSidesPanel.tsx              # BFS 2-coloring + fleet profile
│   │   │   ├── BattleKillFeed.tsx
│   │   │   ├── BattleShipClasses.tsx
│   │   │   ├── BattleDamageAnalysis.tsx
│   │   │   ├── BattleCommanderIntel.tsx
│   │   │   ├── BattleDoctrines.tsx
│   │   │   ├── BattleReshipments.tsx
│   │   │   ├── BattleTimeline.tsx
│   │   │   ├── BattleAttackerLoadouts.tsx        # Per-alliance weapon loadouts
│   │   │   ├── BattleContext.tsx                  # Battle significance scoring
│   │   │   ├── BattleSovContext.tsx               # Sov campaign alerts
│   │   │   └── BattleVictimTank.tsx              # Dogma engine tank profiles
│   │   │
│   │   ├── wormhole/                       # 7 wormhole components
│   │   │   ├── TheraRouterTab.tsx                # Thera route calculator + viz
│   │   │   ├── HuntersTab.tsx                    # Active hunters
│   │   │   ├── MarketTab.tsx                     # W-space market
│   │   │   ├── ResidentsTab.tsx                  # W-space residents
│   │   │   ├── WormholeHero.tsx                  # Hero section
│   │   │   ├── WormholeTabNav.tsx                # Tab navigation
│   │   │   └── WormholeTicker.tsx                # Activity ticker
│   │   │
│   │   ├── home/                           # Homepage sections
│   │   │   ├── PowerBlocsSection.tsx
│   │   │   ├── AllianceDynamicsSection.tsx
│   │   │   ├── ActiveConflictsSection.tsx
│   │   │   ├── PowerList.tsx
│   │   │   └── ConflictCard.tsx
│   │   │
│   │   └── Layout.tsx                      # Main layout + navigation
│   │
│   ├── services/                    # API clients
│   │   ├── api.ts                          # Base axios client
│   │   ├── allianceApi.ts                  # Alliance intelligence
│   │   ├── corporationApi.ts               # Corporation intelligence
│   │   └── api/                            # Domain-specific API modules
│   │       ├── battles.ts                  # Battle detail + loadouts + tank
│   │       ├── economy.ts                  # War economy endpoints
│   │       ├── powerbloc.ts                # Coalition/power bloc APIs
│   │       ├── reports.ts                  # Coalition reports
│   │       └── wormhole.ts                 # Wormhole + Thera APIs
│   │
│   ├── types/                       # TypeScript interfaces (13 files)
│   │   ├── alliance.ts, corporation.ts     # Entity data types
│   │   ├── battle.ts, hunting.ts           # Combat data types
│   │   ├── powerbloc.ts, reports.ts        # Coalition data types
│   │   ├── dotlan.ts, geography-dotlan.ts  # DOTLAN geography types
│   │   ├── economy.ts, intelligence.ts     # Market/intel types
│   │   ├── wormhole.ts, thera.ts           # W-space data types
│   │   └── warfare-intel.ts                # Warfare intelligence types
│   │
│   ├── utils/                       # Utility functions
│   │   └── format.ts                       # ISK formatting, etc.
│   │
│   └── lib/                         # Library configurations
│       └── queryClient.ts                  # React Query setup
│
├── public/                          # Static assets
│   └── icons/                              # Optimized icons
│       ├── 64/                                   # Small (5-7KB)
│       ├── 128/                                  # Medium (17-23KB)
│       └── 256/                                  # Large (49-82KB)
│
├── docker/
│   ├── Dockerfile                   # Multi-stage build
│   └── nginx.conf                   # Production nginx config
│
├── dev.sh                           # HMR dev server script
├── vite.config.ts                   # Vite configuration
├── tsconfig.json                    # TypeScript configuration
├── package.json                     # Dependencies
├── FEATURES.md                      # 📚 Complete feature documentation
├── DEVELOPMENT.md                   # Development workflow guide
└── README.md                        # This file
```

---

## Performance

### Bundle Size
- Initial bundle: **~250KB** (gzipped)
- Code splitting: All pages lazy-loaded
- React Query cache: 10-minute retention

### Auto-Refresh
| Page | Interval | Reason |
|------|----------|--------|
| Home | 60s | Live battle feed |
| Battle Map (ectmap) | 5s | Real-time battles |
| Battle Detail | Manual | Historical data |
| Alliance/Corp Detail | Manual | Deep analytics |

### API Optimizations
- Power Blocs: **60s TTL cache** (1.7s → 86ms, 20x faster)
- React Query: 1-minute stale time, 5-minute garbage collection
- Parallel queries: TanStack Query automatic batching

### Image Optimization
Icons optimized from 1.6-3.2 MB to 5-82 KB (**99% smaller**)

---

## Design System

### Dark Mode (Mandatory)
EVE Online is a space game. All UI uses dark mode.

### Color Palette

```css
--bg-primary: #0d1117;       /* Deep space */
--bg-elevated: #161b22;      /* Cards, panels */
--bg-surface: #21262d;       /* Hover states */
--border-color: #30363d;     /* Borders */
--text-primary: #e6edf3;     /* High contrast */
--text-secondary: #8b949e;   /* Muted text */
--accent-blue: #58a6ff;      /* Links, actions */
--success: #3fb950;          /* Profit, wins */
--danger: #f85149;           /* Losses, errors */
```

### Compact Dashboard Style

Recent design pattern used across all intelligence pages:

```tsx
// Panel with colored accent
<div style={{
  background: 'rgba(0,0,0,0.3)',
  borderRadius: '8px',
  borderLeft: '2px solid #58a6ff',
  padding: '0.5rem',
}}>
  {/* Dot header */}
  <div style={{ fontSize: '0.7rem', fontWeight: 600 }}>
    • UPPERCASE LABEL
  </div>

  {/* Content with scrollbar */}
  <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
    {/* Compact single-line cards */}
  </div>
</div>
```

---

## API Integration

### Environment Configuration

```typescript
const API_BASE_URL = import.meta.env.PROD
  ? 'https://eve.infinimind-creations.com/api'
  : '/api';  // Proxied via Vite in dev mode
```

### Main API Endpoints

**War/Battle APIs** (`/api/war/*`):
- `/battles/active` - Live battles
- `/battle/{id}/*` - Battle details, kills, sides, ship classes
- `/battle/{id}/attacker-loadouts` - Per-alliance weapon loadouts + fleet sizes
- `/battle/{id}/strategic-context` - Sovereignty + ADM context
- `/battle/{id}/victim-tank-analysis` - Dogma engine tank profiles
- `/ticker` - Recent kills
- `/system/{id}/*` - System danger, losses, ship classes

**Intelligence APIs** (`/api/intelligence/fast/*`):
- `/{alliance_id}/complete` - Alliance overview
- `/{alliance_id}/offensive-stats` - Offensive operations (+ fleet profile)
- `/{alliance_id}/defensive-stats` - Defensive analysis
- `/{alliance_id}/capital-intel` - Capital fleet intelligence
- `/{alliance_id}/corps-*` - Corporation rankings (4 endpoints)
- `/{alliance_id}/capsuleers` - Pilot intelligence
- `/corporation/{corp_id}/*` - Corporation intelligence (8 endpoints)

**PowerBloc APIs** (`/api/powerbloc/*`):
- `/{leader_id}/offensive` - Coalition offensive (Redis cached, 5min TTL)
- `/{leader_id}/defensive` - Coalition defensive
- `/{leader_id}/capitals` - Coalition capital intel
- `/{leader_id}/geography` - Coalition DOTLAN geography
- `/{leader_id}/capsuleers` - Coalition pilot intel
- `/{leader_id}/details` - Coalition detail intel
- `/{leader_id}/hunting` - Coalition hunting
- `/{leader_id}/victim-tank-profile` - Victim tank analysis

**Reports APIs** (`/api/reports/*`):
- `/power-blocs/live` - Coalition rankings (60s cache)

**DOTLAN APIs** (`/api/dotlan/*`):
- `/activity/systems/top` - Top active systems
- `/sovereignty/campaigns/map` - Active sov campaigns
- `/sovereignty/changes/recent` - Territory changes
- `/alliance/rankings` - Alliance power rankings

---

## Development

### Adding a New Page

1. **Create page component:**
```typescript
// src/pages/NewPage.tsx
export function NewPage() {
  return <div>New intelligence page</div>;
}
```

2. **Add lazy route in App.tsx:**
```typescript
const NewPage = lazy(() => import('./pages/NewPage').then(m => ({ default: m.NewPage })));

// In Routes:
<Route path="/new-page" element={<NewPage />} />
```

3. **Add navigation in Layout.tsx:**
```typescript
<Link to="/new-page">New Page</Link>
```

### Adding an API Endpoint

1. **Add to service file:**
```typescript
// src/services/allianceApi.ts
export const allianceApi = {
  getNewData: async (id: number) => {
    const { data } = await api.get(`/intelligence/fast/${id}/new-data`);
    return data;
  }
};
```

2. **Use in component with React Query:**
```typescript
import { useQuery } from '@tanstack/react-query';
import { allianceApi } from '../services/allianceApi';

const { data, isLoading } = useQuery({
  queryKey: ['allianceNewData', allianceId],
  queryFn: () => allianceApi.getNewData(allianceId)
});
```

---

## Troubleshooting

### Frontend won't start
```bash
# Check port 5175 (dev) or 5173 (prod)
lsof -i :5175
lsof -i :5173

# Reinstall dependencies
cd public-frontend
npm install

# Start dev server
./dev.sh
```

### API calls fail
1. Check backend is running: `curl http://localhost:8000/health`
2. Check Vite proxy in `vite.config.ts`
3. Check browser DevTools Network tab
4. Verify nginx proxy config (production)

### Docker build fails
```bash
# Clear Docker cache
cd docker
docker compose build --no-cache public-frontend
docker compose up -d public-frontend
```

### ectmap iframe not loading
1. Check ectmap service: `docker ps | grep ectmap`
2. Verify port 3001 accessible
3. Check iframe src URL matches hostname
4. Check browser console for CORS errors

---

## Documentation

| Document | Description |
|----------|-------------|
| **[FEATURES.md](FEATURES.md)** | 📚 **Complete feature documentation** - all 19 pages, components, APIs |
| [DEVELOPMENT.md](DEVELOPMENT.md) | Development workflow, HMR setup, best practices |
| [../CLAUDE.md](../CLAUDE.md) | Main project guide |
| [../CLAUDE.frontend.md](../CLAUDE.frontend.md) | General frontend patterns |
| [../ARCHITECTURE.md](../ARCHITECTURE.md) | System architecture overview |

---

## Dependencies

```json
{
  "dependencies": {
    "@tanstack/react-query": "^5.90.16",
    "axios": "^1.13.2",
    "react": "^19.2.0",
    "react-dom": "^19.2.0",
    "react-router-dom": "^7.11.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^5.1.1",
    "typescript": "~5.9.3",
    "vite": "^7.2.4"
  }
}
```

---

## Production Deployment

**Live Site:** https://eve.infinimind-creations.com

**Architecture:**
```
Cloudflare CDN
    ↓
nginx (Proxmox VM 100, IP: your-server-ip)
    ↓ /api/* → api-gateway:8000
    ↓ / → public-frontend:5173 (Docker nginx)
```

**Security:**
- Cloudflare WAF + Bot Fight Mode
- Rate limiting: 100 req/10s for `/api/*`
- SSL: Full (Strict)
- nginx blocks non-Cloudflare IPs

---

## Related Services

| Service | Port | Purpose |
|---------|------|---------|
| public-frontend (Dev HMR) | 5175 | Development with hot reload |
| public-frontend (Prod) | 5173 | Production Docker container |
| api-gateway | 8000 | Backend API router → 18 microservices |
| war-intel-service | 8002 | Battle, alliance, sovereignty, military intel |
| dotlan-service | 8014 | DOTLAN geography scraping |
| ectmap | 3001 | EVE universe map (IHUB markers, battle filters) |
| PostgreSQL | internal | Data storage (Docker network only) |
| Redis | internal | Cache & rate limiting (Docker network only) |

---

**Last Updated:** 2026-02-07
**Version:** 3.0 (Battle Intelligence + DOTLAN Geography + PowerBloc Expansion)
