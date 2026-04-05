"""ESI API client for character data."""
import logging
from typing import Optional, Dict, Any, List

import httpx

from app.config import settings
from eve_shared.integrations.esi.shared_rate_state import shared_rate_state
from eve_shared.integrations.esi.etag_cache import etag_cache

logger = logging.getLogger(__name__)


class ESIClient:
    """Client for EVE ESI API."""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or settings.esi_base_url
        self.timeout = settings.esi_timeout

    def _request(
        self,
        method: str,
        endpoint: str,
        token: Optional[str] = None,
        params: Optional[Dict] = None,
        json_data: Optional[Any] = None
    ) -> Optional[Any]:
        """Make ESI API request.

        Args:
            method: HTTP method
            endpoint: API endpoint
            token: Optional access token for authenticated endpoints
            params: Optional query parameters
            json_data: Optional JSON body data

        Returns:
            Response data or None on error
        """
        # Global safety check
        if shared_rate_state.is_globally_banned() or shared_rate_state.should_hard_stop():
            logger.warning(f"ESI blocked by global rate limit: {endpoint}")
            return None

        url = f"{self.base_url}{endpoint}"
        headers = {}

        if token:
            headers["Authorization"] = f"Bearer {token}"

        # ETag: send If-None-Match for GET requests
        if method == "GET":
            cached_etag = etag_cache.get_etag(endpoint)
            if cached_etag:
                headers["If-None-Match"] = cached_etag

        if params is None:
            params = {}
        params["datasource"] = "tranquility"

        try:
            with httpx.Client(timeout=self.timeout) as client:
                if method == "GET":
                    response = client.get(url, headers=headers, params=params)
                elif method == "POST":
                    response = client.post(
                        url, headers=headers, params=params, json=json_data
                    )
                else:
                    return None

                # Share rate limit state across services
                try:
                    shared_rate_state.update_from_headers(dict(response.headers))
                except Exception:
                    pass

                if response.status_code == 200:
                    data = response.json()
                    # Store ETag if present
                    response_etag = response.headers.get("etag")
                    if response_etag and method == "GET":
                        etag_cache.store(endpoint, response_etag, data)
                    return data
                elif response.status_code == 304:
                    # Return cached data on Not Modified
                    cached = etag_cache.get_cached_data(endpoint)
                    if cached is not None:
                        return cached
                    return None
                elif response.status_code == 420:
                    shared_rate_state.set_global_ban()
                    logger.critical(f"ESI ERROR BANNED (420): {endpoint}")
                    return None
                else:
                    logger.warning(
                        f"ESI request failed: {endpoint} - {response.status_code}"
                    )
                    return None
        except Exception as e:
            logger.error(f"ESI request error: {endpoint} - {e}")
            return None

    # Character endpoints

    def get_wallet(self, character_id: int, token: str) -> Optional[float]:
        """Get character wallet balance."""
        result = self._request(
            "GET", f"/characters/{character_id}/wallet/", token=token
        )
        return result if isinstance(result, (int, float)) else None

    def get_assets(
        self,
        character_id: int,
        token: str,
        page: int = 1
    ) -> List[Dict]:
        """Get character assets."""
        result = self._request(
            "GET",
            f"/characters/{character_id}/assets/",
            token=token,
            params={"page": page}
        )
        return result if isinstance(result, list) else []

    def get_skills(self, character_id: int, token: str) -> Optional[Dict]:
        """Get character skills."""
        return self._request(
            "GET", f"/characters/{character_id}/skills/", token=token
        )

    def get_skillqueue(self, character_id: int, token: str) -> List[Dict]:
        """Get character skill queue."""
        result = self._request(
            "GET", f"/characters/{character_id}/skillqueue/", token=token
        )
        return result if isinstance(result, list) else []

    def get_orders(self, character_id: int, token: str) -> List[Dict]:
        """Get character market orders."""
        result = self._request(
            "GET", f"/characters/{character_id}/orders/", token=token
        )
        return result if isinstance(result, list) else []

    def get_industry_jobs(
        self,
        character_id: int,
        token: str,
        include_completed: bool = False
    ) -> List[Dict]:
        """Get character industry jobs."""
        result = self._request(
            "GET",
            f"/characters/{character_id}/industry/jobs/",
            token=token,
            params={"include_completed": include_completed}
        )
        return result if isinstance(result, list) else []

    def get_blueprints(
        self,
        character_id: int,
        token: str,
        page: int = 1
    ) -> List[Dict]:
        """Get character blueprints."""
        result = self._request(
            "GET",
            f"/characters/{character_id}/blueprints/",
            token=token,
            params={"page": page}
        )
        return result if isinstance(result, list) else []

    def get_location(self, character_id: int, token: str) -> Optional[Dict]:
        """Get character location."""
        return self._request(
            "GET", f"/characters/{character_id}/location/", token=token
        )

    def get_ship(self, character_id: int, token: str) -> Optional[Dict]:
        """Get character ship."""
        return self._request(
            "GET", f"/characters/{character_id}/ship/", token=token
        )

    def get_attributes(self, character_id: int, token: str) -> Optional[Dict]:
        """Get character attributes."""
        return self._request(
            "GET", f"/characters/{character_id}/attributes/", token=token
        )

    def get_implants(self, character_id: int, token: str) -> List[int]:
        """Get character implants."""
        result = self._request(
            "GET", f"/characters/{character_id}/implants/", token=token
        )
        return result if isinstance(result, list) else []

    def get_wallet_journal(
        self,
        character_id: int,
        token: str,
        page: int = 1
    ) -> List[Dict]:
        """Get character wallet journal."""
        result = self._request(
            "GET",
            f"/characters/{character_id}/wallet/journal/",
            token=token,
            params={"page": page}
        )
        return result if isinstance(result, list) else []

    def get_wallet_transactions(
        self,
        character_id: int,
        token: str,
        from_id: Optional[int] = None
    ) -> List[Dict]:
        """Get character wallet transactions."""
        params = {}
        if from_id:
            params["from_id"] = from_id
        result = self._request(
            "GET",
            f"/characters/{character_id}/wallet/transactions/",
            token=token,
            params=params if params else None
        )
        return result if isinstance(result, list) else []

    # Public endpoints

    def get_character_info(self, character_id: int) -> Optional[Dict]:
        """Get public character information."""
        return self._request(
            "GET", f"/characters/{character_id}/"
        )

    def get_character_corporation_history(self, character_id: int) -> List[Dict]:
        """Get character corporation history (public, sorted by start_date desc)."""
        result = self._request(
            "GET", f"/characters/{character_id}/corporationhistory/"
        )
        return result if isinstance(result, list) else []

    def get_character_portrait(self, character_id: int) -> Optional[Dict]:
        """Get character portrait URLs."""
        return self._request(
            "GET", f"/characters/{character_id}/portrait/"
        )

    # Corporation endpoints

    def get_corporation_info(self, corporation_id: int) -> Optional[Dict]:
        """Get public corporation information."""
        return self._request(
            "GET", f"/corporations/{corporation_id}/"
        )

    def get_corporation_wallets(
        self,
        corporation_id: int,
        token: str
    ) -> List[Dict]:
        """Get corporation wallet balances."""
        result = self._request(
            "GET",
            f"/corporations/{corporation_id}/wallets/",
            token=token
        )
        return result if isinstance(result, list) else []

    def get_corporation_orders(
        self,
        corporation_id: int,
        token: str,
        page: int = 1
    ) -> List[Dict]:
        """Get corporation market orders."""
        result = self._request(
            "GET",
            f"/corporations/{corporation_id}/orders/",
            token=token,
            params={"page": page}
        )
        return result if isinstance(result, list) else []

    def get_corporation_transactions(
        self,
        corporation_id: int,
        division: int,
        token: str,
        from_id: Optional[int] = None
    ) -> List[Dict]:
        """Get corporation wallet transactions."""
        params = {}
        if from_id:
            params["from_id"] = from_id
        result = self._request(
            "GET",
            f"/corporations/{corporation_id}/wallets/{division}/transactions/",
            token=token,
            params=params if params else None
        )
        return result if isinstance(result, list) else []

    def get_corporation_journal(
        self,
        corporation_id: int,
        division: int,
        token: str
    ) -> List[Dict]:
        """Get corporation wallet journal."""
        result = self._request(
            "GET",
            f"/corporations/{corporation_id}/wallets/{division}/journal/",
            token=token
        )
        return result if isinstance(result, list) else []
