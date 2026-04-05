"""Wormhole Intelligence Helper Functions - Shared code for Alliance and Corporation endpoints."""

import logging
from typing import Dict, Any, List, Tuple
from app.database import db_cursor
from app.services.intelligence.esi_utils import batch_resolve_alliance_names, batch_resolve_corporation_names

logger = logging.getLogger(__name__)

# Wormhole system ID range
WH_SYSTEM_MIN = 31000000
WH_SYSTEM_MAX = 32000000


def get_summary_stats(entity_id: int, entity_field: str, days: int) -> Dict[str, Any]:
    """
    Get wormhole summary statistics for an entity (alliance or corporation).

    Args:
        entity_id: Alliance ID or Corporation ID
        entity_field: 'alliance_id' or 'corporation_id'
        days: Time period in days

    Returns:
        Summary dict with kills, deaths, ISK, efficiency, K/D ratio
    """
    with db_cursor() as cur:
        # Kills as attacker in J-space
        cur.execute(f"""
            SELECT
                COUNT(DISTINCT k.killmail_id) as kills,
                COALESCE(SUM(k.ship_value), 0) as isk_destroyed,
                COUNT(DISTINCT k.solar_system_id) as systems_active
            FROM killmails k
            JOIN killmail_attackers ka ON k.killmail_id = ka.killmail_id
            WHERE ka.{entity_field} = %s
              AND ka.is_final_blow = true
              AND k.solar_system_id >= %s
              AND k.solar_system_id < %s
              AND k.killmail_time >= NOW() - INTERVAL '%s days'
        """, (entity_id, WH_SYSTEM_MIN, WH_SYSTEM_MAX, days))
        kills_row = cur.fetchone()

        # Deaths in J-space
        victim_field = 'victim_alliance_id' if entity_field == 'alliance_id' else 'victim_corporation_id'
        cur.execute(f"""
            SELECT
                COUNT(*) as deaths,
                COALESCE(SUM(k.ship_value), 0) as isk_lost,
                COUNT(DISTINCT k.solar_system_id) as systems_died_in
            FROM killmails k
            WHERE k.{victim_field} = %s
              AND k.solar_system_id >= %s
              AND k.solar_system_id < %s
              AND k.killmail_time >= NOW() - INTERVAL '%s days'
        """, (entity_id, WH_SYSTEM_MIN, WH_SYSTEM_MAX, days))
        deaths_row = cur.fetchone()

        kills = kills_row['kills'] or 0
        deaths = deaths_row['deaths'] or 0
        isk_destroyed = float(kills_row['isk_destroyed'] or 0)
        isk_lost = float(deaths_row['isk_lost'] or 0)

        return {
            "kills": kills,
            "deaths": deaths,
            "isk_destroyed": isk_destroyed,
            "isk_lost": isk_lost,
            "efficiency": round(isk_destroyed / (isk_destroyed + isk_lost) * 100, 1) if (isk_destroyed + isk_lost) > 0 else 0,
            "systems_active": kills_row['systems_active'] or 0,
            "kd_ratio": round(kills / deaths, 2) if deaths > 0 else kills
        }


def get_hunting_grounds(entity_id: int, entity_field: str, days: int, limit: int = 10) -> List[Dict]:
    """Get top systems where entity gets kills in J-space."""
    with db_cursor() as cur:
        cur.execute(f"""
            SELECT
                k.solar_system_id as system_id,
                ss."solarSystemName" as system_name,
                wc."wormholeClassID" as wh_class,
                COUNT(DISTINCT k.killmail_id) as kills,
                COALESCE(SUM(k.ship_value), 0) as isk_destroyed
            FROM killmails k
            JOIN killmail_attackers ka ON k.killmail_id = ka.killmail_id
            JOIN "mapSolarSystems" ss ON k.solar_system_id = ss."solarSystemID"
            LEFT JOIN "mapLocationWormholeClasses" wc ON k.solar_system_id = wc."locationID"
            WHERE ka.{entity_field} = %s
              AND ka.is_final_blow = true
              AND k.solar_system_id >= %s
              AND k.solar_system_id < %s
              AND k.killmail_time >= NOW() - INTERVAL '%s days'
            GROUP BY k.solar_system_id, ss."solarSystemName", wc."wormholeClassID"
            ORDER BY kills DESC
            LIMIT %s
        """, (entity_id, WH_SYSTEM_MIN, WH_SYSTEM_MAX, days, limit))

        return [
            {
                "system_id": r["system_id"],
                "system_name": r["system_name"],
                "wh_class": r["wh_class"],
                "kills": r["kills"],
                "isk_destroyed": float(r["isk_destroyed"] or 0)
            }
            for r in cur.fetchall()
        ]


def get_danger_zones(entity_id: int, entity_field: str, days: int, limit: int = 10) -> List[Dict]:
    """Get top systems where entity loses ships in J-space."""
    victim_field = 'victim_alliance_id' if entity_field == 'alliance_id' else 'victim_corporation_id'

    with db_cursor() as cur:
        cur.execute(f"""
            SELECT
                k.solar_system_id as system_id,
                ss."solarSystemName" as system_name,
                wc."wormholeClassID" as wh_class,
                COUNT(*) as deaths,
                COALESCE(SUM(k.ship_value), 0) as isk_lost
            FROM killmails k
            JOIN "mapSolarSystems" ss ON k.solar_system_id = ss."solarSystemID"
            LEFT JOIN "mapLocationWormholeClasses" wc ON k.solar_system_id = wc."locationID"
            WHERE k.{victim_field} = %s
              AND k.solar_system_id >= %s
              AND k.solar_system_id < %s
              AND k.killmail_time >= NOW() - INTERVAL '%s days'
            GROUP BY k.solar_system_id, ss."solarSystemName", wc."wormholeClassID"
            ORDER BY deaths DESC
            LIMIT %s
        """, (entity_id, WH_SYSTEM_MIN, WH_SYSTEM_MAX, days, limit))

        return [
            {
                "system_id": r["system_id"],
                "system_name": r["system_name"],
                "wh_class": r["wh_class"],
                "deaths": r["deaths"],
                "isk_lost": float(r["isk_lost"] or 0)
            }
            for r in cur.fetchall()
        ]


def get_wh_class_distribution(entity_id: int, entity_field: str, days: int) -> List[Dict]:
    """Get wormhole class distribution of kills."""
    with db_cursor() as cur:
        cur.execute(f"""
            SELECT
                wc."wormholeClassID" as wh_class,
                COUNT(DISTINCT k.killmail_id) as kills
            FROM killmails k
            JOIN killmail_attackers ka ON k.killmail_id = ka.killmail_id
            LEFT JOIN "mapLocationWormholeClasses" wc ON k.solar_system_id = wc."locationID"
            WHERE ka.{entity_field} = %s
              AND ka.is_final_blow = true
              AND k.solar_system_id >= %s
              AND k.solar_system_id < %s
              AND k.killmail_time >= NOW() - INTERVAL '%s days'
            GROUP BY wc."wormholeClassID"
            ORDER BY kills DESC
        """, (entity_id, WH_SYSTEM_MIN, WH_SYSTEM_MAX, days))

        return [
            {"wh_class": r["wh_class"], "kills": r["kills"]}
            for r in cur.fetchall()
        ]


def get_top_enemies(entity_id: int, entity_field: str, days: int, limit: int = 10) -> Tuple[List[Dict], bool]:
    """
    Get top enemies (who kill us) in J-space.

    Returns:
        (enemies_list, is_alliance_mode) where is_alliance_mode determines naming resolution
    """
    is_alliance = entity_field == 'alliance_id'
    victim_field = 'victim_alliance_id' if is_alliance else 'victim_corporation_id'
    enemy_field = 'alliance_id' if is_alliance else 'corporation_id'

    with db_cursor() as cur:
        cur.execute(f"""
            SELECT
                ka.{enemy_field} as enemy_id,
                COUNT(*) as kills_against_us
            FROM killmails k
            JOIN killmail_attackers ka ON k.killmail_id = ka.killmail_id
            WHERE k.{victim_field} = %s
              AND ka.{enemy_field} IS NOT NULL
              AND ka.{enemy_field} != %s
              AND ka.is_final_blow = true
              AND k.solar_system_id >= %s
              AND k.solar_system_id < %s
              AND k.killmail_time >= NOW() - INTERVAL '%s days'
            GROUP BY ka.{enemy_field}
            ORDER BY kills_against_us DESC
            LIMIT %s
        """, (entity_id, entity_id, WH_SYSTEM_MIN, WH_SYSTEM_MAX, days, limit))
        enemy_rows = cur.fetchall()

        enemy_ids = [r["enemy_id"] for r in enemy_rows]
        if is_alliance:
            enemy_names = batch_resolve_alliance_names(enemy_ids) if enemy_ids else {}
            name_key = 'alliance_name'
            id_key = 'alliance_id'
        else:
            enemy_names = batch_resolve_corporation_names(enemy_ids) if enemy_ids else {}
            name_key = 'corporation_name'
            id_key = 'corporation_id'

        return [
            {
                id_key: r["enemy_id"],
                name_key: enemy_names.get(r["enemy_id"], f"{'Alliance' if is_alliance else 'Corporation'} {r['enemy_id']}"),
                "kills": r["kills_against_us"]
            }
            for r in enemy_rows
        ], is_alliance


def get_top_victims(entity_id: int, entity_field: str, days: int, limit: int = 10) -> Tuple[List[Dict], bool]:
    """
    Get top victims (who we kill) in J-space.

    Returns:
        (victims_list, is_alliance_mode) where is_alliance_mode determines naming resolution
    """
    is_alliance = entity_field == 'alliance_id'
    victim_field = 'victim_alliance_id' if is_alliance else 'victim_corporation_id'

    with db_cursor() as cur:
        cur.execute(f"""
            SELECT
                k.{victim_field} as victim_id,
                COUNT(*) as kills
            FROM killmails k
            JOIN killmail_attackers ka ON k.killmail_id = ka.killmail_id
            WHERE ka.{entity_field} = %s
              AND ka.is_final_blow = true
              AND k.{victim_field} IS NOT NULL
              AND k.{victim_field} != %s
              AND k.solar_system_id >= %s
              AND k.solar_system_id < %s
              AND k.killmail_time >= NOW() - INTERVAL '%s days'
            GROUP BY k.{victim_field}
            ORDER BY kills DESC
            LIMIT %s
        """, (entity_id, entity_id, WH_SYSTEM_MIN, WH_SYSTEM_MAX, days, limit))
        victim_rows = cur.fetchall()

        victim_ids = [r["victim_id"] for r in victim_rows]
        if is_alliance:
            victim_names = batch_resolve_alliance_names(victim_ids) if victim_ids else {}
            name_key = 'alliance_name'
            id_key = 'alliance_id'
        else:
            victim_names = batch_resolve_corporation_names(victim_ids) if victim_ids else {}
            name_key = 'corporation_name'
            id_key = 'corporation_id'

        return [
            {
                id_key: r["victim_id"],
                name_key: victim_names.get(r["victim_id"], f"{'Alliance' if is_alliance else 'Corporation'} {r['victim_id']}"),
                "kills": r["kills"]
            }
            for r in victim_rows
        ], is_alliance


def get_recent_high_value(entity_id: int, entity_field: str, days: int, min_value: float = 50_000_000, limit: int = 10) -> Tuple[List[Dict], List[Dict]]:
    """
    Get recent high-value kills and losses in J-space.

    Returns:
        (recent_kills, recent_losses)
    """
    victim_field = 'victim_alliance_id' if entity_field == 'alliance_id' else 'victim_corporation_id'

    with db_cursor() as cur:
        # Recent kills
        cur.execute(f"""
            SELECT
                k.killmail_id,
                k.solar_system_id as system_id,
                ss."solarSystemName" as system_name,
                wc."wormholeClassID" as wh_class,
                k.ship_type_id,
                t."typeName" as ship_name,
                k.ship_value as value,
                k.killmail_time as time,
                'kill' as type
            FROM killmails k
            JOIN killmail_attackers ka ON k.killmail_id = ka.killmail_id
            JOIN "mapSolarSystems" ss ON k.solar_system_id = ss."solarSystemID"
            LEFT JOIN "mapLocationWormholeClasses" wc ON k.solar_system_id = wc."locationID"
            LEFT JOIN "invTypes" t ON k.ship_type_id = t."typeID"
            WHERE ka.{entity_field} = %s
              AND ka.is_final_blow = true
              AND k.solar_system_id >= %s
              AND k.solar_system_id < %s
              AND k.killmail_time >= NOW() - INTERVAL '%s days'
              AND k.ship_value > %s
            ORDER BY k.killmail_time DESC
            LIMIT %s
        """, (entity_id, WH_SYSTEM_MIN, WH_SYSTEM_MAX, days, min_value, limit))
        recent_kills = [
            {
                "killmail_id": r["killmail_id"],
                "system_id": r["system_id"],
                "system_name": r["system_name"],
                "wh_class": r["wh_class"],
                "ship_type_id": r["ship_type_id"],
                "ship_name": r["ship_name"] or "Unknown",
                "value": float(r["value"] or 0),
                "time": r["time"].isoformat() if r["time"] else None,
                "type": "kill"
            }
            for r in cur.fetchall()
        ]

        # Recent losses
        cur.execute(f"""
            SELECT
                k.killmail_id,
                k.solar_system_id as system_id,
                ss."solarSystemName" as system_name,
                wc."wormholeClassID" as wh_class,
                k.ship_type_id,
                t."typeName" as ship_name,
                k.ship_value as value,
                k.killmail_time as time,
                'loss' as type
            FROM killmails k
            JOIN "mapSolarSystems" ss ON k.solar_system_id = ss."solarSystemID"
            LEFT JOIN "mapLocationWormholeClasses" wc ON k.solar_system_id = wc."locationID"
            LEFT JOIN "invTypes" t ON k.ship_type_id = t."typeID"
            WHERE k.{victim_field} = %s
              AND k.solar_system_id >= %s
              AND k.solar_system_id < %s
              AND k.killmail_time >= NOW() - INTERVAL '%s days'
              AND k.ship_value > %s
            ORDER BY k.killmail_time DESC
            LIMIT %s
        """, (entity_id, WH_SYSTEM_MIN, WH_SYSTEM_MAX, days, min_value, limit))
        recent_losses = [
            {
                "killmail_id": r["killmail_id"],
                "system_id": r["system_id"],
                "system_name": r["system_name"],
                "wh_class": r["wh_class"],
                "ship_type_id": r["ship_type_id"],
                "ship_name": r["ship_name"] or "Unknown",
                "value": float(r["value"] or 0),
                "time": r["time"].isoformat() if r["time"] else None,
                "type": "loss"
            }
            for r in cur.fetchall()
        ]

        return recent_kills, recent_losses


def get_ships_used(entity_id: int, entity_field: str, days: int, limit: int = 10) -> List[Dict]:
    """Get top ships used by entity in J-space."""
    with db_cursor() as cur:
        cur.execute(f"""
            SELECT
                ka.ship_type_id,
                t."typeName" as ship_name,
                g."groupName" as ship_class,
                COUNT(*) as uses
            FROM killmails k
            JOIN killmail_attackers ka ON k.killmail_id = ka.killmail_id
            LEFT JOIN "invTypes" t ON ka.ship_type_id = t."typeID"
            LEFT JOIN "invGroups" g ON t."groupID" = g."groupID"
            WHERE ka.{entity_field} = %s
              AND ka.ship_type_id IS NOT NULL
              AND ka.ship_type_id > 0
              AND g."groupID" NOT IN (29, 31)  -- Exclude Capsule, Shuttle
              AND k.solar_system_id >= %s
              AND k.solar_system_id < %s
              AND k.killmail_time >= NOW() - INTERVAL '%s days'
            GROUP BY ka.ship_type_id, t."typeName", g."groupName"
            ORDER BY uses DESC
            LIMIT %s
        """, (entity_id, WH_SYSTEM_MIN, WH_SYSTEM_MAX, days, limit))

        return [
            {
                "ship_type_id": r["ship_type_id"],
                "ship_name": r["ship_name"] or "Unknown",
                "ship_class": r["ship_class"] or "Unknown",
                "uses": r["uses"]
            }
            for r in cur.fetchall()
        ]
