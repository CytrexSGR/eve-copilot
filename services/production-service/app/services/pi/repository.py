"""
Planetary Industry (PI) Repository
Database queries for PI schematics (from EVE SDE) and colonies (from ESI sync).

Adapted for eve_shared pattern - uses db interface from app.state.db

Domain methods are split into mixins:
- SchematicMixin: SDE schematic/planet lookups (schematic_repo.py)
- ColonyMixin: Colony CRUD, character skills, system planets (colony_repo.py)
- ProjectMixin: Project CRUD, assignments, SOLL planning (project_repo.py)

Cross-domain methods (empire plans, logistics, alerts) remain here.
"""

import hashlib
import json
from typing import List, Optional, Dict, Any
from datetime import datetime

from psycopg2.extras import RealDictCursor

from app.services.pi.schematic_repo import SchematicMixin
from app.services.pi.colony_repo import ColonyMixin
from app.services.pi.project_repo import ProjectMixin


class PIRepository(SchematicMixin, ColonyMixin, ProjectMixin):
    """
    PI Repository provides database access for Planetary Industry data.

    Handles two types of data:
    - Schematics (from EVE SDE tables): Production recipes for PI items
    - Colonies (from pi_* tables): Character-specific colony data synced from ESI

    Pattern: Uses eve_shared database interface.
    Domain methods are organized in mixins; cross-domain methods stay here.
    """

    def __init__(self, db):
        """
        Initialize PI Repository with database interface.

        Args:
            db: eve_shared database interface (from app.state.db)
        """
        self.db = db

    # ==================== Empire Plan Queries ====================

    def create_empire_plan(
        self,
        name: str,
        target_product_id: int,
        target_product_name: Optional[str] = None,
        home_system_id: Optional[int] = None,
        home_system_name: Optional[str] = None,
        total_planets: int = 18,
        extraction_planets: int = 12,
        factory_planets: int = 6,
        poco_tax_rate: float = 0.10
    ) -> int:
        """
        Create a new PI empire plan.

        Args:
            name: Plan name
            target_product_id: Target P4 product type ID
            target_product_name: Target product name (optional)
            home_system_id: Home system ID for logistics (optional)
            home_system_name: Home system name (optional)
            total_planets: Total planets across all characters (default 18)
            extraction_planets: Number of extraction planets (default 12)
            factory_planets: Number of factory planets (default 6)
            poco_tax_rate: POCO tax rate (default 0.10)

        Returns:
            Created plan ID
        """
        with self.db.cursor() as cur:
            cur.execute("""
                INSERT INTO pi_empire_plans (
                    name, target_product_id, target_product_name,
                    home_system_id, home_system_name,
                    total_planets, extraction_planets, factory_planets,
                    poco_tax_rate, status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'planning')
                RETURNING id
            """, (
                name, target_product_id, target_product_name,
                home_system_id, home_system_name,
                total_planets, extraction_planets, factory_planets,
                poco_tax_rate
            ))
            result = cur.fetchone()
            # Note: Commit is handled automatically by DatabasePool.cursor() context manager
        if not result:
            raise ValueError("Failed to create empire plan")
        return result['id']

    def get_empire_plan(self, plan_id: int) -> Optional[dict]:
        """
        Get an empire plan by ID.

        Args:
            plan_id: The plan ID

        Returns:
            Plan dict if found, None otherwise
        """
        with self.db.cursor() as cur:
            cur.execute("""
                SELECT
                    id,
                    name,
                    target_product_id,
                    target_product_name,
                    home_system_id,
                    home_system_name,
                    total_planets,
                    extraction_planets,
                    factory_planets,
                    poco_tax_rate,
                    status,
                    estimated_monthly_output,
                    estimated_monthly_profit,
                    created_at,
                    updated_at
                FROM pi_empire_plans
                WHERE id = %s
            """, (plan_id,))
            result = cur.fetchone()

        if not result:
            return None

        return {
            "id": result['id'],
            "name": result['name'],
            "target_product_id": result['target_product_id'],
            "target_product_name": result['target_product_name'],
            "home_system_id": result['home_system_id'],
            "home_system_name": result['home_system_name'],
            "total_planets": result['total_planets'],
            "extraction_planets": result['extraction_planets'],
            "factory_planets": result['factory_planets'],
            "poco_tax_rate": float(result['poco_tax_rate']),
            "status": result['status'],
            "estimated_monthly_output": result['estimated_monthly_output'],
            "estimated_monthly_profit": float(result['estimated_monthly_profit']) if result['estimated_monthly_profit'] else None,
            "created_at": result['created_at'],
            "updated_at": result['updated_at']
        }

    def list_empire_plans(self, status: Optional[str] = None) -> List[dict]:
        """
        List all empire plans with optional status filter.

        Args:
            status: Optional status filter ('planning', 'active', 'paused', 'completed')

        Returns:
            List of plan dicts
        """
        with self.db.cursor() as cur:
            if status:
                cur.execute("""
                    SELECT
                        id,
                        name,
                        target_product_id,
                        target_product_name,
                        home_system_id,
                        home_system_name,
                        total_planets,
                        extraction_planets,
                        factory_planets,
                        poco_tax_rate,
                        status,
                        estimated_monthly_output,
                        estimated_monthly_profit,
                        created_at,
                        updated_at
                    FROM pi_empire_plans
                    WHERE status = %s
                    ORDER BY created_at DESC
                """, (status,))
            else:
                cur.execute("""
                    SELECT
                        id,
                        name,
                        target_product_id,
                        target_product_name,
                        home_system_id,
                        home_system_name,
                        total_planets,
                        extraction_planets,
                        factory_planets,
                        poco_tax_rate,
                        status,
                        estimated_monthly_output,
                        estimated_monthly_profit,
                        created_at,
                        updated_at
                    FROM pi_empire_plans
                    ORDER BY created_at DESC
                """)
            rows = cur.fetchall()

        return [
            {
                "id": r['id'],
                "name": r['name'],
                "target_product_id": r['target_product_id'],
                "target_product_name": r['target_product_name'],
                "home_system_id": r['home_system_id'],
                "home_system_name": r['home_system_name'],
                "total_planets": r['total_planets'],
                "extraction_planets": r['extraction_planets'],
                "factory_planets": r['factory_planets'],
                "poco_tax_rate": float(r['poco_tax_rate']),
                "status": r['status'],
                "estimated_monthly_output": r['estimated_monthly_output'],
                "estimated_monthly_profit": float(r['estimated_monthly_profit']) if r['estimated_monthly_profit'] else None,
                "created_at": r['created_at'],
                "updated_at": r['updated_at']
            }
            for r in rows
        ]

    def add_plan_assignment(
        self,
        plan_id: int,
        character_id: int,
        character_name: Optional[str] = None,
        role: str = "extractor",
        planets: Optional[List[dict]] = None
    ) -> int:
        """
        Add a character assignment to an empire plan.

        Args:
            plan_id: The plan ID
            character_id: The character ID
            character_name: The character name (optional)
            role: Character role ('extractor', 'factory', 'hybrid')
            planets: Planet configuration as list of dicts (optional)

        Returns:
            Created assignment ID
        """
        planets_json = json.dumps(planets or [])

        with self.db.cursor() as cur:
            cur.execute("""
                INSERT INTO pi_empire_plan_assignments (
                    plan_id, character_id, character_name, role, planets
                ) VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """, (plan_id, character_id, character_name, role, planets_json))
            result = cur.fetchone()
            # Note: Commit is handled automatically by DatabasePool.cursor() context manager
        return result['id']

    def get_plan_assignments(self, plan_id: int) -> List[dict]:
        """
        Get all character assignments for an empire plan.

        Args:
            plan_id: The plan ID

        Returns:
            List of assignment dicts
        """
        with self.db.cursor() as cur:
            cur.execute("""
                SELECT
                    id,
                    plan_id,
                    character_id,
                    character_name,
                    role,
                    planets,
                    created_at
                FROM pi_empire_plan_assignments
                WHERE plan_id = %s
                ORDER BY id
            """, (plan_id,))
            rows = cur.fetchall()

        return [
            {
                "id": r['id'],
                "plan_id": r['plan_id'],
                "character_id": r['character_id'],
                "character_name": r['character_name'],
                "role": r['role'],
                "planets": json.loads(r['planets']) if r['planets'] else [],
                "created_at": r['created_at']
            }
            for r in rows
        ]

    def update_plan_status(self, plan_id: int, status: str) -> bool:
        """
        Update an empire plan's status.

        Args:
            plan_id: The plan ID
            status: New status ('planning', 'active', 'paused', 'completed')

        Returns:
            True if updated, False if plan not found

        Raises:
            ValueError: If status is not valid
        """
        valid_statuses = {'planning', 'active', 'paused', 'completed'}
        if status not in valid_statuses:
            raise ValueError(f"Invalid status '{status}'. Must be one of: {', '.join(sorted(valid_statuses))}")

        with self.db.cursor() as cur:
            cur.execute("""
                UPDATE pi_empire_plans
                SET status = %s, updated_at = NOW()
                WHERE id = %s
                RETURNING id
            """, (status, plan_id))
            result = cur.fetchone()
            # Note: Commit is handled automatically by DatabasePool.cursor() context manager
        return result is not None

    def delete_empire_plan(self, plan_id: int) -> bool:
        """
        Delete an empire plan and all its assignments (cascade).

        Args:
            plan_id: The plan ID

        Returns:
            True if deleted, False if plan not found
        """
        with self.db.cursor() as cur:
            cur.execute("""
                DELETE FROM pi_empire_plans
                WHERE id = %s
                RETURNING id
            """, (plan_id,))
            result = cur.fetchone()
            # Note: Commit is handled automatically by DatabasePool.cursor() context manager
        return result is not None

    # ==================== Logistics Methods ====================

    def get_plan_colonies_with_systems(self, plan_id: int) -> List[Dict]:
        """Get all colonies for a plan with system information."""
        with self.db.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT
                    c.character_id,
                    c.planet_id,
                    c.planet_type,
                    c.solar_system_id,
                    COALESCE(s."solarSystemName", 'Unknown') as system_name,
                    COALESCE(s.security, 0.5) as security,
                    a.character_name,
                    a.role
                FROM pi_empire_plan_assignments a
                JOIN pi_colonies c ON c.character_id = a.character_id
                LEFT JOIN "mapSolarSystems" s ON s."solarSystemID" = c.solar_system_id
                WHERE a.plan_id = %s
                ORDER BY c.character_id, c.solar_system_id
            """, (plan_id,))
            return cur.fetchall()

    def get_system_jump_distance(self, from_system_id: int, to_system_id: int) -> int:
        """Get jump distance between two systems using cached route data."""
        if from_system_id == to_system_id:
            return 0
        # Use simple heuristic based on region - actual routing would need pathfinding
        with self.db.cursor() as cur:
            cur.execute("""
                SELECT
                    ABS(s1."solarSystemID" - s2."solarSystemID") / 1000000 as est_jumps
                FROM "mapSolarSystems" s1, "mapSolarSystems" s2
                WHERE s1."solarSystemID" = %s AND s2."solarSystemID" = %s
            """, (from_system_id, to_system_id))
            result = cur.fetchone()
            # Return estimated jumps, min 1 if different systems
            return max(1, int(result['est_jumps'])) if result else 5

    def get_stations_in_system(self, system_id: int) -> List[Dict]:
        """Get NPC stations in a system."""
        with self.db.cursor() as cur:
            cur.execute("""
                SELECT
                    "stationID" as station_id,
                    "stationName" as station_name,
                    "solarSystemID" as system_id
                FROM "staStations"
                WHERE "solarSystemID" = %s
                ORDER BY "stationName"
            """, (system_id,))
            return cur.fetchall()

    def save_hub_station(self, plan_id: int, station_id: int, station_name: str,
                         system_id: int, system_name: str, security: float) -> int:
        """Save or update hub station for a plan."""
        with self.db.cursor() as cur:
            cur.execute("""
                INSERT INTO pi_hub_stations (plan_id, station_id, station_name, system_id, system_name, security)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (plan_id, station_id) DO UPDATE SET
                    station_name = EXCLUDED.station_name,
                    selected_at = NOW()
                RETURNING id
            """, (plan_id, station_id, station_name, system_id, system_name, security))
            self.db.commit()
            return cur.fetchone()['id']

    def get_hub_station(self, plan_id: int) -> Optional[Dict]:
        """Get primary hub station for a plan."""
        with self.db.cursor() as cur:
            cur.execute("""
                SELECT * FROM pi_hub_stations
                WHERE plan_id = %s AND is_primary = true
                ORDER BY selected_at DESC LIMIT 1
            """, (plan_id,))
            return cur.fetchone()

    def save_transfer(self, plan_id: int, from_char: int, to_char: int,
                      material_type_id: int, material_name: str, quantity: int,
                      volume_m3: float, method: str, station_id: int,
                      station_name: str, frequency_hours: int) -> int:
        """Save a transfer record."""
        with self.db.cursor() as cur:
            cur.execute("""
                INSERT INTO pi_transfers
                (plan_id, from_character_id, to_character_id, material_type_id,
                 material_name, quantity, volume_m3, method, station_id,
                 station_name, frequency_hours)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (plan_id, from_char, to_char, material_type_id, material_name,
                  quantity, volume_m3, method, station_id, station_name, frequency_hours))
            self.db.commit()
            return cur.fetchone()['id']

    def get_transfers(self, plan_id: int) -> List[Dict]:
        """Get all transfers for a plan."""
        with self.db.cursor() as cur:
            cur.execute("""
                SELECT * FROM pi_transfers
                WHERE plan_id = %s
                ORDER BY from_character_id, to_character_id
            """, (plan_id,))
            return cur.fetchall()

    def log_pickup_run(self, plan_id: int, character_id: int,
                       planets_visited: int, total_volume: float) -> int:
        """Log a completed pickup run."""
        with self.db.cursor() as cur:
            cur.execute("""
                INSERT INTO pi_pickup_runs
                (plan_id, character_id, started_at, completed_at, planets_visited, total_volume_m3)
                VALUES (%s, %s, NOW(), NOW(), %s, %s)
                RETURNING id
            """, (plan_id, character_id, planets_visited, total_volume))
            self.db.commit()
            return cur.fetchone()['id']

    # ==================== PI Alert Methods ====================

    def get_alert_config(self, character_id: int) -> Optional[Dict]:
        """Get alert configuration for character."""
        with self.db.cursor() as cur:
            cur.execute("""
                SELECT * FROM pi_alert_config WHERE character_id = %s
            """, (character_id,))
            return cur.fetchone()

    def upsert_alert_config(self, character_id: int, config: Dict) -> Dict:
        """Create or update alert configuration."""
        # Default values for new records - these match the model defaults
        defaults = {
            'discord_webhook_url': None,
            'discord_enabled': True,
            'extractor_warning_hours': 12,
            'extractor_critical_hours': 4,
            'storage_warning_percent': 75,
            'storage_critical_percent': 90,
            'alert_extractor_depleting': True,
            'alert_extractor_stopped': True,
            'alert_storage_full': True,
            'alert_factory_idle': True,
            'alert_pickup_reminder': True,
            'pickup_reminder_hours': 48,
        }
        # Merge defaults with provided config (provided values override defaults)
        full_config = {**defaults, **config, 'character_id': character_id}

        with self.db.cursor() as cur:
            cur.execute("""
                INSERT INTO pi_alert_config (
                    character_id, discord_webhook_url, discord_enabled,
                    extractor_warning_hours, extractor_critical_hours,
                    storage_warning_percent, storage_critical_percent,
                    alert_extractor_depleting, alert_extractor_stopped,
                    alert_storage_full, alert_factory_idle, alert_pickup_reminder,
                    pickup_reminder_hours, updated_at
                ) VALUES (
                    %(character_id)s, %(discord_webhook_url)s, %(discord_enabled)s,
                    %(extractor_warning_hours)s, %(extractor_critical_hours)s,
                    %(storage_warning_percent)s, %(storage_critical_percent)s,
                    %(alert_extractor_depleting)s, %(alert_extractor_stopped)s,
                    %(alert_storage_full)s, %(alert_factory_idle)s, %(alert_pickup_reminder)s,
                    %(pickup_reminder_hours)s, NOW()
                )
                ON CONFLICT (character_id) DO UPDATE SET
                    discord_webhook_url = COALESCE(EXCLUDED.discord_webhook_url, pi_alert_config.discord_webhook_url),
                    discord_enabled = COALESCE(EXCLUDED.discord_enabled, pi_alert_config.discord_enabled),
                    extractor_warning_hours = COALESCE(EXCLUDED.extractor_warning_hours, pi_alert_config.extractor_warning_hours),
                    extractor_critical_hours = COALESCE(EXCLUDED.extractor_critical_hours, pi_alert_config.extractor_critical_hours),
                    storage_warning_percent = COALESCE(EXCLUDED.storage_warning_percent, pi_alert_config.storage_warning_percent),
                    storage_critical_percent = COALESCE(EXCLUDED.storage_critical_percent, pi_alert_config.storage_critical_percent),
                    alert_extractor_depleting = COALESCE(EXCLUDED.alert_extractor_depleting, pi_alert_config.alert_extractor_depleting),
                    alert_extractor_stopped = COALESCE(EXCLUDED.alert_extractor_stopped, pi_alert_config.alert_extractor_stopped),
                    alert_storage_full = COALESCE(EXCLUDED.alert_storage_full, pi_alert_config.alert_storage_full),
                    alert_factory_idle = COALESCE(EXCLUDED.alert_factory_idle, pi_alert_config.alert_factory_idle),
                    alert_pickup_reminder = COALESCE(EXCLUDED.alert_pickup_reminder, pi_alert_config.alert_pickup_reminder),
                    pickup_reminder_hours = COALESCE(EXCLUDED.pickup_reminder_hours, pi_alert_config.pickup_reminder_hours),
                    updated_at = NOW()
                RETURNING *
            """, full_config)
            return cur.fetchone()

    def create_alert(
        self,
        character_id: int,
        alert_type: str,
        severity: str,
        message: str,
        planet_id: Optional[int] = None,
        planet_name: Optional[str] = None,
        pin_id: Optional[int] = None,
        product_type_id: Optional[int] = None,
        product_name: Optional[str] = None,
        details: Optional[Dict] = None,
        expires_hours: int = 24
    ) -> Optional[int]:
        """
        Create a new PI alert with deduplication.

        Returns alert ID if created, None if duplicate exists.
        """
        # Generate deduplication hash
        hash_data = f"{character_id}:{alert_type}:{planet_id}:{pin_id}:{product_type_id}"
        alert_hash = hashlib.sha256(hash_data.encode()).hexdigest()[:64]

        with self.db.cursor() as cur:
            try:
                cur.execute("""
                    INSERT INTO pi_alert_log (
                        character_id, alert_type, severity, message,
                        planet_id, planet_name, pin_id,
                        product_type_id, product_name, details,
                        expires_at, alert_hash
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        NOW() + INTERVAL '%s hours', %s
                    )
                    RETURNING id
                """, (
                    character_id, alert_type, severity, message,
                    planet_id, planet_name, pin_id,
                    product_type_id, product_name,
                    json.dumps(details) if details else None,
                    expires_hours, alert_hash
                ))
                result = cur.fetchone()
                return result['id'] if result else None
            except Exception as e:
                # Duplicate alert (unique constraint violation)
                if 'unique constraint' in str(e).lower():
                    return None
                raise

    def get_alerts(
        self,
        character_id: Optional[int] = None,
        unread_only: bool = False,
        limit: int = 50
    ) -> List[Dict]:
        """Get PI alerts, optionally filtered by character and read status."""
        with self.db.cursor() as cur:
            where_clauses = []
            params = []

            if character_id:
                where_clauses.append("character_id = %s")
                params.append(character_id)

            if unread_only:
                where_clauses.append("is_read = FALSE")

            where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

            cur.execute(f"""
                SELECT * FROM pi_alert_log
                {where_sql}
                ORDER BY created_at DESC
                LIMIT %s
            """, params + [limit])
            return cur.fetchall()

    def mark_alerts_read(self, alert_ids: List[int]) -> int:
        """Mark alerts as read. Returns count updated."""
        if not alert_ids:
            return 0
        with self.db.cursor() as cur:
            cur.execute("""
                UPDATE pi_alert_log
                SET is_read = TRUE
                WHERE id = ANY(%s)
            """, (alert_ids,))
            return cur.rowcount

    def mark_alert_discord_sent(self, alert_id: int) -> bool:
        """Mark alert as sent to Discord."""
        with self.db.cursor() as cur:
            cur.execute("""
                UPDATE pi_alert_log
                SET discord_sent = TRUE, discord_sent_at = NOW()
                WHERE id = %s
                RETURNING id
            """, (alert_id,))
            return cur.fetchone() is not None

    def cleanup_old_alerts(self) -> int:
        """Remove old/expired alerts. Returns count deleted."""
        with self.db.cursor() as cur:
            cur.execute("""
                DELETE FROM pi_alert_log
                WHERE created_at < NOW() - INTERVAL '7 days'
                   OR (expires_at IS NOT NULL AND expires_at < NOW())
            """)
            return cur.rowcount
