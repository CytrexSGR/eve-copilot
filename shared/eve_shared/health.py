"""Health check endpoints for all services."""

from fastapi import APIRouter, Response
from pydantic import BaseModel
from typing import Dict
from datetime import datetime, timezone

from eve_shared.database import get_db
from eve_shared.redis_client import get_redis
from eve_shared.config import get_config


class HealthStatus(BaseModel):
    """Health check response model."""
    status: str  # healthy, degraded, unhealthy
    service: str
    version: str
    timestamp: str
    checks: Dict[str, Dict]


health_router = APIRouter(tags=["Health"])


@health_router.get("/health", response_model=HealthStatus)
async def health_check() -> HealthStatus:
    """Comprehensive health check endpoint."""
    config = get_config()
    checks = {}
    overall_status = "healthy"

    # Database check
    try:
        db = get_db()
        with db.cursor() as cur:
            cur.execute("SELECT 1")
        checks["database"] = {"status": "healthy", "latency_ms": 0}
    except Exception as e:
        checks["database"] = {"status": "unhealthy", "error": str(e)}
        overall_status = "unhealthy"

    # Redis check
    try:
        redis_client = get_redis()
        redis_client.client.ping()
        checks["redis"] = {"status": "healthy"}
    except Exception as e:
        checks["redis"] = {"status": "unhealthy", "error": str(e)}
        if overall_status == "healthy":
            overall_status = "degraded"

    return HealthStatus(
        status=overall_status,
        service=config.service_name,
        version=config.service_version,
        timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        checks=checks
    )


@health_router.get("/ready")
async def readiness_check(response: Response):
    """Kubernetes readiness probe."""
    try:
        db = get_db()
        with db.cursor() as cur:
            cur.execute("SELECT 1")
        return {"ready": True}
    except Exception:
        response.status_code = 503
        return {"ready": False}


@health_router.get("/live")
async def liveness_check():
    """Kubernetes liveness probe."""
    return {"alive": True}
