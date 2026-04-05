"""EVE-Scout API client for Thera/Turnur wormhole connections."""
import logging
from datetime import datetime
from typing import Optional

import httpx

from app.models.thera import TheraConnection

logger = logging.getLogger(__name__)


# EVE-Scout system IDs
THERA_SYSTEM_ID = 31000005
TURNUR_SYSTEM_ID = 30002086


class EveScoutClient:
    """Client for EVE-Scout API v2."""

    BASE_URL = "https://api.eve-scout.com/v2"
    TIMEOUT = 30.0
    USER_AGENT = "EVE-Copilot/1.0 (github.com/CytrexSGR/Eve-Online-Copilot)"

    def __init__(self):
        """Initialize the EVE-Scout client."""
        self._client: Optional[httpx.Client] = None

    @property
    def client(self) -> httpx.Client:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.BASE_URL,
                timeout=self.TIMEOUT,
                headers={"User-Agent": self.USER_AGENT}
            )
        return self._client

    def close(self):
        """Close HTTP client."""
        if self._client:
            self._client.close()
            self._client = None

    def get_signatures(self) -> list[dict]:
        """
        Fetch all active signatures from EVE-Scout.

        Returns:
            List of raw signature dicts from the API
        """
        try:
            response = self.client.get("/public/signatures")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"EVE-Scout API error: {e}")
            return []

    def get_all_connections(self) -> list[TheraConnection]:
        """
        Get all active Thera and Turnur connections.

        Returns:
            List of TheraConnection objects
        """
        raw_signatures = self.get_signatures()
        connections = []

        for sig in raw_signatures:
            try:
                # Skip incomplete or non-wormhole signatures
                if not sig.get("completed", False):
                    continue
                if sig.get("signature_type") != "wormhole":
                    continue

                connection = TheraConnection(
                    id=str(sig["id"]),
                    wh_type=sig.get("wh_type", "unknown"),
                    max_ship_size=sig.get("max_ship_size", "medium"),
                    remaining_hours=sig.get("remaining_hours", 0),
                    expires_at=datetime.fromisoformat(
                        sig["expires_at"].replace("Z", "+00:00")
                    ),
                    out_system_id=sig["out_system_id"],
                    out_system_name=sig["out_system_name"],
                    out_signature=sig.get("out_signature", ""),
                    in_system_id=sig["in_system_id"],
                    in_system_name=sig["in_system_name"],
                    in_system_class=sig.get("in_system_class", "unknown"),
                    in_region_id=sig.get("in_region_id", 0),
                    in_region_name=sig.get("in_region_name", "Unknown"),
                    in_signature=sig.get("in_signature"),
                    completed=sig.get("completed", True),
                    created_at=datetime.fromisoformat(
                        sig["created_at"].replace("Z", "+00:00")
                    ) if sig.get("created_at") else None,
                    updated_at=datetime.fromisoformat(
                        sig["updated_at"].replace("Z", "+00:00")
                    ) if sig.get("updated_at") else None,
                )
                connections.append(connection)

            except (KeyError, ValueError, TypeError) as e:
                logger.warning(f"Failed to parse signature {sig.get('id')}: {e}")
                continue

        return connections

    def get_thera_connections(self) -> list[TheraConnection]:
        """
        Get only Thera connections (excluding Turnur).

        Returns:
            List of TheraConnection objects from Thera
        """
        all_connections = self.get_all_connections()
        return [c for c in all_connections if c.out_system_id == THERA_SYSTEM_ID]

    def get_turnur_connections(self) -> list[TheraConnection]:
        """
        Get only Turnur connections (excluding Thera).

        Returns:
            List of TheraConnection objects from Turnur
        """
        all_connections = self.get_all_connections()
        return [c for c in all_connections if c.out_system_id == TURNUR_SYSTEM_ID]

    def get_route(self, from_system: str, to_system: str) -> Optional[dict]:
        """
        Get K-Space route from EVE-Scout (direct route, no Thera shortcuts).

        Args:
            from_system: Origin system name
            to_system: Destination system name

        Returns:
            Route dict with jumps and route list, or None on error
        """
        try:
            response = self.client.get(
                "/public/routes",
                params={"from": from_system, "to": to_system}
            )
            response.raise_for_status()
            routes = response.json()
            return routes[0] if routes else None
        except httpx.HTTPError as e:
            logger.error(f"EVE-Scout route error: {e}")
            return None

    def is_healthy(self) -> bool:
        """Check if EVE-Scout API is reachable."""
        try:
            response = self.client.get("/public/signatures")
            return response.status_code == 200
        except Exception:
            return False
