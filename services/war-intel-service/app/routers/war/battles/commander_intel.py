"""Commander intel endpoint for battle analysis."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.database import db_cursor
from eve_shared.utils.error_handling import handle_endpoint_errors
from app.services.intelligence.esi_utils import (
    batch_resolve_alliance_names,
    batch_resolve_character_names,
)

from ..utils import get_coalition_memberships

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/battle/{battle_id}/commander-intel")
@handle_endpoint_errors()
def get_commander_intel(battle_id: int):
    """Get comprehensive battle intel for fleet commanders.

    Provides:
    - Capital/supercapital presence
    - Top killers (individual pilots)
    - High-value losses (SRP candidates)
    - Momentum analysis (who's winning over time)
    - Doctrine detection per side
    """
    with db_cursor() as cur:
        # Verify battle exists
        cur.execute("""
            SELECT solar_system_id, started_at, total_kills, total_isk_destroyed
            FROM battles WHERE battle_id = %s
        """, (battle_id,))
        battle = cur.fetchone()
        if not battle:
            raise HTTPException(status_code=404, detail=f"Battle {battle_id} not found")

        # 1. CAPITAL PRESENCE - Detect capitals/supers on field
        cur.execute("""
            SELECT
                ig."categoryID",
                ig."categoryName",
                t."typeName" as ship_name,
                k.victim_alliance_id,
                COUNT(*) as count,
                SUM(k.ship_value) as total_value
            FROM killmails k
            JOIN "invTypes" t ON k.ship_type_id = t."typeID"
            JOIN "invGroups" g ON t."groupID" = g."groupID"
            JOIN "invCategories" ig ON g."categoryID" = ig."categoryID"
            WHERE k.battle_id = %s
            AND ig."categoryID" IN (6)  -- Ships category
            AND g."groupID" IN (
                30,   -- Titans
                659,  -- Supercarriers
                485,  -- Dreadnoughts
                547,  -- Carriers
                898,  -- Force Auxiliaries
                883,  -- Rorquals (Capital Industrial)
                1538  -- Force Auxiliary
            )
            GROUP BY ig."categoryID", ig."categoryName", t."typeName", k.victim_alliance_id
            ORDER BY total_value DESC
        """, (battle_id,))
        capital_losses = cur.fetchall()

        # Also check for capitals on attacker side (final blows)
        cur.execute("""
            SELECT DISTINCT
                t."typeName" as ship_name,
                ka.alliance_id,
                g."groupID"
            FROM killmails k
            JOIN killmail_attackers ka ON k.killmail_id = ka.killmail_id
            JOIN "invTypes" t ON ka.ship_type_id = t."typeID"
            JOIN "invGroups" g ON t."groupID" = g."groupID"
            WHERE k.battle_id = %s
            AND ka.ship_type_id IS NOT NULL
            AND g."groupID" IN (30, 659, 485, 547, 898, 883, 1538)
        """, (battle_id,))
        capital_attackers = cur.fetchall()

        # 2. TOP KILLERS - Individual pilots making impact
        cur.execute("""
            SELECT
                ka.character_id,
                MAX(ka.character_name) as character_name,
                ka.corporation_id,
                ka.alliance_id,
                COUNT(*) as kills,
                SUM(k.ship_value) as isk_destroyed,
                COUNT(DISTINCT k.ship_type_id) as ship_variety
            FROM killmails k
            JOIN killmail_attackers ka ON k.killmail_id = ka.killmail_id
                AND ka.is_final_blow = true
            WHERE k.battle_id = %s
            AND ka.character_id IS NOT NULL
            GROUP BY ka.character_id, ka.corporation_id, ka.alliance_id
            ORDER BY isk_destroyed DESC
            LIMIT 10
        """, (battle_id,))
        top_killers = cur.fetchall()

        # 3. HIGH-VALUE LOSSES - SRP candidates
        cur.execute("""
            SELECT
                k.killmail_id,
                k.killmail_time,
                k.ship_type_id,
                t."typeName" as ship_name,
                k.ship_value,
                k.victim_character_id,
                k.victim_character_name,
                k.victim_corporation_id,
                k.victim_alliance_id,
                g."groupName" as ship_class
            FROM killmails k
            JOIN "invTypes" t ON k.ship_type_id = t."typeID"
            JOIN "invGroups" g ON t."groupID" = g."groupID"
            WHERE k.battle_id = %s
            AND k.ship_value > 100000000  -- > 100M ISK
            ORDER BY k.ship_value DESC
            LIMIT 20
        """, (battle_id,))
        high_value_losses = cur.fetchall()

        # 4. MOMENTUM - Kills over time (5-minute buckets)
        cur.execute("""
            WITH time_buckets AS (
                SELECT
                    date_trunc('minute', killmail_time) -
                    (EXTRACT(minute FROM killmail_time)::int %% 5) * INTERVAL '1 minute' as bucket,
                    victim_alliance_id,
                    COUNT(*) as kills,
                    SUM(ship_value) as isk_destroyed
                FROM killmails
                WHERE battle_id = %s
                GROUP BY bucket, victim_alliance_id
            )
            SELECT
                bucket,
                victim_alliance_id,
                kills,
                isk_destroyed
            FROM time_buckets
            ORDER BY bucket
        """, (battle_id,))
        momentum_data = cur.fetchall()

        # 5. DOCTRINE DETECTION - Ship types per alliance
        cur.execute("""
            SELECT
                k.victim_alliance_id as alliance_id,
                g."groupName" as ship_class,
                t."typeName" as ship_name,
                COUNT(*) as count,
                SUM(k.ship_value) as total_value
            FROM killmails k
            JOIN "invTypes" t ON k.ship_type_id = t."typeID"
            JOIN "invGroups" g ON t."groupID" = g."groupID"
            WHERE k.battle_id = %s
            AND k.victim_alliance_id IS NOT NULL
            GROUP BY k.victim_alliance_id, g."groupName", t."typeName"
            ORDER BY k.victim_alliance_id, count DESC
        """, (battle_id,))
        doctrine_losses = cur.fetchall()

        # Also get what attackers are flying
        cur.execute("""
            SELECT
                ka.alliance_id,
                g."groupName" as ship_class,
                t."typeName" as ship_name,
                COUNT(DISTINCT k.killmail_id) as engagements
            FROM killmails k
            JOIN killmail_attackers ka ON k.killmail_id = ka.killmail_id
            JOIN "invTypes" t ON ka.ship_type_id = t."typeID"
            JOIN "invGroups" g ON t."groupID" = g."groupID"
            WHERE k.battle_id = %s
            AND ka.alliance_id IS NOT NULL
            AND ka.ship_type_id IS NOT NULL
            GROUP BY ka.alliance_id, g."groupName", t."typeName"
            HAVING COUNT(DISTINCT k.killmail_id) >= 2
            ORDER BY ka.alliance_id, engagements DESC
        """, (battle_id,))
        doctrine_attackers = cur.fetchall()

    # Resolve alliance names
    all_alliance_ids = set()
    for row in top_killers:
        if row.get("alliance_id"):
            all_alliance_ids.add(row["alliance_id"])
    for row in high_value_losses:
        if row.get("victim_alliance_id"):
            all_alliance_ids.add(row["victim_alliance_id"])
    for row in capital_losses:
        if row.get("victim_alliance_id"):
            all_alliance_ids.add(row["victim_alliance_id"])
    for row in doctrine_losses:
        if row.get("alliance_id"):
            all_alliance_ids.add(row["alliance_id"])
    for row in doctrine_attackers:
        if row.get("alliance_id"):
            all_alliance_ids.add(row["alliance_id"])

    alliance_names = batch_resolve_alliance_names(list(all_alliance_ids)) if all_alliance_ids else {}

    # Resolve corporation names
    all_corp_ids = set()
    for row in top_killers:
        if row.get("corporation_id"):
            all_corp_ids.add(row["corporation_id"])
    for row in high_value_losses:
        if row.get("victim_corporation_id"):
            all_corp_ids.add(row["victim_corporation_id"])

    corp_names = {}
    if all_corp_ids:
        with db_cursor() as cur2:
            cur2.execute("""
                SELECT corporation_id, corporation_name, ticker
                FROM corp_name_cache
                WHERE corporation_id = ANY(%s)
            """, (list(all_corp_ids),))
            for row in cur2.fetchall():
                corp_names[row["corporation_id"]] = {
                    "name": row["corporation_name"],
                    "ticker": row["ticker"]
                }

    # Get coalition memberships
    coalitions = get_coalition_memberships()

    # Collect character names from DB results first
    character_names = {}
    chars_needing_resolution = set()

    for row in top_killers:
        char_id = row.get("character_id")
        if char_id:
            stored_name = row.get("character_name")
            if stored_name:
                character_names[char_id] = stored_name
            else:
                chars_needing_resolution.add(char_id)

    for row in high_value_losses:
        char_id = row.get("victim_character_id")
        if char_id:
            stored_name = row.get("victim_character_name")
            if stored_name:
                character_names[char_id] = stored_name
            elif char_id not in character_names:
                chars_needing_resolution.add(char_id)

    # Only resolve via ESI for characters without stored names
    if chars_needing_resolution:
        esi_names = batch_resolve_character_names(list(chars_needing_resolution))
        character_names.update(esi_names)

    # Format capital presence
    capitals = {
        "lost": [{
            "ship_name": row["ship_name"],
            "alliance_id": row["victim_alliance_id"],
            "alliance_name": alliance_names.get(row["victim_alliance_id"], "Unknown"),
            "count": row["count"],
            "value": float(row["total_value"] or 0)
        } for row in capital_losses],
        "on_field": [{
            "ship_name": row["ship_name"],
            "alliance_id": row["alliance_id"],
            "alliance_name": alliance_names.get(row["alliance_id"], "Unknown") if row["alliance_id"] else "Unknown"
        } for row in capital_attackers],
        "has_capitals": len(capital_losses) > 0 or len(capital_attackers) > 0,
        "has_supers": any(row.get("group_id") in [30, 659] for row in capital_attackers) or
                     any("Titan" in (row.get("ship_name") or "") or "Supercarrier" in (row.get("ship_name") or "")
                         for row in capital_losses)
    }

    # Format top killers with corp and coalition info
    killers = []
    for row in top_killers:
        alliance_id = row["alliance_id"]
        corp_id = row["corporation_id"]
        corp_info = corp_names.get(corp_id, {}) if corp_id else {}
        coalition_leader = coalitions.get(alliance_id) if alliance_id else None

        killers.append({
            "character_id": row["character_id"],
            "character_name": character_names.get(row["character_id"], f"Pilot {row['character_id']}"),
            "corporation_id": corp_id,
            "corporation_name": corp_info.get("name"),
            "corporation_ticker": corp_info.get("ticker"),
            "alliance_id": alliance_id,
            "alliance_name": alliance_names.get(alliance_id, "No Alliance") if alliance_id else "No Alliance",
            "coalition_id": coalition_leader,
            "coalition_name": f"{alliance_names.get(coalition_leader, 'Unknown')} Coalition" if coalition_leader and coalition_leader != alliance_id else None,
            "kills": row["kills"],
            "isk_destroyed": float(row["isk_destroyed"] or 0)
        })

    # Format high-value losses with corp and coalition info
    expensive_losses = []
    for row in high_value_losses:
        alliance_id = row["victim_alliance_id"]
        corp_id = row["victim_corporation_id"]
        corp_info = corp_names.get(corp_id, {}) if corp_id else {}
        coalition_leader = coalitions.get(alliance_id) if alliance_id else None

        expensive_losses.append({
            "killmail_id": row["killmail_id"],
            "ship_name": row["ship_name"],
            "ship_class": row["ship_class"],
            "value": float(row["ship_value"] or 0),
            "pilot_name": character_names.get(row["victim_character_id"], f"Pilot {row['victim_character_id']}") if row.get("victim_character_id") else "Unknown",
            "corporation_id": corp_id,
            "corporation_name": corp_info.get("name"),
            "corporation_ticker": corp_info.get("ticker"),
            "alliance_id": alliance_id,
            "alliance_name": alliance_names.get(alliance_id, "No Alliance") if alliance_id else "No Alliance",
            "coalition_id": coalition_leader,
            "coalition_name": f"{alliance_names.get(coalition_leader, 'Unknown')} Coalition" if coalition_leader and coalition_leader != alliance_id else None,
            "time": row["killmail_time"].isoformat() if row["killmail_time"] else None
        })

    # Format momentum data
    momentum_by_time = {}
    for row in momentum_data:
        bucket = row["bucket"].isoformat() if row["bucket"] else None
        if bucket not in momentum_by_time:
            momentum_by_time[bucket] = {"time": bucket, "kills_by_alliance": {}}
        alliance_id = row["victim_alliance_id"]
        alliance_name = alliance_names.get(alliance_id, f"Alliance {alliance_id}") if alliance_id else "Unknown"
        momentum_by_time[bucket]["kills_by_alliance"][alliance_name] = {
            "kills": row["kills"],
            "isk_destroyed": float(row["isk_destroyed"] or 0)
        }

    momentum = list(momentum_by_time.values())

    # Format doctrine detection - group by alliance
    doctrines = {}
    for row in doctrine_losses:
        alliance_id = row["alliance_id"]
        alliance_name = alliance_names.get(alliance_id, f"Alliance {alliance_id}")
        if alliance_name not in doctrines:
            doctrines[alliance_name] = {"losses": [], "fielding": []}
        doctrines[alliance_name]["losses"].append({
            "ship_class": row["ship_class"],
            "ship_name": row["ship_name"],
            "count": row["count"],
            "value": float(row["total_value"] or 0)
        })

    for row in doctrine_attackers:
        alliance_id = row["alliance_id"]
        alliance_name = alliance_names.get(alliance_id, f"Alliance {alliance_id}")
        if alliance_name not in doctrines:
            doctrines[alliance_name] = {"losses": [], "fielding": []}
        doctrines[alliance_name]["fielding"].append({
            "ship_class": row["ship_class"],
            "ship_name": row["ship_name"],
            "engagements": row["engagements"]
        })

    # Truncate doctrine lists
    for alliance in doctrines:
        doctrines[alliance]["losses"] = doctrines[alliance]["losses"][:10]
        doctrines[alliance]["fielding"] = doctrines[alliance]["fielding"][:10]

    return {
        "battle_id": battle_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "capitals": capitals,
        "top_killers": killers,
        "high_value_losses": expensive_losses,
        "momentum": momentum,
        "doctrines": doctrines,
        "summary": {
            "total_kills": battle["total_kills"],
            "total_isk": float(battle["total_isk_destroyed"] or 0),
            "capital_engagement": capitals["has_capitals"],
            "super_escalation": capitals["has_supers"],
            "high_value_count": len(expensive_losses)
        }
    }
