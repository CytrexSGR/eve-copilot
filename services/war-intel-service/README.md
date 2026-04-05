# War Intel Service

Real-time combat intelligence and battle tracking.

## Overview

Processes killmails from zKillboard, detects battles, and provides combat analytics.

**Port:** 8002

## Features

- **Killmail Processing** - Real-time via RedisQ, bulk via EVE Ref
- **Battle Detection** - Automatic battle grouping (30min window)
- **Alliance Intelligence** - Combat statistics and analysis
- **Panoptikum** - Target tracking and sightings
- **Telegram Alerts** - Battle notifications

## Endpoints

### War Room
| Endpoint | Description |
|----------|-------------|
| `GET /api/war/summary` | Regional combat summary |
| `GET /api/war/battles/active` | Active battles |
| `GET /api/war/battle/{id}/kills` | Battle killmails |
| `GET /api/war/battle/{id}/reshipments` | Reshipment analysis |
| `GET /api/war/heatmap` | Galaxy heatmap data |
| `GET /api/war/top-ships` | Most destroyed ships |

### Intelligence
| Endpoint | Description |
|----------|-------------|
| `GET /api/intelligence/alliances` | Available alliances |
| `GET /api/intelligence/{id}` | Alliance reports |
| `GET /api/intelligence/fast/{id}/dashboard` | Fast dashboard |

### Panoptikum
| Endpoint | Description |
|----------|-------------|
| `GET /api/panoptikum/watchlist` | Tracked targets |
| `POST /api/panoptikum/watchlist` | Add target |
| `GET /api/panoptikum/sightings` | Recent sightings |

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ZKILL_REDISQ_URL` | zKillboard RedisQ URL | `https://zkillredisq.stream/listen.php` |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token | - |
| `TELEGRAM_ALERTS_CHANNEL` | Alert channel ID | - |
| `TELEGRAM_ENABLED` | Enable Telegram | `false` |

## Database Tables

- `killmails` - Raw killmail data
- `killmail_items` - Destroyed/dropped items
- `killmail_attackers` - Attacker information
- `battles` - Detected battles
- `battle_participants` - Alliance participation
- `panoptikum_watchlist` - Tracked targets
- `panoptikum_sightings` - Target sightings

## Local Development

```bash
cd services/war-intel-service
pip install -e ../../eve_shared
pip install -e .
uvicorn app.main:app --reload --port 8002
```
