"""Dashboard Endpoint - Aggregates all intelligence data."""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import logging
import inspect

from fastapi import APIRouter, HTTPException, Query
import asyncio
import httpx

from .combat_analysis import get_ship_effectiveness, get_damage_taken, get_ewar_threats, get_enemy_vulnerabilities
from .danger_activity import get_danger_zones, get_ships_lost, get_top_enemies, get_hourly_activity
from .economics import get_economics, get_expensive_losses, get_production_needs
from .summary import get_alliance_summary
from app.database import db_cursor
from app.services.intelligence.equipment_service import equipment_intel_service
from app.services.intelligence.esi_utils import batch_resolve_alliance_names, batch_resolve_alliance_info
from app.utils.cache import get_cached, set_cached
from eve_shared.utils.error_handling import handle_endpoint_errors

logger = logging.getLogger(__name__)
router = APIRouter()


def generate_recommendations_sync(
    danger_zones: List[Dict],
    hourly: Dict,
    damage: List[Dict],
    enemies: List[Dict],
    ships: List[Dict]
) -> List[Dict[str, Any]]:
    """Generate tactical recommendations from pre-fetched data (NO DB calls)."""
    recommendations = []
    priority = 1

    try:

        # Avoid recommendation - danger zones
        if danger_zones and danger_zones[0]["deaths"] > 20:
            top_zone = danger_zones[0]
            recommendations.append({
                "priority": priority,
                "category": "avoid",
                "text": f"Avoid {top_zone['system_name']} ({top_zone['region_name']}) - {top_zone['deaths']} deaths recently"
            })
            priority += 1

        # Timing recommendation
        peak_start = hourly.get("peak_danger_start", 18)
        peak_end = hourly.get("peak_danger_end", 22)
        safe_start = hourly.get("safe_start", 6)
        safe_end = hourly.get("safe_end", 12)
        recommendations.append({
            "priority": priority,
            "category": "avoid",
            "text": f"Peak danger: {peak_start}:00-{peak_end}:00 UTC. Safer: {safe_start}:00-{safe_end}:00 UTC"
        })
        priority += 1

        # Tank recommendation - based on damage taken
        if damage:
            top_damage = damage[0]
            recommendations.append({
                "priority": priority,
                "category": "fit",
                "text": f"Prioritize {top_damage['damage_type'].upper()} resist - {top_damage['percentage']}% of incoming damage"
            })
            priority += 1

        # Attack recommendation - enemy vulnerabilities
        if enemies:
            enemy = enemies[0]
            hours = enemy.get("weak_hours", [18, 20])
            recommendations.append({
                "priority": priority,
                "category": "attack",
                "text": f"Strike {enemy['alliance_name']} at {hours[0]}:00-{hours[1]}:00 UTC - {enemy['losses_to_us']} kills achieved"
            })
            priority += 1

        # Doctrine recommendation - ship losses
        if ships and len(ships) >= 2:
            top_ship = ships[0]
            if top_ship["count"] > 30:
                recommendations.append({
                    "priority": priority,
                    "category": "doctrine",
                    "text": f"High {top_ship['ship_name']} losses ({top_ship['count']}x) - consider doctrine review"
                })

    except Exception as e:
        logger.warning(f"Error generating recommendations: {e}")

    return recommendations


@router.get("/fast/{alliance_id}/dashboard")
@handle_endpoint_errors()
async def get_dashboard(
    alliance_id: int,
    days: float = Query(7, ge=0.04, le=30)  # ge=0.04 allows ~1 hour minimum
) -> Dict[str, Any]:
    """Get complete dashboard data in a single call."""
    # Collect all metrics in parallel
    # Helper to wrap sync function results for asyncio.gather
    async def _ensure_coro(val):
        return await val if inspect.isawaitable(val) else val

    (
        summary,
        danger_zones,
        ships_lost,
        top_enemies,
        hourly,
        economics,
        expensive_losses,
        production_needs,
        ship_effectiveness,
        damage_taken,
        ewar_threats,
        enemy_vulnerabilities,
    ) = await asyncio.gather(
        _ensure_coro(get_alliance_summary(alliance_id, days)),
        _ensure_coro(get_danger_zones(alliance_id, days, limit=5)),
        _ensure_coro(get_ships_lost(alliance_id, days, limit=10)),
        _ensure_coro(get_top_enemies(alliance_id, days, limit=5)),
        _ensure_coro(get_hourly_activity(alliance_id, days)),
        _ensure_coro(get_economics(alliance_id, days)),
        _ensure_coro(get_expensive_losses(alliance_id, days, limit=5)),
        _ensure_coro(get_production_needs(alliance_id, days, limit=10)),
        _ensure_coro(get_ship_effectiveness(alliance_id, days)),
        _ensure_coro(get_damage_taken(alliance_id, days)),
        _ensure_coro(get_ewar_threats(alliance_id, days)),
        _ensure_coro(get_enemy_vulnerabilities(alliance_id, days, limit=5)),
    )

    # Generate recommendations from pre-fetched data (no extra DB calls)
    recommendations = generate_recommendations_sync(
        danger_zones=danger_zones[:3],
        hourly=hourly,
        damage=damage_taken,
        enemies=enemy_vulnerabilities[:3],
        ships=ships_lost[:5]
    )

    # Equipment intel (synchronous)
    equipment_intel = equipment_intel_service.get_equipment_intel(alliance_id, days)

    # Resolve alliance names for top_enemies
    enemy_ids = [e["alliance_id"] for e in top_enemies if e.get("alliance_id")]
    if enemy_ids:
        names = batch_resolve_alliance_names(enemy_ids)
        for enemy in top_enemies:
            enemy["alliance_name"] = names.get(enemy["alliance_id"], f"Alliance {enemy['alliance_id']}")

    # Add activity levels to danger zones
    if danger_zones:
        max_deaths = max(z["deaths"] for z in danger_zones)
        for zone in danger_zones:
            ratio = zone["deaths"] / max_deaths if max_deaths > 0 else 0
            if ratio >= 0.8:
                zone["activity_level"] = "CRITICAL"
            elif ratio >= 0.5:
                zone["activity_level"] = "HIGH"
            elif ratio >= 0.25:
                zone["activity_level"] = "MEDIUM"
            else:
                zone["activity_level"] = "LOW"

    # Calculate total weekly production cost
    total_weekly_cost = sum(p.get("estimated_cost", 0) for p in production_needs)

    return {
        "alliance_id": alliance_id,
        "period_days": days,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
        "economics": economics,
        "danger_zones": danger_zones,
        "ships_lost": ships_lost,
        "top_enemies": top_enemies,
        "hourly_activity": hourly,
        "expensive_losses": expensive_losses,
        "ship_effectiveness": ship_effectiveness,
        "production_needs": production_needs,
        "total_weekly_production_cost": total_weekly_cost,
        "damage_taken": damage_taken,
        "ewar_threats": ewar_threats,
        "enemy_vulnerabilities": enemy_vulnerabilities,
        "recommendations": recommendations,
        "equipment_intel": equipment_intel
    }

async def get_alliance_kills_activity(alliance_id: int, days: int = 7) -> Dict[str, Any]:
    """Get kill activity by hour and by day."""
    with db_cursor() as cur:
        # Hourly kills (24h buckets)
        cur.execute("""
            SELECT
                EXTRACT(HOUR FROM hour_bucket) as hour,
                SUM(kills) as kills,
                SUM(isk_destroyed) as isk_destroyed
            FROM intelligence_hourly_stats
            WHERE alliance_id = %s
              AND hour_bucket >= NOW() - INTERVAL '%s days'
            GROUP BY EXTRACT(HOUR FROM hour_bucket)
            ORDER BY hour
        """, (alliance_id, days))
        hourly_kills = [{"hour": int(r["hour"]), "kills": r["kills"], "isk": float(r["isk_destroyed"] or 0)} for r in cur.fetchall()]

        # Daily kills
        cur.execute("""
            SELECT
                DATE(hour_bucket) as day,
                SUM(kills) as kills,
                SUM(deaths) as deaths,
                SUM(isk_destroyed) as isk_destroyed,
                SUM(isk_lost) as isk_lost
            FROM intelligence_hourly_stats
            WHERE alliance_id = %s
              AND hour_bucket >= NOW() - INTERVAL '%s days'
            GROUP BY DATE(hour_bucket)
            ORDER BY day
        """, (alliance_id, days))
        daily = [{"day": r["day"].isoformat(), "kills": r["kills"], "deaths": r["deaths"],
                  "isk_destroyed": float(r["isk_destroyed"] or 0), "isk_lost": float(r["isk_lost"] or 0)} for r in cur.fetchall()]

        return {"hourly_kills": hourly_kills, "daily_activity": daily}


async def get_alliance_ships_killed(alliance_id: int, days: int = 7, limit: int = 20) -> List[Dict[str, Any]]:
    """Get ships killed by this alliance."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT
                key::INT as type_id,
                SUM(value::INT) as count,
                t."typeName" as ship_name,
                g."groupName" as ship_class
            FROM intelligence_hourly_stats,
                LATERAL jsonb_each_text(ships_killed) as j(key, value)
            LEFT JOIN "invTypes" t ON key::INT = t."typeID"
            LEFT JOIN "invGroups" g ON t."groupID" = g."groupID"
            WHERE alliance_id = %s
              AND hour_bucket >= NOW() - INTERVAL '%s days'
            GROUP BY key, t."typeName", g."groupName"
            ORDER BY count DESC
            LIMIT %s
        """, (alliance_id, days, limit))
        return [{"type_id": r["type_id"], "count": r["count"],
                 "ship_name": r["ship_name"] or f"Type {r['type_id']}",
                 "ship_class": r["ship_class"] or "Unknown"} for r in cur.fetchall()]


async def get_alliance_activity_zones(alliance_id: int, days: int = 7, limit: int = 10) -> List[Dict[str, Any]]:
    """Get systems where alliance achieves kills."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT
                j.system_id::INT as system_id,
                SUM(CASE
                    WHEN jsonb_typeof(j.data) = 'object'
                    THEN (j.data->>'kills')::INT
                    ELSE j.data::TEXT::INT
                END) as kills,
                s."solarSystemName" as system_name,
                r."regionName" as region_name,
                s.security as security_status
            FROM intelligence_hourly_stats,
                LATERAL jsonb_each(systems_kills) as j(system_id, data)
            LEFT JOIN "mapSolarSystems" s ON j.system_id::INT = s."solarSystemID"
            LEFT JOIN "mapRegions" r ON s."regionID" = r."regionID"
            WHERE alliance_id = %s
              AND hour_bucket >= NOW() - INTERVAL '%s days'
            GROUP BY j.system_id, s."solarSystemName", r."regionName", s.security
            ORDER BY kills DESC
            LIMIT %s
        """, (alliance_id, days, limit))
        return [{"system_id": r["system_id"], "kills": r["kills"],
                 "system_name": r["system_name"] or f"System {r['system_id']}",
                 "region_name": r["region_name"] or "Unknown",
                 "security_status": round(r["security_status"] or 0, 2)} for r in cur.fetchall()]


async def get_alliance_sovereignty(alliance_id: int) -> Dict[str, Any]:
    """Get sovereignty holdings for an alliance."""
    try:
        # Fetch from ESI
        async with httpx.AsyncClient() as client:
            resp = await client.get("https://esi.evetech.net/latest/sovereignty/structures/", timeout=10)
            if resp.status_code != 200:
                return {"systems": [], "count": 0, "error": "ESI unavailable"}

            structures = resp.json()
            alliance_structures = [s for s in structures if s.get("alliance_id") == alliance_id]

            # Get system names
            system_ids = list(set(s["solar_system_id"] for s in alliance_structures))

            with db_cursor() as cur:
                if system_ids:
                    cur.execute("""
                        SELECT s."solarSystemID", s."solarSystemName", r."regionName", s.security
                        FROM "mapSolarSystems" s
                        LEFT JOIN "mapRegions" r ON s."regionID" = r."regionID"
                        WHERE s."solarSystemID" = ANY(%s)
                    """, (system_ids,))
                    system_info = {r["solarSystemID"]: r for r in cur.fetchall()}
                else:
                    system_info = {}

            systems = []
            for s in alliance_structures:
                sys_id = s["solar_system_id"]
                info = system_info.get(sys_id, {})
                systems.append({
                    "solar_system_id": sys_id,
                    "system_name": info.get("solarSystemName", f"System {sys_id}"),
                    "region_name": info.get("regionName", "Unknown"),
                    "security_status": round(info.get("security", 0), 2),
                    "structure_type_id": s.get("structure_type_id"),
                    "vulnerability_occupancy_level": s.get("vulnerability_occupancy_level"),
                    "vulnerable_start_time": s.get("vulnerable_start_time"),
                    "vulnerable_end_time": s.get("vulnerable_end_time")
                })

            # Aggregate by region
            regions = {}
            for sys in systems:
                rn = sys["region_name"]
                if rn not in regions:
                    regions[rn] = {"count": 0, "avg_adm": 0, "adm_sum": 0}
                regions[rn]["count"] += 1
                adm = sys.get("vulnerability_occupancy_level") or 0
                regions[rn]["adm_sum"] += adm

            for rn in regions:
                if regions[rn]["count"] > 0:
                    regions[rn]["avg_adm"] = round(regions[rn]["adm_sum"] / regions[rn]["count"], 2)

            return {
                "systems": systems,
                "count": len(systems),
                "regions": [{"region_name": k, "system_count": v["count"], "avg_adm": v["avg_adm"]} for k, v in regions.items()]
            }
    except Exception as e:
        logger.warning(f"Failed to fetch sovereignty for {alliance_id}: {e}")
        return {"systems": [], "count": 0, "error": str(e)}


async def get_alliance_recent_battles(alliance_id: int, limit: int = 5) -> List[Dict[str, Any]]:
    """Get recent battles involving this alliance."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT
                b.battle_id,
                b.started_at,
                b.last_kill_at,
                b.total_kills,
                b.total_isk_destroyed,
                b.capital_kills,
                s."solarSystemName" as system_name,
                r."regionName" as region_name,
                bp.kills as alliance_kills,
                bp.losses as alliance_losses,
                bp.isk_destroyed as alliance_isk_destroyed,
                bp.isk_lost as alliance_isk_lost
            FROM battles b
            JOIN battle_participants bp ON b.battle_id = bp.battle_id AND bp.alliance_id = %s
            LEFT JOIN "mapSolarSystems" s ON b.solar_system_id = s."solarSystemID"
            LEFT JOIN "mapRegions" r ON s."regionID" = r."regionID"
            WHERE b.started_at >= NOW() - INTERVAL '30 days'
            ORDER BY b.started_at DESC
            LIMIT %s
        """, (alliance_id, limit))

        return [{
            "battle_id": r["battle_id"],
            "started_at": r["started_at"].isoformat() if r["started_at"] else None,
            "last_kill_at": r["last_kill_at"].isoformat() if r["last_kill_at"] else None,
            "total_kills": r["total_kills"],
            "total_isk_destroyed": float(r["total_isk_destroyed"] or 0),
            "capital_kills": r["capital_kills"],
            "system_name": r["system_name"],
            "region_name": r["region_name"],
            "alliance_kills": r["alliance_kills"],
            "alliance_losses": r["alliance_losses"],
            "alliance_isk_destroyed": float(r["alliance_isk_destroyed"] or 0),
            "alliance_isk_lost": float(r["alliance_isk_lost"] or 0)
        } for r in cur.fetchall()]


async def get_alliance_active_wars(alliance_id: int, limit: int = 5) -> List[Dict[str, Any]]:
    """Get active wars for this alliance."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT
                war_id,
                alliance_a_id,
                alliance_b_id,
                first_kill_at,
                last_kill_at,
                duration_days,
                total_kills,
                total_isk_destroyed,
                status
            FROM alliance_wars
            WHERE (alliance_a_id = %s OR alliance_b_id = %s)
              AND status = 'active'
            ORDER BY total_kills DESC
            LIMIT %s
        """, (alliance_id, alliance_id, limit))

        wars = cur.fetchall()
        if not wars:
            return []

        # Resolve alliance names
        all_alliance_ids = set()
        for w in wars:
            all_alliance_ids.add(w["alliance_a_id"])
            all_alliance_ids.add(w["alliance_b_id"])

        names = batch_resolve_alliance_names(list(all_alliance_ids))

        return [{
            "war_id": r["war_id"],
            "enemy_alliance_id": r["alliance_b_id"] if r["alliance_a_id"] == alliance_id else r["alliance_a_id"],
            "enemy_alliance_name": names.get(r["alliance_b_id"] if r["alliance_a_id"] == alliance_id else r["alliance_a_id"], "Unknown"),
            "first_kill_at": r["first_kill_at"].isoformat() if r["first_kill_at"] else None,
            "last_kill_at": r["last_kill_at"].isoformat() if r["last_kill_at"] else None,
            "duration_days": r["duration_days"],
            "total_kills": r["total_kills"],
            "total_isk_destroyed": float(r["total_isk_destroyed"] or 0)
        } for r in wars]


async def get_coalition_members(alliance_id: int, days: int = 7) -> List[Dict[str, Any]]:
    """
    Detect coalition members based on co-attackers (OPTIMIZED - uses hourly_stats).

    Phase 3: Migrated from killmail_attackers JOINs to pre-aggregated coalition_allies.
    Reduces query time from ~1.9s to <50ms.
    """
    with db_cursor() as cur:
        # Query pre-aggregated coalition_allies from hourly_stats
        cur.execute("""
            WITH allies_agg AS (
                SELECT
                    (ally->>'alliance_id')::BIGINT as ally_id,
                    SUM((ally->>'joint_kills')::INT) as joint_kills
                FROM intelligence_hourly_stats,
                LATERAL jsonb_array_elements(coalition_allies) AS ally
                WHERE alliance_id = %s
                  AND hour_bucket >= NOW() - make_interval(days => %s::INT)
                  AND coalition_allies != '[]'::jsonb
                GROUP BY (ally->>'alliance_id')::BIGINT
                HAVING SUM((ally->>'joint_kills')::INT) >= 10
            )
            SELECT ally_id, joint_kills
            FROM allies_agg
            ORDER BY joint_kills DESC
            LIMIT 20
        """, (alliance_id, days))

        allies = cur.fetchall()
        if not allies:
            return []

        # Resolve names
        ally_ids = [r["ally_id"] for r in allies]
        names = batch_resolve_alliance_names(ally_ids)

        return [{
            "alliance_id": r["ally_id"],
            "alliance_name": names.get(r["ally_id"], f"Alliance {r['ally_id']}"),
            "joint_kills": r["joint_kills"],
            "joint_isk": 0  # Not tracked, kept for API compatibility
        } for r in allies]


def get_equipment_summary_fast(alliance_id: int, days: int = 7) -> Dict[str, Any]:
    """
    Get lightweight equipment summary (OPTIMIZED - uses hourly_stats).

    Phase 3: Migrated from killmail_items JOINs to pre-aggregated equipment_summary.
    Reduces query time from ~2.6s to <50ms.

    Returns simplified equipment profile based on ship race inference.
    For detailed module analysis, use equipment_intel_service.get_equipment_intel().
    """
    with db_cursor() as cur:
        # Aggregate equipment_summary from hourly_stats
        cur.execute("""
            SELECT
                SUM((equipment_summary->>'weapon_laser')::INT) as weapon_laser,
                SUM((equipment_summary->>'weapon_projectile')::INT) as weapon_projectile,
                SUM((equipment_summary->>'weapon_hybrid')::INT) as weapon_hybrid,
                SUM((equipment_summary->>'weapon_missile')::INT) as weapon_missile,
                SUM((equipment_summary->>'weapon_mixed')::INT) as weapon_mixed,
                SUM((equipment_summary->>'tank_shield')::INT) as tank_shield,
                SUM((equipment_summary->>'tank_armor')::INT) as tank_armor,
                SUM((equipment_summary->>'tank_mixed')::INT) as tank_mixed
            FROM intelligence_hourly_stats
            WHERE alliance_id = %s
              AND hour_bucket >= NOW() - make_interval(days => %s::INT)
              AND equipment_summary != '{}'::jsonb
        """, (alliance_id, days))

        row = cur.fetchone()
        if not row:
            return {
                "alliance_id": alliance_id,
                "analysis_period_days": days,
                "weapons_lost": {"primary_weapon_class": "unknown", "distribution": {}},
                "tank_profile": {"doctrine": "unknown", "shield_percent": 0, "armor_percent": 0},
                "strategic_summary": ["Insufficient equipment data"]
            }

        # Parse weapon distribution
        weapon_counts = {
            "laser": row["weapon_laser"] or 0,
            "projectile": row["weapon_projectile"] or 0,
            "hybrid": row["weapon_hybrid"] or 0,
            "missile": row["weapon_missile"] or 0,
            "mixed": row["weapon_mixed"] or 0
        }
        total_weapons = sum(weapon_counts.values())

        weapon_distribution = {}
        primary_weapon = "mixed"
        if total_weapons > 0:
            weapon_distribution = {k: round((v / total_weapons) * 100, 1) for k, v in weapon_counts.items()}
            primary_weapon = max(weapon_counts, key=weapon_counts.get)

        # Parse tank distribution
        tank_shield = row["tank_shield"] or 0
        tank_armor = row["tank_armor"] or 0
        tank_mixed = row["tank_mixed"] or 0
        total_tank = tank_shield + tank_armor + tank_mixed

        shield_pct = round((tank_shield / total_tank) * 100, 1) if total_tank > 0 else 0
        armor_pct = round((tank_armor / total_tank) * 100, 1) if total_tank > 0 else 0

        # Determine doctrine
        if shield_pct > 70:
            doctrine = "heavy_shield"
        elif shield_pct > 55:
            doctrine = "shield_leaning"
        elif armor_pct > 70:
            doctrine = "heavy_armor"
        elif armor_pct > 55:
            doctrine = "armor_leaning"
        else:
            doctrine = "mixed"

        # Generate strategic summary
        strategic_summary = [
            f"Primary weapon class: {primary_weapon.upper()}",
            f"Tank doctrine: {doctrine}",
            "Note: Equipment summary inferred from ship types (lightweight)",
            "Use /equipment-intel endpoint for detailed module analysis"
        ]

        return {
            "alliance_id": alliance_id,
            "analysis_period_days": days,
            "weapons_lost": {
                "primary_weapon_class": primary_weapon,
                "weapon_class_distribution": weapon_distribution,
                "total_weapons_lost": total_weapons
            },
            "tank_profile": {
                "shield_percent": shield_pct,
                "armor_percent": armor_pct,
                "doctrine": doctrine,
                "total_tank_modules": total_tank
            },
            "cargo_intel": {},  # Not available in lightweight version
            "strategic_summary": strategic_summary
        }


async def get_weekly_pattern(alliance_id: int) -> Dict[str, Any]:
    """Get weekly activity pattern (Mon-Sun)."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT
                EXTRACT(DOW FROM hour_bucket) as day_of_week,
                SUM(kills) as kills,
                SUM(deaths) as deaths,
                SUM(isk_destroyed) as isk_destroyed,
                SUM(isk_lost) as isk_lost
            FROM intelligence_hourly_stats
            WHERE alliance_id = %s
              AND hour_bucket >= NOW() - INTERVAL '30 days'
            GROUP BY EXTRACT(DOW FROM hour_bucket)
            ORDER BY day_of_week
        """, (alliance_id,))

        day_names = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        days = []
        for r in cur.fetchall():
            dow = int(r["day_of_week"])
            days.append({
                "day": day_names[dow],
                "day_index": dow,
                "kills": r["kills"],
                "deaths": r["deaths"],
                "isk_destroyed": float(r["isk_destroyed"] or 0),
                "isk_lost": float(r["isk_lost"] or 0)
            })

        # Find best and worst days
        best_day = max(days, key=lambda x: x["kills"] - x["deaths"]) if days else None
        worst_day = min(days, key=lambda x: x["kills"] - x["deaths"]) if days else None

        return {
            "days": days,
            "best_day": best_day["day"] if best_day else None,
            "worst_day": worst_day["day"] if worst_day else None
        }


async def get_security_preference(alliance_id: int, days: int = 7) -> Dict[str, Any]:
    """Analyze activity by security status."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT
                CASE
                    WHEN s.security >= 0.5 THEN 'highsec'
                    WHEN s.security > 0 THEN 'lowsec'
                    ELSE 'nullsec'
                END as security_class,
                SUM(j.value::INT) as deaths
            FROM intelligence_hourly_stats ihs,
                LATERAL jsonb_each_text(systems_deaths) as j(key, value)
            LEFT JOIN "mapSolarSystems" s ON j.key::INT = s."solarSystemID"
            WHERE alliance_id = %s
              AND hour_bucket >= NOW() - INTERVAL '%s days'
            GROUP BY security_class
            ORDER BY deaths DESC
        """, (alliance_id, days))

        result = {"highsec": 0, "lowsec": 0, "nullsec": 0, "wormhole": 0}
        total = 0
        for r in cur.fetchall():
            if r["security_class"]:
                result[r["security_class"]] = r["deaths"]
                total += r["deaths"]

        # Calculate percentages
        if total > 0:
            for k in list(result.keys()):
                result[k + "_pct"] = round(result[k] / total * 100, 1)

        return result


@router.get("/fast/{alliance_id}/complete")
@handle_endpoint_errors()
async def get_complete_intelligence(
    alliance_id: int,
    days: float = Query(7, ge=0.04, le=30)
) -> Dict[str, Any]:
    """
    COMPLETE ALLIANCE INTELLIGENCE

    Returns ALL available intelligence data for an alliance in a single call.
    This is the maximum-information endpoint designed for the alliance detail page.

    Includes:
    - Alliance info (name, ticker, logo)
    - Combat summary (kills, deaths, efficiency, ISK)
    - Kill/loss activity (hourly, daily)
    - Ships killed and lost
    - Danger zones and activity zones
    - Top enemies and coalition members
    - Hourly and weekly patterns
    - Economics (ISK flow, expensive losses)
    - Equipment intel (weapons, tank, cargo)
    - Ship effectiveness analysis
    - Damage taken analysis
    - Enemy vulnerabilities
    - Recommendations
    - Sovereignty holdings
    - Recent battles
    - Active wars

    Performance: 60s TTL cache for massive speedup on repeated requests.
    """
    # Check cache first
    cache_key = f"alliance-complete:{alliance_id}:{days}"
    cached = get_cached(cache_key, ttl_seconds=300)
    if cached:
        return cached

    # Get alliance info from ESI
    alliance_info_batch = batch_resolve_alliance_info([alliance_id])
    alliance_info = alliance_info_batch.get(alliance_id, {"name": f"Alliance {alliance_id}", "ticker": "????"})

    # PARALLEL data collection - all async calls run concurrently
    logger.info(f"Starting parallel data collection for alliance {alliance_id}")
    start_time = datetime.now(timezone.utc)

    # Wrapper to time each function call
    async def timed_call(name, coro):
        func_start = datetime.now(timezone.utc)
        result = await coro if inspect.isawaitable(coro) else coro
        func_elapsed = (datetime.now(timezone.utc) - func_start).total_seconds()
        if func_elapsed > 0.5:  # Log slow functions (>500ms)
            logger.warning(f"[SLOW] {name} took {func_elapsed:.3f}s")
        else:
            logger.debug(f"{name} took {func_elapsed:.3f}s")
        return result

    (
        summary,
        kills_activity,
        ships_killed,
        ships_lost,
        danger_zones,
        activity_zones,
        top_enemies,
        coalition_members,
        hourly,
        weekly,
        security_pref,
        economics,
        expensive_losses,
        production_needs,
        ship_effectiveness,
        damage_taken,
        ewar_threats,
        enemy_vulnerabilities,
        sovereignty,
        recent_battles,
        active_wars
    ) = await asyncio.gather(
        timed_call("get_alliance_summary", get_alliance_summary(alliance_id, days)),
        timed_call("get_alliance_kills_activity", get_alliance_kills_activity(alliance_id, int(days))),
        timed_call("get_alliance_ships_killed", get_alliance_ships_killed(alliance_id, int(days), limit=20)),
        timed_call("get_ships_lost", get_ships_lost(alliance_id, days, limit=20)),
        timed_call("get_danger_zones", get_danger_zones(alliance_id, days, limit=10)),
        timed_call("get_alliance_activity_zones", get_alliance_activity_zones(alliance_id, int(days), limit=10)),
        timed_call("get_top_enemies", get_top_enemies(alliance_id, days, limit=10)),
        timed_call("get_coalition_members", get_coalition_members(alliance_id, int(days))),
        timed_call("get_hourly_activity", get_hourly_activity(alliance_id, days)),
        timed_call("get_weekly_pattern", get_weekly_pattern(alliance_id)),
        timed_call("get_security_preference", get_security_preference(alliance_id, int(days))),
        timed_call("get_economics", get_economics(alliance_id, days)),
        timed_call("get_expensive_losses", get_expensive_losses(alliance_id, days, limit=10)),
        timed_call("get_production_needs", get_production_needs(alliance_id, days, limit=15)),
        timed_call("get_ship_effectiveness", get_ship_effectiveness(alliance_id, days)),
        timed_call("get_damage_taken", get_damage_taken(alliance_id, days)),
        timed_call("get_ewar_threats", get_ewar_threats(alliance_id, days)),
        timed_call("get_enemy_vulnerabilities", get_enemy_vulnerabilities(alliance_id, days, limit=10)),
        timed_call("get_alliance_sovereignty", get_alliance_sovereignty(alliance_id)),
        timed_call("get_alliance_recent_battles", get_alliance_recent_battles(alliance_id, limit=10)),
        timed_call("get_alliance_active_wars", get_alliance_active_wars(alliance_id, limit=10))
    )

    # Equipment intel: Use lightweight pre-aggregated summary from hourly_stats
    equip_start = datetime.now(timezone.utc)
    equipment_intel = get_equipment_summary_fast(alliance_id, days)
    equip_elapsed = (datetime.now(timezone.utc) - equip_start).total_seconds()
    if equip_elapsed > 0.5:
        logger.warning(f"[SLOW] get_equipment_summary_fast took {equip_elapsed:.3f}s")

    # Generate recommendations using already-fetched data (NO duplicate DB calls)
    recommendations = generate_recommendations_sync(
        danger_zones=danger_zones[:3],
        hourly=hourly,
        damage=damage_taken,
        enemies=enemy_vulnerabilities[:3],
        ships=ships_lost[:5]
    )

    elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
    logger.info(f"Parallel data collection completed in {elapsed:.3f}s for alliance {alliance_id}")

    # Resolve all enemy alliance names
    enemy_ids = [e["alliance_id"] for e in top_enemies if e.get("alliance_id")]
    if enemy_ids:
        names = batch_resolve_alliance_names(enemy_ids)
        for enemy in top_enemies:
            enemy["alliance_name"] = names.get(enemy["alliance_id"], f"Alliance {enemy['alliance_id']}")

    # Calculate derived metrics
    total_kills = summary.get("kills", 0)
    total_deaths = summary.get("deaths", 0)
    kd_ratio = round(total_kills / total_deaths, 2) if total_deaths > 0 else total_kills

    # Trend calculation: % change in kills vs previous period
    trend_kills = summary.get("kills_trend", 0)
    prev_kills = summary.get("prev_kills", 0)

    # Peak hour calculation
    peak_hour = hourly.get("peak_danger_start", 19)
    safe_hours = [hourly.get("safe_start", 6), hourly.get("safe_end", 12)]

    result = {
        "alliance_id": alliance_id,
        "period_days": days,
        "generated_at": datetime.now(timezone.utc).isoformat(),

        # Alliance Info
        "alliance_info": alliance_info,

        # Header Stats
        "header": {
            "net_isk": economics.get("isk_balance", 0),
            "efficiency": summary.get("isk_efficiency", summary.get("efficiency", 0)),
            "isk_efficiency": summary.get("isk_efficiency", summary.get("efficiency", 0)),
            "kill_efficiency": summary.get("kill_efficiency", 0),
            "kills": total_kills,
            "deaths": total_deaths,
            "kd_ratio": kd_ratio,
            "active_pilots": summary.get("active_pilots", 0),
            "peak_hour": peak_hour,
            "trend_pct": round(trend_kills / max(prev_kills, 1) * 100, 1) if prev_kills > 0 else 0.0,
            "timeseries": kills_activity.get("daily_activity", [])
        },

        # Combat Data
        "combat": {
            "summary": summary,
            "kills_activity": kills_activity,
            "ships_killed": ships_killed,
            "ships_lost": ships_lost,
            "ship_effectiveness": ship_effectiveness
        },

        # Geographic Data
        "geography": {
            "danger_zones": danger_zones,
            "activity_zones": activity_zones,
            "security_preference": security_pref
        },

        # Temporal Data
        "temporal": {
            "hourly_activity": hourly,
            "weekly_pattern": weekly
        },

        # Enemy Intelligence
        "enemies": {
            "top_enemies": top_enemies,
            "enemy_vulnerabilities": enemy_vulnerabilities,
            "active_wars": active_wars
        },

        # Coalition Data
        "coalition": {
            "detected_allies": coalition_members
        },

        # Economics
        "economics": {
            "summary": economics,
            "expensive_losses": expensive_losses,
            "production_needs": production_needs,
            "total_weekly_production_cost": sum(p.get("estimated_cost", 0) for p in production_needs)
        },

        # Equipment Intel
        "equipment": equipment_intel,

        # Threat Analysis
        "threats": {
            "damage_taken": damage_taken,
            "ewar_threats": ewar_threats
        },

        # Sovereignty
        "sovereignty": sovereignty,

        # Battles
        "battles": {
            "recent": recent_battles
        },

        # Recommendations
        "recommendations": recommendations
    }

    # Cache the result before returning
    set_cached(cache_key, result)
    logger.info(f"Cached data for {cache_key}")
    return result
