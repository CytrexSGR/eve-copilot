"""Metrics endpoint router for FastAPI services."""

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse
from prometheus_client import REGISTRY, generate_latest

metrics_router = APIRouter(tags=["Metrics"])


@metrics_router.get("/metrics", response_class=PlainTextResponse)
def metrics():
    """Expose Prometheus metrics."""
    return generate_latest(REGISTRY)
