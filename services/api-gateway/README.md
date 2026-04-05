# API Gateway

Central entry point for EVE Co-Pilot microservices.

## Overview

The API Gateway routes incoming requests to the appropriate microservice, handles CORS, and provides aggregated health checks.

**Port:** 8000

## Features

- **Request Routing** - Routes by path prefix to microservices
- **CORS** - Centralized CORS configuration
- **Health Aggregation** - `/health/services` checks all backends
- **Rate Limiting** - Optional rate limiting middleware (disabled by default)

## Route Configuration

| Path Prefix | Target Service | Port |
|-------------|----------------|------|
| `/api/auth/*` | auth-service | 8001 |
| `/api/war/*` | war-intel-service | 8002 |
| `/api/scheduler/*` | scheduler-service | 8003 |
| `/api/market/*` | market-service | 8004 |
| `/api/production/*` | production-service | 8005 |
| `/api/reactions/*` | production-service | 8005 |
| `/api/shopping/*` | shopping-service | 8006 |
| `/api/character/*` | character-service | 8007 |

## Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /` | Gateway info and service list |
| `GET /health` | Gateway health check |
| `GET /health/services` | Aggregated health of all services |

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SERVICE_NAME` | Service identifier | `eve-api-gateway` |
| `CORS_ORIGINS` | Allowed origins | `*` |
| `AUTH_SERVICE_URL` | Auth service URL | `http://auth-service:8000` |
| `WAR_INTEL_SERVICE_URL` | War intel URL | `http://war-intel-service:8000` |
| `MARKET_SERVICE_URL` | Market service URL | `http://market-service:8000` |
| `PRODUCTION_SERVICE_URL` | Production URL | `http://production-service:8000` |
| `SHOPPING_SERVICE_URL` | Shopping URL | `http://shopping-service:8000` |
| `CHARACTER_SERVICE_URL` | Character URL | `http://character-service:8000` |
| `PROXY_TIMEOUT` | Request timeout (s) | `60.0` |

## Local Development

```bash
cd services/api-gateway
pip install -e ../../eve_shared
pip install -e .
uvicorn app.main:app --reload --port 8000
```
