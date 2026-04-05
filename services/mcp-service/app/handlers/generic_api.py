"""Generic HTTP handler for dynamic tool execution."""

import httpx
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class GenericAPIHandler:
    """
    Executes API calls based on OpenAPI endpoint metadata.

    Handles:
        - Path parameter replacement: {type_id} → 44992
        - Query parameter separation (GET/DELETE)
        - Body parameter separation (POST/PUT/PATCH)
        - HTTP request execution
        - Error handling and logging
    """

    # Service base URLs
    SERVICE_URLS = {
        'market': 'http://market-service:8000',
        'war_intel': 'http://war-intel-service:8000',
        'production': 'http://production-service:8000',
        'shopping': 'http://shopping-service:8000',
        'character': 'http://character-service:8000',
        'auth': 'http://auth-service:8000',
        'scheduler': 'http://scheduler-service:8000',
        'wormhole': 'http://wormhole-service:8000',
    }

    async def call_endpoint(
        self,
        service: str,
        method: str,
        path: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute API call based on OpenAPI metadata.

        Args:
            service: Service identifier (e.g., "market", "war_intel")
            method: HTTP method (GET, POST, PUT, DELETE, PATCH)
            path: API path template (e.g., "/api/market/price/{type_id}")
            arguments: Tool call arguments (e.g., {"type_id": 44992, "region_id": 10000002})

        Returns:
            API response as dict

        Raises:
            ValueError: If service is unknown
        """
        # Get base URL for service
        base_url = self.SERVICE_URLS.get(service)
        if not base_url:
            error_msg = f"Unknown service: {service}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Build full URL
        url = f"{base_url}{path}"

        # Replace path parameters
        path_params = {}
        for key, value in arguments.items():
            placeholder = f"{{{key}}}"
            if placeholder in path:
                url = url.replace(placeholder, str(value))
                path_params[key] = value

        # Separate query vs body parameters
        query_params = {}
        body_params = {}

        for key, value in arguments.items():
            if key not in path_params:
                if method.upper() in ['GET', 'DELETE']:
                    query_params[key] = value
                else:
                    body_params[key] = value

        # Log request
        logger.info(f"{method} {url}")
        if query_params:
            logger.debug(f"Query params: {query_params}")
        if body_params:
            logger.debug(f"Body params: {body_params}")

        # Execute HTTP request
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                if method.upper() in ['GET', 'DELETE']:
                    response = await client.request(
                        method=method,
                        url=url,
                        params=query_params
                    )
                else:
                    response = await client.request(
                        method=method,
                        url=url,
                        json=body_params
                    )

                response.raise_for_status()
                result = response.json()
                logger.info(f"Success: {method} {url}")
                return result

        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP {e.response.status_code}"
            logger.error(f"{error_msg}: {method} {url}")
            return {
                'error': error_msg,
                'detail': e.response.text
            }

        except httpx.RequestError as e:
            logger.error(f"Request failed: {method} {url} - {e}")
            return {
                'error': 'Request failed',
                'detail': str(e)
            }

        except Exception as e:
            logger.error(f"Unexpected error: {method} {url} - {e}")
            return {
                'error': 'Unexpected error',
                'detail': str(e)
            }
