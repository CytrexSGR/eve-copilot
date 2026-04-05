# EVE Co-Pilot Frontend - Feature Documentation

**Last Updated:** 2026-02-21

Public-facing combat intelligence dashboard for EVE Online with real-time battle tracking, alliance analytics, and strategic intelligence.

---

## Quick Access

- **Dev Server (HMR):** http://localhost:5175 ⚡ (via `./dev.sh`)
- **Production:** http://localhost:5173 (Docker)
- **Live Site:** https://eve.infinimind-creations.com

---

## Pages & Features

### 🏠 Home Dashboard (`/`)

**Purpose:** Main combat intelligence dashboard with live battle feed

**Features:**
- **Live Battle Map:** Real-time battles with 5s auto-refresh
- **Battle Ticker:** Latest kills scrolling feed
- **Power Blocs:** Coalition rankings and activity
- **Alliance Dynamics:** Rising/Falling alliances by efficiency
- **Active Conflicts:** Ongoing alliance wars with kill counts
- **Power Rankings:** Top alliances by kills, ISK destroyed, efficiency
- **Featured Battles:** Highlighted major engagements

**Data Sources:**
- `/api/war/battles/active` - Live battles
- `/api/war/ticker` - Recent kills
- `/api/reports/power-blocs/live` - Coalition data (60s cache)

---

### ⚔️ Battle Report (`/battle-report`)

**Purpose:** 24-hour combat summary with ectmap integration

**Features:**
- **ectmap iframe:** Full EVE universe map with battle overlay
- **24h Statistics:** Total kills, ISK destroyed, active systems
- **Top Systems:** Highest activity heatmap
- **Battle Feed:** Recent battles with details
- **Click Navigation:** Battle markers link to detail pages

**Data Sources:**
- ectmap internal API (port 3001)
- `/api/war/battles/active`

---

### 🗺️ Battle Map (`/battle-map`)

**Purpose:** Interactive 2D battle visualization

**Features:**
- **Canvas-based map:** System positions and connections
- **Battle markers:** Color-coded by intensity
- **Auto-refresh:** 5-second updates
- **Click details:** Navigate to battle detail page

---

### 💥 Battle Detail (`/battle/:id`)

**Purpose:** Comprehensive analysis of individual battle

**Features:**
- **Battle Header:** System, start time, duration, status, SOV holder badge
- **Sov Campaign Alerts:** Active sovereignty campaigns in battle system (structure type, defender, score, ADM)
- **Battle Significance:** Compare kills/ISK/capitals to 24h war totals (major/notable/moderate/minor badges)
- **Battle Sides:** BFS 2-coloring algorithm, alliance performance comparison, fleet profile (avg/median/max)
- **Kill Timeline:** Chronological kill feed with ship icons
- **Ship Classes:** Composition breakdown by ship type
- **Damage Analysis:** Damage types distribution
- **Commander Intel:** Top killers and key fleet commanders
- **Battle Doctrines:** Ship doctrines and counter-doctrines
- **Attacker Loadouts:** Per-alliance weapon loadouts + range (Close/Medium/Long) + damage type + fleet size estimation
- **Reshipments:** Pilot reships and persistence analysis
- **Victim Tank Analysis:** Dogma engine EHP calculation, tank distribution (shield/armor/hull), resist weaknesses (EXPLOIT/SOFT/NORMAL)
- **Tactical Timeline:** Major tactical shifts and phases

**Render Order:**
BattleHeader → BattleSovContext → BattleContext → BattleSidesPanel → BattleCommanderIntel → BattleDoctrines → BattleAttackerLoadouts → BattleDamageAnalysis → BattleVictimTank → BattleShipClasses → BattleTimeline → BattleReshipments → BattleKillFeed

**Data Sources:**
- `/api/war/battle/{id}` - Battle summary
- `/api/war/battle/{id}/sides` - BFS 2-coloring side determination
- `/api/war/battle/{id}/kills` - Kill feed
- `/api/war/battle/{id}/ship-classes` - Ship composition
- `/api/war/battle/{id}/attacker-loadouts` - Weapon loadouts + fleet sizes
- `/api/war/battle/{id}/strategic-context` - Sovereignty + ADM context
- `/api/war/battle/{id}/victim-tank-analysis` - Dogma engine tank profiles

---

### 🏛️ Alliance Detail (`/alliance/:id`)

**Purpose:** Deep intelligence on alliance operations and performance

**9 Intelligence Tabs:**

1. **OVERVIEW** (`?tab=details`)
   - Summary stats, ship classes, regions, timeline
   - Key metrics: Kills, Deaths, Efficiency, ISK

2. **OFFENSIVE** (`?tab=offensive`)
   - Attack patterns, doctrine usage, kill heatmap
   - Top targets, ship losses inflicted, engagement sizes

3. **DEFENSIVE** (`?tab=defensive`)
   - Vulnerability analysis, death-prone pilots, loss heatmap
   - Threat profile, doctrine weaknesses, death timeline

4. **CAPITALS** (`?tab=capitals`)
   - Capital fleet intelligence (Carriers, Dreads, FAX, Supers, Titans)
   - Fleet composition, ship details, timeline, top killers/losers
   - Geographic hotspots, capital engagements, recent activity

5. **CORPS** (`?tab=corps`)
   - Corporation rankings and performance
   - Carry vs Dead Weight analysis
   - Ship specialization, geographic spread, pilot engagement

6. **PILOTS** (`?tab=capsuleer`)
   - Pilot intelligence and morale scores
   - Elite pilots, struggling pilots, activity trends
   - Combat styles, engagement profiles

7. **WORMHOLE** (`?tab=wormhole`)
   - Wormhole empire analysis
   - Territory control, sovereignty threats

8. **GEOGRAPHY** (`?tab=geography`)
   - DOTLAN panels: Live Activity (heat badges), Sov Defense (campaigns + ADM), Territorial Changes, Alliance Power
   - zKillboard panels: Regions, Top Systems, Home Systems

9. **HUNTING** (`?tab=hunting`)
   - Hunting patterns and threat assessment
   - Target selection, roaming behavior

**Time Periods:** 24H, 7D, 14D, 30D

**Data Sources:**
- `/api/intelligence/fast/{id}/complete` - Overview data
- `/api/intelligence/fast/{id}/offensive-stats` - Offensive tab
- `/api/intelligence/fast/{id}/defensive-stats` - Defensive tab
- `/api/intelligence/fast/{id}/capital-intel` - Capitals tab
- `/api/intelligence/fast/{id}/corps-*` - Corps tab (4 endpoints)

---

### 🏢 Corporation Detail (`/corporation/:id`)

**Purpose:** Corporation-level intelligence dashboard

**8 Intelligence Tabs:**

1. **OVERVIEW** (`?tab=details`)
   - Corporation info, stats, ship classes, regions

2. **OFFENSIVE** (`?tab=offensive`)
   - Attack patterns, victims, kill heatmap

3. **DEFENSIVE** (`?tab=defensive`)
   - Defense analysis, threats, loss patterns

4. **CAPITALS** (`?tab=capitals`)
   - Capital operations and losses

5. **PILOTS** (`?tab=pilots`)
   - Pilot roster and performance

6. **HUNTING** (`?tab=hunting`)
   - Hunting operations and targets

7. **GEOGRAPHY** (`?tab=geography`)
   - DOTLAN panels: Live Activity, Sov Defense, Territorial Changes, Alliance Power
   - zKillboard panels: Regions, Top Systems, Home Systems

8. **WORMHOLE** (`?tab=wormhole`)
   - Corporation wormhole operations

**Data Sources:**
- `/api/intelligence/fast/corporation/{id}/*` - Corp intelligence endpoints
- `/api/dotlan/*` - DOTLAN geography data

---

### 🌐 Power Bloc Detail (`/powerbloc/:leaderAllianceId`)

**Purpose:** Coalition-level strategic intelligence

**10 Intelligence Tabs:**

1. **OFFENSIVE** (`?tab=offensive`)
   - Coalition combat stats, kill heatmap, doctrine analysis
   - Victim Tank Profile panel (Dogma engine: tank distribution, resist weaknesses, overkill ratio)

2. **DEFENSIVE** (`?tab=defensive`)
   - Coalition loss patterns, vulnerability analysis

3. **CAPITALS** (`?tab=capitals`)
   - Coalition capital fleet intel (Carriers, Dreads, FAX, Supers, Titans)

4. **GEOGRAPHY** (`?tab=geography`)
   - DOTLAN panels: Live Activity, Sov Defense, Territorial Changes, Alliance Power
   - zKillboard panels: Regions, Top Systems

5. **ALLIANCES** (`?tab=alliances`)
   - Member alliance rankings, performance comparison, ISK efficiency

6. **CAPSULEERS** (`?tab=capsuleers`)
   - Coalition pilot intel, top pilots, activity trends

7. **DETAILS** (`?tab=details`)
   - Coalition detail intel, enemy analysis

8. **HUNTING** (`?tab=hunting`)
   - Coalition hunting patterns and targets

9. **WORMHOLE** (`?tab=wormhole`)
   - Coalition W-space operations

10. **PILOTS** (`?tab=pilots`)
    - Coalition pilot performance intel

**Performance:** All endpoints Redis-cached with 5-10min TTL (e.g., offensive: 4.8s cold → 13ms cached, 369x faster)

**Data Sources:**
- `/api/powerbloc/{leader_id}/*` - 10+ coalition endpoints (Redis cached)
- `/api/dotlan/*` - DOTLAN geography data

---

### 🌍 System Detail (`/system/:systemId`)

**Purpose:** Solar system intelligence and danger assessment

**Features:**
- **System Header:** Name, region, constellation, security, sovereignty
- **Danger Score:** 0-100 threat level with color coding
- **Active Battles:** Current engagements in system
- **Ship Classes:** Ship type breakdown for kills in system
- **Recent Losses:** Coalition-based kill feed
- **Time Periods:** 15m, 30m, 60m, 3h, 6h, 12h, 24h

**Data Sources:**
- `/api/war/system/{id}/danger` - Danger assessment
- `/api/war/system/{id}/ship-classes` - Ship breakdown
- `/api/war/system/{id}/losses` - Recent kills

---

### ⚡ Conflict Detail (`/conflicts/:conflictId`)

**Purpose:** Alliance vs Alliance war tracking

**Features:**
- **War Header:** Attacker vs Defender with logos
- **Combat Timeline:** Daily kill/death counts
- **Key Battles:** Major engagements in conflict
- **Efficiency Trends:** Performance over time

---

### 🚀 Route Detail (`/route/:origin/:destination`)

**Purpose:** Jump route safety analysis

**Features:**
- **Route Map:** Jump path visualization
- **System Danger:** Per-system threat levels
- **Recent Activity:** Kills along route
- **Safety Score:** Overall route risk assessment

---

### 🌀 Wormhole Intel (`/wormhole`)

**Purpose:** Wormhole space intelligence with 4 tabs

**Tabs:**

1. **Thera Router** - Route calculator via Thera wormhole connections
   - System autocomplete with 16 presets (trade hubs + nullsec staging)
   - Quick-select buttons (Jita, Amarr, Dodixie, Rens, 1DQ1-A, K-6K16, GE-8JV)
   - Route visualization: Origin → Entry WH → Thera → Exit WH → Destination
   - Ship size filter (Small, Medium, Large)
   - Direct vs Thera comparison with recommendation

2. **Hunters** - Active wormhole hunters and threats

3. **Market** - W-space market analysis and opportunities

4. **Residents** - W-space resident tracking and activity

---

### 📜 Doctrines (`/doctrines`)

**Purpose:** Fleet doctrine analysis and counter-doctrines

**Features:**
- **Popular Doctrines:** Most used fleet compositions
- **Doctrine Counters:** Effective counter-doctrines
- **Ship Fitting:** Common fits and modules

---

### 💰 War Economy (`/war-economy`)

**Purpose:** War-driven market opportunities

**Features:**
- **War Profiteering:** Items with price spikes from combat
- **Supply/Demand:** Market gaps in conflict zones
- **Trade Routes:** Profitable war supply routes

**Sections:**
- Market Opportunities
- Trade Route Safety Analysis

---

### 🏭 Supply Chain (`/supply-chain` or `/supply-chain/:allianceId`)

**Purpose:** Alliance logistics and supply chain analysis

**Features:**
- **Resource Flows:** Material supply lines
- **Production Capacity:** Alliance industry metrics
- **Bottlenecks:** Supply chain vulnerabilities

---

### 🗺️ ECTMap (`/ectmap`)

**Purpose:** Standalone full-screen ectmap integration

**Features:**
- **Full universe map:** All EVE systems and regions
- **Battle overlay:** Live battle markers with 5s refresh
- **IHUB markers:** Active sovereignty campaigns (magenta circles with I/T/S letters)
- **Battle status filters:** Gank, Brawl, Battle, Hellcamp (toggleable with counts)
- **Interactive navigation:** Click to explore
- **Direct iframe:** Port 3001 ectmap service

---

### ⚖️ Legal Pages

**Impressum** (`/impressum`) - German legal notice
**Datenschutz** (`/datenschutz`) - Privacy policy (German)

---

## Component Architecture

### Alliance Components (`src/components/alliance/`)

| Component | Purpose |
|-----------|---------|
| `OverviewView.tsx` | Overview tab - summary stats |
| `OffensiveView.tsx` | Offensive operations tab (+ fleet profile) |
| `DefensiveView.tsx` | Defensive vulnerability tab |
| `CapitalsView.tsx` | Capital fleet intelligence (9 panels) |
| `CorpsView.tsx` | Corporation rankings (6 panels) |
| `CapsuleersView.tsx` | Pilot intelligence (6 panels) |
| `WormholeView.tsx` | Wormhole empire analysis |
| `GeographyView.tsx` | DOTLAN geography + zKillboard data |
| `HuntingView.tsx` | Hunting patterns |

### Corporation Components (`src/components/corporation/`)

| Component | Purpose |
|-----------|---------|
| `OverviewView.tsx` | Corp overview |
| `OffensiveView.tsx` | Corp offensive operations (11 panels) |
| `DefensiveView.tsx` | Corp defensive analysis (11 panels) |
| `CapitalsView.tsx` | Corp capital intelligence (6 panels) |
| `PilotsView.tsx` | Corp pilot roster (6 panels) |
| `HuntingView.tsx` | Corp hunting operations |
| `GeographyView.tsx` | DOTLAN geography + zKillboard |
| `CorporationWormholeView.tsx` | Corp W-space operations |
| `geography/` | Shared panels: LiveActivity, SovDefense, TerritorialChanges, AlliancePower |

### Shared Killmail Intelligence Components (`src/components/shared/`)

| Component | Purpose |
|-----------|---------|
| `ThreatIntelPanels.tsx` | ThreatPanel (top attackers + damage profiles), CapitalRadarPanel (capital sightings + escalation stats), LogiScorePanel (enemy logi strength 0-100) |
| `HuntingScoreBoard.tsx` | Ranked system table with score bars, ADM, player deaths, avg ISK value, capital umbrella badge |
| `PilotRiskPanels.tsx` | AWOXRiskPanel (summary badges + at-risk pilot list), CorpHealthDashboard (member count, activity rate, ISK efficiency, sparkline) |

### PowerBloc Components (`src/components/powerbloc/`)

| Component | Purpose |
|-----------|---------|
| `PBOffensiveView.tsx` | Coalition offensive + victim tank profile |
| `PBDefensiveView.tsx` | Coalition defensive analysis |
| `PBCapitalsView.tsx` | Coalition capital fleet intel |
| `PBGeographyView.tsx` | Coalition DOTLAN geography |
| `PBAlliancesView.tsx` | Member alliance rankings |
| `PBCapsuleersView.tsx` | Coalition pilot intel |
| `PBDetailsView.tsx` | Coalition detail intel |
| `PBHuntingView.tsx` | Coalition hunting patterns |
| `PBWormholeView.tsx` | Coalition W-space operations |
| `PBPilotsView.tsx` | Coalition pilot performance |

### Battle Components (`src/components/battle/`)

| Component | Purpose |
|-----------|---------|
| `BattleHeader.tsx` | Battle header + SOV holder badge |
| `BattleSidesPanel.tsx` | BFS 2-coloring sides + alliance comparison + fleet profile |
| `BattleKillFeed.tsx` | Chronological kills |
| `BattleShipClasses.tsx` | Ship composition |
| `BattleDamageAnalysis.tsx` | Damage types |
| `BattleCommanderIntel.tsx` | Top pilots |
| `BattleDoctrines.tsx` | Fleet doctrines |
| `BattleReshipments.tsx` | Pilot persistence |
| `BattleTimeline.tsx` | Tactical shifts |
| `BattleAttackerLoadouts.tsx` | Per-alliance weapon loadouts + fleet sizes |
| `BattleContext.tsx` | Battle significance vs 24h war totals |
| `BattleSovContext.tsx` | Sov campaign alerts + ADM |
| `BattleVictimTank.tsx` | Dogma engine tank profiles + resist weaknesses |

### Wormhole Components (`src/components/wormhole/`)

| Component | Purpose |
|-----------|---------|
| `TheraRouterTab.tsx` | Thera route calculator + route visualization |
| `HuntersTab.tsx` | Active wormhole hunters |
| `MarketTab.tsx` | W-space market analysis |
| `ResidentsTab.tsx` | W-space resident tracking |
| `WormholeHero.tsx` | Hero banner section |
| `WormholeTabNav.tsx` | Tab navigation |
| `WormholeTicker.tsx` | Activity ticker |

### Home Components (`src/components/home/`)

| Component | Purpose |
|-----------|---------|
| `PowerBlocsSection.tsx` | Coalition rankings |
| `AllianceDynamicsSection.tsx` | Rising/Falling alliances |
| `ActiveConflictsSection.tsx` | Ongoing wars |
| `PowerList.tsx` | Alliance rankings |
| `ConflictCard.tsx` | War summary cards |

---

## API Integration

### Main API Clients (`src/services/`)

| File | Purpose |
|------|---------|
| `api.ts` | Base axios client |
| `allianceApi.ts` | Alliance intelligence endpoints |
| `corporationApi.ts` | Corporation intelligence endpoints |
| `api/battles.ts` | Battle detail + loadouts + tank analysis |
| `api/economy.ts` | War economy endpoints |
| `api/intelligence.ts` | Killmail intelligence (threats, capital radar, logi, hunting, pilot risk, corp health) |
| `api/powerbloc.ts` | Coalition/power bloc APIs |
| `api/reports.ts` | Coalition reports |
| `api/wormhole.ts` | Wormhole + Thera APIs |

### API Endpoints Used

**War/Battle APIs:**
- `/api/war/battles/active` - Live battles
- `/api/war/battle/{id}/*` - Battle details (sides, kills, ship-classes)
- `/api/war/battle/{id}/attacker-loadouts` - Weapon loadouts + fleet sizes
- `/api/war/battle/{id}/strategic-context` - Sovereignty + ADM
- `/api/war/battle/{id}/victim-tank-analysis` - Dogma engine tank profiles
- `/api/war/ticker` - Recent kills
- `/api/war/system/{id}/*` - System intel

**Intelligence APIs:**
- `/api/intelligence/fast/{id}/*` - Alliance intel (12+ endpoints)
- `/api/intelligence/fast/corporation/{id}/*` - Corp intel (8+ endpoints)
- `/api/intelligence/threats/{entity_type}/{entity_id}` - Threat composition + damage profiles
- `/api/intelligence/capital-radar/{entity_type}/{entity_id}` - Capital sightings + escalation timeline
- `/api/intelligence/logi-score/{entity_type}/{entity_id}` - Enemy logi shield score (0-100)
- `/api/intelligence/hunting/scores` - Ranked hunting opportunities (killmail + DOTLAN ADM)
- `/api/intelligence/pilot-risk/{corp_id}` - AWOX risk assessment
- `/api/intelligence/corp-health/{corp_id}` - Corp health metrics

**PowerBloc APIs:**
- `/api/powerbloc/{leader_id}/*` - 10+ coalition endpoints (Redis cached, 5-10min TTL)

**DOTLAN APIs:**
- `/api/dotlan/activity/*` - System activity, heat indices
- `/api/dotlan/sovereignty/*` - Campaigns, changes, ADM
- `/api/dotlan/alliance/*` - Alliance rankings

**Reports APIs:**
- `/api/reports/power-blocs/live` - Coalition rankings (60s cache)

---

## Performance Optimizations

### Code Splitting
- All pages lazy-loaded with `React.lazy()`
- Suspense boundaries with skeleton loaders
- Initial bundle: ~250KB (compressed)

### React Query
```typescript
staleTime: 60000,           // 1 minute
gcTime: 300000,             // 5 minutes
refetchOnWindowFocus: false,
refetchOnReconnect: true,
```

### Auto-Refresh
- **Home page:** 60s
- **Battle map:** 5s (ectmap)
- **Battle detail:** Manual only
- **Alliance/Corp:** Manual only

### Image Optimization
- Icons: 3 sizes (64px, 128px, 256px)
- Original: 1.6-3.2 MB → Optimized: 5-82 KB (~99% smaller)
- Located: `/public/icons/{64,128,256}/`

---

## Design System

### Color Palette

| Purpose | Hex | Usage |
|---------|-----|-------|
| Background | `#0d1117` | Page background |
| Surface | `#161b22` | Cards, panels |
| Border | `#30363d` | Subtle borders |
| Text Primary | `#e6edf3` | High contrast |
| Text Secondary | `#8b949e` | Muted text |
| Accent Blue | `#58a6ff` | Links, actions |
| Success | `#3fb950` | Profit, wins |
| Danger | `#f85149` | Losses, errors |

### Layout Patterns

**Compact Dashboard Style:**
- `borderLeft: 2px solid [color]` accents
- `background: rgba(0,0,0,0.3)` panels
- `padding: 0.5rem` spacing
- `fontSize: 0.7-0.9rem` compact text
- `maxHeight + overflowY: auto` scrollable

**Dot Headers:**
```
• UPPERCASE LABEL
```

**Single-Line Cards:**
```
Logo (18-20px) + Name + Metrics + Stats
```

---

## Development Workflow

### Fast Iteration (Recommended)

```bash
cd /home/cytrex/eve_copilot/public-frontend
./dev.sh
# Access: http://localhost:5175
# Auto-reload: ~200ms ⚡
```

### Production Build

```bash
cd /home/cytrex/eve_copilot/docker
docker compose build public-frontend
docker compose up -d public-frontend
# Access: http://localhost:5173
```

**Speed Comparison:**
- Dev Mode (HMR): <1 second per change ⚡
- Docker Build: ~20 seconds per change

---

## Recent Features

### February 2026

**Killmail Intelligence System (2026-02-21):**
- 6 new backend endpoints under `/api/intelligence/`:
  - `GET /threats/{entity_type}/{entity_id}` — Threat composition (top attackers, damage profiles)
  - `GET /capital-radar/{entity_type}/{entity_id}` — Capital escalation radar (sightings + escalation timeline)
  - `GET /logi-score/{entity_type}/{entity_id}` — Logi shield score (enemy logistics strength 0-100)
  - `GET /hunting/scores` — Ranked hunting opportunities (killmail + DOTLAN ADM fusion)
  - `GET /pilot-risk/{corp_id}` — Pilot risk assessment (AWOX detection)
  - `GET /corp-health/{corp_id}` — Corp health dashboard
- 3 new shared frontend components:
  - `ThreatIntelPanels.tsx` — ThreatPanel, CapitalRadarPanel, LogiScorePanel (integrated into DefensiveView)
  - `HuntingScoreBoard.tsx` — Ranked system table with score bars, ADM, deaths, capital badge (integrated into HuntingView)
  - `PilotRiskPanels.tsx` — AWOXRiskPanel, CorpHealthDashboard (integrated into PilotsView)
- API client: `services/api/intelligence.ts` (axios, 6 methods)
- TypeScript types: 12 new interfaces in `types/intelligence.ts`
- Migration 111: `doctrine_temporal_cache`, `hunting_opportunity_scores`, `pilot_risk_scores` tables
- Score calculator: `services/hunting/score_calculator.py`
- Data fusion: Killmail data (DB) + DOTLAN ADM (HTTP to dotlan-service)

**Moon Mining Operations (2026-02-14):**
- New Moon Mining tab on Corp Tools page (`/corp/tools`)
- Operations Overview: 4 KPI tiles (structures, ISK mined, next extraction, fuel alerts)
- Structure performance table with ISK/day, miner count, ore breakdown
- Revenue analytics: ore breakdown by rarity (R64-R4), top miners ranking
- Extraction calendar with status badges (active/ready/expired)
- Time period selector (7D/14D/30D)
- Scheduler job: 30-min ESI sync for mining observers + extractions

**Battle Intelligence Enhancement (2026-02-06):**
- 4 new battle panels: Attacker Loadouts, Battle Significance, Sov Context, Victim Tank
- BFS 2-coloring for battle side determination (replaced kill-ratio heuristic)
- Alliance performance comparison + fleet profile in expandable BattleSidesPanel
- Dogma Engine integration for victim tank analysis (EHP, resist weaknesses)

**DOTLAN Geography Integration (2026-02-05):**
- Geography tab for Alliance, Corporation, and PowerBloc pages
- 4 DOTLAN panels: Live Activity, Sov Defense, Territorial Changes, Alliance Power
- Color-coded badges: HOT/ACT/WRM/COL/QT (heat), CRIT/VULN/DEF/RF (sov)

**PowerBloc Expansion (2026-02-04 - 2026-02-06):**
- 10 intelligence tabs (Offensive, Defensive, Capitals, Geography, Alliances, Capsuleers, Details, Hunting, Wormhole, Pilots)
- Redis caching: 5-10min TTL (offensive: 4.8s → 13ms, 369x faster)
- Victim Tank Profile panel on Offensive tab
- Dual efficiency display (ISK% + K/D%)

**Wormhole Intel Enhancement (2026-02-05):**
- Thera Router with system presets, quick-select buttons, and route visualization
- 4 tabs: Thera Router, Hunters, Market, Residents

**ECTMap Enhancement (2026-02-05):**
- IHUB sovereignty campaign markers (magenta circles with I/T/S letters)
- Battle status filters: Gank, Brawl, Battle, Hellcamp (toggleable with counts)

**Data Consistency Overhaul (2026-02-06):**
- 53 bugs fixed across all War Intelligence tabs
- ISK deduplication via DISTINCT killmail queries
- Division-by-zero guards (`isFinite()`) across 17 frontend files

### January 2026

**Alliance Intelligence Overhaul:**
- 9 Tabs: Overview, Offensive, Defensive, Capitals, Corps, Pilots, Wormhole, Geography, Hunting
- Capitals Tab: 9 panels, Corps Tab: 6 panels, Pilots Tab: 6 panels

**Corporation Intelligence:**
- 8 Tabs: Overview, Offensive, Defensive, Capitals, Pilots, Hunting, Geography, Wormhole
- Offensive/Defensive: 11 panels each, Capitals: 6 panels

**Homepage & Performance:**
- Power Blocs, Alliance Dynamics, Active Conflicts sections
- Power Blocs API: 60s TTL cache (20x faster)
- Icons: Optimized to 64/128/256px sizes (99% smaller)

---

## Roadmap / Coming Soon

- Doctrine efficiency comparison
- Capital fit analysis with Dogma Engine
- Pilot replacement rate analysis
- Activity tab: Daily patterns, timezone analysis, peak hours

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

## Related Documentation

- **Main Guide:** [CLAUDE.md](../CLAUDE.md)
- **Development:** [DEVELOPMENT.md](DEVELOPMENT.md)
- **Services:** [CLAUDE.services.md](../CLAUDE.services.md)
- **Backend:** [CLAUDE.backend.md](../CLAUDE.backend.md)
