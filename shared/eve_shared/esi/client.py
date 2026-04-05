"""Shared ESI client with retry logic, ETag caching, and circuit breaker.

Replaces per-service ad-hoc httpx calls with a unified client that all
services share. Integrates with Redis-backed ETag cache, circuit breaker,
and rate limit coordination.

Usage:
    from eve_shared.esi import EsiClient

    client = EsiClient()

    # Simple GET
    data = client.get("/characters/12345/wallet/", token="...")

    # GET with full response (headers included)
    data, headers = client.request("GET", "/characters/12345/assets/",
                                   token="...", params={"page": 1},
                                   return_headers=True)

    # All pages
    from eve_shared.esi.pagination import fetch_all_pages
    all_assets = fetch_all_pages(client.request, "GET",
                                 "/characters/12345/assets/", token="...")
"""

import logging
import random
import time
from typing import Any, Dict, List, Optional, Tuple, Union

import httpx

from eve_shared.esi.circuit_breaker import esi_circuit_breaker
from eve_shared.integrations.esi.etag_cache import etag_cache

logger = logging.getLogger(__name__)

ESI_BASE_URL = "https://esi.evetech.net/latest"
ESI_TIMEOUT = 30.0
DATASOURCE = "tranquility"

# Retry configuration
MAX_RETRIES = 4
RETRY_STATUS_CODES = {502, 503, 504}
NO_RETRY_STATUS_CODES = {400, 401, 403, 404, 420}
RETRY_BACKOFF_BASE = 1.0  # seconds
RETRY_JITTER_MAX = 0.5    # seconds


class EsiError(Exception):
    """ESI API error with status code."""

    def __init__(self, status_code: int, message: str, endpoint: str):
        self.status_code = status_code
        self.endpoint = endpoint
        super().__init__(f"ESI {status_code} on {endpoint}: {message}")


class EsiCircuitOpenError(Exception):
    """Raised when the circuit breaker is open."""

    def __init__(self, blocked_seconds: float):
        self.blocked_seconds = blocked_seconds
        super().__init__(
            f"ESI circuit breaker open, blocked for {blocked_seconds:.0f}s"
        )


class EsiClient:
    """Shared ESI HTTP client with retry, ETag caching, and circuit breaker.

    Thread-safe: creates a new httpx.Client per request (stateless).
    All services should use a single EsiClient instance.
    """

    def __init__(
        self,
        base_url: str = ESI_BASE_URL,
        timeout: float = ESI_TIMEOUT,
        max_retries: int = MAX_RETRIES,
    ):
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries

    def get(
        self,
        endpoint: str,
        token: Optional[str] = None,
        params: Optional[Dict] = None,
    ) -> Optional[Any]:
        """GET request returning parsed JSON data or None on error."""
        return self.request("GET", endpoint, token=token, params=params)

    def post(
        self,
        endpoint: str,
        token: Optional[str] = None,
        params: Optional[Dict] = None,
        json_data: Optional[Any] = None,
    ) -> Optional[Any]:
        """POST request returning parsed JSON data or None on error."""
        return self.request(
            "POST", endpoint, token=token, params=params, json_data=json_data
        )

    def request(
        self,
        method: str,
        endpoint: str,
        token: Optional[str] = None,
        params: Optional[Dict] = None,
        json_data: Optional[Any] = None,
        return_headers: bool = False,
    ) -> Union[Optional[Any], Optional[Tuple[Any, Dict[str, str]]]]:
        """Make an ESI API request with retry logic and caching.

        Args:
            method: HTTP method (GET, POST)
            endpoint: ESI endpoint path (e.g. /characters/12345/wallet/)
            token: Optional Bearer token for authenticated endpoints
            params: Optional query parameters
            json_data: Optional JSON body for POST
            return_headers: If True, return (data, headers) tuple

        Returns:
            Parsed JSON response, or (data, headers) if return_headers=True.
            Returns None on unrecoverable errors.
        """
        # Circuit breaker check
        if esi_circuit_breaker.is_open():
            blocked = esi_circuit_breaker.get_blocked_seconds()
            logger.warning(f"ESI circuit breaker open, skipping {endpoint} ({blocked:.0f}s remaining)")
            if return_headers:
                return None
            return None

        url = f"{self.base_url}{endpoint}"
        params = dict(params) if params else {}
        params["datasource"] = DATASOURCE

        headers: Dict[str, str] = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        # ETag for conditional GET
        if method == "GET":
            cached_etag = etag_cache.get_etag(endpoint)
            if cached_etag:
                headers["If-None-Match"] = cached_etag

        last_error: Optional[Exception] = None

        for attempt in range(self.max_retries):
            if attempt > 0:
                backoff = RETRY_BACKOFF_BASE * (2 ** (attempt - 1))
                jitter = random.uniform(0, RETRY_JITTER_MAX)
                time.sleep(backoff + jitter)

            try:
                with httpx.Client(timeout=self.timeout) as client:
                    if method == "GET":
                        response = client.get(url, headers=headers, params=params)
                    elif method == "POST":
                        response = client.post(
                            url, headers=headers, params=params, json=json_data
                        )
                    else:
                        logger.error(f"Unsupported HTTP method: {method}")
                        return None

                resp_headers = dict(response.headers)

                # Update circuit breaker from response
                esi_circuit_breaker.record_response(resp_headers, response.status_code)

                # 200 OK
                if response.status_code == 200:
                    data = response.json()
                    # Cache ETag
                    resp_etag = response.headers.get("etag")
                    if resp_etag and method == "GET":
                        etag_cache.store(endpoint, resp_etag, data)
                    if return_headers:
                        return data, resp_headers
                    return data

                # 304 Not Modified — return cached data
                if response.status_code == 304:
                    cached = etag_cache.get_cached_data(endpoint)
                    if cached is not None:
                        if return_headers:
                            return cached, resp_headers
                        return cached
                    logger.warning(f"304 but no cached data for {endpoint}")
                    # Remove stale ETag so next request fetches fresh
                    headers.pop("If-None-Match", None)
                    continue

                # 420 Enhance Your Calm — global ban
                if response.status_code == 420:
                    logger.critical(f"ESI 420 on {endpoint}")
                    return None

                # Non-retryable errors
                if response.status_code in NO_RETRY_STATUS_CODES:
                    logger.warning(
                        f"ESI {response.status_code} on {endpoint} (non-retryable)"
                    )
                    return None

                # Retryable server errors
                if response.status_code in RETRY_STATUS_CODES:
                    logger.warning(
                        f"ESI {response.status_code} on {endpoint} "
                        f"(attempt {attempt + 1}/{self.max_retries})"
                    )
                    last_error = EsiError(
                        response.status_code, response.text[:200], endpoint
                    )
                    continue

                # Other status codes — don't retry
                logger.warning(f"ESI {response.status_code} on {endpoint}")
                return None

            except (httpx.ConnectError, httpx.TimeoutException) as e:
                logger.warning(
                    f"ESI connection error on {endpoint}: {e} "
                    f"(attempt {attempt + 1}/{self.max_retries})"
                )
                last_error = e
                continue

            except Exception as e:
                logger.error(f"Unexpected ESI error on {endpoint}: {e}")
                return None

        # All retries exhausted
        logger.error(
            f"ESI request failed after {self.max_retries} attempts: {endpoint}"
        )
        return None
