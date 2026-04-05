"""Battle sides determination endpoint."""

import logging
from collections import deque

from fastapi import APIRouter, HTTPException

from app.database import db_cursor
from eve_shared.utils.error_handling import handle_endpoint_errors
from app.services.intelligence.esi_utils import batch_resolve_alliance_names
from ..utils import get_coalition_memberships

logger = logging.getLogger(__name__)
router = APIRouter()


def determine_sides(
    kill_relations: list[dict],
    pilot_counts: dict[int, int],
    coalition_memberships: dict[int, int],
) -> tuple[set[int], set[int]]:
    """Determine battle sides using BFS 2-coloring on kill graph.

    Uses kill relationships to build an enemy adjacency graph, then BFS
    2-colors it so alliances that fight each other end up on opposite sides.
    Coalition members split across sides are consolidated by pilot count,
    unless they fight each other in the battle.

    Args:
        kill_relations: List of dicts with attacker_alliance, victim_alliance, kills.
        pilot_counts: Mapping of alliance_id to pilot count (for coalition tiebreaking).
        coalition_memberships: Mapping of alliance_id to coalition leader_id.

    Returns:
        Tuple of (side_a, side_b) alliance ID sets.
    """
    # Collect all alliances and build enemy adjacency + kill/loss tallies
    all_alliances = set()
    alliance_kills: dict[int, int] = {}
    alliance_losses: dict[int, int] = {}
    enemy_adj: dict[int, set[int]] = {}

    for rel in kill_relations:
        attacker = rel["attacker_alliance"]
        victim = rel["victim_alliance"]
        all_alliances.add(attacker)
        all_alliances.add(victim)
        alliance_kills[attacker] = alliance_kills.get(attacker, 0) + rel["kills"]
        alliance_losses[victim] = alliance_losses.get(victim, 0) + rel["kills"]
        enemy_adj.setdefault(attacker, set()).add(victim)
        enemy_adj.setdefault(victim, set()).add(attacker)

    # BFS 2-coloring: assign sides based on who fights whom
    side_a: set[int] = set()
    side_b: set[int] = set()
    assigned: dict[int, str] = {}
    remaining = set(all_alliances)

    while remaining:
        # Start each disconnected component from the most involved alliance
        start = max(remaining, key=lambda a:
                    alliance_kills.get(a, 0) + alliance_losses.get(a, 0))

        assigned[start] = 'a'
        side_a.add(start)
        remaining.discard(start)

        queue = deque([start])
        while queue:
            current = queue.popleft()
            current_side = assigned[current]
            opposite = 'b' if current_side == 'a' else 'a'

            for neighbor in enemy_adj.get(current, set()):
                if neighbor not in remaining:
                    continue
                assigned[neighbor] = opposite
                (side_b if opposite == 'b' else side_a).add(neighbor)
                remaining.discard(neighbor)
                queue.append(neighbor)

    # Build in-battle enemy pairs for coalition consolidation check
    battle_enemies = set()
    for rel in kill_relations:
        battle_enemies.add(frozenset([rel["attacker_alliance"], rel["victim_alliance"]]))

    # Coalition consolidation: move all coalition members to the side
    # where the majority sits (weighted by pilot count).
    # But: never consolidate alliances that fight each other in this battle.
    coalition_groups: dict[int, set[int]] = {}
    for alliance in all_alliances:
        leader = coalition_memberships.get(alliance)
        if leader:
            coalition_groups.setdefault(leader, set()).add(alliance)

    for _leader_id, members in coalition_groups.items():
        a_members = members & side_a
        b_members = members & side_b
        if a_members and b_members:
            has_internal_conflict = any(
                frozenset([a, b]) in battle_enemies
                for a in a_members for b in b_members
            )
            if has_internal_conflict:
                continue

            a_pilots = sum(pilot_counts.get(a, 1) for a in a_members)
            b_pilots = sum(pilot_counts.get(a, 1) for a in b_members)
            if a_pilots >= b_pilots:
                for m in b_members:
                    side_b.discard(m)
                    side_a.add(m)
            else:
                for m in a_members:
                    side_a.discard(m)
                    side_b.add(m)

    return side_a, side_b


@router.get("/battle/{battle_id}/sides")
@handle_endpoint_errors()
def get_battle_sides(battle_id: int):
    """Analyze battle sides by grouping alliances into opposing coalitions.

    Uses kill relationships to determine which alliances fight on the same side:
    - Alliances that kill each other are on opposite sides
    - Alliances killed by the same attackers are grouped together
    """
    with db_cursor() as cur:
        # Verify battle exists
        cur.execute("SELECT solar_system_id FROM battles WHERE battle_id = %s", (battle_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail=f"Battle {battle_id} not found")

        # Get all kill relationships (who killed whom)
        cur.execute("""
            SELECT
                ka.alliance_id as attacker_alliance,
                k.victim_alliance_id as victim_alliance,
                COUNT(*) as kills,
                SUM(k.ship_value) as isk_destroyed
            FROM killmails k
            JOIN killmail_attackers ka ON k.killmail_id = ka.killmail_id
                AND ka.is_final_blow = true
            WHERE k.battle_id = %s
            AND ka.alliance_id IS NOT NULL
            AND k.victim_alliance_id IS NOT NULL
            GROUP BY ka.alliance_id, k.victim_alliance_id
        """, (battle_id,))
        kill_relations = cur.fetchall()

        # Get all alliance stats (kills + losses)
        cur.execute("""
            WITH attacker_stats AS (
                SELECT
                    ka.alliance_id,
                    COUNT(*) as kills,
                    SUM(k.ship_value) as isk_destroyed
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
                    SUM(k.ship_value) as isk_lost
                FROM killmails k
                WHERE k.battle_id = %s
                AND k.victim_alliance_id IS NOT NULL
                GROUP BY k.victim_alliance_id
            )
            SELECT
                COALESCE(a.alliance_id, v.alliance_id) as alliance_id,
                COALESCE(a.kills, 0) as kills,
                COALESCE(a.isk_destroyed, 0) as isk_destroyed,
                COALESCE(v.losses, 0) as losses,
                COALESCE(v.isk_lost, 0) as isk_lost
            FROM attacker_stats a
            FULL OUTER JOIN victim_stats v ON a.alliance_id = v.alliance_id
            ORDER BY COALESCE(a.kills, 0) + COALESCE(v.losses, 0) DESC
        """, (battle_id, battle_id))
        alliance_stats = cur.fetchall()

        # Get ships lost per alliance (victim ships destroyed) - with ship names from invTypes
        cur.execute("""
            SELECT
                k.victim_alliance_id as alliance_id,
                k.ship_type_id,
                t."typeName" as ship_name,
                COALESCE(g."groupName", k.ship_class, 'Unknown') as ship_class,
                COUNT(*) as count,
                SUM(k.ship_value) as total_value
            FROM killmails k
            LEFT JOIN "invTypes" t ON k.ship_type_id = t."typeID"
            LEFT JOIN "invGroups" g ON t."groupID" = g."groupID"
            WHERE k.battle_id = %s
            AND k.victim_alliance_id IS NOT NULL
            AND k.ship_type_id IS NOT NULL
            GROUP BY k.victim_alliance_id, k.ship_type_id, t."typeName", g."groupName", k.ship_class
            ORDER BY k.victim_alliance_id, SUM(k.ship_value) DESC
        """, (battle_id,))
        ships_lost_raw = cur.fetchall()

        # Get ships used by attackers (ships that got final blows) - with ship names from invTypes
        cur.execute("""
            SELECT
                ka.alliance_id,
                ka.ship_type_id,
                t."typeName" as ship_name,
                COALESCE(g."groupName", 'Unknown') as ship_class,
                COUNT(*) as kills,
                SUM(k.ship_value) as isk_destroyed
            FROM killmails k
            JOIN killmail_attackers ka ON k.killmail_id = ka.killmail_id
                AND ka.is_final_blow = true
            LEFT JOIN "invTypes" t ON ka.ship_type_id = t."typeID"
            LEFT JOIN "invGroups" g ON t."groupID" = g."groupID"
            WHERE k.battle_id = %s
            AND ka.alliance_id IS NOT NULL
            AND ka.ship_type_id IS NOT NULL
            GROUP BY ka.alliance_id, ka.ship_type_id, t."typeName", g."groupName"
            ORDER BY ka.alliance_id, COUNT(*) DESC
        """, (battle_id,))
        ships_used_raw = cur.fetchall()

        # Get pilot and corp counts per alliance (unique characters and corporations)
        cur.execute("""
            WITH attacker_pilots AS (
                SELECT DISTINCT ka.alliance_id, ka.character_id, ka.corporation_id
                FROM killmail_attackers ka
                JOIN killmails k ON k.killmail_id = ka.killmail_id
                WHERE k.battle_id = %s
                AND ka.alliance_id IS NOT NULL
                AND ka.character_id IS NOT NULL
            ),
            victim_pilots AS (
                SELECT DISTINCT k.victim_alliance_id as alliance_id, k.victim_character_id as character_id, k.victim_corporation_id as corporation_id
                FROM killmails k
                WHERE k.battle_id = %s
                AND k.victim_alliance_id IS NOT NULL
                AND k.victim_character_id IS NOT NULL
            ),
            all_pilots AS (
                SELECT alliance_id, character_id, corporation_id FROM attacker_pilots
                UNION
                SELECT alliance_id, character_id, corporation_id FROM victim_pilots
            )
            SELECT alliance_id, COUNT(DISTINCT character_id) as pilot_count, COUNT(DISTINCT corporation_id) as corp_count
            FROM all_pilots
            GROUP BY alliance_id
        """, (battle_id, battle_id))
        pilot_counts_raw = cur.fetchall()

    # Build pilot and corp count lookups
    pilot_counts = {row["alliance_id"]: row["pilot_count"] for row in pilot_counts_raw}
    corp_counts = {row["alliance_id"]: row["corp_count"] for row in pilot_counts_raw}

    # Build ship data structures (names already resolved via SQL join)
    ships_lost_by_alliance = {}  # alliance_id -> list of ships
    for row in ships_lost_raw:
        aid = row["alliance_id"]
        stid = row["ship_type_id"]
        if aid not in ships_lost_by_alliance:
            ships_lost_by_alliance[aid] = []
        ships_lost_by_alliance[aid].append({
            "ship_type_id": stid,
            "ship_name": row.get("ship_name") or f"Unknown ({stid})",
            "ship_class": row.get("ship_class") or "Unknown",
            "count": row["count"],
            "total_value": float(row["total_value"] or 0)
        })

    ships_used_by_alliance = {}  # alliance_id -> list of ships
    for row in ships_used_raw:
        aid = row["alliance_id"]
        stid = row["ship_type_id"]
        if aid not in ships_used_by_alliance:
            ships_used_by_alliance[aid] = []
        ships_used_by_alliance[aid].append({
            "ship_type_id": stid,
            "ship_name": row.get("ship_name") or f"Unknown ({stid})",
            "ship_class": row.get("ship_class") or "Unknown",
            "kills": row["kills"],
            "isk_destroyed": float(row["isk_destroyed"] or 0)
        })

    if not kill_relations:
        return {
            "battle_id": battle_id,
            "sides_determined": False,
            "message": "Not enough kill data to determine sides",
            "side_a": {"alliances": [], "totals": {}},
            "side_b": {"alliances": [], "totals": {}}
        }

    # Get coalition memberships for side consolidation
    coalition_memberships = get_coalition_memberships()

    # Determine sides via BFS 2-coloring + coalition consolidation
    side_a, side_b = determine_sides(kill_relations, pilot_counts, coalition_memberships)
    all_alliances = side_a | side_b

    # Resolve alliance names (including coalition leaders for display)
    all_coalition_leaders = set(
        coalition_memberships.get(a) for a in all_alliances
        if coalition_memberships.get(a)
    )
    all_ids_to_resolve = list(all_alliances | all_coalition_leaders)
    alliance_names = batch_resolve_alliance_names(all_ids_to_resolve)

    # Get coalition names for display (use leader alliance name + "Coalition")
    coalition_names = {}
    for leader_id in all_coalition_leaders:
        leader_name = alliance_names.get(leader_id, f"Alliance {leader_id}")
        coalition_names[leader_id] = f"{leader_name} Coalition"

    # Build stats by side
    def build_side_data(side_set):
        side_alliances = []
        for stat in alliance_stats:
            if stat["alliance_id"] in side_set:
                efficiency = 0
                total_involved = float(stat["isk_destroyed"] or 0) + float(stat["isk_lost"] or 0)
                if total_involved > 0:
                    efficiency = (float(stat["isk_destroyed"] or 0) / total_involved) * 100

                # Get coalition info for this alliance
                coalition_leader = coalition_memberships.get(stat["alliance_id"])
                coalition_name = coalition_names.get(coalition_leader) if coalition_leader else None

                side_alliances.append({
                    "alliance_id": stat["alliance_id"],
                    "alliance_name": alliance_names.get(stat["alliance_id"], f"Alliance {stat['alliance_id']}"),
                    "coalition_id": coalition_leader,
                    "coalition_name": coalition_name,
                    "pilots": pilot_counts.get(stat["alliance_id"], 0),
                    "corps": corp_counts.get(stat["alliance_id"], 0),
                    "kills": stat["kills"],
                    "losses": stat["losses"],
                    "isk_destroyed": float(stat["isk_destroyed"] or 0),
                    "isk_lost": float(stat["isk_lost"] or 0),
                    "efficiency": round(efficiency, 1)
                })

        # Sort by coalition first (grouped), then by kills within coalition
        side_alliances.sort(key=lambda x: (x["coalition_name"] or "zzz", -x["kills"]))

        # Aggregate ships lost by this side (from all alliances)
        ships_lost_agg = {}  # ship_type_id -> {ship_name, ship_class, count, total_value}
        for aid in side_set:
            for ship in ships_lost_by_alliance.get(aid, []):
                stid = ship["ship_type_id"]
                if stid not in ships_lost_agg:
                    ships_lost_agg[stid] = {
                        "ship_type_id": stid,
                        "ship_name": ship["ship_name"],
                        "ship_class": ship["ship_class"],
                        "count": 0,
                        "total_value": 0.0
                    }
                ships_lost_agg[stid]["count"] += ship["count"]
                ships_lost_agg[stid]["total_value"] += ship["total_value"]

        # Sort by value (most expensive losses first)
        ships_lost = sorted(ships_lost_agg.values(),
                            key=lambda x: x["total_value"], reverse=True)

        # Aggregate ships used by this side (from all alliances)
        ships_used_agg = {}  # ship_type_id -> {ship_name, ship_class, kills, isk_destroyed}
        for aid in side_set:
            for ship in ships_used_by_alliance.get(aid, []):
                stid = ship["ship_type_id"]
                if stid not in ships_used_agg:
                    ships_used_agg[stid] = {
                        "ship_type_id": stid,
                        "ship_name": ship["ship_name"],
                        "ship_class": ship["ship_class"],
                        "kills": 0,
                        "isk_destroyed": 0.0
                    }
                ships_used_agg[stid]["kills"] += ship["kills"]
                ships_used_agg[stid]["isk_destroyed"] += ship["isk_destroyed"]

        # Sort by kills (most effective ships first)
        ships_used = sorted(ships_used_agg.values(),
                            key=lambda x: x["kills"], reverse=True)

        # Calculate totals
        total_pilots = sum(a["pilots"] for a in side_alliances)
        total_kills = sum(a["kills"] for a in side_alliances)
        total_losses = sum(a["losses"] for a in side_alliances)
        total_isk_destroyed = sum(a["isk_destroyed"] for a in side_alliances)
        total_isk_lost = sum(a["isk_lost"] for a in side_alliances)
        total_involved = total_isk_destroyed + total_isk_lost
        total_efficiency = (total_isk_destroyed / total_involved * 100) if total_involved > 0 else 0

        # Count distinct coalitions (None counts as independent)
        coalition_ids = set(a["coalition_id"] for a in side_alliances if a["coalition_id"])
        independent_count = sum(1 for a in side_alliances if not a["coalition_id"])

        return {
            "alliances": side_alliances,
            "ships_lost": ships_lost[:20],  # Top 20 most valuable losses
            "ships_used": ships_used[:20],  # Top 20 most effective ships
            "totals": {
                "pilots": total_pilots,
                "kills": total_kills,
                "losses": total_losses,
                "isk_destroyed": total_isk_destroyed,
                "isk_lost": total_isk_lost,
                "efficiency": round(total_efficiency, 1),
                "alliance_count": len(side_alliances),
                "coalition_count": len(coalition_ids),
                "independent_count": independent_count,
                "ship_types_lost": len(ships_lost),
                "ship_types_used": len(ships_used)
            }
        }

    side_a_data = build_side_data(side_a)
    side_b_data = build_side_data(side_b)

    # Strip coalition labels from minority side when coalition is split by internal conflict
    coalitions_a = {}
    coalitions_b = {}
    for a in side_a_data["alliances"]:
        cid = a.get("coalition_id")
        if cid:
            coalitions_a[cid] = coalitions_a.get(cid, 0) + a["pilots"]
    for a in side_b_data["alliances"]:
        cid = a.get("coalition_id")
        if cid:
            coalitions_b[cid] = coalitions_b.get(cid, 0) + a["pilots"]

    for cid in set(coalitions_a) & set(coalitions_b):
        target = side_b_data if coalitions_a[cid] >= coalitions_b[cid] else side_a_data
        for a in target["alliances"]:
            if a.get("coalition_id") == cid:
                a["coalition_id"] = None
                a["coalition_name"] = None

    # Ensure Side A is the "winning" side (higher efficiency)
    if side_b_data["totals"]["efficiency"] > side_a_data["totals"]["efficiency"]:
        side_a_data, side_b_data = side_b_data, side_a_data

    return {
        "battle_id": battle_id,
        "sides_determined": True,
        "side_a": side_a_data,
        "side_b": side_b_data
    }
