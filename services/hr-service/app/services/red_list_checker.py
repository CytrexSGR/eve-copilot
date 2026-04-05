"""Red List Management - CRUD operations and Bloom Filter pre-check.

Architecture: Database-centric approach for intersection checks.
Contacts are loaded into a temp table and JOINed against red_list_entities
to leverage PostgreSQL's B-Tree indexes instead of Python set operations.

A Redis Bloom Filter provides O(1) pre-screening for high-frequency lookups
(e.g., Local chat scanning). Only positive Bloom Filter matches trigger
the more expensive SQL query.
"""

import hashlib
import logging
import struct
from typing import List, Optional, Dict, Any

from eve_shared import get_db, get_redis

logger = logging.getLogger(__name__)

# Bloom filter config
BLOOM_KEY = "hr:redlist:bloom"
BLOOM_SIZE = 1_000_000  # bits
BLOOM_HASHES = 7


def _bloom_hashes(entity_id: int) -> List[int]:
    """Generate k hash positions for a Bloom filter."""
    data = struct.pack(">Q", entity_id)
    positions = []
    for i in range(BLOOM_HASHES):
        h = hashlib.sha256(data + struct.pack(">I", i)).digest()
        pos = int.from_bytes(h[:4], "big") % BLOOM_SIZE
        positions.append(pos)
    return positions


class RedListChecker:
    """Red list CRUD and Bloom Filter pre-check."""

    def __init__(self):
        self.db = get_db()
        self.redis = get_redis()

    def get_all(
        self,
        category: Optional[str] = None,
        active_only: bool = True,
    ) -> List[Dict[str, Any]]:
        """List red list entries with optional filters."""
        conditions = []
        params: dict = {}

        if active_only:
            conditions.append("active = TRUE")
        if category:
            conditions.append("category = %(category)s")
            params["category"] = category

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        with self.db.cursor() as cur:
            cur.execute(
                f"""
                SELECT id, entity_id, entity_name, category, severity,
                       reason, added_by, added_at, active
                FROM red_list_entities
                {where}
                ORDER BY severity DESC, added_at DESC
                """,
                params,
            )
            rows = cur.fetchall()

        return [dict(r) for r in rows]

    def add_entry(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Add a single entity to the red list."""
        with self.db.cursor() as cur:
            cur.execute(
                """
                INSERT INTO red_list_entities
                    (entity_id, entity_name, category, severity, reason, added_by)
                VALUES
                    (%(entity_id)s, %(entity_name)s, %(category)s,
                     %(severity)s, %(reason)s, %(added_by)s)
                ON CONFLICT (entity_id, category) WHERE active = TRUE
                DO UPDATE SET
                    severity = EXCLUDED.severity,
                    reason = EXCLUDED.reason,
                    entity_name = COALESCE(EXCLUDED.entity_name, red_list_entities.entity_name)
                RETURNING id, entity_id, entity_name, category, severity,
                          reason, added_by, added_at, active
                """,
                entry,
            )
            row = cur.fetchone()
            
        # Update Bloom filter
        self._bloom_add(entry["entity_id"])

        return dict(row)

    def bulk_import(self, entries: List[Dict[str, Any]]) -> int:
        """Bulk import red list entries. Returns count of imported entries."""
        if not entries:
            return 0

        imported = 0
        with self.db.cursor() as cur:
            for entry in entries:
                cur.execute(
                    """
                    INSERT INTO red_list_entities
                        (entity_id, entity_name, category, severity, reason, added_by)
                    VALUES
                        (%(entity_id)s, %(entity_name)s, %(category)s,
                         %(severity)s, %(reason)s, %(added_by)s)
                    ON CONFLICT (entity_id, category) WHERE active = TRUE
                    DO UPDATE SET
                        severity = EXCLUDED.severity,
                        reason = EXCLUDED.reason,
                        entity_name = COALESCE(EXCLUDED.entity_name, red_list_entities.entity_name)
                    """,
                    entry,
                )
                imported += 1
                self._bloom_add(entry["entity_id"])

            
        logger.info(f"Bulk imported {imported} red list entries")
        return imported

    def deactivate(self, entry_id: int) -> bool:
        """Deactivate a red list entry by ID."""
        with self.db.cursor() as cur:
            cur.execute(
                """
                UPDATE red_list_entities
                SET active = FALSE
                WHERE id = %(id)s AND active = TRUE
                RETURNING entity_id
                """,
                {"id": entry_id},
            )
            row = cur.fetchone()
            
        if row:
            # Rebuild bloom filter since we can't remove from it
            self._rebuild_bloom()
            return True
        return False

    def check_entity(self, entity_id: int) -> Dict[str, Any]:
        """Quick check if entity is on red list (Bloom Filter + SQL fallback)."""
        # Phase 1: Bloom Filter pre-check
        if not self._bloom_check(entity_id):
            return {"entity_id": entity_id, "on_red_list": False, "entries": []}

        # Phase 2: SQL confirmation (Bloom filter has false positives)
        with self.db.cursor() as cur:
            cur.execute(
                """
                SELECT id, entity_id, entity_name, category, severity, reason
                FROM red_list_entities
                WHERE entity_id = %(entity_id)s AND active = TRUE
                ORDER BY severity DESC
                """,
                {"entity_id": entity_id},
            )
            rows = cur.fetchall()

        entries = [dict(r) for r in rows]
        return {
            "entity_id": entity_id,
            "on_red_list": len(entries) > 0,
            "entries": entries,
        }

    def intersect_contacts(self, contact_ids: List[int]) -> List[Dict[str, Any]]:
        """Database-centric intersection: temp table JOIN against red list.

        This is the core vetting check from the spec (Section 2.1.2).
        """
        if not contact_ids:
            return []

        with self.db.cursor() as cur:
            # Create temp table with contact IDs
            cur.execute(
                "CREATE TEMP TABLE tmp_vetting_contacts (contact_id BIGINT) ON COMMIT DROP"
            )

            # Bulk insert contact IDs
            from psycopg2.extras import execute_values

            execute_values(
                cur,
                "INSERT INTO tmp_vetting_contacts (contact_id) VALUES %s",
                [(cid,) for cid in contact_ids],
            )

            # In-database intersection using index on red_list_entities
            cur.execute(
                """
                SELECT r.entity_id, r.entity_name, r.category, r.severity, r.reason
                FROM red_list_entities r
                JOIN tmp_vetting_contacts c ON r.entity_id = c.contact_id
                WHERE r.active = TRUE
                ORDER BY r.severity DESC
                """
            )
            rows = cur.fetchall()
            
        return [dict(r) for r in rows]

    # --- Bloom Filter Operations ---

    def _bloom_add(self, entity_id: int):
        """Add entity to Redis Bloom filter."""
        try:
            r = self.redis.client
            if not r:
                return
            pipe = r.pipeline()
            for pos in _bloom_hashes(entity_id):
                pipe.setbit(BLOOM_KEY, pos, 1)
            pipe.execute()
        except Exception:
            logger.debug("Bloom filter add failed (Redis unavailable)")

    def _bloom_check(self, entity_id: int) -> bool:
        """Check if entity might be in Bloom filter. False = definitely not on list."""
        try:
            r = self.redis.client
            if not r:
                return True  # Fallback: assume possible match, let SQL decide

            pipe = r.pipeline()
            for pos in _bloom_hashes(entity_id):
                pipe.getbit(BLOOM_KEY, pos)
            results = pipe.execute()

            return all(results)
        except Exception:
            return True  # Fallback: let SQL decide

    def _rebuild_bloom(self):
        """Rebuild entire Bloom filter from DB (after deactivation)."""
        try:
            r = self.redis.client
            if not r:
                return

            r.delete(BLOOM_KEY)

            with self.db.cursor() as cur:
                cur.execute(
                    "SELECT DISTINCT entity_id FROM red_list_entities WHERE active = TRUE"
                )
                for row in cur:
                    self._bloom_add(row["entity_id"])

            logger.info("Bloom filter rebuilt from DB")
        except Exception:
            logger.warning("Bloom filter rebuild failed")

    def initialize_bloom(self):
        """Initialize Bloom filter on service startup."""
        self._rebuild_bloom()
