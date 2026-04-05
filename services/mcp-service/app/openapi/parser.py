"""OpenAPI specification parser for microservices."""

from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import httpx
import logging

logger = logging.getLogger(__name__)


class OpenAPIEndpoint(BaseModel):
    """Structured representation of an OpenAPI endpoint."""

    service: str
    method: str
    path: str
    operation_id: str
    summary: str
    description: str
    parameters: List[Dict[str, Any]]
    request_body: Optional[Dict[str, Any]] = None
    responses: Dict[str, Any]
    tags: List[str]


class OpenAPIParser:
    """Fetches and parses OpenAPI specs from microservices."""

    def __init__(self):
        self.specs: Dict[str, Dict] = {}

    async def load_service_spec(self, service_name: str, url: str):
        """
        Fetch OpenAPI spec from a service.

        Args:
            service_name: Service identifier (e.g., "market", "war_intel")
            url: OpenAPI spec URL (e.g., "http://market-service:8000/openapi.json")

        Stores spec in self.specs[service_name]
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                logger.info(f"Fetching OpenAPI spec from {url}")
                response = await client.get(url)
                response.raise_for_status()
                self.specs[service_name] = response.json()
                logger.info(f"Successfully loaded spec for {service_name}")
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch OpenAPI spec for {service_name}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error loading {service_name} spec: {e}")
            raise

    def parse_endpoints(self, service_name: str, mcp_only: bool = False) -> List[OpenAPIEndpoint]:
        """
        Extract all endpoints from a loaded spec.

        Args:
            service_name: Service identifier
            mcp_only: If True, only include /api/mcp/* endpoints

        Returns:
            List of structured OpenAPI endpoints
        """
        spec = self.specs.get(service_name)
        if not spec:
            logger.warning(f"No spec loaded for {service_name}")
            return []

        endpoints = []
        paths = spec.get('paths', {})

        for path, path_item in paths.items():
            # Filter to MCP endpoints only if requested
            if mcp_only and not path.startswith('/api/mcp/'):
                continue

            for method, operation in path_item.items():
                # Only process HTTP methods
                if method.lower() not in ['get', 'post', 'put', 'delete', 'patch']:
                    continue

                try:
                    endpoint = OpenAPIEndpoint(
                        service=service_name,
                        method=method.upper(),
                        path=path,
                        operation_id=operation.get('operationId', ''),
                        summary=operation.get('summary', ''),
                        description=operation.get('description', ''),
                        parameters=operation.get('parameters', []),
                        request_body=operation.get('requestBody'),
                        responses=operation.get('responses', {}),
                        tags=operation.get('tags', [])
                    )
                    endpoints.append(endpoint)
                except Exception as e:
                    logger.warning(f"Failed to parse endpoint {method.upper()} {path}: {e}")
                    continue

        logger.info(f"Parsed {len(endpoints)} endpoints from {service_name} (mcp_only={mcp_only})")
        return endpoints
