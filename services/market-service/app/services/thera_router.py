"""Thera hybrid route calculator."""
import logging
from datetime import datetime, timezone
from typing import Optional

from app.models.thera import (
    TheraConnection,
    TheraRoute,
    TheraRouteSegment,
    RouteSavings,
    SystemInfo,
    TheraStatus,
)
from app.services.thera_client import EveScoutClient, THERA_SYSTEM_ID, TURNUR_SYSTEM_ID
from app.services.thera_cache import TheraCache

logger = logging.getLogger(__name__)

# Average time per jump in minutes (including align/warp)
MINUTES_PER_JUMP = 0.5


class TheraRouter:
    """Hybrid route calculator using Thera shortcuts."""

    def __init__(self, cache: TheraCache, client: EveScoutClient):
        """
        Initialize router.

        Args:
            cache: TheraCache for caching connections
            client: EveScoutClient for API calls
        """
        self.cache = cache
        self.client = client

    def _get_connections(self, force_refresh: bool = False) -> list[TheraConnection]:
        """
        Get Thera connections, using cache if available.

        Args:
            force_refresh: Force fetch from API

        Returns:
            List of active TheraConnection objects
        """
        if not force_refresh:
            cached = self.cache.get_connections()
            if cached is not None:
                # Filter out expired connections
                now = datetime.now(timezone.utc)
                return [c for c in cached if c.expires_at > now]

        # Fetch from EVE-Scout
        connections = self.client.get_all_connections()

        # Cache the results
        if connections:
            self.cache.set_connections(connections)

        return connections

    def _filter_by_ship_size(
        self,
        connections: list[TheraConnection],
        ship_size: str
    ) -> list[TheraConnection]:
        """Filter connections by ship size capability."""
        return [c for c in connections if c.supports_ship_size(ship_size)]

    def _filter_by_hub(
        self,
        connections: list[TheraConnection],
        hub: str = "thera"
    ) -> list[TheraConnection]:
        """Filter connections by hub type."""
        if hub == "thera":
            return [c for c in connections if c.out_system_id == THERA_SYSTEM_ID]
        elif hub == "turnur":
            return [c for c in connections if c.out_system_id == TURNUR_SYSTEM_ID]
        return connections  # "all"

    def _get_direct_route(
        self,
        from_system: str,
        to_system: str
    ) -> Optional[dict]:
        """Get direct K-Space route from EVE-Scout."""
        return self.client.get_route(from_system, to_system)

    def _calculate_thera_route(
        self,
        from_system: str,
        to_system: str,
        connections: list[TheraConnection],
        ship_size: str = "large"
    ) -> Optional[TheraRouteSegment]:
        """
        Calculate best Thera route if beneficial.

        This finds the best entry and exit wormhole combination.

        Args:
            from_system: Origin system name
            to_system: Destination system name
            connections: Available Thera connections
            ship_size: Required ship size

        Returns:
            TheraRouteSegment if beneficial route found, None otherwise
        """
        # Filter connections by ship size
        valid_connections = self._filter_by_ship_size(connections, ship_size)

        if not valid_connections:
            logger.info(f"No connections available for ship size: {ship_size}")
            return None

        # Get routes from origin to each entry point
        # Get routes from each exit point to destination
        best_route = None
        best_total = float('inf')

        for entry in valid_connections:
            # Get jumps from origin to entry WH destination system
            entry_route = self._get_direct_route(from_system, entry.in_system_name)
            if not entry_route:
                continue
            entry_jumps = entry_route.get("jumps", 999)

            for exit_wh in valid_connections:
                # Skip if same connection (need different entry/exit)
                if entry.id == exit_wh.id:
                    continue

                # Get jumps from exit WH destination to final destination
                exit_route = self._get_direct_route(exit_wh.in_system_name, to_system)
                if not exit_route:
                    continue
                exit_jumps = exit_route.get("jumps", 999)

                # Total: entry_jumps + 1 (through Thera) + exit_jumps
                total_jumps = entry_jumps + 1 + exit_jumps

                if total_jumps < best_total:
                    best_total = total_jumps
                    best_route = TheraRouteSegment(
                        entry_connection=entry,
                        exit_connection=exit_wh,
                        entry_jumps=entry_jumps,
                        exit_jumps=exit_jumps,
                        total_jumps=total_jumps,
                    )

        return best_route

    def find_route(
        self,
        from_system: str,
        to_system: str,
        ship_size: str = "large",
        hub: str = "thera"
    ) -> TheraRoute:
        """
        Find optimal route, comparing direct vs Thera.

        Args:
            from_system: Origin system name
            to_system: Destination system name
            ship_size: Required ship size (medium, large, xlarge, capital)
            hub: Hub to use (thera, turnur, all)

        Returns:
            TheraRoute with comparison and recommendation
        """
        # Get direct route
        direct_route = self._get_direct_route(from_system, to_system)
        direct_jumps = direct_route.get("jumps", 0) if direct_route else 0

        # Build origin/destination info
        origin = SystemInfo(
            system_id=direct_route["route"][0]["system_id"] if direct_route and direct_route.get("route") else 0,
            system_name=from_system,
            region_name=direct_route["route"][0].get("region_name") if direct_route and direct_route.get("route") else None,
            security_class=direct_route["route"][0].get("system_class") if direct_route and direct_route.get("route") else None,
        )

        destination = SystemInfo(
            system_id=direct_route["route"][-1]["system_id"] if direct_route and direct_route.get("route") else 0,
            system_name=to_system,
            region_name=direct_route["route"][-1].get("region_name") if direct_route and direct_route.get("route") else None,
            security_class=direct_route["route"][-1].get("system_class") if direct_route and direct_route.get("route") else None,
        )

        # Get and filter Thera connections
        connections = self._get_connections()
        connections = self._filter_by_hub(connections, hub)

        # Calculate Thera route
        thera_segment = None
        if connections and direct_jumps > 10:  # Only check Thera for longer routes
            thera_segment = self._calculate_thera_route(
                from_system, to_system, connections, ship_size
            )

        # Calculate savings
        if thera_segment:
            jumps_saved = direct_jumps - thera_segment.total_jumps
            percentage = (jumps_saved / direct_jumps * 100) if direct_jumps > 0 else 0
            time_saved = jumps_saved * MINUTES_PER_JUMP
        else:
            jumps_saved = 0
            percentage = 0
            time_saved = 0

        savings = RouteSavings(
            jumps_saved=jumps_saved,
            percentage=round(percentage, 1),
            estimated_time_saved_minutes=round(time_saved, 1) if time_saved > 0 else None,
        )

        # Determine recommendation
        # Recommend Thera if it saves at least 10 jumps or 20% of the route
        recommended = "direct"
        if thera_segment and (jumps_saved >= 10 or percentage >= 20):
            recommended = "thera"

        return TheraRoute(
            origin=origin,
            destination=destination,
            direct_jumps=direct_jumps,
            thera_route=thera_segment,
            savings=savings,
            recommended=recommended,
        )

    def get_connections(
        self,
        hub: str = "thera",
        ship_size: Optional[str] = None
    ) -> list[TheraConnection]:
        """
        Get active connections for a hub.

        Args:
            hub: Hub type (thera, turnur, all)
            ship_size: Optional ship size filter

        Returns:
            List of active connections
        """
        connections = self._get_connections()
        connections = self._filter_by_hub(connections, hub)

        if ship_size:
            connections = self._filter_by_ship_size(connections, ship_size)

        # Sort by remaining hours (longest-lived first)
        connections.sort(key=lambda c: c.remaining_hours, reverse=True)

        return connections

    def get_status(self) -> TheraStatus:
        """Get Thera service status."""
        connections = self._get_connections()

        thera_count = len([c for c in connections if c.out_system_id == THERA_SYSTEM_ID])
        turnur_count = len([c for c in connections if c.out_system_id == TURNUR_SYSTEM_ID])

        return TheraStatus(
            status="healthy" if connections else "degraded",
            thera_connections=thera_count,
            turnur_connections=turnur_count,
            cache_age_seconds=self.cache.get_cache_age_seconds(),
            last_fetch=self.cache.get_last_fetch(),
            eve_scout_reachable=self.client.is_healthy(),
        )
