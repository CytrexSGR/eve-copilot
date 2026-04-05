"""Wormhole data repository for database operations."""
from typing import Optional
from psycopg2.extras import execute_values

from eve_shared import get_db


class WormholeRepository:
    """Database operations for wormhole data."""

    def __init__(self, db=None):
        self.db = db or get_db()

    # =========================================================================
    # Import Tracking
    # =========================================================================

    def get_last_import(self, source: str, import_type: str) -> Optional[dict]:
        """Get last import record for change detection."""
        with self.db.cursor() as cur:
            cur.execute("""
                SELECT * FROM wormhole_data_imports
                WHERE source = %s AND import_type = %s
                ORDER BY imported_at DESC LIMIT 1
            """, (source, import_type))
            return cur.fetchone()

    def record_import(self, source: str, import_type: str, count: int, checksum: str):
        """Record completed import."""
        with self.db.cursor() as cur:
            cur.execute("""
                INSERT INTO wormhole_data_imports (source, import_type, records_imported, checksum)
                VALUES (%s, %s, %s, %s)
            """, (source, import_type, count, checksum))

    # =========================================================================
    # Static Data Operations
    # =========================================================================

    def upsert_statics(self, statics: list[dict]) -> int:
        """Upsert system static data. Returns count."""
        if not statics:
            return 0
        with self.db.cursor() as cur:
            cur.execute("TRUNCATE wormhole_system_statics RESTART IDENTITY")
            execute_values(
                cur,
                "INSERT INTO wormhole_system_statics (system_id, wormhole_type_id) VALUES %s",
                [(s['system_id'], s['type_id']) for s in statics]
            )
            return len(statics)

    def upsert_wormhole_extended(self, wormholes: list[dict]) -> int:
        """Upsert wormhole extended data. Returns count."""
        if not wormholes:
            return 0
        with self.db.cursor() as cur:
            # Get type_id mapping
            cur.execute("""
                SELECT "typeID", REPLACE("typeName", 'Wormhole ', '') as code
                FROM "invTypes" WHERE "groupID" = 988
            """)
            type_map = {r['code']: r['typeID'] for r in cur.fetchall()}

            count = 0
            for wh in wormholes:
                type_id = type_map.get(wh['code'])
                if type_id:
                    cur.execute("""
                        INSERT INTO wormhole_type_extended (type_id, type_code, scan_wormhole_strength)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (type_id) DO UPDATE SET
                            scan_wormhole_strength = EXCLUDED.scan_wormhole_strength,
                            updated_at = NOW()
                    """, (type_id, wh['code'], wh['scan_strength']))
                    count += 1
            return count

    # =========================================================================
    # Query Operations
    # =========================================================================

    def get_wormhole_types(self) -> list[dict]:
        """Get all WH types with full attributes."""
        with self.db.cursor() as cur:
            cur.execute("SELECT * FROM v_wormhole_types ORDER BY type_code")
            return cur.fetchall()

    def get_wormhole_type(self, code: str) -> Optional[dict]:
        """Get single WH type by code."""
        with self.db.cursor() as cur:
            cur.execute("SELECT * FROM v_wormhole_types WHERE UPPER(type_code) = UPPER(%s)", (code,))
            return cur.fetchone()

    def get_wormhole_systems(self, wh_class: Optional[int] = None, limit: int = 100) -> list[dict]:
        """Get J-Space systems."""
        with self.db.cursor() as cur:
            if wh_class:
                cur.execute("""
                    SELECT * FROM v_wormhole_systems
                    WHERE wormhole_class = %s
                    ORDER BY system_name LIMIT %s
                """, (wh_class, limit))
            else:
                cur.execute("SELECT * FROM v_wormhole_systems ORDER BY system_name LIMIT %s", (limit,))
            return cur.fetchall()

    def get_system_statics(self, system_id: int) -> list[dict]:
        """Get statics for a specific system."""
        with self.db.cursor() as cur:
            cur.execute("SELECT * FROM v_system_statics WHERE system_id = %s", (system_id,))
            return cur.fetchall()

    def get_systems_by_static(self, type_code: str) -> list[dict]:
        """Get all systems with a specific static."""
        with self.db.cursor() as cur:
            cur.execute("""
                SELECT * FROM v_system_statics
                WHERE UPPER(type_code) = UPPER(%s)
                ORDER BY system_name
            """, (type_code,))
            return cur.fetchall()

    def search_system(self, query: str, limit: int = 20) -> list[dict]:
        """Search J-Space systems by name."""
        with self.db.cursor() as cur:
            cur.execute("""
                SELECT * FROM v_wormhole_systems
                WHERE UPPER(system_name) LIKE UPPER(%s)
                ORDER BY system_name LIMIT %s
            """, (f'%{query}%', limit))
            return cur.fetchall()
