"""
Colony management mixin for PIRepository.

Colony CRUD (ESI sync), character skills, system planets, and
character-level PI queries.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime

from app.services.pi.models import (
    PIColony,
    PIPin,
    PIRoute,
    PIColonyDetail,
)


class ColonyMixin:
    """Colony management, character skills, and system planet methods for PIRepository."""

    # ==================== Colony Queries (pi_* tables) ====================

    def get_colonies(self, character_id: int) -> List[PIColony]:
        """
        Get all PI colonies for a character.

        Args:
            character_id: The character ID

        Returns:
            List of PIColony objects
        """
        with self.db.cursor() as cur:
            cur.execute("""
                SELECT
                    c.id,
                    c.character_id,
                    c.planet_id,
                    c.planet_type,
                    c.solar_system_id,
                    ms."solarSystemName" as solar_system_name,
                    c.upgrade_level,
                    c.num_pins,
                    c.last_update,
                    c.last_sync
                FROM pi_colonies c
                LEFT JOIN "mapSolarSystems" ms ON c.solar_system_id = ms."solarSystemID"
                WHERE c.character_id = %s
                ORDER BY c.planet_id
            """, (character_id,))
            results = cur.fetchall()

        return [
            PIColony(
                id=r['id'],
                character_id=r['character_id'],
                planet_id=r['planet_id'],
                planet_type=r['planet_type'] or 'unknown',
                solar_system_id=r['solar_system_id'],
                solar_system_name=r['solar_system_name'],
                upgrade_level=r['upgrade_level'],
                num_pins=r['num_pins'],
                last_update=r['last_update'],
                last_sync=r['last_sync']
            )
            for r in results
        ]

    def get_colony_detail(self, colony_id: int) -> Optional[PIColonyDetail]:
        """
        Get full colony details including pins and routes.

        Args:
            colony_id: The colony ID

        Returns:
            PIColonyDetail if found, None otherwise
        """
        with self.db.cursor() as cur:
            # Fetch colony
            cur.execute("""
                SELECT
                    c.id,
                    c.character_id,
                    c.planet_id,
                    c.planet_type,
                    c.solar_system_id,
                    ms."solarSystemName" as solar_system_name,
                    c.upgrade_level,
                    c.num_pins,
                    c.last_update,
                    c.last_sync
                FROM pi_colonies c
                LEFT JOIN "mapSolarSystems" ms ON c.solar_system_id = ms."solarSystemID"
                WHERE c.id = %s
            """, (colony_id,))
            colony_data = cur.fetchone()

            if not colony_data:
                return None

            # Fetch pins with type names and schematic info
            cur.execute("""
                SELECT
                    p.pin_id,
                    p.type_id,
                    it."typeName" as type_name,
                    p.schematic_id,
                    ps."schematicName" as schematic_name,
                    p.product_type_id,
                    pit."typeName" as product_name,
                    p.expiry_time,
                    p.qty_per_cycle,
                    p.cycle_time,
                    p.latitude,
                    p.longitude
                FROM pi_pins p
                JOIN "invTypes" it ON p.type_id = it."typeID"
                LEFT JOIN "planetSchematics" ps ON p.schematic_id = ps."schematicID"
                LEFT JOIN "invTypes" pit ON p.product_type_id = pit."typeID"
                WHERE p.colony_id = %s
                ORDER BY p.pin_id
            """, (colony_id,))
            pins_data = cur.fetchall()

            # Fetch routes with content names
            cur.execute("""
                SELECT
                    r.route_id,
                    r.source_pin_id,
                    r.destination_pin_id,
                    r.content_type_id,
                    it."typeName" as content_name,
                    r.quantity
                FROM pi_routes r
                JOIN "invTypes" it ON r.content_type_id = it."typeID"
                WHERE r.colony_id = %s
                ORDER BY r.route_id
            """, (colony_id,))
            routes_data = cur.fetchall()

        colony = PIColony(
            id=colony_data['id'],
            character_id=colony_data['character_id'],
            planet_id=colony_data['planet_id'],
            planet_type=colony_data['planet_type'] or 'unknown',
            solar_system_id=colony_data['solar_system_id'],
            solar_system_name=colony_data['solar_system_name'],
            upgrade_level=colony_data['upgrade_level'],
            num_pins=colony_data['num_pins'],
            last_update=colony_data['last_update'],
            last_sync=colony_data['last_sync']
        )

        pins = [
            PIPin(
                pin_id=p['pin_id'],
                type_id=p['type_id'],
                type_name=p['type_name'],
                schematic_id=p['schematic_id'],
                schematic_name=p['schematic_name'],
                product_type_id=p['product_type_id'],
                product_name=p['product_name'],
                expiry_time=p['expiry_time'],
                qty_per_cycle=p['qty_per_cycle'],
                cycle_time=p['cycle_time'],
                latitude=p['latitude'],
                longitude=p['longitude']
            )
            for p in pins_data
        ]

        routes = [
            PIRoute(
                route_id=r['route_id'],
                source_pin_id=r['source_pin_id'],
                destination_pin_id=r['destination_pin_id'],
                content_type_id=r['content_type_id'],
                content_name=r['content_name'],
                quantity=r['quantity']
            )
            for r in routes_data
        ]

        return PIColonyDetail(
            colony=colony,
            pins=pins,
            routes=routes
        )

    def upsert_colony(
        self,
        character_id: int,
        planet_id: int,
        planet_type: str,
        solar_system_id: int,
        upgrade_level: int,
        num_pins: int,
        last_update: Optional[datetime] = None
    ) -> int:
        """
        Insert or update a PI colony.

        Returns:
            Colony ID (new or existing)
        """
        with self.db.cursor() as cur:
            cur.execute("""
                INSERT INTO pi_colonies (
                    character_id, planet_id, planet_type, solar_system_id,
                    upgrade_level, num_pins, last_update, last_sync
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (character_id, planet_id) DO UPDATE SET
                    planet_type = EXCLUDED.planet_type,
                    solar_system_id = EXCLUDED.solar_system_id,
                    upgrade_level = EXCLUDED.upgrade_level,
                    num_pins = EXCLUDED.num_pins,
                    last_update = EXCLUDED.last_update,
                    last_sync = NOW()
                RETURNING id
            """, (
                character_id, planet_id, planet_type, solar_system_id,
                upgrade_level, num_pins, last_update
            ))
            result = cur.fetchone()

        return result['id']

    def upsert_pins(self, colony_id: int, pins: List[Dict[str, Any]]) -> int:
        """Replace all pins for a colony."""
        if not pins:
            with self.db.cursor() as cur:
                cur.execute("DELETE FROM pi_pins WHERE colony_id = %s", (colony_id,))
            return 0

        with self.db.cursor() as cur:
            cur.execute("DELETE FROM pi_pins WHERE colony_id = %s", (colony_id,))

            for pin in pins:
                cur.execute("""
                    INSERT INTO pi_pins (
                        colony_id, pin_id, type_id, schematic_id,
                        latitude, longitude, install_time, expiry_time,
                        last_cycle_start, product_type_id, qty_per_cycle, cycle_time
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    colony_id,
                    pin.get('pin_id'),
                    pin.get('type_id'),
                    pin.get('schematic_id'),
                    pin.get('latitude'),
                    pin.get('longitude'),
                    pin.get('install_time'),
                    pin.get('expiry_time'),
                    pin.get('last_cycle_start'),
                    pin.get('product_type_id'),
                    pin.get('qty_per_cycle'),
                    pin.get('cycle_time')
                ))

        return len(pins)

    def upsert_routes(self, colony_id: int, routes: List[Dict[str, Any]]) -> int:
        """Replace all routes for a colony."""
        if not routes:
            with self.db.cursor() as cur:
                cur.execute("DELETE FROM pi_routes WHERE colony_id = %s", (colony_id,))
            return 0

        with self.db.cursor() as cur:
            cur.execute("DELETE FROM pi_routes WHERE colony_id = %s", (colony_id,))

            for route in routes:
                cur.execute("""
                    INSERT INTO pi_routes (
                        colony_id, route_id, source_pin_id,
                        destination_pin_id, content_type_id, quantity
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    colony_id,
                    route.get('route_id'),
                    route.get('source_pin_id'),
                    route.get('destination_pin_id'),
                    route.get('content_type_id'),
                    route.get('quantity')
                ))

        return len(routes)

    def delete_colony(self, colony_id: int) -> bool:
        """Delete a colony and all its pins and routes."""
        with self.db.cursor() as cur:
            cur.execute(
                "DELETE FROM pi_colonies WHERE id = %s RETURNING id",
                (colony_id,)
            )
            result = cur.fetchone()

        return result is not None

    def get_colony_by_planet_id(self, planet_id: int) -> Optional[PIColony]:
        """Get a PI colony by its planet ID."""
        with self.db.cursor() as cur:
            cur.execute("""
                SELECT
                    c.id,
                    c.character_id,
                    c.planet_id,
                    c.planet_type,
                    c.solar_system_id,
                    ms."solarSystemName" as solar_system_name,
                    c.upgrade_level,
                    c.num_pins,
                    c.last_update,
                    c.last_sync
                FROM pi_colonies c
                LEFT JOIN "mapSolarSystems" ms ON c.solar_system_id = ms."solarSystemID"
                WHERE c.planet_id = %s
            """, (planet_id,))
            result = cur.fetchone()

        if not result:
            return None

        return PIColony(
            id=result[0],
            character_id=result[1],
            planet_id=result[2],
            planet_type=result[3] or 'unknown',
            solar_system_id=result[4],
            solar_system_name=result[5],
            upgrade_level=result[6],
            num_pins=result[7],
            last_update=result[8],
            last_sync=result[9]
        )

    # ==================== Character Skills Queries ====================

    def get_character_skills(self, character_id: int) -> Optional[dict]:
        """Get cached PI skills for a character."""
        with self.db.cursor() as cur:
            cur.execute("""
                SELECT
                    character_id,
                    interplanetary_consolidation,
                    command_center_upgrades,
                    (1 + interplanetary_consolidation) as max_planets,
                    updated_at
                FROM pi_character_skills
                WHERE character_id = %s
            """, (character_id,))
            result = cur.fetchone()

        if not result:
            return None

        return {
            "character_id": result[0],
            "interplanetary_consolidation": result[1],
            "command_center_upgrades": result[2],
            "max_planets": result[3],
            "updated_at": result[4]
        }

    def upsert_character_skills(
        self,
        character_id: int,
        interplanetary_consolidation: int,
        command_center_upgrades: int
    ) -> None:
        """Insert or update character PI skills."""
        with self.db.cursor() as cur:
            cur.execute("""
                INSERT INTO pi_character_skills (
                    character_id, interplanetary_consolidation,
                    command_center_upgrades, updated_at
                )
                VALUES (%s, %s, %s, NOW())
                ON CONFLICT (character_id) DO UPDATE SET
                    interplanetary_consolidation = EXCLUDED.interplanetary_consolidation,
                    command_center_upgrades = EXCLUDED.command_center_upgrades,
                    updated_at = NOW()
            """, (character_id, interplanetary_consolidation, command_center_upgrades))

    # ==================== System Planets Queries ====================

    def get_system_planets(self, system_id: int) -> List[dict]:
        """Get all planets in a system configured for PI."""
        with self.db.cursor() as cur:
            cur.execute("""
                SELECT planet_id, system_id, system_name, planet_type, planet_index
                FROM pi_system_planets
                WHERE system_id = %s
                ORDER BY planet_index
            """, (system_id,))
            rows = cur.fetchall()

        return [
            {
                "planet_id": r['planet_id'],
                "system_id": r['system_id'],
                "system_name": r['system_name'],
                "planet_type": r['planet_type'],
                "planet_index": r['planet_index']
            }
            for r in rows
        ]

    def get_available_planet_types(self, system_id: int) -> dict:
        """Get planet type counts for a system."""
        with self.db.cursor() as cur:
            cur.execute("""
                SELECT planet_type, COUNT(*) as count
                FROM pi_system_planets
                WHERE system_id = %s
                GROUP BY planet_type
            """, (system_id,))
            rows = cur.fetchall()
        return {r['planet_type']: r['count'] for r in rows}

    def add_system_planets_from_sde(self, system_id: int) -> int:
        """Populate pi_system_planets from EVE SDE mapDenormalize."""
        with self.db.cursor() as cur:
            # Get system name
            cur.execute("""
                SELECT "solarSystemName"
                FROM "mapSolarSystems"
                WHERE "solarSystemID" = %s
            """, (system_id,))
            system_row = cur.fetchone()
            system_name = system_row['solarSystemName'] if system_row else 'Unknown'

            # Get planets from SDE
            cur.execute("""
                SELECT
                    d."itemID" as planet_id,
                    d."typeID",
                    ROW_NUMBER() OVER (ORDER BY d."itemID") as planet_index
                FROM "mapDenormalize" d
                WHERE d."solarSystemID" = %s AND d."groupID" = 7
                ORDER BY d."itemID"
            """, (system_id,))
            planets = cur.fetchall()

            # Map typeID to planet type
            type_map = {
                11: 'temperate', 12: 'ice', 13: 'gas',
                2014: 'oceanic', 2015: 'lava', 2016: 'barren',
                2017: 'storm', 2063: 'plasma'
            }

            count = 0
            for p in planets:
                planet_type = type_map.get(p[1], 'unknown')
                cur.execute("""
                    INSERT INTO pi_system_planets
                        (planet_id, system_id, system_name, planet_type, planet_index)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (planet_id) DO NOTHING
                """, (p[0], system_id, system_name, planet_type, p[2]))
                count += 1

        return count

    def get_all_character_ids_with_pi(self) -> List[int]:
        """Get all character IDs that have PI colonies."""
        with self.db.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT character_id FROM pi_colonies
            """)
            return [row['character_id'] for row in cur.fetchall()]
