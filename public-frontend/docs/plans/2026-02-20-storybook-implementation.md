# Storybook Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Set up Storybook 8 with MSW, Autodocs, and MDX architecture pages to document all 249 React components of the Infinimind Intelligence EVE Online frontend.

**Architecture:** Monolithic Storybook inside `public-frontend/`, stories colocated with components (`*.stories.tsx`), MSW for API mocking, domain-based sidebar grouping. Global decorators wrap every story with AuthContext, QueryClientProvider, and MemoryRouter.

**Tech Stack:** Storybook 8, Vite builder, MSW 2, React 19, TypeScript 5.9, TanStack React Query 5

---

## Phase 1: Storybook Setup & Configuration

### Task 1: Install Storybook dependencies

**Files:**
- Modify: `public-frontend/package.json`

**Step 1: Install Storybook with Vite builder**

Run:
```bash
cd /home/andreas/projects/Eve-Online-Copilot/public-frontend
npx storybook@latest init --builder @storybook/builder-vite --skip-install
```

This scaffolds `.storybook/main.ts` and `.storybook/preview.ts`. Accept defaults.

**Step 2: Install MSW and addon packages**

Run:
```bash
cd /home/andreas/projects/Eve-Online-Copilot/public-frontend
npm install -D msw msw-storybook-addon @storybook/addon-a11y @storybook/addon-interactions @storybook/test
```

**Step 3: Initialize MSW service worker**

Run:
```bash
cd /home/andreas/projects/Eve-Online-Copilot/public-frontend
npx msw init public/ --save
```

This creates `public/mockServiceWorker.js`.

**Step 4: Verify installation**

Run:
```bash
cd /home/andreas/projects/Eve-Online-Copilot/public-frontend
ls .storybook/main.ts .storybook/preview.ts public/mockServiceWorker.js
```

Expected: All 3 files exist.

**Step 5: Commit**

```bash
cd /home/andreas/projects/Eve-Online-Copilot/public-frontend
git add package.json package-lock.json .storybook/ public/mockServiceWorker.js
git commit -m "feat: initialize Storybook 8 with MSW"
```

---

### Task 2: Configure Storybook main.ts

**Files:**
- Modify: `public-frontend/.storybook/main.ts`

**Step 1: Write the Storybook config**

Replace `.storybook/main.ts` with:

```typescript
import type { StorybookConfig } from '@storybook/react-vite';

const config: StorybookConfig = {
  stories: [
    '../src/stories/**/*.mdx',
    '../src/**/*.stories.@(ts|tsx)',
  ],
  addons: [
    '@storybook/addon-essentials',
    '@storybook/addon-a11y',
    '@storybook/addon-interactions',
  ],
  framework: {
    name: '@storybook/react-vite',
    options: {},
  },
  staticDirs: ['../public'],
  docs: {
    autodocs: 'tag',
  },
  viteFinal: async (config) => {
    // Remove the proxy config (MSW handles API mocking)
    if (config.server) {
      delete config.server.proxy;
    }
    return config;
  },
};

export default config;
```

**Step 2: Verify Storybook starts**

Run:
```bash
cd /home/andreas/projects/Eve-Online-Copilot/public-frontend
npx storybook dev -p 6006 --no-open &
sleep 10 && curl -s -o /dev/null -w "%{http_code}" http://localhost:6006
kill %1
```

Expected: HTTP 200

**Step 3: Commit**

```bash
cd /home/andreas/projects/Eve-Online-Copilot/public-frontend
git add .storybook/main.ts
git commit -m "feat: configure Storybook with Vite builder and autodocs"
```

---

### Task 3: Configure Storybook preview.ts with global decorators

**Files:**
- Modify: `public-frontend/.storybook/preview.ts`

**Step 1: Write the preview config with all decorators**

Replace `.storybook/preview.ts` with:

```typescript
import type { Preview, Decorator } from '@storybook/react';
import { initialize, mswLoader } from 'msw-storybook-addon';
import React from 'react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClientProvider, QueryClient } from '@tanstack/react-query';
import { AuthContext } from '../src/context/AuthContext';
import type { AuthState } from '../src/context/AuthContext';
import type { AccountInfo, TierInfo } from '../src/types/auth';
import '../src/index.css';
import '../src/App.css';

// Initialize MSW
initialize({
  onUnhandledRequest: 'bypass',
});

// Create a fresh QueryClient per story
const createQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        staleTime: Infinity,
        gcTime: Infinity,
      },
    },
  });

// Default mock auth state
const defaultAccount: AccountInfo = {
  character_id: 1117367444,
  character_name: 'Cytrex',
  corporation_id: 98378388,
  corporation_name: 'Infinimind Creations',
  alliance_id: 99003581,
  alliance_name: 'Fraternity.',
  portrait_url: 'https://images.evetech.net/characters/1117367444/portrait?size=64',
};

const defaultTierInfo: TierInfo = {
  tier: 'coalition',
  tier_label: 'Coalition',
  expires_at: null,
};

const defaultAuthState: AuthState = {
  isLoading: false,
  isLoggedIn: true,
  account: defaultAccount,
  tierInfo: defaultTierInfo,
  activeModules: ['intel', 'market', 'production', 'fittings', 'navigation', 'shopping', 'corp'],
  orgPlan: null,
  login: async () => {},
  logout: async () => {},
  refresh: async () => {},
};

// Auth decorator — controllable via Storybook args
const withAuth: Decorator = (Story, context) => {
  const tier = context.globals.tier || 'coalition';
  const loggedIn = context.globals.loggedIn !== false;

  const authState: AuthState = {
    ...defaultAuthState,
    isLoggedIn: loggedIn,
    account: loggedIn ? defaultAccount : null,
    tierInfo: loggedIn ? { ...defaultTierInfo, tier, tier_label: tier } : null,
  };

  return React.createElement(
    AuthContext.Provider,
    { value: authState },
    React.createElement(Story)
  );
};

// Router decorator
const withRouter: Decorator = (Story) =>
  React.createElement(MemoryRouter, null, React.createElement(Story));

// QueryClient decorator
const withQueryClient: Decorator = (Story) =>
  React.createElement(
    QueryClientProvider,
    { client: createQueryClient() },
    React.createElement(Story)
  );

const preview: Preview = {
  decorators: [withAuth, withQueryClient, withRouter],
  loaders: [mswLoader],
  parameters: {
    controls: {
      matchers: {
        color: /(background|color)$/i,
        date: /Date$/i,
      },
    },
    backgrounds: {
      default: 'eve-dark',
      values: [
        { name: 'eve-dark', value: '#0d1117' },
        { name: 'eve-darker', value: '#010409' },
        { name: 'white', value: '#ffffff' },
      ],
    },
    layout: 'padded',
  },
  globalTypes: {
    tier: {
      description: 'Subscription tier for feature gating',
      toolbar: {
        title: 'Tier',
        icon: 'shield',
        items: ['free', 'pilot', 'corp', 'coalition'],
        dynamicTitle: true,
      },
    },
    loggedIn: {
      description: 'Auth state',
      toolbar: {
        title: 'Auth',
        icon: 'user',
        items: [
          { value: true, title: 'Logged In' },
          { value: false, title: 'Logged Out' },
        ],
        dynamicTitle: true,
      },
    },
  },
};

export default preview;
```

**Step 2: Commit**

```bash
cd /home/andreas/projects/Eve-Online-Copilot/public-frontend
git add .storybook/preview.ts
git commit -m "feat: add global decorators (Auth, Router, QueryClient, MSW)"
```

---

### Task 4: Set up MSW mock handlers (auth baseline)

**Files:**
- Create: `public-frontend/.storybook/mocks/handlers.ts`
- Create: `public-frontend/.storybook/mocks/data/auth.ts`
- Create: `public-frontend/.storybook/mocks/handlers/auth.ts`

**Step 1: Create mock data directory structure**

Run:
```bash
mkdir -p /home/andreas/projects/Eve-Online-Copilot/public-frontend/.storybook/mocks/data
mkdir -p /home/andreas/projects/Eve-Online-Copilot/public-frontend/.storybook/mocks/handlers
```

**Step 2: Write auth mock data**

Create `.storybook/mocks/data/auth.ts`:

```typescript
export const mockAccount = {
  character_id: 1117367444,
  character_name: 'Cytrex',
  corporation_id: 98378388,
  corporation_name: 'Infinimind Creations',
  alliance_id: 99003581,
  alliance_name: 'Fraternity.',
  portrait_url: 'https://images.evetech.net/characters/1117367444/portrait?size=64',
};

export const mockTierInfo = {
  tier: 'coalition',
  tier_label: 'Coalition',
  expires_at: null,
  subscription: {
    plan: 'coalition',
    status: 'active',
    isk_paid: 500000000,
  },
};

export const mockModules = {
  modules: ['intel', 'market', 'production', 'fittings', 'navigation', 'shopping', 'corp'],
  org_plan: null,
};
```

**Step 3: Write auth handlers**

Create `.storybook/mocks/handlers/auth.ts`:

```typescript
import { http, HttpResponse } from 'msw';
import { mockAccount, mockTierInfo, mockModules } from '../data/auth';

export const authHandlers = [
  http.get('/api/auth/account', () => HttpResponse.json(mockAccount)),
  http.get('/api/tier/my-tier', () => HttpResponse.json(mockTierInfo)),
  http.get('/api/tier/modules', () => HttpResponse.json(mockModules)),
  http.post('/api/auth/logout', () => new HttpResponse(null, { status: 204 })),
];
```

**Step 4: Write combined handlers file**

Create `.storybook/mocks/handlers.ts`:

```typescript
import { authHandlers } from './handlers/auth';

// All MSW handlers — add new domain handlers here
export const handlers = [
  ...authHandlers,
];
```

**Step 5: Commit**

```bash
cd /home/andreas/projects/Eve-Online-Copilot/public-frontend
git add .storybook/mocks/
git commit -m "feat: add MSW mock handlers for auth baseline"
```

---

## Phase 2: Shared UI Component Stories

### Task 5: Write Card component stories

**Files:**
- Create: `public-frontend/src/components/ui/Card.stories.tsx`

**Step 1: Write the stories**

Create `src/components/ui/Card.stories.tsx`:

```typescript
import type { Meta, StoryObj } from '@storybook/react';
import { Card, CardHeader, CardLink } from './Card';

const meta: Meta<typeof Card> = {
  title: 'Shared UI/Card',
  component: Card,
  tags: ['autodocs'],
  argTypes: {
    variant: {
      control: 'select',
      options: ['default', 'danger', 'accent', 'warning'],
    },
    padding: {
      control: 'select',
      options: ['none', 'sm', 'md', 'lg'],
    },
  },
};
export default meta;

type Story = StoryObj<typeof Card>;

export const Default: Story = {
  args: {
    children: 'Card content goes here',
  },
};

export const Danger: Story = {
  args: {
    variant: 'danger',
    children: 'Critical alert — hostile fleet detected in system',
  },
};

export const Accent: Story = {
  args: {
    variant: 'accent',
    children: 'Intel update available',
  },
};

export const Warning: Story = {
  args: {
    variant: 'warning',
    children: 'Sovereignty campaign active',
  },
};

export const WithHeader: Story = {
  render: () => (
    <Card>
      <CardHeader
        icon="⚔️"
        title="Battle Report"
        subtitle="Last 7 days"
        action={<CardLink to="/battle-report">View All</CardLink>}
      />
      <p style={{ color: 'rgba(255,255,255,0.6)', margin: 0 }}>
        47 battles detected across New Eden
      </p>
    </Card>
  ),
};

export const NoPadding: Story = {
  args: {
    padding: 'none',
    children: 'Edge-to-edge content',
  },
};

export const NoNoise: Story = {
  args: {
    withNoise: false,
    children: 'Clean card without noise texture',
  },
};
```

**Step 2: Verify story renders**

Run:
```bash
cd /home/andreas/projects/Eve-Online-Copilot/public-frontend
npx storybook dev -p 6006 --no-open &
sleep 10 && curl -s http://localhost:6006/iframe.html | head -5
kill %1
```

Expected: HTML content returned (Storybook renders)

**Step 3: Commit**

```bash
cd /home/andreas/projects/Eve-Online-Copilot/public-frontend
git add src/components/ui/Card.stories.tsx
git commit -m "feat: add Card component stories"
```

---

### Task 6: Write StatBox component stories

**Files:**
- Create: `public-frontend/src/components/ui/StatBox.stories.tsx`

**Step 1: Write the stories**

Create `src/components/ui/StatBox.stories.tsx`:

```typescript
import type { Meta, StoryObj } from '@storybook/react';
import { StatBox, StatRow, InlineStat } from './StatBox';
import { COLORS } from '../../constants';

const meta: Meta<typeof StatBox> = {
  title: 'Shared UI/StatBox',
  component: StatBox,
  tags: ['autodocs'],
  argTypes: {
    color: { control: 'color' },
    size: { control: 'select', options: ['sm', 'md'] },
  },
};
export default meta;

type Story = StoryObj<typeof StatBox>;

export const Default: Story = {
  args: {
    label: 'Total Kills',
    value: '17,941',
  },
};

export const Positive: Story = {
  args: {
    label: 'ISK Efficiency',
    value: '60.1%',
    color: COLORS.positive,
  },
};

export const Negative: Story = {
  args: {
    label: 'Losses',
    value: '15,262',
    color: COLORS.negative,
  },
};

export const Small: Story = {
  args: {
    label: 'Active Pilots',
    value: '4,909',
    size: 'sm',
  },
};

export const ISKValue: Story = {
  args: {
    label: 'ISK Destroyed',
    value: '2.3T',
    color: COLORS.warning,
  },
};

export const InStatRow: Story = {
  name: 'StatRow (Multiple Stats)',
  render: () => (
    <StatRow>
      <StatBox label="Kills" value="17,941" color={COLORS.positive} />
      <StatBox label="Deaths" value="15,262" color={COLORS.negative} />
      <StatBox label="Efficiency" value="60.1%" color={COLORS.accent} />
      <StatBox label="ISK Destroyed" value="2.3T" color={COLORS.warning} />
    </StatRow>
  ),
};

export const InlineStats: Story = {
  name: 'InlineStat Variants',
  render: () => (
    <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
      <InlineStat icon="⚔️" value="17,941" color={COLORS.positive} label="kills" />
      <InlineStat icon="💀" value="15,262" color={COLORS.negative} label="deaths" />
      <InlineStat icon="💰" value="2.3T" color={COLORS.warning} label="ISK" />
    </div>
  ),
};
```

**Step 2: Commit**

```bash
cd /home/andreas/projects/Eve-Online-Copilot/public-frontend
git add src/components/ui/StatBox.stories.tsx
git commit -m "feat: add StatBox, StatRow, InlineStat stories"
```

---

### Task 7: Write stories for remaining shared components

**Files:**
- Create: `public-frontend/src/components/Sparkline.stories.tsx`
- Create: `public-frontend/src/components/EveImage.stories.tsx`
- Create: `public-frontend/src/components/ModuleGate.stories.tsx`
- Create: `public-frontend/src/components/TierGate.stories.tsx`
- Create: `public-frontend/src/components/RefreshIndicator.stories.tsx`
- Create: `public-frontend/src/components/WarRoomAlertBar.stories.tsx`

**Step 1: Read each component to understand its props**

Read these files first:
- `src/components/Sparkline.tsx`
- `src/components/EveImage.tsx`
- `src/components/ModuleGate.tsx`
- `src/components/TierGate.tsx`
- `src/components/RefreshIndicator.tsx`
- `src/components/WarRoomAlertBar.tsx`

**Step 2: Write stories for each**

For each component, create a `*.stories.tsx` file following this pattern:
- Import the component
- Set `title` to `'Shared UI/{ComponentName}'`
- Add `tags: ['autodocs']`
- Create `Default`, and relevant variant stories
- Use realistic EVE Online data in examples

**Step 3: Commit**

```bash
cd /home/andreas/projects/Eve-Online-Copilot/public-frontend
git add src/components/*.stories.tsx
git commit -m "feat: add stories for shared components (Sparkline, EveImage, Gates, etc.)"
```

---

## Phase 3: MDX Architecture Documentation

### Task 8: Write Welcome page

**Files:**
- Create: `public-frontend/src/stories/Welcome.mdx`

**Step 1: Create the stories directory**

Run:
```bash
mkdir -p /home/andreas/projects/Eve-Online-Copilot/public-frontend/src/stories
```

**Step 2: Write Welcome.mdx**

```mdx
import { Meta } from '@storybook/blocks';

<Meta title="Docs/Welcome" />

# Infinimind Intelligence — Component Library

Welcome to the Storybook documentation for the **Infinimind Intelligence** EVE Online frontend.

## Overview

| Metric | Value |
|--------|-------|
| Framework | React 19 + TypeScript 5.9 |
| Build Tool | Vite 7 |
| State Management | TanStack React Query + React Context |
| Components | 249 |
| Pages | 54 |
| API Services | 21 domain modules |
| Backend | 18 microservices |

## Navigation

Use the sidebar to browse components organized by domain:

- **Shared UI** — Reusable primitives (Card, StatBox, EveImage)
- **Intel & Battle** — Battle reports, alliance analysis, wormholes
- **Economy & Market** — Market data, war economy, supply chains
- **Production** — Planetary Industry, manufacturing, projects
- **Fittings & Navigation** — Ship fittings, route planner, shopping
- **Corporation Tools** — Finance, HR, fleet, timers
- **Characters & Account** — Multi-character dashboard
- **Pages** — Full page components

## Tier System

Use the **Tier** toolbar control (top) to switch between subscription levels:
- `free` — Basic intel access
- `pilot` — Full pilot tools
- `corp` — Corporation management
- `coalition` — Full coalition features

## Auth Toggle

Use the **Auth** toolbar control to toggle between logged-in and logged-out states.
```

**Step 3: Commit**

```bash
cd /home/andreas/projects/Eve-Online-Copilot/public-frontend
git add src/stories/Welcome.mdx
git commit -m "docs: add Storybook Welcome page"
```

---

### Task 9: Write Architecture documentation pages

**Files:**
- Create: `public-frontend/src/stories/Architecture.mdx`
- Create: `public-frontend/src/stories/Routing.mdx`
- Create: `public-frontend/src/stories/APIIntegration.mdx`
- Create: `public-frontend/src/stories/Authentication.mdx`
- Create: `public-frontend/src/stories/FeatureGates.mdx`

**Step 1: Write Architecture.mdx**

Cover: Component hierarchy, state management (React Query + Context), directory structure, styling approach (inline styles, COLORS constant).

**Step 2: Write Routing.mdx**

Cover: Full route table from App.tsx (all 47 routes), lazy loading pattern, redirect routes.

**Step 3: Write APIIntegration.mdx**

Cover: Service layer in `src/services/api/`, Axios setup, TanStack Query patterns (staleTime, gcTime), all 21 API modules with their base paths.

**Step 4: Write Authentication.mdx**

Cover: EVE SSO flow, AuthContext shape (isLoggedIn, account, tierInfo, activeModules), JWT handling, localStorage eve_auth flag.

**Step 5: Write FeatureGates.mdx**

Cover: TierGate component, ModuleGate component, useModules hook, tier hierarchy (free < pilot < corp < coalition).

**Step 6: Commit**

```bash
cd /home/andreas/projects/Eve-Online-Copilot/public-frontend
git add src/stories/*.mdx
git commit -m "docs: add Architecture, Routing, API, Auth, FeatureGates MDX docs"
```

---

## Phase 4: Intel & Battle Domain Stories

### Task 10: Write Battle Report component stories

**Files:**
- Create stories for all components in `src/components/battle/`:
  - `BattleHeader.stories.tsx`
  - `BattleSidesPanel.stories.tsx`
  - `BattleTimeline.stories.tsx`
  - `BattleDoctrines.stories.tsx`
  - `BattleStatsCards.stories.tsx`
  - `BattleReshipments.stories.tsx`
- Create: `.storybook/mocks/data/battles.ts`
- Create: `.storybook/mocks/handlers/battles.ts`

**Step 1: Read all battle components to understand their props**

Read each component file in `src/components/battle/` to determine:
- Props interface
- Required data shape
- API dependencies (which endpoints they call)

**Step 2: Write battle mock data**

Create `.storybook/mocks/data/battles.ts` with realistic EVE battle data:
- A mock battle between Fraternity. and Goonswarm Federation
- Systems like M-OEE8, 1DQ1-A
- Ship types (Muninn, Cerberus, Eagle, Ferox, Munnin)
- ISK values in realistic ranges

**Step 3: Write battle MSW handlers**

Create `.storybook/mocks/handlers/battles.ts` with handlers for:
- `GET /api/war/battles`
- `GET /api/war/battles/:id`
- `GET /api/war/battle/:id/attacker-loadouts`
- `GET /api/war/battle/:id/strategic-context`
- `GET /api/war/battle/:id/victim-tank-analysis`

**Step 4: Write stories for each battle component**

Title pattern: `'Intel & Battle/Battle Report/{ComponentName}'`

Create Default + Loading + Empty stories for each.

**Step 5: Commit**

```bash
cd /home/andreas/projects/Eve-Online-Copilot/public-frontend
git add src/components/battle/*.stories.tsx .storybook/mocks/data/battles.ts .storybook/mocks/handlers/battles.ts
git commit -m "feat: add Battle Report component stories with MSW mocks"
```

---

### Task 11: Write Alliance/Corp/PowerBloc shared view stories

**Files:**
- Create stories for components in `src/components/shared/`:
  - `OffensiveView.stories.tsx`
  - `DefensiveView.stories.tsx`
  - `CapitalsView.stories.tsx`
  - `GeographyView.stories.tsx`
- Create: `.storybook/mocks/data/alliances.ts`
- Create: `.storybook/mocks/handlers/alliances.ts`

**Step 1: Read shared view components**

These are the largest components (OffensiveView: 1,323 lines, GeographyView: 12,885 lines). Understand their props and API dependencies.

**Step 2: Write alliance/corp mock data**

Use real EVE alliance data as basis:
- Fraternity. (99003581)
- Goonswarm Federation (1354830081)
- Pandemic Horde (99005338)

**Step 3: Write stories**

Title pattern: `'Intel & Battle/Alliance Views/{ComponentName}'`

For OffensiveView, create stories showing different time ranges (1d, 7d, 30d).

**Step 4: Commit**

```bash
cd /home/andreas/projects/Eve-Online-Copilot/public-frontend
git add src/components/shared/*.stories.tsx .storybook/mocks/data/alliances.ts .storybook/mocks/handlers/alliances.ts
git commit -m "feat: add Alliance/Corp shared view stories"
```

---

### Task 12: Write Wormhole component stories

**Files:**
- Create stories for components in `src/components/wormhole/`
- Create: `.storybook/mocks/data/wormhole.ts`
- Create: `.storybook/mocks/handlers/wormhole.ts`

**Step 1: Read wormhole components**

**Step 2: Write mock data with Thera connections, WH signatures**

**Step 3: Write stories**

Title pattern: `'Intel & Battle/Wormhole/{ComponentName}'`

**Step 4: Commit**

```bash
cd /home/andreas/projects/Eve-Online-Copilot/public-frontend
git add src/components/wormhole/*.stories.tsx .storybook/mocks/data/wormhole.ts .storybook/mocks/handlers/wormhole.ts
git commit -m "feat: add Wormhole component stories"
```

---

## Phase 5: Economy & Market Domain Stories

### Task 13: Write Market component stories

**Files:**
- Create stories for components in `src/components/market/`
- Create: `.storybook/mocks/data/market.ts`
- Create: `.storybook/mocks/handlers/market.ts`

**Step 1: Read market components (PriceChart, HubSelector, MarketBrowser)**

**Step 2: Write mock data with Jita/Amarr market prices, volume data**

**Step 3: Write stories**

Title pattern: `'Economy & Market/Market/{ComponentName}'`

**Step 4: Commit**

```bash
cd /home/andreas/projects/Eve-Online-Copilot/public-frontend
git add src/components/market/*.stories.tsx .storybook/mocks/data/market.ts .storybook/mocks/handlers/market.ts
git commit -m "feat: add Market component stories"
```

---

### Task 14: Write War Economy and Supply Chain stories

**Files:**
- Create stories for components in `src/components/war-economy/`
- Create stories for components in `src/components/trade-routes/`

**Step 1: Read components, write stories**

Title patterns:
- `'Economy & Market/War Economy/{ComponentName}'`
- `'Economy & Market/Supply Chain/{ComponentName}'`

**Step 2: Commit**

```bash
cd /home/andreas/projects/Eve-Online-Copilot/public-frontend
git add src/components/war-economy/*.stories.tsx src/components/trade-routes/*.stories.tsx
git commit -m "feat: add War Economy and Trade Routes stories"
```

---

## Phase 6: Production Domain Stories

### Task 15: Write Production/PI component stories

**Files:**
- Create stories for components in `src/components/production/`
- Create: `.storybook/mocks/data/production.ts`
- Create: `.storybook/mocks/handlers/production.ts`

**Step 1: Read production components (PIChainBrowser, PIChainPlanner, PlannerTab, SchematicSelector)**

**Step 2: Write mock data with PI schematics, chain data, project data**

**Step 3: Write stories**

Title pattern: `'Production/PI Chain/{ComponentName}'` and `'Production/Projects/{ComponentName}'`

**Step 4: Commit**

```bash
cd /home/andreas/projects/Eve-Online-Copilot/public-frontend
git add src/components/production/*.stories.tsx .storybook/mocks/data/production.ts .storybook/mocks/handlers/production.ts
git commit -m "feat: add Production/PI component stories"
```

---

## Phase 7: Fittings & Navigation Domain Stories

### Task 16: Write Fitting component stories

**Files:**
- Create stories for components in `src/components/fittings/`
- Create: `.storybook/mocks/data/fittings.ts`
- Create: `.storybook/mocks/handlers/fittings.ts`

**Step 1: Read fitting components (FittingBrowser, FittingPicker, ModulePicker, SlotPanel, StatsPanel, ImportDialog, FittingNameDialog)**

**Step 2: Write mock data with ship fittings (Drake, Muninn, Gila), module data, stats**

**Step 3: Write stories**

Title pattern: `'Fittings & Navigation/Fittings/{ComponentName}'`

Include stories for:
- Empty fitting
- Fully fitted ship
- Fitting editor with active module picker
- Import dialog with EFT paste

**Step 4: Commit**

```bash
cd /home/andreas/projects/Eve-Online-Copilot/public-frontend
git add src/components/fittings/*.stories.tsx .storybook/mocks/data/fittings.ts .storybook/mocks/handlers/fittings.ts
git commit -m "feat: add Fitting component stories"
```

---

### Task 17: Write Navigation and Shopping stories

**Files:**
- Create stories for components in `src/components/navigation/`
- Create stories for components in `src/components/shopping/`

**Step 1: Read and write stories**

Title patterns:
- `'Fittings & Navigation/Navigation/{ComponentName}'`
- `'Fittings & Navigation/Shopping/{ComponentName}'`

**Step 2: Commit**

```bash
cd /home/andreas/projects/Eve-Online-Copilot/public-frontend
git add src/components/navigation/*.stories.tsx src/components/shopping/*.stories.tsx
git commit -m "feat: add Navigation and Shopping stories"
```

---

## Phase 8: Corporation Tools Domain Stories

### Task 18: Write Corp Finance, HR, Fleet, Timers stories

**Files:**
- Create stories for components in `src/components/finance/`, `src/components/hr/`, `src/components/fleet/`, `src/components/srp/`
- Create: `.storybook/mocks/data/finance.ts`
- Create: `.storybook/mocks/handlers/finance.ts`

**Step 1: Read all corp-related components**

**Step 2: Write mock data for wallets, SRP claims, HR applications, fleet comp**

**Step 3: Write stories**

Title patterns:
- `'Corporation Tools/Finance/{ComponentName}'`
- `'Corporation Tools/HR/{ComponentName}'`
- `'Corporation Tools/Fleet/{ComponentName}'`
- `'Corporation Tools/Timers/{ComponentName}'`

**Step 4: Commit**

```bash
cd /home/andreas/projects/Eve-Online-Copilot/public-frontend
git add src/components/finance/*.stories.tsx src/components/hr/*.stories.tsx src/components/fleet/*.stories.tsx src/components/srp/*.stories.tsx
git commit -m "feat: add Corporation Tools stories (Finance, HR, Fleet, SRP)"
```

---

## Phase 9: Characters, Dashboard & Pages

### Task 19: Write Character and Dashboard stories

**Files:**
- Create stories for components in `src/components/characters/`, `src/components/dashboard/`
- Create: `.storybook/mocks/data/characters.ts`

**Step 1: Write mock character data (Cytrex, Artallus, Cytricia, Mind Overmatter)**

**Step 2: Write stories**

Title patterns:
- `'Characters & Account/Characters/{ComponentName}'`
- `'Characters & Account/Dashboard/{ComponentName}'`

**Step 3: Commit**

```bash
cd /home/andreas/projects/Eve-Online-Copilot/public-frontend
git add src/components/characters/*.stories.tsx src/components/dashboard/*.stories.tsx .storybook/mocks/data/characters.ts
git commit -m "feat: add Character and Dashboard stories"
```

---

### Task 20: Write Page-level stories

**Files:**
- Create stories for key pages in `src/pages/`:
  - `Home.stories.tsx`
  - `Pricing.stories.tsx`
  - `HowItWorks.stories.tsx`
  - `NotFound.stories.tsx`

**Step 1: Read page components**

**Step 2: Write stories for each page**

Title pattern: `'Pages/{PageName}'`

Note: Pages that require complex data (BattleReport, AllianceDetail, etc.) need their MSW handlers from earlier tasks.

**Step 3: Commit**

```bash
cd /home/andreas/projects/Eve-Online-Copilot/public-frontend
git add src/pages/*.stories.tsx
git commit -m "feat: add Page-level stories"
```

---

## Phase 10: Remaining Domain Components

### Task 21: Write stories for all remaining component directories

**Files:**
- Create stories for components in directories not yet covered:
  - `src/components/alerts/`
  - `src/components/battlefield/`
  - `src/components/battle-report/`
  - `src/components/corp/`
  - `src/components/corptools/`
  - `src/components/doctrines/`
  - `src/components/home/`
  - `src/components/intel/`
  - `src/components/recommendations/`
  - `src/components/warfare/`
  - `src/components/warfare-intel/`

**Step 1: Read each directory's components**

**Step 2: Write stories following domain naming**

Assign each to the appropriate sidebar category. Use existing MSW mocks or create additional mock data as needed.

**Step 3: Commit**

```bash
cd /home/andreas/projects/Eve-Online-Copilot/public-frontend
git add src/components/**/*.stories.tsx
git commit -m "feat: add stories for remaining component directories"
```

---

## Phase 11: Add npm script and final verification

### Task 22: Add Storybook scripts to package.json

**Files:**
- Modify: `public-frontend/package.json`

**Step 1: Add scripts**

Add these scripts to `package.json`:

```json
{
  "scripts": {
    "storybook": "storybook dev -p 6006",
    "build-storybook": "storybook build -o storybook-static"
  }
}
```

**Step 2: Add storybook-static to .gitignore**

Check if `.gitignore` exists and add `storybook-static/` to it.

**Step 3: Run full Storybook build to verify all stories compile**

Run:
```bash
cd /home/andreas/projects/Eve-Online-Copilot/public-frontend
npm run build-storybook 2>&1 | tail -20
```

Expected: Build completes successfully.

**Step 4: Commit**

```bash
cd /home/andreas/projects/Eve-Online-Copilot/public-frontend
git add package.json .gitignore
git commit -m "feat: add Storybook npm scripts and build config"
```

---

### Task 23: Final verification — start Storybook and verify all stories render

**Step 1: Start Storybook**

Run:
```bash
cd /home/andreas/projects/Eve-Online-Copilot/public-frontend
npm run storybook &
sleep 15
```

**Step 2: Verify sidebar has all domain groups**

Check that the Storybook sidebar contains:
- Docs (Welcome, Architecture, Routing, API, Auth, FeatureGates)
- Shared UI
- Intel & Battle
- Economy & Market
- Production
- Fittings & Navigation
- Corporation Tools
- Characters & Account
- Pages

**Step 3: Spot-check stories render without errors**

Open a few stories and verify they render correctly with mock data.

**Step 4: Kill Storybook, final commit**

```bash
kill %1
cd /home/andreas/projects/Eve-Online-Copilot/public-frontend
git add -A
git commit -m "docs: complete Storybook setup with all component stories"
git push origin main
```
