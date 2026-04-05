# Storybook Setup Design - Infinimind Intelligence Frontend

**Datum:** 2026-02-20
**Ziel:** Vollständige Dokumentation aller 249 React-Komponenten mit interaktivem Storybook

## Entscheidungen

| Thema | Entscheidung |
|-------|-------------|
| Hauptziel | Vollständige Komponentendokumentation |
| Mock-Strategie | MSW (Mock Service Worker) |
| Docs-Seiten | Ja, mit Architektur-MDX |
| Organisation | Domain-basierte Sidebar-Gruppierung |
| Ansatz | Monolithisch im public-frontend/ |

## Technisches Setup

### Stack

- **Storybook 8** mit Vite-Builder
- **MSW 2** für API-Mocking
- **React 19 + TypeScript 5.9**
- Stories als `*.stories.tsx` neben den Komponenten

### Addons

- `@storybook/addon-essentials` (Controls, Actions, Viewport, Docs)
- `@storybook/addon-a11y` (Accessibility)
- `@storybook/addon-interactions` (Play-Functions)
- `msw-storybook-addon` (MSW-Integration)

### Verzeichnisstruktur

```
public-frontend/
├── .storybook/
│   ├── main.ts              # Storybook-Config (Vite-Builder, Addons)
│   ├── preview.ts           # Globale Decorators (Auth, Query, Router)
│   ├── preview-head.html    # Globale Styles
│   └── mocks/
│       ├── handlers.ts      # Alle MSW Handler registriert
│       ├── data/             # Mock-Fixtures pro Domain
│       │   ├── battles.ts
│       │   ├── alliances.ts
│       │   ├── characters.ts
│       │   ├── market.ts
│       │   ├── fittings.ts
│       │   ├── production.ts
│       │   ├── wormhole.ts
│       │   ├── finance.ts
│       │   └── ...
│       └── handlers/         # MSW Handler pro API-Service
│           ├── auth.ts
│           ├── battles.ts
│           ├── market.ts
│           └── ...
├── src/
│   ├── components/
│   │   ├── battle/
│   │   │   ├── BattleHeader.tsx
│   │   │   ├── BattleHeader.stories.tsx   # Story neben Komponente
│   │   │   └── ...
│   │   └── ...
│   └── stories/                            # MDX Architektur-Docs
│       ├── Welcome.mdx
│       ├── Architecture.mdx
│       ├── Routing.mdx
│       ├── APIIntegration.mdx
│       ├── Authentication.mdx
│       └── FeatureGates.mdx
```

### Globale Decorators (preview.ts)

Jede Story wird automatisch gewrappt mit:

1. **AuthContext.Provider** - Mock-User mit konfigurierbarem Tier (free/pilot/corp/coalition)
2. **QueryClientProvider** - TanStack React Query Client
3. **MemoryRouter** - React Router für Link-Komponenten
4. **MSW Worker** - API-Mocking aktiv
5. **Globale Styles** - index.css + App.css

## Sidebar-Organisation (Domain-basiert)

```
Docs
├── Welcome
├── Architecture
├── Routing Map
├── API Integration
├── Authentication & Tiers
└── Feature Gates

Shared / UI
├── Card, StatBox, Sparkline, EveImage
├── ModuleGate, TierGate
├── RefreshIndicator, FeedbackWidget
├── NewsTicker, LiveBattles, WarRoomAlertBar

Intel & Battle
├── Battle Report (Header, Sides, Timeline, Doctrines, Stats, Reshipments)
├── Alliance Views (Offensive, Defensive, Capitals, Geography, Capsuleers, Hunting)
├── Corporation, PowerBloc
├── Wormhole (Thera, Hunters, Market)
└── Doctrines

Economy & Market
├── Market (PriceChart, HubSelector, Browser)
├── War Economy (Signals, Combat, Routes)
├── Supply Chain, Trade Routes

Production
├── PI Chain (Browser, Planner, Schematic)
├── Projects (List, Detail, Planner)

Fittings & Navigation
├── Fittings (Browser, Editor, Picker, Stats)
├── Navigation (RouteMap, JumpCalculator)
├── Shopping (ListManager, Multibuy)

Corporation Tools
├── Finance (Cockpit, Wallets, SRP)
├── HR (Applications, Vetting)
├── Fleet, Timers, Corp Tools

Characters & Account
├── Characters (List, Skills, Assets)
├── Dashboard Widgets

Pages
├── Home, Pricing, HowItWorks
├── Impressum, Datenschutz, NotFound
```

## MSW Mock-Daten Strategie

### Prinzipien

- Echte EVE-Daten als Basis (bekannte Allianzen, Schiffe, Systeme)
- 4 Szenarien pro Story: Default, Loading, Error, Empty
- Auth-Tiers mockbar über Storybook Controls
- Separate Fixtures-Dateien pro Domain

### Implementierungsreihenfolge

1. **Auth** - Basis für TierGate/ModuleGate
2. **Shared UI** - Keine API nötig, schnelle Wins
3. **Battle/Intel** - Größte Sichtbarkeit, Kernfeature
4. **Market/Economy** - Charts, Tabellen
5. **Fittings/Production** - Komplexe Formulare
6. **Corp Tools** - Finance, HR, Fleet
7. **Characters/Account** - Multi-Charakter Daten

## Story-Konventionen

### Dateiname

`ComponentName.stories.tsx` neben der Komponente.

### Story-Struktur

```typescript
import type { Meta, StoryObj } from '@storybook/react'
import { ComponentName } from './ComponentName'

const meta: Meta<typeof ComponentName> = {
  title: 'Intel & Battle/Battle Report/BattleHeader',
  component: ComponentName,
  tags: ['autodocs'],
}
export default meta

type Story = StoryObj<typeof ComponentName>

export const Default: Story = { args: { /* ... */ } }
export const Loading: Story = { /* loading state */ }
export const Error: Story = { /* error state */ }
export const Empty: Story = { /* empty state */ }
```

### Naming Convention für Titles

`{Domain}/{Subdomain}/{ComponentName}`

Beispiele:
- `Intel & Battle/Battle Report/BattleHeader`
- `Shared UI/Card`
- `Economy & Market/Market/PriceChart`
- `Docs/Architecture`
