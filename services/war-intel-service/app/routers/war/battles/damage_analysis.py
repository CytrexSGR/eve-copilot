"""Damage analysis endpoint for battle combat data."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.database import db_cursor
from eve_shared.utils.error_handling import handle_endpoint_errors
from app.services.intelligence.esi_utils import batch_resolve_alliance_names

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/battle/{battle_id}/damage-analysis")
@handle_endpoint_errors()
def get_damage_analysis(battle_id: int):
    """Get damage type analysis for a battle.

    Analyzes weapons used by attackers and calculates damage type breakdown
    (EM, Thermal, Kinetic, Explosive) based on weapon profiles.

    Returns:
    - Overall damage type distribution
    - Per-alliance damage profiles
    - Recommended resistance profile
    """
    with db_cursor() as cur:
        # Verify battle exists
        cur.execute("""
            SELECT battle_id, total_kills FROM battles WHERE battle_id = %s
        """, (battle_id,))
        battle = cur.fetchone()
        if not battle:
            raise HTTPException(status_code=404, detail=f"Battle {battle_id} not found")

        # Get damage by weapon type, joined with damage profiles
        cur.execute("""
            SELECT
                ka.alliance_id,
                wp.weapon_class,
                wp.primary_damage_type,
                SUM(ka.damage_done) as total_damage,
                AVG(wp.em_pct) as avg_em_pct,
                AVG(wp.thermal_pct) as avg_thermal_pct,
                AVG(wp.kinetic_pct) as avg_kinetic_pct,
                AVG(wp.explosive_pct) as avg_explosive_pct,
                COUNT(*) as weapon_uses
            FROM killmails k
            JOIN killmail_attackers ka ON k.killmail_id = ka.killmail_id
            LEFT JOIN weapon_damage_profiles wp ON ka.weapon_type_id = wp.type_id
            WHERE k.battle_id = %s
            AND ka.damage_done > 0
            GROUP BY ka.alliance_id, wp.weapon_class, wp.primary_damage_type
            ORDER BY total_damage DESC
        """, (battle_id,))
        weapon_data = cur.fetchall()

        # Get raw damage totals when we don't have profile data (fallback by ship type)
        cur.execute("""
            SELECT
                ka.alliance_id,
                t."typeName" as ship_name,
                g."groupName" as ship_class,
                SUM(ka.damage_done) as total_damage,
                COUNT(*) as engagements
            FROM killmails k
            JOIN killmail_attackers ka ON k.killmail_id = ka.killmail_id
            LEFT JOIN "invTypes" t ON ka.ship_type_id = t."typeID"
            LEFT JOIN "invGroups" g ON t."groupID" = g."groupID"
            WHERE k.battle_id = %s
            AND ka.damage_done > 0
            GROUP BY ka.alliance_id, t."typeName", g."groupName"
            ORDER BY total_damage DESC
            LIMIT 50
        """, (battle_id,))
        ship_damage = cur.fetchall()

        # Get alliance names
        alliance_ids = list(set(
            [r["alliance_id"] for r in weapon_data if r["alliance_id"]] +
            [r["alliance_id"] for r in ship_damage if r["alliance_id"]]
        ))
        alliance_names = batch_resolve_alliance_names(alliance_ids) if alliance_ids else {}

        # Calculate overall damage type breakdown
        total_damage = 0
        em_damage = 0
        thermal_damage = 0
        kinetic_damage = 0
        explosive_damage = 0

        for row in weapon_data:
            dmg = float(row["total_damage"] or 0)
            total_damage += dmg
            if row["avg_em_pct"]:
                em_damage += dmg * float(row["avg_em_pct"]) / 100
            if row["avg_thermal_pct"]:
                thermal_damage += dmg * float(row["avg_thermal_pct"]) / 100
            if row["avg_kinetic_pct"]:
                kinetic_damage += dmg * float(row["avg_kinetic_pct"]) / 100
            if row["avg_explosive_pct"]:
                explosive_damage += dmg * float(row["avg_explosive_pct"]) / 100

        # Calculate percentages
        if total_damage > 0:
            em_pct = round(em_damage / total_damage * 100, 1)
            thermal_pct = round(thermal_damage / total_damage * 100, 1)
            kinetic_pct = round(kinetic_damage / total_damage * 100, 1)
            explosive_pct = round(explosive_damage / total_damage * 100, 1)
        else:
            em_pct = thermal_pct = kinetic_pct = explosive_pct = 0

        # Damage per alliance
        alliance_damage = {}
        for row in weapon_data:
            aid = row["alliance_id"]
            if not aid:
                continue
            aname = alliance_names.get(aid, f"Alliance {aid}")
            if aname not in alliance_damage:
                alliance_damage[aname] = {
                    "alliance_id": aid,
                    "total_damage": 0,
                    "em": 0, "thermal": 0, "kinetic": 0, "explosive": 0,
                    "weapon_classes": {}
                }
            dmg = float(row["total_damage"] or 0)
            alliance_damage[aname]["total_damage"] += dmg
            if row["avg_em_pct"]:
                alliance_damage[aname]["em"] += dmg * float(row["avg_em_pct"]) / 100
            if row["avg_thermal_pct"]:
                alliance_damage[aname]["thermal"] += dmg * float(row["avg_thermal_pct"]) / 100
            if row["avg_kinetic_pct"]:
                alliance_damage[aname]["kinetic"] += dmg * float(row["avg_kinetic_pct"]) / 100
            if row["avg_explosive_pct"]:
                alliance_damage[aname]["explosive"] += dmg * float(row["avg_explosive_pct"]) / 100

            wc = row["weapon_class"] or "Unknown"
            if wc not in alliance_damage[aname]["weapon_classes"]:
                alliance_damage[aname]["weapon_classes"][wc] = 0
            alliance_damage[aname]["weapon_classes"][wc] += dmg

        # Convert to list and calculate percentages per alliance
        alliance_profiles = []
        for aname, data in sorted(alliance_damage.items(), key=lambda x: x[1]["total_damage"], reverse=True):
            td = data["total_damage"]
            if td > 0:
                alliance_profiles.append({
                    "alliance_id": data["alliance_id"],
                    "alliance_name": aname,
                    "total_damage": int(td),
                    "damage_profile": {
                        "em": round(data["em"] / td * 100, 1),
                        "thermal": round(data["thermal"] / td * 100, 1),
                        "kinetic": round(data["kinetic"] / td * 100, 1),
                        "explosive": round(data["explosive"] / td * 100, 1),
                    },
                    "primary_weapons": sorted(
                        [{"class": k, "damage": int(v)} for k, v in data["weapon_classes"].items()],
                        key=lambda x: x["damage"],
                        reverse=True
                    )[:5]
                })

        # Top damage dealers by ship
        top_ships = []
        for row in ship_damage[:20]:
            top_ships.append({
                "alliance_id": row["alliance_id"],
                "alliance_name": alliance_names.get(row["alliance_id"], "Unknown") if row["alliance_id"] else "Unknown",
                "ship_name": row["ship_name"] or "Unknown",
                "ship_class": row["ship_class"] or "Unknown",
                "total_damage": int(row["total_damage"] or 0),
                "engagements": row["engagements"]
            })

        # Determine recommended tank
        damage_types = [
            ("em", em_pct),
            ("thermal", thermal_pct),
            ("kinetic", kinetic_pct),
            ("explosive", explosive_pct)
        ]
        sorted_types = sorted(damage_types, key=lambda x: x[1], reverse=True)
        primary = sorted_types[0][0] if sorted_types[0][1] > 0 else None
        secondary = sorted_types[1][0] if len(sorted_types) > 1 and sorted_types[1][1] > 10 else None

        # Tank recommendations
        tank_recommendation = None
        if primary:
            if primary in ["em", "thermal"]:
                tank_recommendation = "Armor tank recommended (natural EM/Thermal resist)"
            elif primary in ["kinetic", "explosive"]:
                tank_recommendation = "Shield tank recommended (natural Kinetic/Explosive resist)"

        return {
            "battle_id": battle_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_damage_analyzed": int(total_damage),
            "damage_profile": {
                "em": em_pct,
                "thermal": thermal_pct,
                "kinetic": kinetic_pct,
                "explosive": explosive_pct,
            },
            "primary_damage_type": primary,
            "secondary_damage_type": secondary,
            "tank_recommendation": tank_recommendation,
            "alliance_profiles": alliance_profiles[:10],
            "top_damage_ships": top_ships,
            "coverage": {
                "matched_weapons": sum(1 for r in weapon_data if r["avg_em_pct"] is not None),
                "unmatched_weapons": sum(1 for r in weapon_data if r["avg_em_pct"] is None),
            }
        }
