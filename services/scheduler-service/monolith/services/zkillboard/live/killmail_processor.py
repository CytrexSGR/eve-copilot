"""
Killmail Processing Module.

Provides fetching, parsing, and persistent storage of killmail data.
"""

from typing import Dict, List, Optional, TYPE_CHECKING

import aiohttp

from src.database import get_db_connection
from .models import (
    LiveKillmail,
    ZKILL_API_URL, ZKILL_USER_AGENT, ZKILL_REQUEST_TIMEOUT,
    ESI_KILLMAIL_URL, ESI_USER_AGENT
)
from .ship_classifier import classify_ship, is_capital_ship, safe_int_value

# Import business metrics for tracking kills
try:
    from eve_shared.monitoring.business_metrics import track_kill_processed
except ImportError:
    # Graceful fallback if eve_shared not installed
    def track_kill_processed(*args, **kwargs):
        pass


class KillmailProcessorMixin:
    """Mixin providing killmail processing methods for ZKillboardLiveService."""

    async def fetch_recent_kills(self) -> List[Dict]:
        """
        Fetch recent killmails from zkillboard API.

        Returns list of zkillboard kill entries (killmail_id + hash).
        Full killmail data must be fetched from ESI.
        """
        session = await self._get_session()

        try:
            async with session.get(
                ZKILL_API_URL,
                headers={"User-Agent": ZKILL_USER_AGENT},
                timeout=aiohttp.ClientTimeout(total=ZKILL_REQUEST_TIMEOUT)
            ) as response:
                if response.status == 200:
                    kills = await response.json()
                    return kills if isinstance(kills, list) else []

                return []

        except Exception as e:
            print(f"Error fetching from zkillboard API: {e}")
            return []

    async def fetch_killmail_from_esi(self, killmail_id: int, hash_str: str) -> Optional[Dict]:
        """
        Fetch full killmail data from ESI.

        NOTE: This is a convenience method for the mixin. The canonical implementation
        with rate limiting is in services/zkillboard/redisq_client.py:ZKillRedisQClient.
        When using the ZKillRedisQClient, prefer its fetch_killmail_from_esi() method
        which includes proper rate limiting and session management.

        Args:
            killmail_id: Killmail ID
            hash_str: zkillboard hash for this killmail

        Returns:
            Full killmail dict or None if failed
        """
        if not killmail_id or not hash_str:
            return None

        session = await self._get_session()
        url = ESI_KILLMAIL_URL.format(killmail_id=killmail_id, hash=hash_str)

        try:
            async with session.get(
                url,
                headers={"User-Agent": ESI_USER_AGENT},
                timeout=aiohttp.ClientTimeout(total=ZKILL_REQUEST_TIMEOUT)
            ) as response:
                if response.status == 200:
                    return await response.json()

                print(f"[ESI] Failed to fetch killmail {killmail_id}: HTTP {response.status}")
                return None

        except Exception as e:
            print(f"[ESI] Error fetching killmail {killmail_id}: {e}")
            return None

    def parse_killmail(self, killmail: Dict, zkb: Dict) -> Optional[LiveKillmail]:
        """
        Parse ESI killmail + zkillboard data into structured LiveKillmail.

        Args:
            killmail: ESI killmail dict
            zkb: zkillboard metadata dict

        Returns:
            LiveKillmail object or None if invalid
        """
        try:

            # Extract core data
            killmail_id = killmail.get("killmail_id")
            solar_system_id = killmail.get("solar_system_id")
            killmail_time = killmail.get("killmail_time")

            if not all([killmail_id, solar_system_id, killmail_time]):
                return None

            # Get region from our mapping
            region_id = self.system_region_map.get(solar_system_id)
            if not region_id:
                # Skip wormhole systems and unknown systems
                return None

            # Victim data
            victim = killmail.get("victim", {})
            ship_type_id = victim.get("ship_type_id")

            if not ship_type_id:
                return None

            # Attacker analysis
            attackers = killmail.get("attackers", [])
            attacker_count = len(attackers)
            is_solo = attacker_count == 1
            is_npc = zkb.get("npc", False)

            # Extract attacker corps and alliances
            attacker_corporations = []
            attacker_alliances = []
            for attacker in attackers:
                corp_id = attacker.get("corporation_id")
                if corp_id:
                    attacker_corporations.append(corp_id)
                alliance_id = attacker.get("alliance_id")
                if alliance_id:
                    attacker_alliances.append(alliance_id)

            # Item segregation: destroyed vs dropped
            items = victim.get("items", [])
            destroyed_items = []
            dropped_items = []

            for item in items:
                item_type_id = item.get("item_type_id")
                qty_destroyed = item.get("quantity_destroyed", 0)
                qty_dropped = item.get("quantity_dropped", 0)
                flag = item.get("flag")           # Slot position (11-18=Low, 19-26=Mid, 27-34=High, 5=Cargo)
                singleton = item.get("singleton") # 0=stackable, 1=assembled/singleton

                if item_type_id:
                    if qty_destroyed > 0:
                        destroyed_items.append({
                            "item_type_id": item_type_id,
                            "quantity": qty_destroyed,
                            "flag": flag,
                            "singleton": singleton
                        })
                    if qty_dropped > 0:
                        dropped_items.append({
                            "item_type_id": item_type_id,
                            "quantity": qty_dropped,
                            "flag": flag,
                            "singleton": singleton
                        })

            return LiveKillmail(
                killmail_id=killmail_id,
                killmail_time=killmail_time,
                solar_system_id=solar_system_id,
                region_id=region_id,
                ship_type_id=ship_type_id,
                ship_value=zkb.get("totalValue", 0.0),
                victim_character_id=victim.get("character_id"),
                victim_corporation_id=victim.get("corporation_id"),
                victim_alliance_id=victim.get("alliance_id"),
                attacker_count=attacker_count,
                is_solo=is_solo,
                is_npc=is_npc,
                destroyed_items=destroyed_items,
                dropped_items=dropped_items,
                attacker_corporations=attacker_corporations,
                attacker_alliances=attacker_alliances
            )

        except Exception as e:
            print(f"Error parsing killmail: {e}")
            return None

    def store_persistent_kill(self, kill: LiveKillmail, zkb_data: Dict, esi_killmail: Dict) -> Optional[int]:
        """
        Store killmail permanently in PostgreSQL with atomic battle assignment.

        CRITICAL: This method atomically:
        1. Inserts the killmail with battle_id assignment in ONE query
        2. Returns battle_id if kill was associated with a battle
        3. Returns None if kill was a duplicate (ON CONFLICT DO NOTHING)

        This prevents the 18.5x kill inflation bug by ensuring:
        - Each kill is counted EXACTLY ONCE
        - Battle stats are updated from battle_stats_computed view (always accurate)

        Args:
            kill: Parsed killmail data
            zkb_data: zkillboard metadata (points, npc, awox flags)
            esi_killmail: Full ESI killmail data (for attacker details)

        Returns:
            battle_id if kill was stored and associated with battle
            0 if kill was stored but not part of a battle
            None if kill was a duplicate (already exists)
        """
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    # Determine if victim ship is a capital
                    is_capital = is_capital_ship(kill.ship_type_id)

                    # Classify ship type (official EVE classification)
                    ship_category, ship_role = classify_ship(kill.ship_type_id)

                    # Legacy ship_class for backward compatibility
                    ship_class = ship_category if ship_category else None

                    # Find final blow attacker
                    final_blow_char_id = None
                    final_blow_corp_id = None
                    final_blow_alliance_id = None
                    attackers = esi_killmail.get("attackers", [])
                    for attacker in attackers:
                        if attacker.get("final_blow", False):
                            final_blow_char_id = attacker.get("character_id")
                            final_blow_corp_id = attacker.get("corporation_id")
                            final_blow_alliance_id = attacker.get("alliance_id")
                            break

                    # UNIFIED EVENT SYSTEM: Ensure every kill has a battle/event
                    # This creates a new battle if none exists in the system
                    self.ensure_battle_exists(kill)

                    # ATOMIC INSERT with battle assignment
                    # The subquery finds an active battle in the same system
                    # Since we just called ensure_battle_exists(), one will always exist
                    cur.execute("""
                        INSERT INTO killmails (
                            killmail_id, killmail_time, solar_system_id, region_id,
                            ship_type_id, ship_value, ship_class, ship_category, ship_role,
                            victim_character_id, victim_corporation_id, victim_alliance_id,
                            attacker_count,
                            final_blow_character_id, final_blow_corporation_id, final_blow_alliance_id,
                            is_solo, is_npc, is_capital,
                            zkb_points, zkb_npc, zkb_awox,
                            processed_at,
                            battle_id
                        ) VALUES (
                            %s, %s, %s, %s,
                            %s, %s, %s, %s, %s,
                            %s, %s, %s,
                            %s,
                            %s, %s, %s,
                            %s, %s, %s,
                            %s, %s, %s,
                            CURRENT_TIMESTAMP,
                            (SELECT battle_id FROM battles
                             WHERE solar_system_id = %s
                               AND status = 'active'
                               AND last_kill_at > NOW() - INTERVAL '30 minutes'
                             ORDER BY battle_id DESC
                             LIMIT 1)
                        )
                        ON CONFLICT (killmail_id) DO NOTHING
                        RETURNING killmail_id, battle_id
                    """, (
                        kill.killmail_id,
                        kill.killmail_time,
                        kill.solar_system_id,
                        kill.region_id,
                        kill.ship_type_id,
                        safe_int_value(kill.ship_value),
                        ship_class,
                        ship_category,
                        ship_role,
                        kill.victim_character_id,
                        kill.victim_corporation_id,
                        kill.victim_alliance_id,
                        kill.attacker_count,
                        final_blow_char_id,
                        final_blow_corp_id,
                        final_blow_alliance_id,
                        kill.is_solo,
                        kill.is_npc,
                        is_capital,
                        zkb_data.get("points"),
                        zkb_data.get("npc", False),
                        zkb_data.get("awox", False),
                        kill.solar_system_id  # For the battle subquery
                    ))

                    # Check if insert was successful (not a duplicate)
                    result = cur.fetchone()
                    if result is None:
                        # Duplicate kill - DO NOT count
                        print(f"[DUPLICATE] Killmail {kill.killmail_id} already exists - skipping")
                        return None

                    inserted_killmail_id, battle_id = result

                    # Track business metrics for Prometheus
                    # Get alliance names for proper labeling
                    attacker_alliance_name = "Unknown"
                    victim_alliance_name = "Unknown"

                    if final_blow_alliance_id:
                        cur.execute(
                            "SELECT alliance_name FROM alliance_name_cache WHERE alliance_id = %s",
                            (final_blow_alliance_id,)
                        )
                        row = cur.fetchone()
                        if row:
                            attacker_alliance_name = row[0] if isinstance(row, tuple) else row.get('alliance_name', 'Unknown')

                    if kill.victim_alliance_id:
                        cur.execute(
                            "SELECT alliance_name FROM alliance_name_cache WHERE alliance_id = %s",
                            (kill.victim_alliance_id,)
                        )
                        row = cur.fetchone()
                        if row:
                            victim_alliance_name = row[0] if isinstance(row, tuple) else row.get('alliance_name', 'Unknown')

                    # Track the kill in Prometheus metrics
                    track_kill_processed(
                        attacker_alliance=attacker_alliance_name,
                        victim_alliance=victim_alliance_name,
                        isk_value=float(kill.ship_value or 0)
                    )

                    # 2. Insert destroyed items (with flag and singleton for fitting analysis)
                    for item in kill.destroyed_items:
                        cur.execute("""
                            INSERT INTO killmail_items (
                                killmail_id, item_type_id, quantity, was_destroyed, flag, singleton
                            ) VALUES (%s, %s, %s, %s, %s, %s)
                        """, (
                            kill.killmail_id,
                            item['item_type_id'],
                            item['quantity'],
                            True,
                            item.get('flag'),
                            item.get('singleton')
                        ))

                    # 3. Insert dropped items (with flag and singleton for fitting analysis)
                    for item in kill.dropped_items:
                        cur.execute("""
                            INSERT INTO killmail_items (
                                killmail_id, item_type_id, quantity, was_destroyed, flag, singleton
                            ) VALUES (%s, %s, %s, %s, %s, %s)
                        """, (
                            kill.killmail_id,
                            item['item_type_id'],
                            item['quantity'],
                            False,
                            item.get('flag'),
                            item.get('singleton')
                        ))

                    # 4. Insert attacker details
                    for attacker in attackers:
                        cur.execute("""
                            INSERT INTO killmail_attackers (
                                killmail_id,
                                character_id,
                                corporation_id,
                                alliance_id,
                                ship_type_id,
                                weapon_type_id,
                                damage_done,
                                is_final_blow
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            kill.killmail_id,
                            attacker.get("character_id"),
                            attacker.get("corporation_id"),
                            attacker.get("alliance_id"),
                            attacker.get("ship_type_id"),
                            attacker.get("weapon_type_id"),
                            attacker.get("damage_done", 0),
                            attacker.get("final_blow", False)
                        ))

                    # 5. If kill is associated with a battle, refresh stats from computed view
                    # This ensures battle statistics are ALWAYS accurate
                    if battle_id:
                        # Use killmail_time to update last_kill_at (not server time)
                        # This prevents negative durations due to ESI processing delay
                        cur.execute("""
                            UPDATE battles b SET
                                last_kill_at = GREATEST(last_kill_at, %s)
                            WHERE b.battle_id = %s
                        """, (kill.killmail_time, battle_id,))

                        # Refresh battle stats from computed view (always accurate)
                        cur.execute("SELECT refresh_battle_stats(%s)", (battle_id,))

                        # Update status_level based on total_kills
                        cur.execute("""
                            UPDATE battles SET status_level = CASE
                                WHEN total_kills >= 200 THEN 'hellcamp'
                                WHEN total_kills >= 50 THEN 'battle'
                                WHEN total_kills >= 10 THEN 'brawl'
                                ELSE 'gank'
                            END
                            WHERE battle_id = %s
                        """, (battle_id,))

                        print(f"[BATTLE] Kill {kill.killmail_id} added to battle {battle_id}")

                    conn.commit()

                    # Return battle_id (or 0 if not part of battle)
                    return battle_id if battle_id else 0

        except Exception as e:
            print(f"Error storing killmail {kill.killmail_id} to PostgreSQL: {e}")
            return None

    def _get_system_name(self, system_id: int) -> str:
        """Get system name from DB"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT solarSystemName FROM mapSolarSystems WHERE solarSystemID = %s",
                        (system_id,)
                    )
                    result = cur.fetchone()
                    return result[0] if result else f"System {system_id}"
        except Exception:
            return f"System {system_id}"

    def _get_ship_name(self, type_id: int) -> str:
        """Get ship name from DB"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT typeName FROM invTypes WHERE typeID = %s",
                        (type_id,)
                    )
                    result = cur.fetchone()
                    return result[0] if result else f"Ship {type_id}"
        except Exception:
            return f"Ship {type_id}"
