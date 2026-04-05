# Production Service

Manufacturing calculations and production planning.

## Overview

Calculates production costs, analyzes production chains, and manages manufacturing workflows.

**Port:** 8005

## Features

- **Cost Calculation** - Manufacturing cost with ME/TE bonuses
- **Production Chains** - Full material tree analysis
- **Economic Analysis** - Profitability and ROI calculations
- **Reactions** - T2 reaction profitability
- **Tax/Facility Profiles** - Custom tax and facility configurations
- **Planetary Industry** - PI advisor, chain browser, empire analysis, multi-character management

## Endpoints

### Production
| Endpoint | Description |
|----------|-------------|
| `GET /api/production/cost/{type_id}` | Production cost |
| `GET /api/production/optimize/{type_id}` | Regional optimization |
| `POST /api/production/cost` | Batch cost calculation |

### Chains
| Endpoint | Description |
|----------|-------------|
| `GET /api/production/chains/{type_id}` | Full production tree |
| `GET /api/production/chains/{type_id}/materials` | All materials needed |
| `GET /api/production/chains/{type_id}/direct` | Direct materials only |

### Economics
| Endpoint | Description |
|----------|-------------|
| `GET /api/production/economics/opportunities` | Profitable items |
| `GET /api/production/economics/{type_id}` | Item economics |

### Reactions
| Endpoint | Description |
|----------|-------------|
| `GET /api/reactions` | List all reactions |
| `GET /api/reactions/{id}/profitability` | Reaction profit |
| `GET /api/reactions/profitable` | Top profitable reactions |

### Tax/Facility
| Endpoint | Description |
|----------|-------------|
| `GET /api/production/tax-profiles` | Tax profiles |
| `GET /api/production/facilities` | Facility profiles |

### Planetary Industry (PI)
| Endpoint | Description |
|----------|-------------|
| `GET /api/pi/formulas` | PI schematics (P0→P4 recipes) |
| `GET /api/pi/opportunities` | Profitable PI products |
| `GET /api/pi/empire/analysis` | Multi-character empire analysis (P4 feasibility, production map) |
| `GET /api/pi/empire/plans` | Empire production plans |
| `POST /api/pi/empire/plans` | Create empire plan |
| `GET /api/pi/multi-character/detail` | Multi-character PI colony detail |
| `GET /api/pi/advisor/recommendations` | PI product recommendations |
| `GET /api/pi/chain-planner/plans` | Chain planner plans |
| `GET /api/pi/alerts` | PI extractor alerts |

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `POSTGRES_*` | Database connection | Yes |
| `REDIS_URL` | Cache | Yes |
| `MARKET_SERVICE_URL` | Market service | `http://market-service:8000` |
| `AUTH_SERVICE_URL` | Auth service (token management) | `http://eve-auth-service:8000` |

## Database Tables

- `tax_profiles` - Player tax configurations
- `facility_profiles` - Facility bonuses
- `reaction_formulas` - Reaction definitions
- `production_ledger` - Production projects
- `pi_schematics` - PI production schematics (P0→P4)
- `pi_colonies` - Character PI colonies (planets, extractors, factories)
- `pi_empire_plans` - Empire-level PI production plans

## Local Development

```bash
cd services/production-service
pip install -e ../../eve_shared
pip install -e .
uvicorn app.main:app --reload --port 8005
```
