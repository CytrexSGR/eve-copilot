# Market Service

Market data, pricing, and arbitrage calculations.

## Overview

Provides market prices with L1/L2/L3 caching, order data, and arbitrage opportunities.

**Port:** 8004

## Features

- **Price Data** - Regional prices with multi-tier caching
- **L1/L2/L3 Caching** - Redis (5min) → PostgreSQL (1hr) → ESI
- **Order Books** - Buy/sell orders from ESI
- **Arbitrage** - Cross-region arbitrage calculations
- **Price History** - Historical price tracking

## Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/market/stats/{region_id}/{type_id}` | Market statistics |
| `GET /api/market/compare/{type_id}` | Multi-region comparison |
| `GET /api/market/arbitrage/{type_id}` | Arbitrage opportunities |
| `GET /api/market/orders/{region_id}/{type_id}` | Order book |
| `GET /api/market/history/{region_id}/{type_id}` | Price history |
| `POST /api/market/prices/batch` | Batch price lookup |
| `GET /health` | Service health check |

## Caching Strategy

```
Request → L1 Redis (5min TTL)
              ↓ miss
          L2 PostgreSQL (1hr TTL)
              ↓ miss
          L3 ESI API
              ↓
          Write to L1 + L2
```

### Hot Items (Proactive Caching)

56 items refreshed every 4 minutes:
- Minerals (8): Tritanium, Pyerite, Mexallon, etc.
- Isotopes (4): O2, N2, H2, He
- Fuel Blocks (4): All racial types
- Moon Materials (20): R4-R64
- Components (20): T2/T3 materials

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `POSTGRES_*` | Database connection | Yes |
| `REDIS_URL` | L1 cache | Yes |
| `ESI_BASE_URL` | ESI API URL | `https://esi.evetech.net/latest` |
| `ESI_TIMEOUT` | Request timeout (s) | `30` |

## Database Tables

- `market_prices` - Cached regional prices
- `market_prices_cache` - Global adjusted prices

## Local Development

```bash
cd services/market-service
pip install -e ../../eve_shared
pip install -e .
uvicorn app.main:app --reload --port 8004
```
