"""Freight pricing calculator."""
import logging
from decimal import Decimal
from typing import Optional, List

logger = logging.getLogger(__name__)


class FreightService:
    """Calculates freight prices and manages route configuration."""

    def __init__(self, db):
        self.db = db

    def list_routes(self, active_only: bool = True) -> list[dict]:
        """List all configured freight routes."""
        with self.db.cursor() as cur:
            if active_only:
                cur.execute("""
                    SELECT fr.*,
                           s1."solarSystemName" as start_name,
                           s2."solarSystemName" as end_name
                    FROM freight_routes fr
                    LEFT JOIN "mapSolarSystems" s1 ON fr.start_system_id = s1."solarSystemID"
                    LEFT JOIN "mapSolarSystems" s2 ON fr.end_system_id = s2."solarSystemID"
                    WHERE fr.is_active = TRUE
                    ORDER BY fr.name
                """)
            else:
                cur.execute("""
                    SELECT fr.*,
                           s1."solarSystemName" as start_name,
                           s2."solarSystemName" as end_name
                    FROM freight_routes fr
                    LEFT JOIN "mapSolarSystems" s1 ON fr.start_system_id = s1."solarSystemID"
                    LEFT JOIN "mapSolarSystems" s2 ON fr.end_system_id = s2."solarSystemID"
                    ORDER BY fr.name
                """)
            return [self._row_to_route(row) for row in cur.fetchall()]

    def get_route(self, route_id: int) -> Optional[dict]:
        """Get a single freight route by ID."""
        with self.db.cursor() as cur:
            cur.execute("""
                SELECT fr.*,
                       s1."solarSystemName" as start_name,
                       s2."solarSystemName" as end_name
                FROM freight_routes fr
                LEFT JOIN "mapSolarSystems" s1 ON fr.start_system_id = s1."solarSystemID"
                LEFT JOIN "mapSolarSystems" s2 ON fr.end_system_id = s2."solarSystemID"
                WHERE fr.id = %s
            """, (route_id,))
            row = cur.fetchone()
            return self._row_to_route(row) if row else None

    def find_routes(
        self, start_system_id: int, end_system_id: int
    ) -> list[dict]:
        """Find matching routes between two systems."""
        with self.db.cursor() as cur:
            cur.execute("""
                SELECT fr.*,
                       s1."solarSystemName" as start_name,
                       s2."solarSystemName" as end_name
                FROM freight_routes fr
                LEFT JOIN "mapSolarSystems" s1 ON fr.start_system_id = s1."solarSystemID"
                LEFT JOIN "mapSolarSystems" s2 ON fr.end_system_id = s2."solarSystemID"
                WHERE fr.start_system_id = %s
                  AND fr.end_system_id = %s
                  AND fr.is_active = TRUE
                ORDER BY fr.base_price
            """, (start_system_id, end_system_id))
            return [self._row_to_route(row) for row in cur.fetchall()]

    def calculate_price(
        self,
        route_id: int,
        volume_m3: float,
        collateral_isk: float,
    ) -> Optional[dict]:
        """Calculate freight price for a shipment.

        Formula: base_price + (volume * rate_per_m3) + (collateral * collateral_pct / 100)
        """
        route = self.get_route(route_id)
        if not route:
            return None

        # Validate constraints
        errors = []
        if route["max_volume"] and volume_m3 > route["max_volume"]:
            errors.append(
                f"Volume {volume_m3:,.0f} m³ exceeds max {route['max_volume']:,.0f} m³"
            )
        if route["max_collateral"] and collateral_isk > route["max_collateral"]:
            errors.append(
                f"Collateral {collateral_isk:,.0f} ISK exceeds max {route['max_collateral']:,.0f} ISK"
            )

        base = Decimal(str(route["base_price"]))
        volume_cost = Decimal(str(volume_m3)) * Decimal(str(route["rate_per_m3"]))
        collateral_cost = (
            Decimal(str(collateral_isk))
            * Decimal(str(route["collateral_pct"]))
            / Decimal("100")
        )
        total = base + volume_cost + collateral_cost

        return {
            "route": route,
            "volume_m3": volume_m3,
            "collateral_isk": collateral_isk,
            "breakdown": {
                "base_price": float(base),
                "volume_cost": float(volume_cost),
                "collateral_cost": float(collateral_cost),
                "total_price": float(total),
            },
            "errors": errors,
            "is_valid": len(errors) == 0,
        }

    def create_route(self, data: dict) -> dict:
        """Create a new freight route."""
        with self.db.cursor() as cur:
            cur.execute("""
                INSERT INTO freight_routes
                    (name, start_system_id, end_system_id, route_type,
                     base_price, rate_per_m3, collateral_pct,
                     max_volume, max_collateral, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                data["name"],
                data["start_system_id"],
                data["end_system_id"],
                data.get("route_type", "jf"),
                data.get("base_price", 0),
                data.get("rate_per_m3", 0),
                data.get("collateral_pct", 1.0),
                data.get("max_volume", 360000),
                data.get("max_collateral", 3000000000),
                data.get("notes"),
            ))
            row = cur.fetchone()
            return self.get_route(row["id"])

    def update_route(self, route_id: int, data: dict) -> Optional[dict]:
        """Update an existing freight route."""
        sets = []
        params = []
        for field in [
            "name", "route_type", "base_price", "rate_per_m3",
            "collateral_pct", "max_volume", "max_collateral",
            "is_active", "notes",
        ]:
            if field in data:
                sets.append(f"{field} = %s")
                params.append(data[field])

        if not sets:
            return self.get_route(route_id)

        sets.append("updated_at = NOW()")
        params.append(route_id)

        with self.db.cursor() as cur:
            cur.execute(
                f"UPDATE freight_routes SET {', '.join(sets)} WHERE id = %s",
                params,
            )
            if cur.rowcount == 0:
                return None
        return self.get_route(route_id)

    def _row_to_route(self, row: dict) -> dict:
        """Convert DB row to route dict."""
        return {
            "id": row["id"],
            "name": row["name"],
            "start_system_id": row["start_system_id"],
            "start_system_name": row.get("start_name"),
            "end_system_id": row["end_system_id"],
            "end_system_name": row.get("end_name"),
            "route_type": row["route_type"],
            "base_price": float(row["base_price"]),
            "rate_per_m3": float(row["rate_per_m3"]),
            "collateral_pct": float(row["collateral_pct"]),
            "max_volume": float(row["max_volume"]) if row["max_volume"] else None,
            "max_collateral": float(row["max_collateral"]) if row["max_collateral"] else None,
            "is_active": row["is_active"],
            "notes": row.get("notes"),
        }
