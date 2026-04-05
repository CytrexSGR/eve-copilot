# Character Service

Character data management, ESI integration, and account aggregation.

## Overview

Provides character data from EVE ESI with L1/L2 caching, fittings management with Dogma engine, SDE browser, and aggregated multi-character account summaries.

**Port:** 8007

## Features

- **Character Data** - Wallet, assets, skills, skillqueue
- **Account Summary** - Aggregated multi-character overview (ISK, SP, locations)
- **Industry** - Jobs, blueprints
- **Location** - Current location, ship
- **Corporation** - Corp wallet, orders, transactions
- **Fittings** - ESI + custom fittings, Dogma engine stats
- **SDE Browser** - Ship/module/charge/drone market tree
- **Caching** - L1 Redis / L2 PostgreSQL caching

## Endpoints

### Character
| Endpoint | Description |
|----------|-------------|
| `GET /api/character/{id}/info` | Character info |
| `GET /api/character/{id}/wallet` | Wallet balance |
| `GET /api/character/{id}/assets` | Character assets |
| `GET /api/character/{id}/skills` | Trained skills |
| `GET /api/character/{id}/skillqueue` | Skill queue |
| `GET /api/character/{id}/orders` | Market orders |
| `GET /api/character/{id}/industry` | Industry jobs |
| `GET /api/character/{id}/blueprints` | Owned blueprints |
| `GET /api/character/{id}/location` | Current location |
| `GET /api/character/{id}/ship` | Current ship |
| `GET /api/character/{id}/attributes` | Attributes |
| `GET /api/character/{id}/implants` | Active implants |

### Wallet
| Endpoint | Description |
|----------|-------------|
| `GET /api/character/{id}/wallet/journal` | Wallet journal |
| `GET /api/character/{id}/wallet/transactions` | Transactions |

### Account Summary (Phase 5)
| Endpoint | Description |
|----------|-------------|
| `GET /api/characters/summary/account` | Aggregated account summary |

**Account Summary Response:**
```json
{
  "account_id": 2,
  "total_isk": 5234567890.50,
  "total_sp": 142000000,
  "characters": [
    {
      "character_id": 1117367444,
      "name": "Cytrex",
      "is_primary": true,
      "isk": 3200000000,
      "sp": 95000000,
      "location": "Jita IV - Moon 4",
      "ship": "Proteus",
      "skill_queue_length": 12,
      "skill_queue_finish": "2026-03-15",
      "token_health": "valid"
    }
  ]
}
```

### Corporation
| Endpoint | Description |
|----------|-------------|
| `GET /api/character/{id}/corporation/info` | Corp info |
| `GET /api/character/{id}/corporation/wallet` | Corp wallets |
| `GET /api/character/{id}/corporation/orders` | Corp orders |
| `GET /api/character/{id}/corporation/transactions` | Corp transactions |
| `GET /api/character/{id}/corporation/journal/{div}` | Corp journal |

### Sync
| Endpoint | Description |
|----------|-------------|
| `POST /api/character/{id}/sync` | Full data sync |
| `GET /api/character/characters` | All characters |

## Cache TTLs

| Data Type | L1 Redis | L2 PostgreSQL |
|-----------|----------|---------------|
| Wallet | 5 min | Sync |
| Assets | 30 min | Sync |
| Skills | 1 hour | Sync |
| Location | 1 min | - |

## Router Structure

```
app/routers/
├── character.py          # 19 endpoints: info, wallet, assets, skills, summary/all
├── corporation.py        # Corp data
├── account_summary.py    # Aggregated multi-char account summary (Phase 5)
├── fittings.py           # ESI fittings, custom CRUD, stats
├── mastery.py            # Ship mastery levels
├── research.py           # Skill recommendations
├── sde_browser.py        # Ships, modules, market tree
├── skill_analysis.py     # Skill gap analysis
├── skill_plans.py        # Skill plan management
├── skills.py             # Skill browser
└── sync.py               # Character ESI sync trigger
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `POSTGRES_*` | Database connection | Yes |
| `REDIS_URL` | L1 cache | Yes |
| `AUTH_SERVICE_URL` | Token management | `http://auth-service:8000` |
| `ESI_BASE_URL` | ESI API | `https://esi.evetech.net/latest` |

## Local Development

```bash
cd services/character-service
pip install -e ../../eve_shared
pip install -e .
uvicorn app.main:app --reload --port 8007
```
