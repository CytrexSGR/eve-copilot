"""Character repository for database operations and caching."""
import json
import logging
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any

from psycopg2.extras import RealDictCursor

from app.config import settings
from app.services.auth_client import AuthClient

logger = logging.getLogger(__name__)


class CharacterRepository:
    """Repository for character data with L1/L2 caching."""

    KEY_PREFIX = "character"

    def __init__(self, db, redis=None):
        self.db = db
        self.redis = redis
        self.auth_client = AuthClient()

    # Cache operations

    def _make_key(self, character_id: int, data_type: str) -> str:
        """Generate cache key."""
        return f"{self.KEY_PREFIX}:{character_id}:{data_type}"

    def _get_cached(self, key: str) -> Optional[Any]:
        """Get value from Redis cache."""
        if not self.redis:
            return None
        try:
            data = self.redis.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            logger.warning(f"Cache get failed for {key}: {e}")
        return None

    def _set_cached(self, key: str, value: Any, ttl: int) -> None:
        """Set value in Redis cache."""
        if not self.redis:
            return
        try:
            self.redis.set(key, json.dumps(value, default=str), ex=ttl)
        except Exception as e:
            logger.warning(f"Cache set failed for {key}: {e}")

    def invalidate_cache(self, character_id: int) -> None:
        """Invalidate all cache for a character."""
        if not self.redis:
            return
        keys = [
            self._make_key(character_id, "wallet"),
            self._make_key(character_id, "skills"),
            self._make_key(character_id, "assets"),
            self._make_key(character_id, "orders"),
            self._make_key(character_id, "jobs"),
            self._make_key(character_id, "blueprints"),
        ]
        for key in keys:
            try:
                self.redis.delete(key)
            except Exception:
                pass

    # Type name resolution

    def resolve_type_names(self, type_ids: List[int]) -> Dict[int, str]:
        """Resolve type IDs to names from SDE."""
        if not type_ids:
            return {}

        with self.db.cursor() as cur:
            cur.execute("""
                SELECT "typeID", "typeName"
                FROM "invTypes"
                WHERE "typeID" = ANY(%s)
            """, (list(type_ids),))
            rows = cur.fetchall()
            return {row["typeID"]: row["typeName"] for row in rows}

    def resolve_type_info(self, type_ids: List[int]) -> Dict[int, dict]:
        """Resolve type IDs to full info from SDE."""
        if not type_ids:
            return {}

        with self.db.cursor() as cur:
            cur.execute("""
                SELECT t."typeID", t."typeName",
                       g."groupID", g."groupName",
                       c."categoryID", c."categoryName"
                FROM "invTypes" t
                JOIN "invGroups" g ON t."groupID" = g."groupID"
                JOIN "invCategories" c ON g."categoryID" = c."categoryID"
                WHERE t."typeID" = ANY(%s)
            """, (list(type_ids),))
            rows = cur.fetchall()
            return {
                row["typeID"]: {
                    "type_name": row["typeName"],
                    "group_id": row["groupID"],
                    "group_name": row["groupName"],
                    "category_id": row["categoryID"],
                    "category_name": row["categoryName"],
                }
                for row in rows
            }

    def resolve_type_info_with_volume(self, type_ids: List[int]) -> Dict[int, dict]:
        """Resolve type IDs to full info including volume from SDE."""
        if not type_ids:
            return {}

        with self.db.cursor() as cur:
            cur.execute("""
                SELECT t."typeID", t."typeName", t."volume",
                       g."groupID", g."groupName",
                       c."categoryID", c."categoryName"
                FROM "invTypes" t
                JOIN "invGroups" g ON t."groupID" = g."groupID"
                JOIN "invCategories" c ON g."categoryID" = c."categoryID"
                WHERE t."typeID" = ANY(%s)
            """, (list(type_ids),))
            rows = cur.fetchall()
            return {
                row["typeID"]: {
                    "type_name": row["typeName"],
                    "group_id": row["groupID"],
                    "group_name": row["groupName"],
                    "category_id": row["categoryID"],
                    "category_name": row["categoryName"],
                    "volume": float(row["volume"] or 0),
                }
                for row in rows
            }

    # Location resolution

    def resolve_station_names(self, station_ids: List[int]) -> Dict[int, str]:
        """Resolve station IDs to names."""
        if not station_ids:
            return {}

        with self.db.cursor() as cur:
            cur.execute("""
                SELECT "stationID", "stationName"
                FROM "staStations"
                WHERE "stationID" = ANY(%s)
            """, (list(station_ids),))
            rows = cur.fetchall()
            return {row["stationID"]: row["stationName"] for row in rows}

    def resolve_system_names(self, system_ids: List[int]) -> Dict[int, str]:
        """Resolve system IDs to names."""
        if not system_ids:
            return {}

        with self.db.cursor() as cur:
            cur.execute("""
                SELECT "solarSystemID", "solarSystemName"
                FROM "mapSolarSystems"
                WHERE "solarSystemID" = ANY(%s)
            """, (list(system_ids),))
            rows = cur.fetchall()
            return {row["solarSystemID"]: row["solarSystemName"] for row in rows}

    def resolve_location_names(
        self,
        location_ids: List[int]
    ) -> Dict[int, str]:
        """Resolve location IDs to names."""
        names: Dict[int, str] = {}
        station_ids = []
        system_ids = []

        for loc_id in location_ids:
            if 60000000 <= loc_id < 70000000:
                station_ids.append(loc_id)
            elif 30000000 <= loc_id < 33000000:
                system_ids.append(loc_id)
            elif loc_id >= 1000000000000:
                names[loc_id] = "Player Structure"

        if station_ids:
            station_names = self.resolve_station_names(station_ids)
            names.update(station_names)

        if system_ids:
            system_names = self.resolve_system_names(system_ids)
            names.update(system_names)

        return names

    # Skill info

    def get_skill_info(self, skill_ids: List[int]) -> Dict[int, dict]:
        """Get skill info including description."""
        if not skill_ids:
            return {}

        with self.db.cursor() as cur:
            cur.execute("""
                SELECT "typeID", "typeName", "description"
                FROM "invTypes"
                WHERE "typeID" = ANY(%s)
            """, (list(skill_ids),))
            rows = cur.fetchall()
            return {
                row["typeID"]: {
                    "name": row["typeName"],
                    "description": row["description"] or ""
                }
                for row in rows
            }

    # Implant info

    def get_implant_info(self, implant_ids: List[int]) -> List[dict]:
        """Get implant info with attribute bonuses."""
        if not implant_ids:
            return []

        with self.db.cursor() as cur:
            cur.execute("""
                SELECT
                    t."typeID" as type_id,
                    t."typeName" as type_name,
                    COALESCE(slot.value, 0) as slot,
                    COALESCE(perc.value, 0) as perception_bonus,
                    COALESCE(mem.value, 0) as memory_bonus,
                    COALESCE(will.value, 0) as willpower_bonus,
                    COALESCE(intel.value, 0) as intelligence_bonus,
                    COALESCE(cha.value, 0) as charisma_bonus
                FROM "invTypes" t
                LEFT JOIN (SELECT "typeID", COALESCE("valueInt","valueFloat")::int as value
                           FROM "dgmTypeAttributes" WHERE "attributeID" = 331) slot
                    ON slot."typeID" = t."typeID"
                LEFT JOIN (SELECT "typeID", COALESCE("valueInt","valueFloat")::int as value
                           FROM "dgmTypeAttributes" WHERE "attributeID" = 178) perc
                    ON perc."typeID" = t."typeID"
                LEFT JOIN (SELECT "typeID", COALESCE("valueInt","valueFloat")::int as value
                           FROM "dgmTypeAttributes" WHERE "attributeID" = 177) mem
                    ON mem."typeID" = t."typeID"
                LEFT JOIN (SELECT "typeID", COALESCE("valueInt","valueFloat")::int as value
                           FROM "dgmTypeAttributes" WHERE "attributeID" = 179) will
                    ON will."typeID" = t."typeID"
                LEFT JOIN (SELECT "typeID", COALESCE("valueInt","valueFloat")::int as value
                           FROM "dgmTypeAttributes" WHERE "attributeID" = 176) intel
                    ON intel."typeID" = t."typeID"
                LEFT JOIN (SELECT "typeID", COALESCE("valueInt","valueFloat")::int as value
                           FROM "dgmTypeAttributes" WHERE "attributeID" = 175) cha
                    ON cha."typeID" = t."typeID"
                WHERE t."typeID" = ANY(%s)
            """, (list(implant_ids),))
            rows = cur.fetchall()
            return [dict(row) for row in rows]

    # Asset caching

    def get_cached_assets(self, character_id: int) -> List[dict]:
        """Get cached assets from database."""
        with self.db.cursor() as cur:
            cur.execute("""
                SELECT type_id, type_name, quantity, location_id,
                       location_name, location_type
                FROM character_asset_cache
                WHERE character_id = %s
                AND cached_at > NOW() - INTERVAL '30 minutes'
            """, (character_id,))
            rows = cur.fetchall()
            return [dict(row) for row in rows]

    def save_assets(self, character_id: int, assets: List[dict]) -> None:
        """Save assets to cache."""
        with self.db.cursor() as cur:
            # Clear existing
            cur.execute(
                "DELETE FROM character_asset_cache WHERE character_id = %s",
                (character_id,)
            )

            # Insert new
            for asset in assets:
                cur.execute("""
                    INSERT INTO character_asset_cache
                    (character_id, type_id, type_name, quantity,
                     location_id, location_name, location_type, cached_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                """, (
                    character_id,
                    asset.get("type_id"),
                    asset.get("type_name"),
                    asset.get("quantity", 1),
                    asset.get("location_id"),
                    asset.get("location_name"),
                    asset.get("location_type")
                ))

    # Sync persistence methods

    def _batch_resolve_type_names(self, cur, type_ids: list) -> dict:
        """Resolve type IDs to names from SDE using an existing cursor."""
        if not type_ids:
            return {}
        cur.execute(
            'SELECT "typeID", "typeName" FROM "invTypes" WHERE "typeID" = ANY(%s)',
            (type_ids,),
        )
        return {row["typeID"]: row["typeName"] for row in cur.fetchall()}

    def persist_wallet(self, character_id: int, balance: float) -> None:
        """Insert wallet balance snapshot to character_wallets."""
        try:
            with self.db.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO character_wallets (character_id, balance, recorded_at)
                    VALUES (%s, %s, NOW())
                    ON CONFLICT (character_id, recorded_at) DO NOTHING
                    """,
                    (character_id, balance),
                )
        except Exception as e:
            logger.error(f"persist_wallet failed for {character_id}: {e}")

    def persist_skills(self, character_id: int, skills_list: List[Dict]) -> None:
        """Upsert skills to character_skills with ON CONFLICT DO UPDATE."""
        try:
            with self.db.cursor() as cur:
                # Resolve skill names in batch
                skill_ids = [s["skill_id"] for s in skills_list]
                names = self._batch_resolve_type_names(cur, skill_ids)

                for s in skills_list:
                    skill_id = s["skill_id"]
                    cur.execute(
                        """
                        INSERT INTO character_skills
                            (character_id, skill_id, skill_name,
                             active_skill_level, trained_skill_level,
                             skillpoints_in_skill, last_synced)
                        VALUES (%s, %s, %s, %s, %s, %s, NOW())
                        ON CONFLICT (character_id, skill_id) DO UPDATE SET
                            skill_name = EXCLUDED.skill_name,
                            active_skill_level = EXCLUDED.active_skill_level,
                            trained_skill_level = EXCLUDED.trained_skill_level,
                            skillpoints_in_skill = EXCLUDED.skillpoints_in_skill,
                            last_synced = NOW()
                        """,
                        (
                            character_id,
                            skill_id,
                            names.get(skill_id, "Unknown"),
                            s.get("active_skill_level", 0),
                            s.get("trained_skill_level", 0),
                            s.get("skillpoints_in_skill", 0),
                        ),
                    )
        except Exception as e:
            logger.error(f"persist_skills failed for {character_id}: {e}")

    def persist_implants(self, character_id: int, implant_type_ids: List[int]) -> None:
        """DELETE + INSERT implants to character_implants.

        Resolves implant names via _batch_resolve_type_names() and slot numbers
        from dgmTypeAttributes (attributeID 331).
        """
        try:
            with self.db.cursor() as cur:
                # Clear existing implants
                cur.execute(
                    "DELETE FROM character_implants WHERE character_id = %s",
                    (character_id,),
                )

                if not implant_type_ids:
                    return

                # Resolve implant names in batch
                names = self._batch_resolve_type_names(cur, implant_type_ids)

                # Resolve implant slots (attributeID 331 = implantness / slot)
                cur.execute(
                    """
                    SELECT "typeID",
                           COALESCE("valueInt", "valueFloat")::int as value
                    FROM "dgmTypeAttributes"
                    WHERE "attributeID" = 331
                      AND "typeID" = ANY(%s)
                    """,
                    (implant_type_ids,),
                )
                slots = {row["typeID"]: row["value"] for row in cur.fetchall()}

                for type_id in implant_type_ids:
                    cur.execute(
                        """
                        INSERT INTO character_implants
                            (character_id, implant_type_id, implant_name, slot)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (character_id, implant_type_id) DO UPDATE SET
                            implant_name = EXCLUDED.implant_name,
                            slot = EXCLUDED.slot
                        """,
                        (
                            character_id,
                            type_id,
                            names.get(type_id, "Unknown"),
                            slots.get(type_id, 0),
                        ),
                    )
        except Exception as e:
            logger.error(f"persist_implants failed for {character_id}: {e}")

    def get_implant_type_ids(self, character_id: int) -> List[int]:
        """Get implant type IDs for a character, ordered by slot."""
        with self.db.cursor() as cur:
            cur.execute(
                """
                SELECT implant_type_id
                FROM character_implants
                WHERE character_id = %s
                ORDER BY slot
                """,
                (character_id,),
            )
            return [row["implant_type_id"] for row in cur.fetchall()]

    def persist_skillqueue(self, character_id: int, queue_list: List[Dict]) -> None:
        """DELETE + INSERT skill queue to character_skill_queue."""
        try:
            with self.db.cursor() as cur:
                # Resolve skill names in batch
                skill_ids = [q["skill_id"] for q in queue_list if q.get("skill_id")]
                names = self._batch_resolve_type_names(cur, skill_ids)

                # Clear existing queue
                cur.execute(
                    "DELETE FROM character_skill_queue WHERE character_id = %s",
                    (character_id,),
                )

                for q in queue_list:
                    skill_id = q.get("skill_id")
                    cur.execute(
                        """
                        INSERT INTO character_skill_queue
                            (character_id, queue_position, skill_id, skill_name,
                             finished_level, start_date, finish_date,
                             training_start_sp, level_start_sp, level_end_sp,
                             last_synced)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                        """,
                        (
                            character_id,
                            q.get("queue_position", 0),
                            skill_id,
                            names.get(skill_id, "Unknown"),
                            q.get("finished_level", 0),
                            q.get("start_date"),
                            q.get("finish_date"),
                            q.get("training_start_sp", 0),
                            q.get("level_start_sp", 0),
                            q.get("level_end_sp", 0),
                        ),
                    )
        except Exception as e:
            logger.error(f"persist_skillqueue failed for {character_id}: {e}")

    def persist_location(self, character_id: int, location_dict: Dict) -> None:
        """Upsert to character_location (PK is character_id)."""
        try:
            with self.db.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO character_location
                        (character_id, solar_system_id, station_id,
                         structure_id, last_updated)
                    VALUES (%s, %s, %s, %s, NOW())
                    ON CONFLICT (character_id) DO UPDATE SET
                        solar_system_id = EXCLUDED.solar_system_id,
                        station_id = EXCLUDED.station_id,
                        structure_id = EXCLUDED.structure_id,
                        last_updated = NOW()
                    """,
                    (
                        character_id,
                        location_dict.get("solar_system_id"),
                        location_dict.get("station_id"),
                        location_dict.get("structure_id"),
                    ),
                )
        except Exception as e:
            logger.error(f"persist_location failed for {character_id}: {e}")

    def persist_ship(self, character_id: int, ship_dict: Dict) -> None:
        """Upsert to character_ship (PK is character_id)."""
        try:
            with self.db.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO character_ship
                        (character_id, ship_item_id, ship_type_id,
                         ship_name, ship_type_name, last_updated)
                    VALUES (%s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (character_id) DO UPDATE SET
                        ship_item_id = EXCLUDED.ship_item_id,
                        ship_type_id = EXCLUDED.ship_type_id,
                        ship_name = EXCLUDED.ship_name,
                        ship_type_name = EXCLUDED.ship_type_name,
                        last_updated = NOW()
                    """,
                    (
                        character_id,
                        ship_dict.get("ship_item_id"),
                        ship_dict.get("ship_type_id"),
                        ship_dict.get("ship_name"),
                        ship_dict.get("ship_type_name"),
                    ),
                )
        except Exception as e:
            logger.error(f"persist_ship failed for {character_id}: {e}")

    def _batch_resolve_station_names(self, cur, location_ids: list) -> dict:
        """Batch resolve station names from SDE staStations."""
        if not location_ids:
            return {}
        cur.execute(
            'SELECT "stationID", "stationName" FROM "staStations" WHERE "stationID" = ANY(%s)',
            (location_ids,)
        )
        return {row["stationID"]: row["stationName"] for row in cur.fetchall()}

    def persist_orders(self, character_id: int, orders: list):
        """Upsert active orders. Mark missing ones as expired.

        Orders should come from model_dump(by_alias=True) which already has
        resolved type_name, location_name, and region_id.
        """
        try:
            with self.db.cursor() as cur:
                # Mark all existing active orders as expired
                cur.execute("""
                    UPDATE character_orders SET state = 'expired', last_synced = NOW()
                    WHERE character_id = %s AND state = 'active'
                """, (character_id,))

                for o in orders:
                    cur.execute("""
                        INSERT INTO character_orders
                            (character_id, order_id, type_id, type_name, location_id,
                             location_name, region_id, is_buy_order, price, volume_total,
                             volume_remain, min_volume, "range", duration, escrow,
                             is_corporation, issued, state, last_synced)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'active',NOW())
                        ON CONFLICT (character_id, order_id)
                        DO UPDATE SET price = EXCLUDED.price,
                            volume_remain = EXCLUDED.volume_remain,
                            type_name = EXCLUDED.type_name,
                            location_name = EXCLUDED.location_name,
                            region_id = EXCLUDED.region_id,
                            state = 'active', last_synced = NOW()
                    """, (character_id, o.get("order_id"), o.get("type_id"),
                          o.get("type_name", f"Type {o.get('type_id')}"),
                          o.get("location_id"),
                          o.get("location_name", f"Station {o.get('location_id')}"),
                          o.get("region_id") or 10000002,
                          o.get("is_buy_order", False), o.get("price", 0),
                          o.get("volume_total", 0), o.get("volume_remain", 0),
                          o.get("min_volume", 1), o.get("range"),
                          o.get("duration"), o.get("escrow"),
                          o.get("is_corporation", False), o.get("issued")))
        except Exception as e:
            logger.error(f"Failed to persist orders for {character_id}: {e}")

    def persist_industry_jobs(self, character_id: int, jobs: list):
        """Upsert industry jobs."""
        try:
            with self.db.cursor() as cur:
                type_ids = list({j.get("blueprint_type_id") for j in jobs if j.get("blueprint_type_id")}
                               | {j.get("product_type_id") for j in jobs if j.get("product_type_id")})
                type_names = self._batch_resolve_type_names(cur, type_ids)

                for j in jobs:
                    cur.execute("""
                        INSERT INTO character_industry_jobs
                            (character_id, job_id, installer_id, facility_id,
                             activity_id, blueprint_id, blueprint_type_id,
                             blueprint_type_name, blueprint_location_id,
                             output_location_id, product_type_id, product_type_name,
                             runs, cost, licensed_runs, probability,
                             status, start_date, end_date, last_synced)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW())
                        ON CONFLICT (character_id, job_id)
                        DO UPDATE SET status = EXCLUDED.status,
                            last_synced = NOW()
                    """, (character_id, j.get("job_id"), j.get("installer_id", character_id),
                          j.get("facility_id"), j.get("activity_id"),
                          j.get("blueprint_id"), j.get("blueprint_type_id"),
                          type_names.get(j.get("blueprint_type_id")),
                          j.get("blueprint_location_id"), j.get("output_location_id"),
                          j.get("product_type_id"),
                          type_names.get(j.get("product_type_id")),
                          j.get("runs"), j.get("cost"),
                          j.get("licensed_runs"), j.get("probability"),
                          j.get("status"), j.get("start_date"), j.get("end_date")))
        except Exception as e:
            logger.error(f"Failed to persist industry jobs for {character_id}: {e}")

    def update_sync_status(self, character_id: int, results: dict) -> None:
        """Update sync timestamps for successfully synced data types."""
        try:
            with self.db.cursor() as cur:
                # Ensure row exists
                cur.execute("""
                    INSERT INTO character_sync_status (character_id)
                    VALUES (%s) ON CONFLICT (character_id) DO NOTHING
                """, (character_id,))

                field_map = {
                    "wallet": "wallets_synced_at",
                    "skills": "skills_synced_at",
                    "skillqueue": "skill_queue_synced_at",
                    "orders": "orders_synced_at",
                    "jobs": "industry_jobs_synced_at",
                    "blueprints": "blueprints_synced_at",
                    "assets": "assets_synced_at",
                    "location": "location_synced_at",
                    "ship": "ship_synced_at",
                }
                updates = [f"{col} = NOW()" for key, col in field_map.items() if results.get(key)]
                updates.append("updated_at = NOW()")

                if updates:
                    cur.execute(
                        f"UPDATE character_sync_status SET {', '.join(updates)} WHERE character_id = %s",
                        (character_id,)
                    )
        except Exception as e:
            logger.error(f"update_sync_status failed for {character_id}: {e}")

    # Batch DB reads for summary endpoint

    def _to_iso(self, val) -> Optional[str]:
        """Convert datetime/date to ISO string, pass through strings."""
        if val is None:
            return None
        if isinstance(val, datetime):
            return val.isoformat()
        if hasattr(val, "isoformat"):
            return val.isoformat()
        return str(val)

    def get_all_summaries_from_db(self, character_ids: Optional[List[int]] = None) -> List[Dict[str, Any]]:
        """Read all character summary data from DB in batch queries.

        Returns a list of dicts matching the /summary/all JSON structure.
        This replaces 28+ ESI calls with 8 SQL queries.
        """
        characters = self.get_all_characters()
        if not characters:
            return []

        if character_ids:
            id_set = set(character_ids)
            characters = [c for c in characters if c.get("character_id") in id_set]

        char_ids = [c["character_id"] for c in characters]
        if not char_ids:
            return []

        # Build lookup: character_id -> character_name
        name_map = {c["character_id"]: c.get("character_name", "Unknown") for c in characters}

        # Run all batch queries with a single cursor
        with self.db.cursor() as cur:
            # 1. Latest wallet balance per character
            cur.execute("""
                SELECT DISTINCT ON (character_id)
                    character_id, balance, recorded_at
                FROM character_wallets
                WHERE character_id = ANY(%s)
                ORDER BY character_id, recorded_at DESC
            """, (char_ids,))
            wallet_rows = {r["character_id"]: r for r in cur.fetchall()}

            # 2. Skills total SP + count
            cur.execute("""
                SELECT character_id,
                       SUM(skillpoints_in_skill) as total_sp,
                       COUNT(*) as skill_count
                FROM character_skills
                WHERE character_id = ANY(%s)
                GROUP BY character_id
            """, (char_ids,))
            skill_rows = {r["character_id"]: r for r in cur.fetchall()}

            # 3. Skill queue
            cur.execute("""
                SELECT character_id, queue_position, skill_id, skill_name,
                       finished_level, start_date, finish_date
                FROM character_skill_queue
                WHERE character_id = ANY(%s)
                ORDER BY character_id, queue_position
            """, (char_ids,))
            queue_by_char: Dict[int, list] = defaultdict(list)
            for r in cur.fetchall():
                queue_by_char[r["character_id"]].append(r)

            # 4. Location with system name
            cur.execute("""
                SELECT cl.character_id, cl.solar_system_id, cl.station_id,
                       cl.structure_id,
                       ss."solarSystemName" as solar_system_name
                FROM character_location cl
                LEFT JOIN "mapSolarSystems" ss
                    ON ss."solarSystemID" = cl.solar_system_id
                WHERE cl.character_id = ANY(%s)
            """, (char_ids,))
            location_rows = {r["character_id"]: r for r in cur.fetchall()}

            # 5. Current ship
            cur.execute("""
                SELECT cs.character_id, cs.ship_item_id, cs.ship_type_id,
                       cs.ship_name, cs.ship_type_name
                FROM character_ship cs
                WHERE cs.character_id = ANY(%s)
            """, (char_ids,))
            ship_rows = {r["character_id"]: r for r in cur.fetchall()}

            # 6. Active industry jobs
            cur.execute("""
                SELECT character_id, job_id, activity_id,
                       blueprint_type_name, product_type_name,
                       status, start_date, end_date, runs
                FROM character_industry_jobs
                WHERE character_id = ANY(%s)
                  AND status IN ('active', 'paused', 'ready')
                ORDER BY character_id, end_date
            """, (char_ids,))
            jobs_by_char: Dict[int, list] = defaultdict(list)
            for r in cur.fetchall():
                jobs_by_char[r["character_id"]].append(r)

            # 7. Sync status
            cur.execute("""
                SELECT * FROM character_sync_status
                WHERE character_id = ANY(%s)
            """, (char_ids,))
            sync_rows = {r["character_id"]: r for r in cur.fetchall()}

        # Assemble response dicts
        results = []
        for cid in char_ids:
            char_data: Dict[str, Any] = {
                "character_id": cid,
                "character_name": name_map.get(cid, "Unknown"),
                "wallet": None,
                "skills": None,
                "skillqueue": None,
                "location": None,
                "ship": None,
                "industry": None,
                "last_synced": None,
            }

            # Wallet
            wr = wallet_rows.get(cid)
            if wr:
                balance = wr["balance"]
                char_data["wallet"] = {
                    "balance": float(balance) if isinstance(balance, Decimal) else balance,
                }

            # Skills
            sr = skill_rows.get(cid)
            if sr:
                total_sp = sr["total_sp"]
                char_data["skills"] = {
                    "total_sp": int(total_sp) if total_sp else 0,
                    "skill_count": sr["skill_count"],
                }

            # Skill queue
            queue_items = queue_by_char.get(cid)
            if queue_items is not None:
                char_data["skillqueue"] = {
                    "queue": [
                        {
                            "queue_position": q["queue_position"],
                            "skill_id": q["skill_id"],
                            "skill_name": q["skill_name"],
                            "finished_level": q["finished_level"],
                            "start_date": self._to_iso(q["start_date"]),
                            "finish_date": self._to_iso(q["finish_date"]),
                        }
                        for q in queue_items
                    ],
                }

            # Location
            lr = location_rows.get(cid)
            if lr:
                char_data["location"] = {
                    "solar_system_id": lr["solar_system_id"],
                    "solar_system_name": lr.get("solar_system_name"),
                    "station_id": lr.get("station_id"),
                    "structure_id": lr.get("structure_id"),
                }

            # Ship
            shr = ship_rows.get(cid)
            if shr:
                char_data["ship"] = {
                    "ship_type_id": shr["ship_type_id"],
                    "ship_type_name": shr.get("ship_type_name"),
                    "ship_item_id": shr.get("ship_item_id"),
                }

            # Industry jobs
            job_items = jobs_by_char.get(cid)
            if job_items is not None:
                char_data["industry"] = {
                    "jobs": [
                        {
                            "job_id": j["job_id"],
                            "activity_id": j["activity_id"],
                            "blueprint_type_name": j.get("blueprint_type_name"),
                            "product_type_name": j.get("product_type_name"),
                            "status": j["status"],
                            "start_date": self._to_iso(j["start_date"]),
                            "end_date": self._to_iso(j["end_date"]),
                            "runs": j.get("runs"),
                        }
                        for j in job_items
                    ],
                    "active_jobs": len(job_items),
                }

            # Sync status
            ss = sync_rows.get(cid)
            if ss:
                char_data["last_synced"] = self._to_iso(ss.get("updated_at"))

            results.append(char_data)

        return results

    # Character token lookup (via auth-service)

    def get_character_token(self, character_id: int) -> Optional[str]:
        """Get access token for character from auth-service."""
        return self.auth_client.get_valid_token(character_id)

    def get_all_characters(self) -> List[dict]:
        """Get all authenticated characters from auth-service."""
        return self.auth_client.get_characters()
