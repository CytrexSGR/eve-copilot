"""Alliance and Corporation Wormhole Intelligence Endpoints."""

import logging
from typing import Dict, Any
from fastapi import APIRouter, Query

from app.database import db_cursor
from app.services.intelligence.esi_utils import batch_resolve_alliance_names
from .wormhole_helpers import (
    get_summary_stats,
    get_hunting_grounds,
    get_danger_zones,
    get_wh_class_distribution,
    get_top_enemies,
    get_top_victims,
    get_recent_high_value,
    get_ships_used,
)
from eve_shared.utils.error_handling import handle_endpoint_errors

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/fast/{alliance_id}/wormhole")
@handle_endpoint_errors()
def get_alliance_wormhole_intel(
    alliance_id: int,
    days: int = Query(30, ge=1, le=90)
) -> Dict[str, Any]:
    """
    Get wormhole space activity for an alliance.

    Returns:
    - Summary: kills/deaths/ISK in J-space
    - Hunting grounds: systems where alliance gets kills
    - Danger zones: systems where alliance loses ships
    - WH class distribution
    - Recent kills/deaths
    - Top enemy alliances in J-space
    """
    summary = get_summary_stats(alliance_id, 'alliance_id', days)
    hunting_grounds = get_hunting_grounds(alliance_id, 'alliance_id', days)
    danger_zones = get_danger_zones(alliance_id, 'alliance_id', days)
    class_distribution = get_wh_class_distribution(alliance_id, 'alliance_id', days)
    top_enemies, _ = get_top_enemies(alliance_id, 'alliance_id', days)
    top_victims, _ = get_top_victims(alliance_id, 'alliance_id', days)
    recent_kills, recent_losses = get_recent_high_value(alliance_id, 'alliance_id', days)
    ships_used = get_ships_used(alliance_id, 'alliance_id', days)

    return {
        "alliance_id": alliance_id,
        "period_days": days,
        "summary": summary,
        "hunting_grounds": hunting_grounds,
        "danger_zones": danger_zones,
        "class_distribution": class_distribution,
        "top_enemies": top_enemies,
        "top_victims": top_victims,
        "recent_kills": recent_kills,
        "recent_losses": recent_losses,
        "ships_used": ships_used
    }

# Economic potential estimates by WH class (ISK/month rough estimates)
# Classes 13-18 are special: C13 (Shattered), C14 (Thera), C15-18 (Drifter)
WH_ECONOMIC_POTENTIAL = {
    1: {"gas": 500_000_000, "blue_loot": 200_000_000, "total": 700_000_000, "label": "Low"},
    2: {"gas": 800_000_000, "blue_loot": 400_000_000, "total": 1_200_000_000, "label": "Moderate"},
    3: {"gas": 1_200_000_000, "blue_loot": 800_000_000, "total": 2_000_000_000, "label": "Good"},
    4: {"gas": 1_800_000_000, "blue_loot": 1_500_000_000, "total": 3_300_000_000, "label": "High"},
    5: {"gas": 3_000_000_000, "blue_loot": 4_000_000_000, "total": 7_000_000_000, "label": "Excellent"},
    6: {"gas": 4_000_000_000, "blue_loot": 8_000_000_000, "total": 12_000_000_000, "label": "Premium"},
    # Special wormholes
    13: {"gas": 1_500_000_000, "blue_loot": 1_000_000_000, "total": 2_500_000_000, "label": "Shattered"},  # C13 Shattered
    14: {"gas": 0, "blue_loot": 0, "total": 0, "label": "Transit Hub"},  # Thera - transit, no PVE
    15: {"gas": 5_000_000_000, "blue_loot": 10_000_000_000, "total": 15_000_000_000, "label": "Drifter C5"},  # Drifter wormholes
    16: {"gas": 5_000_000_000, "blue_loot": 10_000_000_000, "total": 15_000_000_000, "label": "Drifter C6"},
    17: {"gas": 5_000_000_000, "blue_loot": 10_000_000_000, "total": 15_000_000_000, "label": "Drifter"},
    18: {"gas": 5_000_000_000, "blue_loot": 10_000_000_000, "total": 15_000_000_000, "label": "Drifter"},
}

# System effect descriptions
SYSTEM_EFFECTS = {
    "Wolf-Rayet": {"color": "#ff4444", "bonuses": "Armor HP +, Small Weapons +", "icon": "🔴"},
    "Pulsar": {"color": "#00d4ff", "bonuses": "Shield Cap +, Sig Radius +", "icon": "⚡"},
    "Magnetar": {"color": "#ff00ff", "bonuses": "Damage +, Targeting Range -", "icon": "🧲"},
    "Black Hole": {"color": "#666666", "bonuses": "Missile Velocity +, Ship Speed +", "icon": "⚫"},
    "Cataclysmic Variable": {"color": "#ffcc00", "bonuses": "Local Reps -, Cap Capacity +", "icon": "💥"},
    "Red Giant": {"color": "#ff8800", "bonuses": "Smart Bomb +, Overheat Bonus +", "icon": "🌟"},
}


@router.get("/fast/{alliance_id}/wormhole-empire")
@handle_endpoint_errors()
def get_alliance_wormhole_empire(
    alliance_id: int,
    days: int = Query(30, ge=1, le=90)
) -> Dict[str, Any]:
    """
    Get wormhole empire data for an alliance - systems they CONTROL.

    Returns:
    - Summary: total systems, corps, economic potential
    - Controlled systems: with effects, statics, activity
    - Visitors: other corps/alliances appearing in controlled systems
    - Threats: recent hostile activity in controlled space
    """
    with db_cursor() as cur:
        # Get systems where alliance has presence (from wormhole_residents)
        cur.execute("""
            SELECT
                wr.system_id,
                ss."solarSystemName" as system_name,
                wc."wormholeClassID" as wh_class,
                COUNT(DISTINCT wr.corporation_id) as resident_corps,
                SUM(wr.kill_count) as total_kills,
                SUM(wr.loss_count) as total_losses,
                MAX(wr.last_activity) as last_activity,
                AVG(wr.activity_score) as avg_activity_score
            FROM wormhole_residents wr
            JOIN "mapSolarSystems" ss ON wr.system_id = ss."solarSystemID"
            LEFT JOIN "mapLocationWormholeClasses" wc ON wr.system_id = wc."locationID"
            WHERE wr.alliance_id = %s
              AND wr.last_activity > NOW() - INTERVAL '%s days'
            GROUP BY wr.system_id, ss."solarSystemName", wc."wormholeClassID"
            ORDER BY SUM(wr.kill_count) + SUM(wr.loss_count) DESC
        """, (alliance_id, days))
        controlled_systems_raw = cur.fetchall()

        if not controlled_systems_raw:
            return {
                "alliance_id": alliance_id,
                "period_days": days,
                "summary": {
                    "total_systems": 0,
                    "total_corps": 0,
                    "monthly_potential_isk": 0,
                    "total_kills": 0,
                    "total_losses": 0,
                    "has_empire": False
                },
                "controlled_systems": [],
                "visitors": [],
                "threats": [],
                "class_distribution": []
            }

        system_ids = [r["system_id"] for r in controlled_systems_raw]

        # Get system effects
        cur.execute("""
            SELECT system_id, effect_name
            FROM wormhole_system_effects
            WHERE system_id = ANY(%s)
        """, (system_ids,))
        effects_map = {r["system_id"]: r["effect_name"] for r in cur.fetchall()}

        # Get system statics (join with wormhole_type_extended for type codes)
        cur.execute("""
            SELECT
                wss.system_id,
                wte.type_code,
                wss.wormhole_type_id
            FROM wormhole_system_statics wss
            LEFT JOIN wormhole_type_extended wte ON wss.wormhole_type_id = wte.type_id
            WHERE wss.system_id = ANY(%s)
        """, (system_ids,))
        statics_map: Dict[int, List[Dict]] = {}
        for r in cur.fetchall():
            sid = r["system_id"]
            if sid not in statics_map:
                statics_map[sid] = []
            statics_map[sid].append({
                "type": r["type_code"] or f"Type {r['wormhole_type_id']}",
                "target_class": None,  # Not available in current schema
                "max_ship": None
            })

        # Build controlled systems list
        controlled_systems = []
        total_monthly_isk = 0
        class_counts: Dict[int, int] = {}

        for row in controlled_systems_raw:
            wh_class = row["wh_class"] or 1
            effect_name = effects_map.get(row["system_id"])
            effect_info = SYSTEM_EFFECTS.get(effect_name, {}) if effect_name else {}
            economic = WH_ECONOMIC_POTENTIAL.get(wh_class, WH_ECONOMIC_POTENTIAL[1])
            total_monthly_isk += economic["total"]

            class_counts[wh_class] = class_counts.get(wh_class, 0) + 1

            controlled_systems.append({
                "system_id": row["system_id"],
                "system_name": row["system_name"],
                "wh_class": wh_class,
                "resident_corps": row["resident_corps"],
                "kills": row["total_kills"] or 0,
                "losses": row["total_losses"] or 0,
                "last_activity": row["last_activity"].isoformat() if row["last_activity"] else None,
                "activity_score": float(row["avg_activity_score"] or 0),
                "effect": {
                    "name": effect_name,
                    "color": effect_info.get("color", "#888888"),
                    "bonuses": effect_info.get("bonuses", ""),
                    "icon": effect_info.get("icon", "")
                } if effect_name else None,
                "statics": statics_map.get(row["system_id"], []),
                "economic_potential": {
                    "monthly_isk": economic["total"],
                    "label": economic["label"],
                    "gas_income": economic["gas"],
                    "blue_loot_income": economic["blue_loot"]
                }
            })

        # Get unique corps in alliance for summary
        cur.execute("""
            SELECT COUNT(DISTINCT corporation_id) as corp_count
            FROM wormhole_residents
            WHERE alliance_id = %s
              AND last_activity > NOW() - INTERVAL '%s days'
        """, (alliance_id, days))
        corp_count = cur.fetchone()["corp_count"]

        # Get visitors (other alliances appearing in controlled systems)
        cur.execute("""
            SELECT
                wr.alliance_id as visitor_alliance_id,
                SUM(wr.kill_count) as kills_in_our_space,
                SUM(wr.loss_count) as losses_in_our_space,
                COUNT(DISTINCT wr.system_id) as systems_visited,
                MAX(wr.last_activity) as last_seen
            FROM wormhole_residents wr
            WHERE wr.system_id = ANY(%s)
              AND wr.alliance_id IS NOT NULL
              AND wr.alliance_id != %s
              AND wr.last_activity > NOW() - INTERVAL '%s days'
            GROUP BY wr.alliance_id
            ORDER BY kills_in_our_space DESC
            LIMIT 15
        """, (system_ids, alliance_id, days))
        visitor_rows = cur.fetchall()

        visitor_ids = [r["visitor_alliance_id"] for r in visitor_rows]
        visitor_names = batch_resolve_alliance_names(visitor_ids) if visitor_ids else {}

        visitors = [
            {
                "alliance_id": r["visitor_alliance_id"],
                "alliance_name": visitor_names.get(r["visitor_alliance_id"], f"Alliance {r['visitor_alliance_id']}"),
                "kills_in_our_space": r["kills_in_our_space"] or 0,
                "losses_in_our_space": r["losses_in_our_space"] or 0,
                "systems_visited": r["systems_visited"],
                "last_seen": r["last_seen"].isoformat() if r["last_seen"] else None,
                "threat_level": "high" if (r["kills_in_our_space"] or 0) > 10 else "medium" if (r["kills_in_our_space"] or 0) > 3 else "low"
            }
            for r in visitor_rows
        ]

        # Get recent threats (kills against us in our controlled systems)
        cur.execute("""
            SELECT
                k.killmail_id,
                k.solar_system_id as system_id,
                ss."solarSystemName" as system_name,
                k.ship_type_id,
                t."typeName" as ship_name,
                k.ship_value as value,
                k.killmail_time as time,
                ka.alliance_id as attacker_alliance_id
            FROM killmails k
            JOIN "mapSolarSystems" ss ON k.solar_system_id = ss."solarSystemID"
            LEFT JOIN "invTypes" t ON k.ship_type_id = t."typeID"
            JOIN killmail_attackers ka ON k.killmail_id = ka.killmail_id AND ka.is_final_blow = true
            WHERE k.victim_alliance_id = %s
              AND k.solar_system_id = ANY(%s)
              AND k.killmail_time >= NOW() - INTERVAL '%s days'
            ORDER BY k.killmail_time DESC
            LIMIT 10
        """, (alliance_id, system_ids, days))
        threat_rows = cur.fetchall()

        attacker_ids = list(set(r["attacker_alliance_id"] for r in threat_rows if r["attacker_alliance_id"]))
        attacker_names = batch_resolve_alliance_names(attacker_ids) if attacker_ids else {}

        threats = [
            {
                "killmail_id": r["killmail_id"],
                "system_id": r["system_id"],
                "system_name": r["system_name"],
                "ship_type_id": r["ship_type_id"],
                "ship_name": r["ship_name"] or "Unknown",
                "value": float(r["value"] or 0),
                "time": r["time"].isoformat() if r["time"] else None,
                "attacker_alliance_id": r["attacker_alliance_id"],
                "attacker_alliance_name": attacker_names.get(r["attacker_alliance_id"], "Unknown") if r["attacker_alliance_id"] else "Unknown"
            }
            for r in threat_rows
        ]

        # Class distribution
        class_distribution = [
            {"wh_class": cls, "count": cnt}
            for cls, cnt in sorted(class_counts.items())
        ]

        # Summary
        total_kills = sum(s["kills"] for s in controlled_systems)
        total_losses = sum(s["losses"] for s in controlled_systems)

        return {
            "alliance_id": alliance_id,
            "period_days": days,
            "summary": {
                "total_systems": len(controlled_systems),
                "total_corps": corp_count,
                "monthly_potential_isk": total_monthly_isk,
                "total_kills": total_kills,
                "total_losses": total_losses,
                "has_empire": len(controlled_systems) > 0
            },
            "controlled_systems": controlled_systems,
            "visitors": visitors,
            "threats": threats,
            "class_distribution": class_distribution
        }

@router.get("/fast/{alliance_id}/sov-threats")
@handle_endpoint_errors()
def get_alliance_sov_threats(
    alliance_id: int
) -> Dict[str, Any]:
    """
    Get pre-calculated wormhole threat analysis for alliance sovereignty space.

    Returns analysis of wormhole activity in the alliance's sov territory:
    - Total WH systems that have attacked sov space
    - Threat level breakdown (CRITICAL/HIGH/MODERATE/LOW)
    - Top attacking alliances with their WH bases
    - Most hit regions in sov space
    - Timezone distribution of attacks
    - Top threatening WH systems
    - Attacker ship doctrines

    Data is pre-calculated daily and stored in wh_sov_threats table.
    Only available for sov-holding alliances (~80 alliances).
    """
    with db_cursor() as cur:
        # Check if alliance has sovereignty first
        cur.execute("""
            SELECT COUNT(*) as sov_count
            FROM sovereignty_map_cache
            WHERE alliance_id = %s
        """, (alliance_id,))
        sov_count = cur.fetchone()["sov_count"]

        if sov_count == 0:
            return {
                "alliance_id": alliance_id,
                "has_sovereignty": False,
                "message": "Alliance does not hold sovereignty",
                "data": None
            }

        # Get pre-calculated threat data
        cur.execute("""
            SELECT
                total_wh_systems,
                total_kills,
                total_isk_destroyed,
                critical_systems,
                high_systems,
                moderate_systems,
                low_systems,
                top_attackers,
                top_regions,
                us_prime_pct,
                eu_prime_pct,
                au_prime_pct,
                top_wh_systems,
                attacker_doctrines,
                period_days,
                updated_at
            FROM wh_sov_threats
            WHERE alliance_id = %s
        """, (alliance_id,))
        row = cur.fetchone()

        if not row:
            return {
                "alliance_id": alliance_id,
                "has_sovereignty": True,
                "message": "No threat data calculated yet (job runs daily)",
                "data": None
            }

        # Calculate threat level summary
        total_threats = (
            row["critical_systems"] +
            row["high_systems"] +
            row["moderate_systems"] +
            row["low_systems"]
        )

        overall_threat = "NONE"
        if row["critical_systems"] >= 5:
            overall_threat = "CRITICAL"
        elif row["critical_systems"] >= 1 or row["high_systems"] >= 5:
            overall_threat = "HIGH"
        elif row["high_systems"] >= 1 or row["moderate_systems"] >= 10:
            overall_threat = "MODERATE"
        elif total_threats > 0:
            overall_threat = "LOW"

        return {
            "alliance_id": alliance_id,
            "has_sovereignty": True,
            "data": {
                "summary": {
                    "total_wh_systems": row["total_wh_systems"],
                    "total_kills": row["total_kills"],
                    "total_isk_destroyed": float(row["total_isk_destroyed"] or 0),
                    "overall_threat_level": overall_threat,
                    "threat_breakdown": {
                        "critical": row["critical_systems"],
                        "high": row["high_systems"],
                        "moderate": row["moderate_systems"],
                        "low": row["low_systems"]
                    }
                },
                "top_attackers": row["top_attackers"] or [],
                "top_regions": row["top_regions"] or [],
                "timezone_distribution": {
                    "us_prime_pct": float(row["us_prime_pct"] or 0),
                    "eu_prime_pct": float(row["eu_prime_pct"] or 0),
                    "au_prime_pct": float(row["au_prime_pct"] or 0)
                },
                "top_wh_systems": row["top_wh_systems"] or [],
                "attacker_doctrines": row["attacker_doctrines"] or [],
                "period_days": row["period_days"],
                "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None
            }
        }

@router.get("/corporation/{corp_id}/wormhole")
@handle_endpoint_errors()
def get_corporation_wormhole_intel(
    corp_id: int,
    days: int = Query(30, ge=1, le=90)
) -> Dict[str, Any]:
    """
    Get wormhole space activity for a corporation.

    Returns:
    - Summary: kills/deaths/ISK in J-space
    - Hunting grounds: systems where corp gets kills
    - Danger zones: systems where corp loses ships
    - WH class distribution
    - Recent kills/deaths
    - Top enemy corporations in J-space
    """
    summary = get_summary_stats(corp_id, 'corporation_id', days)
    hunting_grounds = get_hunting_grounds(corp_id, 'corporation_id', days)
    danger_zones = get_danger_zones(corp_id, 'corporation_id', days)
    class_distribution = get_wh_class_distribution(corp_id, 'corporation_id', days)
    top_enemies, _ = get_top_enemies(corp_id, 'corporation_id', days)
    top_victims, _ = get_top_victims(corp_id, 'corporation_id', days)
    recent_kills, recent_losses = get_recent_high_value(corp_id, 'corporation_id', days)
    ships_used = get_ships_used(corp_id, 'corporation_id', days)

    return {
        "corporation_id": corp_id,
        "period_days": days,
        "summary": summary,
        "hunting_grounds": hunting_grounds,
        "danger_zones": danger_zones,
        "class_distribution": class_distribution,
        "top_enemies": top_enemies,
        "top_victims": top_victims,
        "recent_kills": recent_kills,
        "recent_losses": recent_losses,
        "ships_used": ships_used
    }
