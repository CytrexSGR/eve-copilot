"""Danger Zones & Activity Endpoints."""

import logging
from datetime import datetime, timezone
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Query

from app.database import db_cursor
from app.services.intelligence.esi_utils import batch_resolve_alliance_names, batch_resolve_alliance_info
from eve_shared.utils.error_handling import handle_endpoint_errors

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/fast/{alliance_id}/danger-zones")
@handle_endpoint_errors()
def get_danger_zones(
    alliance_id: int,
    days: int = Query(7, ge=1, le=30),
    limit: int = Query(10, ge=1, le=20)
) -> List[Dict[str, Any]]:
    """Get most dangerous systems for an alliance (where they lose ships)."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT
                system_id::INT,
                death_count::INT,
                s."solarSystemName" as system_name,
                s."regionID" as region_id,
                r."regionName" as region_name
            FROM (
                SELECT
                    key as system_id,
                    SUM(value::INT) as death_count
                FROM intelligence_hourly_stats,
                LATERAL jsonb_each_text(systems_deaths) as j(key, value)
                WHERE alliance_id = %s
                  AND hour_bucket >= NOW() - INTERVAL '%s days'
                  AND systems_deaths != '{}'
                GROUP BY key
            ) zone_stats
            LEFT JOIN "mapSolarSystems" s ON zone_stats.system_id::INT = s."solarSystemID"
            LEFT JOIN "mapRegions" r ON s."regionID" = r."regionID"
            ORDER BY death_count DESC
            LIMIT %s
        """, (alliance_id, days, limit))

        return [
            {
                "system_id": row["system_id"],
                "deaths": row["death_count"],
                "system_name": row.get("system_name") or f"System {row['system_id']}",
                "region_id": row.get("region_id"),
                "region_name": row.get("region_name") or "Unknown"
            }
            for row in cur.fetchall()
        ]

@router.get("/fast/{alliance_id}/ships-lost")
@handle_endpoint_errors()
def get_ships_lost(
    alliance_id: int,
    days: int = Query(7, ge=1, le=30),
    limit: int = Query(10, ge=1, le=20)
) -> List[Dict[str, Any]]:
    """
    Get most commonly lost ship types (OPTIMIZED - uses intelligence_hourly_stats).

    Phase 4: Migrated from killmails GROUP BY to pre-aggregated ships_lost JSONB.
    Reduces query time from ~300ms to <50ms. Note: ISK values require fallback to killmails.
    """
    with db_cursor() as cur:
        # Get ship counts from hourly_stats
        cur.execute("""
            WITH ship_agg AS (
                SELECT
                    key::INT as ship_type_id,
                    SUM(value::INT) as ship_count
                FROM intelligence_hourly_stats,
                LATERAL jsonb_each_text(ships_lost)
                WHERE alliance_id = %s
                  AND hour_bucket >= NOW() - make_interval(days => %s::INT)
                  AND ships_lost != '{}'::jsonb
                GROUP BY key
                ORDER BY SUM(value::INT) DESC
                LIMIT %s
            )
            SELECT
                sa.ship_type_id,
                sa.ship_count,
                COALESCE(SUM(k.ship_value), 0) as total_isk_lost,
                t."typeName" as ship_name,
                g."groupName" as ship_class
            FROM ship_agg sa
            LEFT JOIN killmails k ON k.ship_type_id = sa.ship_type_id
                AND k.victim_alliance_id = %s
                AND k.killmail_time >= NOW() - make_interval(days => %s::INT)
            LEFT JOIN "invTypes" t ON sa.ship_type_id = t."typeID"
            LEFT JOIN "invGroups" g ON t."groupID" = g."groupID"
            GROUP BY sa.ship_type_id, sa.ship_count, t."typeName", g."groupName"
            ORDER BY sa.ship_count DESC
        """, (alliance_id, days, limit, alliance_id, days))

        return [
            {
                "type_id": row["ship_type_id"],
                "count": row["ship_count"],
                "isk_lost": float(row["total_isk_lost"] or 0),
                "ship_name": row.get("ship_name") or f"Unknown ({row['ship_type_id']})",
                "ship_class": row.get("ship_class") or "Unknown"
            }
            for row in cur.fetchall()
        ]

@router.get("/fast/{alliance_id}/top-enemies")
@handle_endpoint_errors()
def get_top_enemies(
    alliance_id: int,
    days: int = Query(7, ge=1, le=30),
    limit: int = Query(10, ge=1, le=20)
) -> List[Dict[str, Any]]:
    """
    Get alliances that kill this alliance the most (OPTIMIZED - uses intelligence_hourly_stats).

    Phase 4: Migrated from killmails+JOIN to pre-aggregated killed_by JSONB.
    Reduces query time from ~1.7s to <50ms by using killed_by field.
    """
    with db_cursor() as cur:
        # Query pre-aggregated killed_by from hourly_stats
        cur.execute("""
            WITH enemy_agg AS (
                SELECT
                    key::BIGINT as enemy_id,
                    SUM((value->>'kills')::INT) as kills,
                    SUM((value->>'isk')::BIGINT) as isk_destroyed
                FROM intelligence_hourly_stats,
                LATERAL jsonb_each(killed_by)
                WHERE alliance_id = %s
                  AND hour_bucket >= NOW() - make_interval(days => %s::INT)
                  AND killed_by != '{}'::jsonb
                GROUP BY key
            )
            SELECT enemy_id, kills, isk_destroyed
            FROM enemy_agg
            ORDER BY kills DESC
            LIMIT %s
        """, (alliance_id, days, limit))

        rows = cur.fetchall()

    # Resolve alliance names and tickers via ESI
    enemy_ids = [row["enemy_id"] for row in rows]
    alliance_info = batch_resolve_alliance_info(enemy_ids)

    return [
        {
            "alliance_id": row["enemy_id"],
            "alliance_name": alliance_info.get(row["enemy_id"], {}).get("name", f"Alliance {row['enemy_id']}"),
            "ticker": alliance_info.get(row["enemy_id"], {}).get("ticker", "???"),
            "kills": row["kills"],
            "isk_destroyed": float(row["isk_destroyed"] or 0)
        }
        for row in rows
    ]

@router.get("/fast/{alliance_id}/hourly")
@handle_endpoint_errors()
def get_hourly_activity(
    alliance_id: int,
    days: int = Query(7, ge=1, le=30)
) -> Dict[str, Any]:
    """Get hourly activity distribution (24h breakdown) WITH peak/safe hour analysis."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT
                EXTRACT(HOUR FROM hour_bucket)::INT as hour,
                SUM(kills) as kills,
                SUM(deaths) as deaths
            FROM intelligence_hourly_stats
            WHERE alliance_id = %s
              AND hour_bucket >= NOW() - INTERVAL '%s days'
            GROUP BY EXTRACT(HOUR FROM hour_bucket)
            ORDER BY hour
        """, (alliance_id, days))

        # Initialize 24 hours
        kills_by_hour = [0] * 24
        deaths_by_hour = [0] * 24

        for row in cur.fetchall():
            hour = row["hour"]
            kills_by_hour[hour] = row["kills"] or 0
            deaths_by_hour[hour] = row["deaths"] or 0

        # Calculate peak danger hours (top 50% of deaths)
        max_deaths = max(deaths_by_hour) if deaths_by_hour else 0
        threshold = max_deaths * 0.5

        peak_hours = [h for h, d in enumerate(deaths_by_hour) if d >= threshold and d > 0]
        safe_hours = [h for h, d in enumerate(deaths_by_hour) if d < threshold * 0.3]

        # Find contiguous windows
        peak_start = min(peak_hours) if peak_hours else 18
        peak_end = max(peak_hours) if peak_hours else 22
        safe_start = min(safe_hours) if safe_hours else 4
        safe_end = max(safe_hours) if safe_hours else 10

        return {
            "kills_by_hour": kills_by_hour,
            "deaths_by_hour": deaths_by_hour,
            "peak_danger_start": peak_start,
            "peak_danger_end": peak_end,
            "safe_start": safe_start,
            "safe_end": safe_end
        }

@router.get("/fast/{alliance_id}/hunting/hot-zones")
@handle_endpoint_errors()
def get_hunting_hot_zones(
    alliance_id: int,
    days: int = Query(30, ge=1, le=90),
    limit: int = Query(10, ge=1, le=20)
) -> List[Dict[str, Any]]:
    """Get systems where target alliance is most active (kills + deaths)."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT
                k.solar_system_id as system_id,
                SUM(CASE WHEN k.victim_alliance_id = %s THEN 1 ELSE 0 END) as deaths,
                COUNT(DISTINCT CASE WHEN ka.alliance_id = %s THEN k.killmail_id END) as kills,
                s."solarSystemName" as system_name,
                r."regionName" as region_name
            FROM killmails k
            LEFT JOIN killmail_attackers ka ON k.killmail_id = ka.killmail_id
            LEFT JOIN "mapSolarSystems" s ON k.solar_system_id = s."solarSystemID"
            LEFT JOIN "mapRegions" r ON s."regionID" = r."regionID"
            WHERE k.killmail_time >= NOW() - INTERVAL '%s days'
              AND (k.victim_alliance_id = %s OR ka.alliance_id = %s)
            GROUP BY k.solar_system_id, s."solarSystemName", r."regionName"
            ORDER BY (SUM(CASE WHEN k.victim_alliance_id = %s THEN 1 ELSE 0 END) + COUNT(DISTINCT CASE WHEN ka.alliance_id = %s THEN k.killmail_id END)) DESC
            LIMIT %s
        """, (alliance_id, alliance_id, days, alliance_id, alliance_id, alliance_id, alliance_id, limit))

        return [
            {
                "system_id": row["system_id"],
                "system_name": row.get("system_name") or f"System {row['system_id']}",
                "region_name": row.get("region_name") or "Unknown",
                "kills": row["kills"],
                "deaths": row["deaths"],
                "total_activity": row["kills"] + row["deaths"]
            }
            for row in cur.fetchall()
        ]

@router.get("/fast/{alliance_id}/hunting/strike-window")
@handle_endpoint_errors()
def get_hunting_strike_window(
    alliance_id: int,
    days: int = Query(30, ge=1, le=90)
) -> Dict[str, Any]:
    """Get optimal strike timing based on activity patterns."""
    with db_cursor() as cur:
        # Get hourly activity pattern
        cur.execute("""
            SELECT
                EXTRACT(HOUR FROM killmail_time)::INT as hour,
                COUNT(*) as activity,
                COUNT(CASE WHEN victim_alliance_id = %s THEN 1 END) as their_deaths,
                COUNT(DISTINCT CASE WHEN ka.alliance_id = %s THEN k.killmail_id END) as their_kills
            FROM killmails k
            LEFT JOIN killmail_attackers ka ON k.killmail_id = ka.killmail_id
            WHERE k.killmail_time >= NOW() - INTERVAL '%s days'
              AND (k.victim_alliance_id = %s OR ka.alliance_id = %s)
            GROUP BY EXTRACT(HOUR FROM killmail_time)
            ORDER BY hour
        """, (alliance_id, alliance_id, days, alliance_id, alliance_id))

        hourly_data = {row["hour"]: row for row in cur.fetchall()}

        # Fill all 24 hours
        activity_by_hour = []
        for h in range(24):
            data = hourly_data.get(h, {"activity": 0, "their_deaths": 0, "their_kills": 0})
            activity_by_hour.append({
                "hour": h,
                "activity": data["activity"] or 0,
                "their_deaths": data["their_deaths"] or 0,
                "their_kills": data["their_kills"] or 0
            })

        # Calculate peak and weak hours
        total_activity = sum(h["activity"] for h in activity_by_hour)
        if total_activity > 0:
            max_activity = max(h["activity"] for h in activity_by_hour)
            threshold_high = max_activity * 0.6
            threshold_low = max_activity * 0.2

            peak_hours = [h["hour"] for h in activity_by_hour if h["activity"] >= threshold_high]
            weak_hours = [h["hour"] for h in activity_by_hour if h["activity"] <= threshold_low]
        else:
            peak_hours = list(range(19, 24))
            weak_hours = list(range(4, 10))

        # Get last 24h summary
        cur.execute("""
            SELECT
                COUNT(*) as total_kills,
                COUNT(*) FILTER (WHERE k.is_capital = true) as capital_kills
            FROM killmails k
            JOIN killmail_attackers ka ON k.killmail_id = ka.killmail_id
            WHERE k.killmail_time >= NOW() - INTERVAL '24 hours'
              AND ka.alliance_id = %s
        """, (alliance_id,))
        last_24h = cur.fetchone()

        # Peak hours as range
        peak_start = min(peak_hours) if peak_hours else 19
        peak_end = max(peak_hours) if peak_hours else 23
        weak_start = min(weak_hours) if weak_hours else 4
        weak_end = max(weak_hours) if weak_hours else 8

        return {
            "activity_by_hour": activity_by_hour,
            "peak_hours": {
                "start": f"{peak_start:02d}:00",
                "end": f"{peak_end:02d}:00",
                "pct": round(sum(h["activity"] for h in activity_by_hour if h["hour"] in peak_hours) / max(total_activity, 1) * 100)
            },
            "weak_hours": {
                "start": f"{weak_start:02d}:00",
                "end": f"{weak_end:02d}:00",
                "pct": round(sum(h["activity"] for h in activity_by_hour if h["hour"] in weak_hours) / max(total_activity, 1) * 100)
            },
            "last_24h": {
                "kills": last_24h["total_kills"] if last_24h else 0,
                "capital_deployments": last_24h["capital_kills"] if last_24h else 0
            },
            "recommendation": f"Strike {weak_start:02d}:00-{weak_end:02d}:00 UTC (Low Activity)"
        }

@router.get("/fast/{alliance_id}/hunting/priority-targets")
@handle_endpoint_errors()
def get_hunting_priority_targets(
    alliance_id: int,
    days: int = Query(30, ge=1, le=90),
    limit: int = Query(20, ge=1, le=50)
) -> List[Dict[str, Any]]:
    """Get high-value targets (pilots who die often with expensive ships)."""
    with db_cursor() as cur:
        # Get pilot death stats with ship values
        cur.execute("""
            WITH pilot_deaths AS (
                SELECT
                    k.victim_character_id as character_id,
                    COUNT(*) as deaths,
                    AVG(k.ship_value) as avg_ship_value,
                    SUM(k.ship_value) as total_isk_lost,
                    MAX(k.killmail_time) as last_death
                FROM killmails k
                WHERE k.victim_alliance_id = %s
                  AND k.killmail_time >= NOW() - INTERVAL '%s days'
                  AND k.victim_character_id IS NOT NULL
                  AND k.ship_value > 10000000  -- Min 10M ISK ships
                GROUP BY k.victim_character_id
                HAVING COUNT(*) >= 2  -- At least 2 deaths
            ),
            pilot_kills AS (
                SELECT
                    ka.character_id,
                    COUNT(DISTINCT k.killmail_id) as kills
                FROM killmails k
                JOIN killmail_attackers ka ON k.killmail_id = ka.killmail_id
                WHERE ka.alliance_id = %s
                  AND k.killmail_time >= NOW() - INTERVAL '%s days'
                  AND ka.character_id IS NOT NULL
                GROUP BY ka.character_id
            ),
            pilot_ships AS (
                SELECT
                    k.victim_character_id as character_id,
                    t."typeName" as ship_name,
                    COUNT(*) as ship_count,
                    ROW_NUMBER() OVER (PARTITION BY k.victim_character_id ORDER BY COUNT(*) DESC) as rn
                FROM killmails k
                LEFT JOIN "invTypes" t ON k.ship_type_id = t."typeID"
                WHERE k.victim_alliance_id = %s
                  AND k.killmail_time >= NOW() - INTERVAL '%s days'
                  AND k.victim_character_id IS NOT NULL
                GROUP BY k.victim_character_id, t."typeName"
            )
            SELECT
                pd.character_id,
                COALESCE(c.character_name, 'Unknown') as character_name,
                pd.deaths,
                COALESCE(pk.kills, 0) as kills,
                pd.avg_ship_value,
                pd.total_isk_lost,
                pd.last_death,
                -- Whale Score: (avg_value * deaths) / (efficiency + 0.1)
                ROUND(
                    (pd.avg_ship_value / 1000000000.0 * pd.deaths) /
                    (COALESCE(pk.kills, 0)::FLOAT / GREATEST(COALESCE(pk.kills, 0) + pd.deaths, 1) + 0.1)
                )::INT as whale_score,
                ARRAY_AGG(DISTINCT ps.ship_name) FILTER (WHERE ps.rn <= 3) as typical_ships
            FROM pilot_deaths pd
            LEFT JOIN pilot_kills pk ON pd.character_id = pk.character_id
            LEFT JOIN pilot_ships ps ON pd.character_id = ps.character_id AND ps.rn <= 3
            LEFT JOIN character_name_cache c ON pd.character_id = c.character_id
            GROUP BY pd.character_id, c.character_name, pd.deaths, pk.kills,
                     pd.avg_ship_value, pd.total_isk_lost, pd.last_death
            ORDER BY whale_score DESC
            LIMIT %s
        """, (alliance_id, days, alliance_id, days, alliance_id, days, limit))

        results = []
        for row in cur.fetchall():
            whale_score = row["whale_score"] or 0
            if whale_score >= 70:
                category = "whale"
            elif whale_score >= 40:
                category = "shark"
            else:
                category = "fish"

            # Calculate time since last death
            last_death = row["last_death"]
            if last_death:
                now = datetime.now(timezone.utc)
                delta = now - last_death.replace(tzinfo=timezone.utc)
                if delta.days > 0:
                    last_active = f"{delta.days}d ago"
                elif delta.seconds > 3600:
                    last_active = f"{delta.seconds // 3600}h ago"
                else:
                    last_active = f"{delta.seconds // 60}m ago"
            else:
                last_active = "Unknown"

            results.append({
                "character_id": row["character_id"],
                "character_name": row["character_name"],
                "whale_score": whale_score,
                "whale_category": category,
                "isk_per_death": float(row["avg_ship_value"] or 0),
                "total_isk_lost": float(row["total_isk_lost"] or 0),
                "deaths": row["deaths"],
                "kills": row["kills"],
                "efficiency": round(row["kills"] / max(row["kills"] + row["deaths"], 1) * 100, 1),
                "typical_ships": [s for s in (row["typical_ships"] or []) if s],
                "last_active": last_active
            })

        return results

@router.get("/fast/{alliance_id}/hunting/counter-doctrine")
@handle_endpoint_errors()
def get_hunting_counter_doctrine(
    alliance_id: int,
    days: int = Query(30, ge=1, le=90)
) -> Dict[str, Any]:
    """Get enemy ship meta and recommended counter fleet composition."""
    with db_cursor() as cur:
        # Get their ship usage (what they fly when attacking)
        cur.execute("""
            SELECT
                t."typeName" as ship_name,
                t."typeID" as type_id,
                g."groupName" as ship_class,
                COUNT(*) as usage_count,
                ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) as pct
            FROM killmail_attackers ka
            JOIN killmails k ON ka.killmail_id = k.killmail_id
            LEFT JOIN "invTypes" t ON ka.ship_type_id = t."typeID"
            LEFT JOIN "invGroups" g ON t."groupID" = g."groupID"
            WHERE ka.alliance_id = %s
              AND k.killmail_time >= NOW() - INTERVAL '%s days'
              AND ka.ship_type_id IS NOT NULL
              AND t."typeName" IS NOT NULL
            GROUP BY t."typeName", t."typeID", g."groupName"
            ORDER BY usage_count DESC
            LIMIT 10
        """, (alliance_id, days))

        their_meta = [
            {
                "ship": row["ship_name"],
                "type_id": row["type_id"],
                "ship_class": row["ship_class"] or "Unknown",
                "pct": float(row["pct"]),
                "count": row["usage_count"]
            }
            for row in cur.fetchall()
        ]

        # Estimate damage profile based on ship races
        cur.execute("""
            SELECT
                CASE
                    WHEN t."typeName" LIKE '%%Caldari%%' OR g."groupName" LIKE '%%Caldari%%'
                         OR t."typeName" IN ('Cerberus', 'Caracal', 'Drake', 'Ferox', 'Raven', 'Rokh')
                        THEN 'kinetic'
                    WHEN t."typeName" LIKE '%%Minmatar%%' OR g."groupName" LIKE '%%Minmatar%%'
                         OR t."typeName" IN ('Vagabond', 'Muninn', 'Hurricane', 'Maelstrom', 'Tornado')
                        THEN 'explosive'
                    WHEN t."typeName" LIKE '%%Amarr%%' OR g."groupName" LIKE '%%Amarr%%'
                         OR t."typeName" IN ('Zealot', 'Sacrilege', 'Harbinger', 'Abaddon', 'Oracle')
                        THEN 'em'
                    WHEN t."typeName" LIKE '%%Gallente%%' OR g."groupName" LIKE '%%Gallente%%'
                         OR t."typeName" IN ('Ishtar', 'Deimos', 'Myrmidon', 'Megathron', 'Talos')
                        THEN 'thermal'
                    ELSE 'kinetic'
                END as damage_type,
                COUNT(*) as count
            FROM killmail_attackers ka
            JOIN killmails k ON ka.killmail_id = k.killmail_id
            LEFT JOIN "invTypes" t ON ka.ship_type_id = t."typeID"
            LEFT JOIN "invGroups" g ON t."groupID" = g."groupID"
            WHERE ka.alliance_id = %s
              AND k.killmail_time >= NOW() - INTERVAL '%s days'
              AND ka.ship_type_id IS NOT NULL
            GROUP BY 1
        """, (alliance_id, days))

        damage_counts = {row["damage_type"]: row["count"] for row in cur.fetchall()}
        total_damage = sum(damage_counts.values()) or 1

        damage_profile = {
            "kinetic": round(damage_counts.get("kinetic", 0) / total_damage * 100),
            "thermal": round(damage_counts.get("thermal", 0) / total_damage * 100),
            "em": round(damage_counts.get("em", 0) / total_damage * 100),
            "explosive": round(damage_counts.get("explosive", 0) / total_damage * 100)
        }

        # Determine primary damage type
        primary_damage = max(damage_profile, key=damage_profile.get)

        # Counter recommendations
        tank_recommendations = {
            "kinetic": "Shield Tank with Kinetic Hardeners",
            "thermal": "Armor Tank with Thermal Hardeners",
            "em": "Shield Tank with EM Hardeners",
            "explosive": "Armor Tank with Explosive Hardeners"
        }

        # Counter fleets based on ship class
        primary_class = their_meta[0]["ship_class"] if their_meta else "Cruiser"
        counter_fleets = {
            "Heavy Assault Cruiser": {
                "dps": {"ship": "Cerberus", "count": 15, "reason": "Range match, kinetic damage", "type_id": 11993},
                "logi": {"ship": "Scimitar", "count": 4, "reason": "Shield logi, mobile", "type_id": 11978},
                "support": {"ship": "Huginn", "count": 2, "reason": "Web support", "type_id": 11961},
                "tackle": {"ship": "Sabre", "count": 3, "reason": "Interdictor", "type_id": 22456}
            },
            "Battlecruiser": {
                "dps": {"ship": "Ferox", "count": 20, "reason": "Rail sniper, range advantage", "type_id": 37480},
                "logi": {"ship": "Basilisk", "count": 5, "reason": "Cap chain logi", "type_id": 11985},
                "support": {"ship": "Huginn", "count": 2, "reason": "Web support", "type_id": 11961},
                "tackle": {"ship": "Sabre", "count": 3, "reason": "Interdictor", "type_id": 22456}
            },
            "Battleship": {
                "dps": {"ship": "Nightmare", "count": 15, "reason": "Beam sniper, EM/Therm", "type_id": 17736},
                "logi": {"ship": "Guardian", "count": 5, "reason": "Armor cap chain", "type_id": 11987},
                "support": {"ship": "Bhaalgorn", "count": 2, "reason": "Neut pressure", "type_id": 17920},
                "tackle": {"ship": "Sabre", "count": 3, "reason": "Interdictor", "type_id": 22456}
            }
        }

        recommended_fleet = counter_fleets.get(primary_class, counter_fleets["Heavy Assault Cruiser"])

        return {
            "their_meta": their_meta,
            "damage_profile": damage_profile,
            "primary_damage_type": primary_damage,
            "tank_recommendation": tank_recommendations.get(primary_damage, "Shield Tank"),
            "recommended_fleet": recommended_fleet,
            "reasoning": f"Counter {primary_class} doctrine with range/mobility advantage"
        }
