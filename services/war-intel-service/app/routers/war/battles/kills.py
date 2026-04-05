"""Battle kills and ship class breakdown endpoints."""

import logging

from fastapi import APIRouter, HTTPException, Query

from app.database import db_cursor
from eve_shared.utils.error_handling import handle_endpoint_errors

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/battle/{battle_id}/kills")
@handle_endpoint_errors()
def get_battle_kills(
    battle_id: int,
    limit: int = Query(500, ge=1, le=1000)
):
    """Get kills for a specific battle."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT
                k.killmail_id, k.killmail_time, k.solar_system_id,
                k.ship_type_id, k.ship_value, k.attacker_count,
                k.victim_character_id, k.victim_alliance_id,
                k.is_solo, k.is_npc,
                t."typeName" as ship_name
            FROM killmails k
            LEFT JOIN "invTypes" t ON k.ship_type_id = t."typeID"
            WHERE k.battle_id = %s
            ORDER BY k.killmail_time DESC
            LIMIT %s
        """, (battle_id, limit))
        rows = cur.fetchall()

    kills = [{
        "killmail_id": row["killmail_id"],
        "killmail_time": row["killmail_time"].isoformat() + "Z",
        "solar_system_id": row["solar_system_id"],
        "ship_type_id": row["ship_type_id"],
        "ship_name": row.get("ship_name"),
        "ship_value": float(row["ship_value"] or 0),
        "victim_character_id": row.get("victim_character_id"),
        "victim_alliance_id": row.get("victim_alliance_id"),
        "attacker_count": row["attacker_count"],
        "is_solo": row.get("is_solo") or False,
        "is_npc": row.get("is_npc") or False
    } for row in rows]

    return {"kills": kills, "count": len(kills)}


@router.get("/battle/{battle_id}/ship-classes")
@handle_endpoint_errors()
def get_battle_ship_classes(
    battle_id: int,
    group_by: str = Query("category", pattern="^(category|role|both)$")
):
    """Get ship class breakdown for kills in a specific battle."""
    with db_cursor() as cur:
        # Verify battle exists
        cur.execute("""
            SELECT solar_system_id, started_at,
                   COALESCE(ended_at, last_kill_at) as end_time
            FROM battles WHERE battle_id = %s
        """, (battle_id,))
        battle = cur.fetchone()
        if not battle:
            raise HTTPException(status_code=404, detail=f"Battle {battle_id} not found")

        # Get ship class breakdown
        if group_by == "category":
            cur.execute("""
                SELECT
                    COALESCE(LOWER(k.ship_category), LOWER(g."groupName")) as category,
                    COUNT(*) as count
                FROM killmails k
                LEFT JOIN "invTypes" t ON t."typeID" = k.ship_type_id
                LEFT JOIN "invGroups" g ON g."groupID" = t."groupID"
                WHERE k.battle_id = %s
                GROUP BY category
                ORDER BY count DESC
            """, (battle_id,))
        elif group_by == "role":
            cur.execute("""
                SELECT
                    COALESCE(ship_role, 'standard') as role,
                    COUNT(*) as count
                FROM killmails
                WHERE battle_id = %s
                GROUP BY role
                ORDER BY count DESC
            """, (battle_id,))
        else:  # both
            cur.execute("""
                SELECT
                    COALESCE(LOWER(k.ship_category), LOWER(g."groupName"))
                        || ':' || COALESCE(k.ship_role, 'standard') as combined,
                    COUNT(*) as count
                FROM killmails k
                LEFT JOIN "invTypes" t ON t."typeID" = k.ship_type_id
                LEFT JOIN "invGroups" g ON g."groupID" = t."groupID"
                WHERE k.battle_id = %s
                GROUP BY combined
                ORDER BY count DESC
            """, (battle_id,))

        rows = cur.fetchall()
        # Build breakdown dict using correct column name based on group_by
        key_col = "category" if group_by == "category" else ("role" if group_by == "role" else "combined")
        breakdown = {row[key_col]: row["count"] for row in rows if row[key_col] is not None}

        # Get total
        cur.execute("SELECT COUNT(*) as cnt FROM killmails WHERE battle_id = %s", (battle_id,))
        total_kills = cur.fetchone()["cnt"]

    return {
        "battle_id": battle_id,
        "system_id": battle["solar_system_id"],
        "started_at": battle["started_at"].isoformat() + "Z",
        "end_time": battle["end_time"].isoformat() + "Z" if battle.get("end_time") else None,
        "total_kills": total_kills,
        "group_by": group_by,
        "breakdown": breakdown
    }
