"""
PI ESI Service for syncing colony data from EVE ESI.

Required scope: esi-planets.manage_planets.v1

ESI Endpoints used:
- GET /characters/{character_id}/planets/ - List colonies
- GET /characters/{character_id}/planets/{planet_id}/ - Colony details
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from app.services.auth_client import AuthClient
from app.services.pi.repository import PIRepository

logger = logging.getLogger(__name__)

ESI_BASE_URL = "https://esi.evetech.net/latest"


class PIESIService:
    """PI ESI Service syncs character colony data from EVE ESI."""

    def __init__(self, repo: PIRepository, auth_client: Optional[AuthClient] = None):
        """Initialize PI ESI Service.

        Args:
            repo: PIRepository for local cache operations
            auth_client: AuthClient for getting access tokens
        """
        self.repo = repo
        self.auth_client = auth_client or AuthClient()
        self.timeout = 30.0

    async def sync_colonies(self, character_id: int) -> Dict[str, Any]:
        """
        Fetch all colonies from ESI and sync to local cache.

        Args:
            character_id: Character ID to sync colonies for

        Returns:
            Dict with sync results (success, colonies_synced, message)
        """
        logger.info(f"Syncing PI colonies for character {character_id}")

        # Get access token from auth service
        access_token = await self.auth_client.get_valid_token_async(character_id)
        if not access_token:
            logger.error(f"No valid token for character {character_id}")
            return {
                "success": False,
                "colonies_synced": 0,
                "message": f"No valid token for character {character_id}",
            }

        headers = {"Authorization": f"Bearer {access_token}"}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Fetch colony list from ESI
                response = await client.get(
                    f"{ESI_BASE_URL}/characters/{character_id}/planets/",
                    headers=headers,
                )

                if response.status_code == 403:
                    return {
                        "success": False,
                        "colonies_synced": 0,
                        "message": "Access forbidden - check ESI scopes",
                    }

                if response.status_code != 200:
                    logger.error(f"ESI error {response.status_code}: {response.text}")
                    return {
                        "success": False,
                        "colonies_synced": 0,
                        "message": f"ESI error: {response.status_code}",
                    }

                colonies_data = response.json()

                if not colonies_data:
                    logger.info(f"No colonies found for character {character_id}")
                    return {
                        "success": True,
                        "colonies_synced": 0,
                        "message": "No colonies found",
                    }

                colonies_synced = 0

                # Process each colony
                for colony in colonies_data:
                    try:
                        planet_id = colony.get("planet_id")
                        if not planet_id:
                            continue

                        # Parse last_update timestamp
                        last_update = self._parse_datetime(colony.get("last_update"))

                        # Upsert colony to cache
                        colony_id = self.repo.upsert_colony(
                            character_id=character_id,
                            planet_id=planet_id,
                            planet_type=colony.get("planet_type", "unknown"),
                            solar_system_id=colony.get("solar_system_id", 0),
                            upgrade_level=colony.get("upgrade_level", 0),
                            num_pins=colony.get("num_pins", 0),
                            last_update=last_update,
                        )

                        # Fetch and sync colony details (pins, routes)
                        await self._sync_colony_details(
                            client, headers, character_id, planet_id, colony_id
                        )
                        colonies_synced += 1

                    except Exception as e:
                        logger.error(f"Error processing colony {colony}: {e}")
                        continue

                logger.info(
                    f"Sync complete for character {character_id}: "
                    f"{colonies_synced} colonies"
                )
                return {
                    "success": True,
                    "colonies_synced": colonies_synced,
                    "message": f"Synced {colonies_synced} colonies",
                }

        except httpx.TimeoutException:
            return {
                "success": False,
                "colonies_synced": 0,
                "message": "ESI request timed out",
            }
        except Exception as e:
            logger.error(f"Sync failed for character {character_id}: {e}")
            return {
                "success": False,
                "colonies_synced": 0,
                "message": str(e),
            }

    async def _sync_colony_details(
        self,
        client: httpx.AsyncClient,
        headers: Dict[str, str],
        character_id: int,
        planet_id: int,
        colony_id: int,
    ) -> None:
        """Fetch and sync colony detail data (pins, links, routes)."""
        try:
            response = await client.get(
                f"{ESI_BASE_URL}/characters/{character_id}/planets/{planet_id}/",
                headers=headers,
            )

            if response.status_code != 200:
                logger.warning(
                    f"Failed to get details for planet {planet_id}: "
                    f"{response.status_code}"
                )
                return

            detail_data = response.json()

            # Process pins
            pins_data = detail_data.get("pins", [])
            processed_pins = []
            for pin in pins_data:
                processed_pin = self._process_pin(pin)
                if processed_pin:
                    processed_pins.append(processed_pin)

            self.repo.upsert_pins(colony_id, processed_pins)

            # Process routes
            routes_data = detail_data.get("routes", [])
            processed_routes = []
            for route in routes_data:
                processed_route = self._process_route(route)
                if processed_route:
                    processed_routes.append(processed_route)

            self.repo.upsert_routes(colony_id, processed_routes)

            logger.debug(
                f"Synced colony {colony_id}: {len(processed_pins)} pins, "
                f"{len(processed_routes)} routes"
            )

        except Exception as e:
            logger.error(f"Error syncing colony details for {planet_id}: {e}")

    def _process_pin(self, pin: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process a pin from ESI response into repository format."""
        pin_id = pin.get("pin_id")
        if not pin_id:
            return None

        # Extract extractor details if present
        extractor_details = pin.get("extractor_details", {})
        product_type_id = extractor_details.get("product_type_id")
        qty_per_cycle = extractor_details.get("qty_per_cycle")
        cycle_time = extractor_details.get("cycle_time")

        # Factory details override
        factory_details = pin.get("factory_details", {})
        if factory_details:
            schematic_id = factory_details.get("schematic_id")
        else:
            schematic_id = pin.get("schematic_id")

        # Contents can also indicate product
        contents = pin.get("contents", [])
        if contents and not product_type_id:
            product_type_id = contents[0].get("type_id")

        return {
            "pin_id": pin_id,
            "type_id": pin.get("type_id"),
            "schematic_id": schematic_id,
            "latitude": pin.get("latitude"),
            "longitude": pin.get("longitude"),
            "install_time": self._parse_datetime(pin.get("install_time")),
            "expiry_time": self._parse_datetime(pin.get("expiry_time")),
            "last_cycle_start": self._parse_datetime(pin.get("last_cycle_start")),
            "product_type_id": product_type_id,
            "qty_per_cycle": qty_per_cycle,
            "cycle_time": cycle_time,
        }

    def _process_route(self, route: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process a route from ESI response into repository format."""
        route_id = route.get("route_id")
        if not route_id:
            return None

        return {
            "route_id": route_id,
            "source_pin_id": route.get("source_pin_id"),
            "destination_pin_id": route.get("destination_pin_id"),
            "content_type_id": route.get("content_type_id"),
            "quantity": route.get("quantity", 0),
        }

    def _parse_datetime(self, dt_str: Optional[str]) -> Optional[datetime]:
        """Parse ISO 8601 datetime string from ESI."""
        if not dt_str:
            return None

        try:
            if dt_str.endswith("Z"):
                dt_str = dt_str[:-1] + "+00:00"
            return datetime.fromisoformat(dt_str)
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to parse datetime '{dt_str}': {e}")
            return None
