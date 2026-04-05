"""
Project management mixin for PIRepository.

Project CRUD, colony assignments, material assignments, and
SOLL planning methods.
"""

from typing import List, Optional, Dict


class ProjectMixin:
    """Project CRUD, assignments, and SOLL planning methods for PIRepository."""

    # ==================== Project Queries ====================

    def create_project(
        self,
        character_id: int,
        name: str,
        strategy: str,
        target_product_type_id: Optional[int] = None,
        target_profit_per_hour: Optional[float] = None
    ) -> int:
        """Create a new PI project."""
        with self.db.cursor() as cur:
            cur.execute("""
                INSERT INTO pi_projects (
                    character_id, name, strategy,
                    target_product_type_id, target_profit_per_hour
                )
                VALUES (%s, %s, %s, %s, %s)
                RETURNING project_id
            """, (character_id, name, strategy, target_product_type_id, target_profit_per_hour))
            result = cur.fetchone()
        return result['project_id']

    def get_project(self, project_id: int) -> Optional[dict]:
        """Get a project by ID."""
        with self.db.cursor() as cur:
            cur.execute("""
                SELECT p.*, it."typeName" as target_product_name
                FROM pi_projects p
                LEFT JOIN "invTypes" it ON p.target_product_type_id = it."typeID"
                WHERE p.project_id = %s
            """, (project_id,))
            row = cur.fetchone()

        if not row:
            return None

        return dict(row)

    def get_projects_by_character(self, character_id: int, status: Optional[str] = None) -> List[dict]:
        """Get all projects for a character with computed fields."""
        with self.db.cursor() as cur:
            base_query = """
                SELECT
                    p.*,
                    it."typeName" as target_product_name,
                    c.character_name,
                    CASE
                        WHEN ig."groupName" LIKE '%%Tier 4%%' OR ig."groupName" LIKE '%%P4%%' THEN 4
                        WHEN ig."groupName" LIKE '%%Tier 3%%' OR ig."groupName" LIKE '%%P3%%' THEN 3
                        WHEN ig."groupName" LIKE '%%Tier 2%%' OR ig."groupName" LIKE '%%P2%%' THEN 2
                        WHEN ig."groupName" LIKE '%%Tier 1%%' OR ig."groupName" LIKE '%%P1%%' THEN 1
                        ELSE 0
                    END as target_tier,
                    COALESCE(a.assigned_count, 0) as assigned_count,
                    COALESCE(a.total_materials, 0) as total_materials
                FROM pi_projects p
                LEFT JOIN "invTypes" it ON p.target_product_type_id = it."typeID"
                LEFT JOIN "invGroups" ig ON it."groupID" = ig."groupID"
                LEFT JOIN characters c ON c.character_id = p.character_id
                LEFT JOIN (
                    SELECT project_id,
                           COUNT(*) as total_materials,
                           COUNT(colony_id) as assigned_count
                    FROM pi_material_assignments
                    GROUP BY project_id
                ) a ON a.project_id = p.project_id
                WHERE p.character_id = %s
            """
            if status:
                cur.execute(base_query + " AND p.status = %s ORDER BY p.updated_at DESC", (character_id, status))
            else:
                cur.execute(base_query + " ORDER BY p.updated_at DESC", (character_id,))
            rows = cur.fetchall()

        return [dict(row) for row in rows]

    def get_all_projects(self, status: Optional[str] = None) -> List[dict]:
        """Get all projects across all characters with computed fields."""
        with self.db.cursor() as cur:
            base_query = """
                SELECT
                    p.*,
                    it."typeName" as target_product_name,
                    c.character_name,
                    CASE
                        WHEN ig."groupName" LIKE '%%Tier 4%%' OR ig."groupName" LIKE '%%P4%%' THEN 4
                        WHEN ig."groupName" LIKE '%%Tier 3%%' OR ig."groupName" LIKE '%%P3%%' THEN 3
                        WHEN ig."groupName" LIKE '%%Tier 2%%' OR ig."groupName" LIKE '%%P2%%' THEN 2
                        WHEN ig."groupName" LIKE '%%Tier 1%%' OR ig."groupName" LIKE '%%P1%%' THEN 1
                        ELSE 0
                    END as target_tier,
                    COALESCE(a.assigned_count, 0) as assigned_count,
                    COALESCE(a.total_materials, 0) as total_materials
                FROM pi_projects p
                LEFT JOIN "invTypes" it ON p.target_product_type_id = it."typeID"
                LEFT JOIN "invGroups" ig ON it."groupID" = ig."groupID"
                LEFT JOIN characters c ON c.character_id = p.character_id
                LEFT JOIN (
                    SELECT project_id,
                           COUNT(*) as total_materials,
                           COUNT(colony_id) as assigned_count
                    FROM pi_material_assignments
                    GROUP BY project_id
                ) a ON a.project_id = p.project_id
            """
            if status:
                cur.execute(base_query + " WHERE p.status = %s ORDER BY p.updated_at DESC", (status,))
            else:
                cur.execute(base_query + " ORDER BY p.updated_at DESC")
            rows = cur.fetchall()

        return [dict(row) for row in rows]

    def update_project_status(self, project_id: int, status: str) -> bool:
        """Update project status."""
        with self.db.cursor() as cur:
            cur.execute("""
                UPDATE pi_projects
                SET status = %s, updated_at = NOW()
                WHERE project_id = %s
                RETURNING project_id
            """, (status, project_id))
            result = cur.fetchone()
        return result is not None

    def delete_project(self, project_id: int) -> bool:
        """Delete a project and its colonies."""
        with self.db.cursor() as cur:
            cur.execute(
                "DELETE FROM pi_projects WHERE project_id = %s RETURNING project_id",
                (project_id,)
            )
            result = cur.fetchone()
        return result is not None

    # ==================== Project Colony Queries ====================

    def add_project_colony(
        self,
        project_id: int,
        planet_id: int,
        role: Optional[str] = None,
        expected_output_type_id: Optional[int] = None,
        expected_output_per_hour: Optional[float] = None
    ) -> int:
        """Add a colony assignment to a project."""
        with self.db.cursor() as cur:
            cur.execute("""
                INSERT INTO pi_project_colonies (
                    project_id, planet_id, role,
                    expected_output_type_id, expected_output_per_hour
                )
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (project_id, planet_id) DO UPDATE SET
                    role = EXCLUDED.role,
                    expected_output_type_id = EXCLUDED.expected_output_type_id,
                    expected_output_per_hour = EXCLUDED.expected_output_per_hour
                RETURNING id
            """, (project_id, planet_id, role, expected_output_type_id, expected_output_per_hour))
            result = cur.fetchone()
        return result['id']

    def get_project_colonies(self, project_id: int) -> List[dict]:
        """Get all colony assignments for a project."""
        with self.db.cursor() as cur:
            cur.execute("""
                SELECT
                    pc.*,
                    it."typeName" as expected_output_name,
                    c.planet_type,
                    c.solar_system_id,
                    ms."solarSystemName" as solar_system_name
                FROM pi_project_colonies pc
                LEFT JOIN "invTypes" it ON pc.expected_output_type_id = it."typeID"
                LEFT JOIN pi_colonies c ON pc.planet_id = c.planet_id
                LEFT JOIN "mapSolarSystems" ms ON c.solar_system_id = ms."solarSystemID"
                WHERE pc.project_id = %s
                ORDER BY pc.id
            """, (project_id,))
            rows = cur.fetchall()

        return [dict(row) for row in rows]

    def update_project_colony_actual(
        self,
        project_id: int,
        planet_id: int,
        actual_output_per_hour: float
    ) -> bool:
        """Update actual output for a project colony (from ESI sync)."""
        with self.db.cursor() as cur:
            cur.execute("""
                UPDATE pi_project_colonies
                SET actual_output_per_hour = %s, last_sync = NOW()
                WHERE project_id = %s AND planet_id = %s
                RETURNING id
            """, (actual_output_per_hour, project_id, planet_id))
            result = cur.fetchone()
        return result is not None

    # ==================== Material Assignment Queries ====================

    def get_material_assignments(self, project_id: int) -> List[dict]:
        """Get all material assignments for a project with status."""
        with self.db.cursor() as cur:
            cur.execute("""
                SELECT
                    ma.id,
                    ma.project_id,
                    ma.material_type_id,
                    it."typeName" as material_name,
                    ma.tier,
                    ma.colony_id,
                    pc.planet_id,
                    sp.planet_type,
                    CONCAT(INITCAP(sp.planet_type), ' ', sp.planet_index) as colony_name,
                    ma.is_auto_assigned,
                    ma.created_at,
                    ma.soll_output_per_hour,
                    ma.soll_notes,
                    -- Status calculation
                    CASE
                        WHEN ma.colony_id IS NULL THEN 'unassigned'
                        WHEN EXISTS (
                            SELECT 1 FROM pi_pins pp
                            JOIN pi_colonies c ON pp.colony_id = c.id
                            WHERE c.planet_id = pc.planet_id
                            AND (pp.product_type_id = ma.material_type_id
                                 OR pp.schematic_id IN (
                                     SELECT pstm."schematicID"
                                     FROM "planetSchematicsTypeMap" pstm
                                     WHERE pstm."typeID" = ma.material_type_id
                                       AND pstm."isInput" = 0
                                 ))
                        ) THEN 'active'
                        ELSE 'planned'
                    END as status
                FROM pi_material_assignments ma
                LEFT JOIN "invTypes" it ON ma.material_type_id = it."typeID"
                LEFT JOIN pi_project_colonies pc ON ma.colony_id = pc.id
                LEFT JOIN pi_system_planets sp ON pc.planet_id = sp.planet_id
                WHERE ma.project_id = %s
                ORDER BY ma.tier, ma.material_type_id
            """, (project_id,))
            rows = cur.fetchall()

        return [dict(row) for row in rows]

    def calculate_material_outputs(
        self,
        project_id: int,
        assignments: List[dict]
    ) -> Dict[int, float]:
        """Calculate actual output per hour for all assigned materials."""
        if not assignments:
            return {}

        assigned = [a for a in assignments if a.get('planet_id')]
        if not assigned:
            return {}

        results = {}
        with self.db.cursor() as cur:
            for a in assigned:
                material_type_id = a['material_type_id']
                tier = a['tier']
                planet_id = a['planet_id']

                if tier == 0:
                    cur.execute("""
                        SELECT COALESCE(SUM(
                            pp.qty_per_cycle * (3600.0 / NULLIF(pp.cycle_time, 0))
                        ), 0) as output_per_hour
                        FROM pi_pins pp
                        JOIN pi_colonies c ON pp.colony_id = c.id
                        WHERE c.planet_id = %s
                          AND pp.product_type_id = %s
                          AND pp.qty_per_cycle IS NOT NULL
                          AND pp.cycle_time IS NOT NULL
                          AND pp.cycle_time > 0
                    """, (planet_id, material_type_id))
                else:
                    cur.execute("""
                        SELECT COALESCE(SUM(
                            pp.qty_per_cycle * (3600.0 / NULLIF(pp.cycle_time, 0))
                        ), 0) as output_per_hour
                        FROM pi_pins pp
                        JOIN pi_colonies c ON pp.colony_id = c.id
                        WHERE c.planet_id = %s
                          AND pp.schematic_id IN (
                              SELECT pst."schematicID"
                              FROM "planetSchematicsTypeMap" pst
                              WHERE pst."typeID" = %s AND pst."isInput" = 0
                          )
                          AND pp.qty_per_cycle IS NOT NULL
                          AND pp.cycle_time IS NOT NULL
                          AND pp.cycle_time > 0
                    """, (planet_id, material_type_id))

                result = cur.fetchone()
                if result and result['output_per_hour']:
                    results[material_type_id] = float(result['output_per_hour'])

        return results

    def upsert_material_assignment(
        self,
        project_id: int,
        material_type_id: int,
        tier: int,
        colony_id: Optional[int] = None,
        is_auto_assigned: bool = True
    ) -> int:
        """Insert or update a material assignment."""
        with self.db.cursor() as cur:
            cur.execute("""
                INSERT INTO pi_material_assignments
                    (project_id, material_type_id, tier, colony_id, is_auto_assigned)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (project_id, material_type_id) DO UPDATE SET
                    colony_id = EXCLUDED.colony_id,
                    is_auto_assigned = EXCLUDED.is_auto_assigned
                RETURNING id
            """, (project_id, material_type_id, tier, colony_id, is_auto_assigned))
            result = cur.fetchone()
        return result['id']

    def update_material_assignment(
        self,
        project_id: int,
        material_type_id: int,
        colony_id: Optional[int]
    ) -> bool:
        """Update a material assignment (manual override)."""
        with self.db.cursor() as cur:
            cur.execute("""
                UPDATE pi_material_assignments
                SET colony_id = %s, is_auto_assigned = false
                WHERE project_id = %s AND material_type_id = %s
                RETURNING id
            """, (colony_id, project_id, material_type_id))
            result = cur.fetchone()
        return result is not None

    def delete_project_assignments(self, project_id: int) -> int:
        """Delete all assignments for a project."""
        with self.db.cursor() as cur:
            cur.execute("""
                DELETE FROM pi_material_assignments
                WHERE project_id = %s
            """, (project_id,))
            count = cur.rowcount
        return count

    # ==================== SOLL Planning Methods ====================

    def update_material_soll(
        self,
        project_id: int,
        material_type_id: int,
        soll_output_per_hour: Optional[float],
        soll_notes: Optional[str] = None
    ) -> bool:
        """Update SOLL planning values for a material assignment."""
        with self.db.cursor() as cur:
            cur.execute("""
                UPDATE pi_material_assignments
                SET soll_output_per_hour = %s,
                    soll_notes = %s
                WHERE project_id = %s AND material_type_id = %s
                RETURNING id
            """, (soll_output_per_hour, soll_notes, project_id, material_type_id))
            result = cur.fetchone()
        return result is not None

    def get_project_soll_summary(self, project_id: int) -> dict:
        """Calculate SOLL vs IST summary for a project."""
        with self.db.cursor() as cur:
            cur.execute("""
                SELECT
                    COALESCE(SUM(soll_output_per_hour), 0) as total_soll,
                    COALESCE(SUM(actual_output_per_hour), 0) as total_ist,
                    COUNT(*) FILTER (WHERE soll_output_per_hour IS NOT NULL
                        AND actual_output_per_hour IS NOT NULL
                        AND ABS((actual_output_per_hour - soll_output_per_hour) / NULLIF(soll_output_per_hour, 0) * 100) <= 10
                    ) as on_target,
                    COUNT(*) FILTER (WHERE soll_output_per_hour IS NOT NULL
                        AND actual_output_per_hour IS NOT NULL
                        AND (actual_output_per_hour - soll_output_per_hour) / NULLIF(soll_output_per_hour, 0) * 100 < -10
                    ) as under_target,
                    COUNT(*) FILTER (WHERE soll_output_per_hour IS NOT NULL
                        AND actual_output_per_hour IS NOT NULL
                        AND (actual_output_per_hour - soll_output_per_hour) / NULLIF(soll_output_per_hour, 0) * 100 > 10
                    ) as over_target,
                    COUNT(*) FILTER (WHERE soll_output_per_hour IS NULL) as no_soll
                FROM pi_material_assignments
                WHERE project_id = %s
            """, (project_id,))
            row = cur.fetchone()

        return {
            "total_soll": row['total_soll'],
            "total_ist": row['total_ist'],
            "on_target": row['on_target'],
            "under_target": row['under_target'],
            "over_target": row['over_target'],
            "no_soll": row['no_soll']
        }

    def log_soll_change(
        self,
        project_id: int,
        material_type_id: int,
        old_soll: Optional[float],
        new_soll: Optional[float],
        changed_by: str,
        reason: Optional[str] = None
    ) -> int:
        """Log a SOLL planning change for audit trail."""
        with self.db.cursor() as cur:
            cur.execute("""
                INSERT INTO pi_planning_history
                    (project_id, material_type_id, old_soll_output, new_soll_output, changed_by, reason)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (project_id, material_type_id, old_soll, new_soll, changed_by, reason))
            result = cur.fetchone()
        return result['id']
