# EVE Copilot Unified Frontend

Modern React frontend for EVE Online character and industry management.

## Tech Stack

- **React 18** with TypeScript
- **Vite** for fast development and builds
- **Tailwind CSS** with shadcn/ui components
- **TanStack Query** for server state management
- **React Router v7** for navigation

## Development

```bash
# Install dependencies
npm install

# Start development server (port 3000)
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## Project Structure

```
src/
├── api/           # API client and endpoint functions
├── components/    # Reusable UI components
│   ├── ui/        # Base components (shadcn/ui style)
│   ├── layout/    # Layout components (Sidebar, Header)
│   └── dashboard/ # Dashboard-specific components
├── contexts/      # React contexts (CharacterContext)
├── hooks/         # Custom React hooks
├── lib/           # Utility functions
├── pages/         # Page components
└── types/         # TypeScript type definitions
```

## Features (Phase 1)

- [x] Multi-character dashboard
- [x] Wallet balance display
- [x] Skill points summary
- [x] Skill queue with progress
- [x] Character detail view
- [x] Character switching with persistence
- [x] Dark theme (EVE Online inspired)
- [x] Responsive design

## Configuration

The development server proxies `/api` requests to `http://localhost:8000` (backend).

## Design System

Colors based on EVE Online aesthetic:
- Background: `#0d1117`
- Card: `#161b22`
- Primary (Blue): `#58a6ff`
- Success (Green): `#3fb950`
- Warning (Orange): `#d29922`
- Destructive (Red): `#f85149`
