"""
Alerts and Telegram notification endpoints for War Intel API.

Provides endpoints for war alerts and Telegram battle notifications.
"""

import logging

from fastapi import APIRouter, HTTPException, Query

from app.database import db_cursor
from eve_shared.utils.error_handling import handle_endpoint_errors
from .utils import get_coalition_memberships

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/alerts")
@handle_endpoint_errors()
def get_war_alerts(limit: int = Query(5, ge=1, le=50)):
    """Get recent high-priority war events from combat losses."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT
                csl.ship_type_id as type_id,
                t."typeName",
                csl.date,
                csl.total_value_destroyed,
                csl.region_id,
                r."regionName",
                csl.solar_system_id,
                ms."solarSystemName"
            FROM combat_ship_losses csl
            JOIN "invTypes" t ON csl.ship_type_id = t."typeID"
            JOIN "mapRegions" r ON csl.region_id = r."regionID"
            LEFT JOIN "mapSolarSystems" ms ON csl.solar_system_id = ms."solarSystemID"
            WHERE csl.total_value_destroyed > 1000000000
                AND csl.date >= CURRENT_DATE - INTERVAL '1 day'
            ORDER BY csl.date DESC, csl.total_value_destroyed DESC
            LIMIT %s
        """, (limit,))
        rows = cur.fetchall()

    alerts = []
    for row in rows:
        value = float(row["total_value_destroyed"])
        priority = "high" if value > 5_000_000_000 else "medium"
        location = row["solarSystemName"] if row.get("solarSystemName") else row["regionName"]

        alerts.append({
            "priority": priority,
            "message": f"High-value {row['typeName']} destroyed in {location}",
            "timestamp": row["date"].isoformat() + "T00:00:00Z",
            "value": value
        })

    return alerts


@router.get("/telegram/recent")
@handle_endpoint_errors()
def get_recent_telegram_alerts(limit: int = Query(5, ge=1, le=50)):
    """Get recent Telegram alerts sent for battles."""
    # Cache check (60s TTL)
    import time
    _cache = getattr(get_recent_telegram_alerts, '_cache', {})
    cache_key = f"telegram_recent_{limit}"
    if cache_key in _cache:
        ts, data = _cache[cache_key]
        if time.time() - ts < 60:
            return data
        del _cache[cache_key]

    with db_cursor() as cur:
        cur.execute("""
            SELECT
                b.battle_id,
                b.solar_system_id,
                ms."solarSystemName" as system_name,
                mr."regionName" as region_name,
                ms.security,
                b.total_kills,
                b.total_isk_destroyed,
                b.last_milestone_notified,
                b.telegram_message_id,
                b.initial_alert_sent,
                b.last_kill_at,
                b.status
            FROM battles b
            JOIN "mapSolarSystems" ms ON ms."solarSystemID" = b.solar_system_id
            JOIN "mapRegions" mr ON mr."regionID" = ms."regionID"
            WHERE b.telegram_message_id IS NOT NULL
            ORDER BY b.last_kill_at DESC
            LIMIT %s
        """, (limit,))
        rows = cur.fetchall()

        # Get battle IDs for alliance lookup
        battle_ids = [row["battle_id"] for row in rows]

        # Get alliance stats per battle from pre-aggregated battle_participants table
        # An alliance goes on ONE side based on kill ratio:
        # - More kills than losses -> Attacker side
        # - More losses than kills -> Defender side
        attackers_map = {}
        victims_map = {}
        if battle_ids:
            cur.execute("""
                SELECT
                    bp.battle_id,
                    bp.alliance_id,
                    COALESCE(anc.alliance_name, 'Unknown') as alliance_name,
                    bp.kills,
                    bp.losses,
                    CASE WHEN bp.kills > bp.losses THEN 'attacker'
                         WHEN bp.losses > bp.kills THEN 'defender'
                         ELSE 'attacker' END as side
                FROM battle_participants bp
                LEFT JOIN alliance_name_cache anc ON anc.alliance_id = bp.alliance_id
                WHERE bp.battle_id = ANY(%s)
                  AND bp.alliance_id IS NOT NULL
                  AND bp.alliance_id != 0
                ORDER BY bp.battle_id, (bp.kills + bp.losses) DESC
            """, (battle_ids,))

            # Build temporary list for coalition lookup
            temp_results = cur.fetchall()

            # Get coalition memberships from utility function (uses fight_together data)
            coalition_map = get_coalition_memberships()

            # Get coalition leader names
            coalition_names = {}
            leader_ids = list(set(coalition_map.values()))
            if leader_ids:
                cur.execute("""
                    SELECT alliance_id, alliance_name
                    FROM alliance_name_cache
                    WHERE alliance_id = ANY(%s)
                """, (leader_ids,))
                for nrow in cur.fetchall():
                    coalition_names[nrow["alliance_id"]] = nrow["alliance_name"]

            for row in temp_results:
                bid = row["battle_id"]
                side = row["side"]
                alliance_id = row["alliance_id"]

                # Get powerbloc info
                coalition_leader = coalition_map.get(alliance_id)
                powerbloc_name = None
                if coalition_leader:
                    leader_name = coalition_names.get(coalition_leader, f"Coalition {coalition_leader}")
                    powerbloc_name = f"{leader_name} Coalition"

                entry = {
                    "alliance_id": alliance_id,
                    "alliance_name": row["alliance_name"],
                    "kills": row["kills"],
                    "losses": row["losses"],
                    "powerbloc": powerbloc_name
                }

                if side == "attacker":
                    if bid not in attackers_map:
                        attackers_map[bid] = []
                    if len(attackers_map[bid]) < 5:  # Increased to 5 for better grouping display
                        attackers_map[bid].append(entry)
                else:
                    if bid not in victims_map:
                        victims_map[bid] = []
                    if len(victims_map[bid]) < 5:
                        victims_map[bid].append(entry)

    alerts = []
    for row in rows:
        last_milestone = row.get("last_milestone_notified") or 0
        status = row["status"]
        battle_id = row["battle_id"]

        if status == 'ended':
            alert_type = "ended"
        elif last_milestone >= 10:
            alert_type = "milestone"
        elif row.get("initial_alert_sent"):
            alert_type = "new_battle"
        else:
            alert_type = "unknown"

        alerts.append({
            "battle_id": battle_id,
            "system_name": row["system_name"],
            "region_name": row["region_name"],
            "security": float(row["security"]) if row.get("security") else 0.0,
            "alert_type": alert_type,
            "milestone": last_milestone,
            "total_kills": row["total_kills"],
            "total_isk_destroyed": int(row["total_isk_destroyed"]),
            "telegram_message_id": row["telegram_message_id"],
            "sent_at": row["last_kill_at"].isoformat() + "Z" if row.get("last_kill_at") else None,
            "status": status,
            "attackers": attackers_map.get(battle_id, []),
            "victims": victims_map.get(battle_id, [])
        })

    result = {"alerts": alerts, "total": len(alerts)}

    # Cache result
    if not hasattr(get_recent_telegram_alerts, '_cache'):
        get_recent_telegram_alerts._cache = {}
    get_recent_telegram_alerts._cache[cache_key] = (time.time(), result)

    return result
