"""FastAPI middleware for Prometheus metrics."""

import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from eve_shared.metrics import (
    http_requests_total,
    http_request_duration_seconds,
    http_request_size_bytes,
    http_response_size_bytes
)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Automatically track HTTP metrics for all requests."""

    def __init__(self, app, service_name: str):
        super().__init__(app)
        self.service_name = service_name

    async def dispatch(self, request: Request, call_next):
        # Skip metrics endpoint itself
        if request.url.path == "/metrics":
            return await call_next(request)

        # Track request size
        request_size = int(request.headers.get("content-length", 0))
        http_request_size_bytes.labels(
            service=self.service_name,
            method=request.method,
            endpoint=request.url.path
        ).observe(request_size)

        # Track request duration
        start_time = time.time()
        response = await call_next(request)
        duration = time.time() - start_time

        http_request_duration_seconds.labels(
            service=self.service_name,
            method=request.method,
            endpoint=request.url.path
        ).observe(duration)

        # Track request count
        http_requests_total.labels(
            service=self.service_name,
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code
        ).inc()

        # Track response size
        response_size = int(response.headers.get("content-length", 0))
        http_response_size_bytes.labels(
            service=self.service_name,
            method=request.method,
            endpoint=request.url.path
        ).observe(response_size)

        return response
