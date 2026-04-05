# Shopping Service

Shopping list management and material planning.

## Overview

Manages shopping lists, calculates materials, and plans transport logistics.

**Port:** 8006

## Features

- **Shopping Lists** - Create and manage shopping lists
- **Material Calculation** - Calculate materials for production
- **Regional Comparison** - Compare prices across regions
- **Transport Planning** - Cargo volume and ship recommendations
- **Shopping Wizard** - Guided shopping workflow

## Endpoints

### Lists
| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /api/shopping/lists` | GET | All lists |
| `POST /api/shopping/lists` | POST | Create list |
| `GET /api/shopping/lists/{id}` | GET | List details |
| `DELETE /api/shopping/lists/{id}` | DELETE | Delete list |

### Items
| Endpoint | Method | Description |
|----------|--------|-------------|
| `POST /api/shopping/lists/{id}/items` | POST | Add item |
| `PATCH /api/shopping/items/{id}` | PATCH | Update item |
| `DELETE /api/shopping/items/{id}` | DELETE | Remove item |
| `POST /api/shopping/items/{id}/purchased` | POST | Mark purchased |

### Materials
| Endpoint | Description |
|----------|-------------|
| `POST /api/shopping/items/{id}/calculate-materials` | Calculate materials |
| `POST /api/shopping/items/{id}/apply-materials` | Apply to list |

### Transport
| Endpoint | Description |
|----------|-------------|
| `GET /api/shopping/lists/{id}/cargo-summary` | Cargo requirements |
| `GET /api/shopping/lists/{id}/transport-options` | Ship recommendations |
| `GET /api/shopping/route` | Shopping route |

### Wizard
| Endpoint | Description |
|----------|-------------|
| `POST /api/shopping/wizard/calculate-materials` | Wizard: materials |
| `POST /api/shopping/wizard/compare-regions` | Wizard: compare |

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `POSTGRES_*` | Database connection | Yes |
| `REDIS_URL` | Cache | Yes |
| `MARKET_SERVICE_URL` | Price lookups | `http://market-service:8000` |
| `PRODUCTION_SERVICE_URL` | Material calc | `http://production-service:8000` |

## Database Tables

- `shopping_lists` - List definitions
- `shopping_list_items` - Items in lists

## Local Development

```bash
cd services/shopping-service
pip install -e ../../eve_shared
pip install -e .
uvicorn app.main:app --reload --port 8006
```
