"""
zkillboard Live Stream Service - Docker Container Entry Point

Provides real-time killmail streaming from zkillboard.
"""

import asyncio
import sys
from datetime import datetime
from fastapi import FastAPI
from contextlib import asynccontextmanager

from eve_shared.middleware.metrics import MetricsMiddleware
from eve_shared.metrics_router import metrics_router
from eve_shared.metrics import service_info

# Add paths for imports (matches container structure)
sys.path.insert(0, '/app')
sys.path.insert(0, '/app/services')

# Import the zkillboard live service
from zkillboard.live_service import ZKillboardLiveService


# Global service instance
zkill_service = None
stream_task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start zkillboard stream on startup."""
    global zkill_service, stream_task

    print("Initializing zkillboard service...")
    zkill_service = ZKillboardLiveService()

    print("Starting zkillboard R2Z2 live stream...")
    stream_task = asyncio.create_task(
        zkill_service.listen_r2z2(verbose=True)
    )

    yield

    # Cleanup on shutdown
    print("Stopping zkillboard stream...")
    if zkill_service:
        zkill_service.stop()

    if stream_task:
        stream_task.cancel()
        try:
            await stream_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="EVE Copilot - zkillboard Stream",
    description="Real-time killmail streaming via R2Z2",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(MetricsMiddleware, service_name="eve-zkillboard-service")

# Set service info for Prometheus
service_info.info({
    'service': 'eve-zkillboard-service',
    'version': '1.0.0'
})

app.include_router(metrics_router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    is_running = stream_task and not stream_task.done() if stream_task else False

    return {
        "status": "healthy" if is_running else "degraded",
        "service": "zkillboard-service",
        "timestamp": datetime.utcnow().isoformat(),
        "stream_running": is_running
    }


@app.get("/")
async def root():
    """Service info."""
    is_running = stream_task and not stream_task.done() if stream_task else False

    return {
        "service": "zkillboard-service",
        "version": "1.0.0",
        "description": "Real-time killmail streaming from zkillboard",
        "stream_status": "running" if is_running else "stopped"
    }
