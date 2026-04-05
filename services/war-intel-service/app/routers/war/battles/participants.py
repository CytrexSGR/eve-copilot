"""Battle participants endpoint."""

import logging

from fastapi import APIRouter, HTTPException

from app.database import db_cursor
from eve_shared.utils.error_handling import handle_endpoint_errors
from app.services.intelligence.esi_utils import batch_resolve_alliance_names
logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/battle/{battle_id}/participants")
@handle_endpoint_errors()
def get_battle_participants(battle_id: int):
    """Get detailed participant breakdown for a battle with resolved alliance names.

    Uses kill ratio to determine sides:
    - More kills than losses -> Attacker side
    - More losses than kills -> Defender side
    This ensures each alliance appears in only ONE list.
    """
    with db_cursor() as cur:
        # Verify battle exists
        cur.execute("SELECT solar_system_id FROM battles WHERE battle_id = %s", (battle_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail=f"Battle {battle_id} not found")

        # Get all alliance stats with both kills AND losses
        cur.execute("""
            WITH attacker_stats AS (
                SELECT
                    ka.alliance_id,
                    COUNT(*) as kills,
                    SUM(k.ship_value) as isk_destroyed,
                    COUNT(DISTINCT ka.corporation_id) as corps_involved
                FROM killmails k
                JOIN killmail_attackers ka ON k.killmail_id = ka.killmail_id
                    AND ka.is_final_blow = true
                WHERE k.battle_id = %s
                AND ka.alliance_id IS NOT NULL
                GROUP BY ka.alliance_id
            ),
            victim_stats AS (
                SELECT
                    k.victim_alliance_id as alliance_id,
                    COUNT(*) as losses,
                    SUM(k.ship_value) as isk_lost,
                    COUNT(DISTINCT k.victim_corporation_id) as corps_involved
                FROM killmails k
                WHERE k.battle_id = %s
                AND k.victim_alliance_id IS NOT NULL
                GROUP BY k.victim_alliance_id
            )
            SELECT
                COALESCE(a.alliance_id, v.alliance_id) as alliance_id,
                COALESCE(a.kills, 0) as kills,
                COALESCE(a.isk_destroyed, 0) as isk_destroyed,
                COALESCE(a.corps_involved, 0) as attacker_corps,
                COALESCE(v.losses, 0) as losses,
                COALESCE(v.isk_lost, 0) as isk_lost,
                COALESCE(v.corps_involved, 0) as victim_corps,
                CASE WHEN COALESCE(a.kills, 0) > COALESCE(v.losses, 0) THEN 'attacker'
                     WHEN COALESCE(v.losses, 0) > COALESCE(a.kills, 0) THEN 'defender'
                     ELSE 'attacker' END as side
            FROM attacker_stats a
            FULL OUTER JOIN victim_stats v ON a.alliance_id = v.alliance_id
            ORDER BY COALESCE(a.kills, 0) + COALESCE(v.losses, 0) DESC
        """, (battle_id, battle_id))
        alliance_rows = cur.fetchall()

    # Collect all alliance IDs to resolve names
    all_alliance_ids = set(row["alliance_id"] for row in alliance_rows if row["alliance_id"])

    # Resolve alliance names via ESI (with Redis caching)
    alliance_names = batch_resolve_alliance_names(list(all_alliance_ids))

    # Separate by side based on kill ratio
    attacker_alliances = []
    victim_alliances = []

    for row in alliance_rows:
        if row["side"] == "attacker":
            attacker_alliances.append({
                "alliance_id": row["alliance_id"],
                "alliance_name": alliance_names.get(row["alliance_id"], f"Alliance {row['alliance_id']}"),
                "kills": row["kills"],
                "isk_destroyed": float(row["isk_destroyed"] or 0),
                "losses": row["losses"],
                "isk_lost": float(row["isk_lost"] or 0),
                "corps_involved": max(row["attacker_corps"], row["victim_corps"])
            })
        else:
            victim_alliances.append({
                "alliance_id": row["alliance_id"],
                "alliance_name": alliance_names.get(row["alliance_id"], f"Alliance {row['alliance_id']}"),
                "kills": row["kills"],
                "isk_destroyed": float(row["isk_destroyed"] or 0),
                "losses": row["losses"],
                "isk_lost": float(row["isk_lost"] or 0),
                "corps_involved": max(row["attacker_corps"], row["victim_corps"])
            })

    return {
        "battle_id": battle_id,
        "attackers": {
            "alliances": attacker_alliances,
            "corporations": [],  # Frontend expects this
            "total_alliances": len(attacker_alliances),
            "total_kills": sum(a["kills"] for a in attacker_alliances)
        },
        "defenders": {
            "alliances": victim_alliances,
            "corporations": [],  # Frontend expects this
            "total_alliances": len(victim_alliances),
            "total_losses": sum(v["losses"] for v in victim_alliances),
            "total_isk_lost": sum(v["isk_lost"] for v in victim_alliances)
        }
    }
