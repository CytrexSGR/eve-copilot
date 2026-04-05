"""HTTP Proxy middleware for routing requests to microservices."""
import logging
from typing import Optional
from urllib.parse import urljoin

import httpx
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import StreamingResponse

from app.settings import SERVICE_ROUTES, settings

logger = logging.getLogger(__name__)


class ProxyMiddleware(BaseHTTPMiddleware):
    """Middleware that proxies requests to appropriate microservices."""

    def __init__(self, app):
        super().__init__(app)
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(settings.proxy_timeout),
            limits=httpx.Limits(max_connections=settings.proxy_max_connections),
            follow_redirects=False,
        )

    async def dispatch(self, request: Request, call_next):
        """Route request to microservice or pass to local handlers."""
        path = request.url.path

        # Find matching service route
        target_url = self._get_target_url(path)

        if target_url:
            # Proxy to microservice
            return await self._proxy_request(request, target_url, path)
        else:
            # Handle locally
            return await call_next(request)

    def _get_target_url(self, path: str) -> Optional[str]:
        """Find the target service URL for a path."""
        for prefix, service_url in SERVICE_ROUTES.items():
            if path.startswith(prefix):
                return service_url
        return None

    async def _proxy_request(
        self, request: Request, service_url: str, path: str
    ) -> Response:
        """Proxy a request to a microservice."""
        # Build target URL
        target_url = urljoin(service_url, path)
        if request.url.query:
            target_url = f"{target_url}?{request.url.query}"

        logger.debug(f"Proxying {request.method} {path} -> {target_url}")

        # Prepare headers (exclude hop-by-hop headers)
        headers = dict(request.headers)
        hop_by_hop = {
            "connection", "keep-alive", "proxy-authenticate",
            "proxy-authorization", "te", "trailers", "transfer-encoding",
            "upgrade", "host"
        }
        headers = {k: v for k, v in headers.items() if k.lower() not in hop_by_hop}

        # Strip client-supplied X-Character-Id — only allow gateway-validated value
        headers.pop("x-character-id", None)
        headers.pop("X-Character-Id", None)

        # Add forwarding headers
        headers["X-Forwarded-For"] = request.client.host if request.client else "unknown"
        headers["X-Forwarded-Proto"] = request.url.scheme
        headers["X-Forwarded-Host"] = request.url.netloc

        # Forward validated character context
        if hasattr(request.state, "character_id"):
            headers["X-Character-Id"] = str(request.state.character_id)

        try:
            # Get request body
            body = await request.body()

            # Make proxy request
            response = await self.client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body,
            )

            # Build response headers (exclude hop-by-hop)
            response_headers = {
                k: v for k, v in response.headers.items()
                if k.lower() not in hop_by_hop and k.lower() != "content-encoding"
            }

            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=response_headers,
                media_type=response.headers.get("content-type"),
            )

        except httpx.TimeoutException:
            logger.error(f"Timeout proxying to {target_url}")
            return Response(
                content='{"detail": "Service timeout"}',
                status_code=504,
                media_type="application/json",
            )
        except httpx.ConnectError:
            logger.error(f"Connection error proxying to {target_url}")
            return Response(
                content='{"detail": "Service unavailable"}',
                status_code=503,
                media_type="application/json",
            )
        except Exception as e:
            logger.error(f"Proxy error for {path}: {e}")
            return Response(
                content='{"detail": "Bad gateway"}',
                status_code=502,
                media_type="application/json",
            )
