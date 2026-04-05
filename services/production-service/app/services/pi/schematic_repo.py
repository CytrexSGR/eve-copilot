"""
Schematic/SDE query mixin for PIRepository.

Read-only lookups against EVE SDE tables (planetSchematics, invTypes, invGroups,
mapSolarSystems, mapDenormalize, mapSolarSystemJumps).
"""

from typing import List, Optional, Dict

from app.services.pi.models import (
    PISchematic,
    PISchematicInput,
)


class SchematicMixin:
    """SDE schematic and planet search methods for PIRepository."""

    # PI tier groups in EVE SDE
    TIER_0_INDICATOR = "Raw Resource"  # P0 materials from extractors

    # ==================== Schematic Queries (EVE SDE) ====================

    def get_all_schematics(self, tier: Optional[int] = None) -> List[PISchematic]:
        """
        Get all PI schematics with their inputs.

        Args:
            tier: Optional tier filter (1-4 for P1-P4)

        Returns:
            List of PISchematic objects with inputs populated
        """
        with self.db.cursor() as cur:
            # Fetch all schematics with output info and tier
            cur.execute("""
                SELECT
                    ps."schematicID" as schematic_id,
                    ps."schematicName" as schematic_name,
                    ps."cycleTime" as cycle_time,
                    pst."typeID" as output_type_id,
                    it."typeName" as output_name,
                    pst.quantity as output_quantity,
                    CASE
                        WHEN ig."groupName" LIKE '%%Tier 1%%' OR ig."groupName" LIKE '%%P1%%' THEN 1
                        WHEN ig."groupName" LIKE '%%Tier 2%%' OR ig."groupName" LIKE '%%P2%%' THEN 2
                        WHEN ig."groupName" LIKE '%%Tier 3%%' OR ig."groupName" LIKE '%%P3%%' THEN 3
                        WHEN ig."groupName" LIKE '%%Tier 4%%' OR ig."groupName" LIKE '%%P4%%' THEN 4
                        ELSE 1
                    END as tier
                FROM "planetSchematics" ps
                JOIN "planetSchematicsTypeMap" pst
                    ON ps."schematicID" = pst."schematicID" AND pst."isInput" = 0
                JOIN "invTypes" it ON pst."typeID" = it."typeID"
                JOIN "invGroups" ig ON it."groupID" = ig."groupID"
                ORDER BY tier, ps."schematicName"
            """)
            schematics_data = cur.fetchall()

            if not schematics_data:
                return []

            # Fetch all inputs
            cur.execute("""
                SELECT
                    pst."schematicID" as schematic_id,
                    pst."typeID" as type_id,
                    it."typeName" as type_name,
                    pst.quantity
                FROM "planetSchematicsTypeMap" pst
                JOIN "invTypes" it ON pst."typeID" = it."typeID"
                WHERE pst."isInput" = 1
                ORDER BY pst."schematicID", it."typeName"
            """)
            inputs_data = cur.fetchall()

        # Group inputs by schematic_id
        inputs_by_schematic: Dict[int, List[PISchematicInput]] = {}
        for inp in inputs_data:
            # Support both tuple and dict access patterns
            if isinstance(inp, dict):
                schematic_id = inp['schematic_id']
                type_id = inp['type_id']
                type_name = inp['type_name']
                quantity = inp['quantity']
            else:
                schematic_id = inp[0]
                type_id = inp[1]
                type_name = inp[2]
                quantity = inp[3]

            if schematic_id not in inputs_by_schematic:
                inputs_by_schematic[schematic_id] = []
            inputs_by_schematic[schematic_id].append(PISchematicInput(
                type_id=type_id,
                type_name=type_name,
                quantity=quantity
            ))

        # Build schematic objects
        schematics = []
        for s in schematics_data:
            # Support both tuple and dict access patterns
            if isinstance(s, dict):
                schematic_tier = s['tier']
                schematic_id = s['schematic_id']
                schematic_name = s['schematic_name']
                cycle_time = s['cycle_time']
                output_type_id = s['output_type_id']
                output_name = s['output_name']
                output_quantity = s['output_quantity']
            else:
                schematic_tier = s[6]
                schematic_id = s[0]
                schematic_name = s[1]
                cycle_time = s[2]
                output_type_id = s[3]
                output_name = s[4]
                output_quantity = s[5]

            # Apply tier filter if specified
            if tier is not None and schematic_tier != tier:
                continue

            schematics.append(PISchematic(
                schematic_id=schematic_id,
                schematic_name=schematic_name,
                cycle_time=cycle_time,
                tier=schematic_tier,
                inputs=inputs_by_schematic.get(schematic_id, []),
                output_type_id=output_type_id,
                output_name=output_name,
                output_quantity=output_quantity
            ))

        return schematics

    def get_schematic(self, schematic_id: int) -> Optional[PISchematic]:
        """
        Get a single PI schematic by its ID.

        Args:
            schematic_id: The schematic ID

        Returns:
            PISchematic if found, None otherwise
        """
        with self.db.cursor() as cur:
            # Fetch schematic with output info
            cur.execute("""
                SELECT
                    ps."schematicID" as schematic_id,
                    ps."schematicName" as schematic_name,
                    ps."cycleTime" as cycle_time,
                    pst."typeID" as output_type_id,
                    it."typeName" as output_name,
                    pst.quantity as output_quantity,
                    CASE
                        WHEN ig."groupName" LIKE '%%Tier 1%%' OR ig."groupName" LIKE '%%P1%%' THEN 1
                        WHEN ig."groupName" LIKE '%%Tier 2%%' OR ig."groupName" LIKE '%%P2%%' THEN 2
                        WHEN ig."groupName" LIKE '%%Tier 3%%' OR ig."groupName" LIKE '%%P3%%' THEN 3
                        WHEN ig."groupName" LIKE '%%Tier 4%%' OR ig."groupName" LIKE '%%P4%%' THEN 4
                        ELSE 1
                    END as tier
                FROM "planetSchematics" ps
                JOIN "planetSchematicsTypeMap" pst
                    ON ps."schematicID" = pst."schematicID" AND pst."isInput" = 0
                JOIN "invTypes" it ON pst."typeID" = it."typeID"
                JOIN "invGroups" ig ON it."groupID" = ig."groupID"
                WHERE ps."schematicID" = %s
            """, (schematic_id,))
            schematic_data = cur.fetchone()

            if not schematic_data:
                return None

            # Fetch inputs for this schematic
            cur.execute("""
                SELECT
                    pst."typeID" as type_id,
                    it."typeName" as type_name,
                    pst.quantity
                FROM "planetSchematicsTypeMap" pst
                JOIN "invTypes" it ON pst."typeID" = it."typeID"
                WHERE pst."schematicID" = %s AND pst."isInput" = 1
                ORDER BY it."typeName"
            """, (schematic_id,))
            inputs_data = cur.fetchall()

        # Support both tuple and dict access
        inputs = []
        for inp in inputs_data:
            if isinstance(inp, dict):
                inputs.append(PISchematicInput(
                    type_id=inp['type_id'],
                    type_name=inp['type_name'],
                    quantity=inp['quantity']
                ))
            else:
                inputs.append(PISchematicInput(
                    type_id=inp[0],
                    type_name=inp[1],
                    quantity=inp[2]
                ))

        # Support both tuple and dict access
        if isinstance(schematic_data, dict):
            return PISchematic(
                schematic_id=schematic_data['schematic_id'],
                schematic_name=schematic_data['schematic_name'],
                cycle_time=schematic_data['cycle_time'],
                tier=schematic_data['tier'],
                inputs=inputs,
                output_type_id=schematic_data['output_type_id'],
                output_name=schematic_data['output_name'],
                output_quantity=schematic_data['output_quantity']
            )
        return PISchematic(
            schematic_id=schematic_data[0],
            schematic_name=schematic_data[1],
            cycle_time=schematic_data[2],
            tier=schematic_data[6],
            inputs=inputs,
            output_type_id=schematic_data[3],
            output_name=schematic_data[4],
            output_quantity=schematic_data[5]
        )

    def search_schematics(self, query: str, limit: int = 50) -> List[PISchematic]:
        """
        Search PI schematics by name (schematic name or output name).

        Args:
            query: Search term (case-insensitive partial match)
            limit: Maximum results to return

        Returns:
            List of matching PISchematic objects
        """
        search_pattern = f"%{query}%"

        with self.db.cursor() as cur:
            # Search schematics
            cur.execute("""
                SELECT
                    ps."schematicID" as schematic_id,
                    ps."schematicName" as schematic_name,
                    ps."cycleTime" as cycle_time,
                    pst."typeID" as output_type_id,
                    it."typeName" as output_name,
                    pst.quantity as output_quantity,
                    CASE
                        WHEN ig."groupName" LIKE '%%Tier 1%%' OR ig."groupName" LIKE '%%P1%%' THEN 1
                        WHEN ig."groupName" LIKE '%%Tier 2%%' OR ig."groupName" LIKE '%%P2%%' THEN 2
                        WHEN ig."groupName" LIKE '%%Tier 3%%' OR ig."groupName" LIKE '%%P3%%' THEN 3
                        WHEN ig."groupName" LIKE '%%Tier 4%%' OR ig."groupName" LIKE '%%P4%%' THEN 4
                        ELSE 1
                    END as tier
                FROM "planetSchematics" ps
                JOIN "planetSchematicsTypeMap" pst
                    ON ps."schematicID" = pst."schematicID" AND pst."isInput" = 0
                JOIN "invTypes" it ON pst."typeID" = it."typeID"
                JOIN "invGroups" ig ON it."groupID" = ig."groupID"
                WHERE ps."schematicName" ILIKE %s
                   OR it."typeName" ILIKE %s
                ORDER BY ps."schematicName"
                LIMIT %s
            """, (search_pattern, search_pattern, limit))
            results = cur.fetchall()

            if not results:
                return []

            # Fetch inputs for all matching schematics
            schematic_ids = [r['schematic_id'] for r in results]
            cur.execute("""
                SELECT
                    pst."schematicID" as schematic_id,
                    pst."typeID" as type_id,
                    it."typeName" as type_name,
                    pst.quantity
                FROM "planetSchematicsTypeMap" pst
                JOIN "invTypes" it ON pst."typeID" = it."typeID"
                WHERE pst."schematicID" = ANY(%s) AND pst."isInput" = 1
                ORDER BY pst."schematicID", it."typeName"
            """, (schematic_ids,))
            inputs_data = cur.fetchall()

        # Group inputs by schematic_id
        inputs_by_schematic: Dict[int, List[PISchematicInput]] = {}
        for inp in inputs_data:
            schematic_id = inp['schematic_id']
            if schematic_id not in inputs_by_schematic:
                inputs_by_schematic[schematic_id] = []
            inputs_by_schematic[schematic_id].append(PISchematicInput(
                type_id=inp['type_id'],
                type_name=inp['type_name'],
                quantity=inp['quantity']
            ))

        return [
            PISchematic(
                schematic_id=r['schematic_id'],
                schematic_name=r['schematic_name'],
                cycle_time=r['cycle_time'],
                tier=r['tier'],
                inputs=inputs_by_schematic.get(r['schematic_id'], []),
                output_type_id=r['output_type_id'],
                output_name=r['output_name'],
                output_quantity=r['output_quantity']
            )
            for r in results
        ]

    def get_schematic_for_output(self, type_id: int) -> Optional[PISchematic]:
        """
        Find the PI schematic that produces a given output type.

        Args:
            type_id: The output type ID

        Returns:
            PISchematic if found, None otherwise
        """
        with self.db.cursor() as cur:
            # Find schematic by output type
            cur.execute("""
                SELECT pst."schematicID"
                FROM "planetSchematicsTypeMap" pst
                WHERE pst."typeID" = %s AND pst."isInput" = 0
            """, (type_id,))
            result = cur.fetchone()

        if not result:
            return None

        # Support both tuple and dict
        schematic_id = result['schematicID'] if isinstance(result, dict) else result[0]
        return self.get_schematic(schematic_id)

    def get_item_tier(self, type_id: int) -> int:
        """
        Get the PI tier (0-4) for an item based on its group name.

        Args:
            type_id: The item type ID

        Returns:
            Tier level: 0 (P0 raw), 1-4 (P1-P4 processed)
        """
        with self.db.cursor() as cur:
            cur.execute("""
                SELECT ig."groupName"
                FROM "invTypes" it
                JOIN "invGroups" ig ON it."groupID" = ig."groupID"
                WHERE it."typeID" = %s
            """, (type_id,))
            result = cur.fetchone()

        if not result:
            return 1  # Default to P1 if not found

        # Support both tuple and dict
        group_name = result['groupName'] if isinstance(result, dict) else result[0]

        # P0 raw resources
        if self.TIER_0_INDICATOR in group_name:
            return 0

        # Check for tier indicators in group name
        if 'Tier 1' in group_name or 'P1' in group_name:
            return 1
        if 'Tier 2' in group_name or 'P2' in group_name:
            return 2
        if 'Tier 3' in group_name or 'P3' in group_name:
            return 3
        if 'Tier 4' in group_name or 'P4' in group_name:
            return 4

        return 1  # Default to P1

    # ==================== System Search Queries (EVE SDE) ====================

    def search_systems(
        self,
        region_id: Optional[int] = None,
        min_security: float = 0.5,
        planet_types: Optional[List[str]] = None,
        limit: int = 50
    ) -> List[dict]:
        """Search for systems suitable for PI based on planet types."""
        query = """
        WITH system_planets AS (
            SELECT
                s."solarSystemID",
                s."solarSystemName",
                s."regionID",
                r."regionName",
                s.security,
                ARRAY_AGG(DISTINCT
                    CASE p."typeID"
                        WHEN 11 THEN 'Temperate'
                        WHEN 12 THEN 'Ice'
                        WHEN 13 THEN 'Gas'
                        WHEN 2014 THEN 'Oceanic'
                        WHEN 2015 THEN 'Lava'
                        WHEN 2016 THEN 'Barren'
                        WHEN 2017 THEN 'Storm'
                        WHEN 2063 THEN 'Plasma'
                        ELSE 'Unknown'
                    END
                ) FILTER (WHERE p."typeID" IS NOT NULL) as planet_types,
                COUNT(DISTINCT p."itemID") as planet_count
            FROM "mapSolarSystems" s
            JOIN "mapRegions" r ON s."regionID" = r."regionID"
            LEFT JOIN "mapDenormalize" p ON s."solarSystemID" = p."solarSystemID"
                AND p."groupID" = 7
            WHERE s.security >= %s
        """
        params = [min_security]

        if region_id:
            query += " AND s.\"regionID\" = %s"
            params.append(region_id)

        query += """
            GROUP BY s."solarSystemID", s."solarSystemName", s."regionID", r."regionName", s.security
        )
        SELECT
            "solarSystemID" as system_id,
            "solarSystemName" as system_name,
            "regionID" as region_id,
            "regionName" as region_name,
            security,
            planet_types,
            planet_count
        FROM system_planets
        WHERE planet_count > 0
        """

        if planet_types:
            query += " AND planet_types @> %s::text[]"
            params.append(planet_types)

        query += """
        ORDER BY planet_count DESC, security DESC
        LIMIT %s
        """
        params.append(limit)

        with self.db.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()

        return [
            {
                "system_id": row['system_id'],
                "system_name": row['system_name'],
                "region_id": row['region_id'],
                "region_name": row['region_name'],
                "security": round(float(row['security']), 2),
                "planet_types": row['planet_types'] if row['planet_types'] else [],
                "planet_count": row['planet_count']
            }
            for row in rows
        ]

    # ==================== Planet Search Queries (SDE mapDenormalize) ====================

    def get_system_by_name(self, system_name: str) -> Optional[dict]:
        """
        Get solar system by name.

        Args:
            system_name: Solar system name (e.g., 'Isikemi')

        Returns:
            Dict with system_id, system_name, region_id, security or None
        """
        with self.db.cursor() as cur:
            cur.execute("""
                SELECT "solarSystemID", "solarSystemName", "regionID", security
                FROM "mapSolarSystems"
                WHERE LOWER("solarSystemName") = LOWER(%s)
            """, (system_name,))
            result = cur.fetchone()

        if not result:
            return None

        return {
            "system_id": result['solarSystemID'],
            "system_name": result['solarSystemName'],
            "region_id": result['regionID'],
            "security": round(float(result['security']), 2)
        }

    def get_systems_within_jumps(self, start_system_id: int, max_jumps: int) -> List[dict]:
        """
        Find all systems within N jumps using BFS.

        Args:
            start_system_id: Starting system ID
            max_jumps: Maximum jump distance

        Returns:
            List of dicts with system_id, system_name, security, jumps
        """
        # BFS to find reachable systems
        visited = {start_system_id: 0}  # system_id -> jumps
        queue = [(start_system_id, 0)]

        with self.db.cursor() as cur:
            while queue:
                current_id, current_jumps = queue.pop(0)

                if current_jumps >= max_jumps:
                    continue

                # Get neighbors
                cur.execute("""
                    SELECT "toSolarSystemID"
                    FROM "mapSolarSystemJumps"
                    WHERE "fromSolarSystemID" = %s
                """, (current_id,))
                neighbors = cur.fetchall()

                for neighbor in neighbors:
                    neighbor_id = neighbor['toSolarSystemID']
                    if neighbor_id not in visited:
                        visited[neighbor_id] = current_jumps + 1
                        queue.append((neighbor_id, current_jumps + 1))

            # Get system details for all visited systems
            if not visited:
                return []

            system_ids = list(visited.keys())
            cur.execute("""
                SELECT "solarSystemID", "solarSystemName", "regionID", security
                FROM "mapSolarSystems"
                WHERE "solarSystemID" = ANY(%s)
            """, (system_ids,))
            systems = cur.fetchall()

        return [
            {
                "system_id": s['solarSystemID'],
                "system_name": s['solarSystemName'],
                "region_id": s['regionID'],
                "security": round(float(s['security']), 2),
                "jumps": visited[s['solarSystemID']]
            }
            for s in systems
        ]

    def get_planets_in_systems(
        self,
        system_ids: List[int],
        planet_type: Optional[str] = None
    ) -> List[dict]:
        """
        Get all planets in given systems.

        Args:
            system_ids: List of system IDs to search
            planet_type: Optional filter by type (barren, gas, lava, etc.)

        Returns:
            List of planet dicts with id, name, type, system_id, system_name, security
        """
        if not system_ids:
            return []

        with self.db.cursor() as cur:
            # Planet type IDs from SDE
            planet_type_map = {
                'barren': 2016,
                'gas': 13,
                'ice': 12,
                'lava': 2015,
                'oceanic': 2014,
                'plasma': 2063,
                'storm': 2017,
                'temperate': 11,
            }

            base_query = """
                SELECT
                    d."itemID" as planet_id,
                    d."itemName" as planet_name,
                    t."typeName" as planet_type_full,
                    d."solarSystemID" as system_id,
                    s."solarSystemName" as system_name,
                    s.security,
                    d."celestialIndex" as planet_index
                FROM "mapDenormalize" d
                JOIN "invTypes" t ON d."typeID" = t."typeID"
                JOIN "invGroups" g ON d."groupID" = g."groupID"
                JOIN "mapSolarSystems" s ON d."solarSystemID" = s."solarSystemID"
                WHERE g."groupName" = 'Planet'
                AND d."solarSystemID" = ANY(%s)
            """

            params = [system_ids]

            if planet_type and planet_type in planet_type_map:
                base_query += " AND d.\"typeID\" = %s"
                params.append(planet_type_map[planet_type])

            base_query += " ORDER BY s.\"solarSystemName\", d.\"celestialIndex\""

            cur.execute(base_query, params)
            planets = cur.fetchall()

        # Normalize planet type name
        def normalize_type(full_name: str) -> str:
            # "Planet (Barren)" -> "barren"
            if '(' in full_name and ')' in full_name:
                return full_name.split('(')[1].split(')')[0].lower()
            return full_name.lower()

        return [
            {
                "planet_id": p['planet_id'],
                "planet_name": p['planet_name'],
                "planet_type": normalize_type(p['planet_type_full']),
                "system_id": p['system_id'],
                "system_name": p['system_name'],
                "security": round(float(p['security']), 2),
                "planet_index": p['planet_index']
            }
            for p in planets
            if 'shattered' not in p['planet_type_full'].lower()  # Exclude shattered planets
        ]
