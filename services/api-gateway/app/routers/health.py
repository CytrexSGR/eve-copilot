"""Health check router with service aggregation."""
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any

import httpx
from fastapi import APIRouter

from app.settings import SERVICES, settings

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Health"])


async def check_service_health(
    client: httpx.AsyncClient,
    name: str,
    url: str
) -> Dict[str, Any]:
    """Check health of a single service."""
    try:
        response = await client.get(f"{url}/health", timeout=5.0)
        if response.status_code == 200:
            return {
                "name": name,
                "status": "healthy",
                "url": url,
                "response_time_ms": response.elapsed.total_seconds() * 1000,
            }
        else:
            return {
                "name": name,
                "status": "unhealthy",
                "url": url,
                "error": f"HTTP {response.status_code}",
            }
    except httpx.TimeoutException:
        return {
            "name": name,
            "status": "unhealthy",
            "url": url,
            "error": "timeout",
        }
    except httpx.ConnectError:
        return {
            "name": name,
            "status": "unhealthy",
            "url": url,
            "error": "connection refused",
        }
    except Exception as e:
        return {
            "name": name,
            "status": "unhealthy",
            "url": url,
            "error": str(e),
        }


@router.get("/health")
def health_check():
    """Basic health check for the gateway itself."""
    return {
        "status": "healthy",
        "service": settings.service_name,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/health/services")
async def aggregated_health_check():
    """Aggregated health check for all microservices."""
    async with httpx.AsyncClient() as client:
        # Check all services in parallel
        tasks = [
            check_service_health(client, name, url)
            for name, url in SERVICES.items()
        ]
        results = await asyncio.gather(*tasks)

    # Calculate overall status
    healthy_count = sum(1 for r in results if r["status"] == "healthy")
    total_count = len(results)

    if healthy_count == total_count:
        overall_status = "healthy"
    elif healthy_count > 0:
        overall_status = "degraded"
    else:
        overall_status = "unhealthy"

    return {
        "status": overall_status,
        "gateway": settings.service_name,
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "healthy": healthy_count,
            "total": total_count,
        },
        "details": results,
    }


@router.get("/")
def root():
    """API Gateway info and available services."""
    return {
        "name": "EVE Co-Pilot API Gateway",
        "version": "1.0.0",
        "status": "online",
        "services": {
            "auth": "/api/auth/*",
            "war-intel": "/api/war/*",
            "scheduler": "/api/scheduler/*",
            "market": "/api/market/*",
            "production": "/api/production/*, /api/reactions/*",
            "shopping": "/api/shopping/*",
            "character": "/api/character/*",
        },
        "health": {
            "gateway": "/health",
            "all_services": "/health/services",
            "esi": "/health/esi",
        },
    }


@router.get("/health/esi")
async def esi_health():
    """Quick ESI health check -- returns server status and player count."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get("https://esi.evetech.net/latest/status/")
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "status": "online",
                    "players": data.get("players", 0),
                    "server_version": data.get("server_version", ""),
                    "start_time": data.get("start_time", ""),
                }
            return {"status": "offline", "players": 0, "error": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"status": "offline", "players": 0, "error": str(e)}
