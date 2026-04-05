"""
Coalition conflict aggregation endpoint for War Intel API.

Aggregates battles by coalition pairs (Coalition A vs Coalition B).
"""

import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple

from fastapi import APIRouter, Query

from app.database import db_cursor
from eve_shared.utils.error_handling import handle_endpoint_errors
from .utils import get_coalition_memberships

logger = logging.getLogger(__name__)

router = APIRouter()

# Simple in-memory cache for conflicts response
_conflicts_cache: Dict[str, Tuple[dict, float]] = {}
_CONFLICTS_CACHE_TTL = 30  # 30 seconds


def _get_time_status(last_kill_at: datetime) -> str:
    """Determine time status based on how recent the last kill was."""
    now = datetime.now(timezone.utc)
    if last_kill_at.tzinfo is None:
        last_kill_at = last_kill_at.replace(tzinfo=timezone.utc)

    delta = now - last_kill_at
    minutes = delta.total_seconds() / 60

    if minutes <= 10:
        return '10m'
    elif minutes <= 60:
        return '1h'
    elif minutes <= 720:  # 12 hours
        return '12h'
    elif minutes <= 1440:  # 24 hours
        return '24h'
    else:
        return '7d'


def _calculate_trend(kills_recent: int, kills_previous: int) -> str:
    """Calculate trend based on kill rate comparison."""
    if kills_previous == 0:
        if kills_recent > 0:
            return 'escalating'
        return 'stable'

    ratio = kills_recent / kills_previous
    if ratio >= 1.5:
        return 'escalating'
    elif ratio <= 0.5:
        return 'cooling'
    return 'stable'


@router.get("/conflicts")
@handle_endpoint_errors()
async def get_conflicts(
    minutes: int = Query(60, description="Time window in minutes", ge=10, le=10080),
    min_kills: int = Query(5, description="Minimum kills to include conflict", ge=1)
):
    """
    Get active conflicts grouped by coalition pairs.

    Aggregates battles by Coalition A vs Coalition B and provides:
    - Kill/loss stats per coalition
    - ISK efficiency
    - Active regions
    - High-value kills
    - Trend analysis
    """
    # Check cache
    cache_key = f"{minutes}_{min_kills}"
    if cache_key in _conflicts_cache:
        cached_data, cache_time = _conflicts_cache[cache_key]
        if time.time() - cache_time < _CONFLICTS_CACHE_TTL:
            return cached_data

    result = await _build_conflicts_response(minutes, min_kills)
    _conflicts_cache[cache_key] = (result, time.time())
    return result


async def _build_conflicts_response(minutes: int, min_kills: int) -> dict:
    """Build the conflicts aggregation response."""

    # Get coalition memberships
    coalition_memberships = get_coalition_memberships()

    with db_cursor() as cur:
        # 1. Get active battles in the time window
        cur.execute("""
            SELECT
                b.battle_id,
                b.solar_system_id,
                b.region_id,
                b.started_at,
                b.last_kill_at,
                b.total_kills,
                b.total_isk_destroyed,
                b.status_level,
                s."solarSystemName" as system_name,
                r."regionName" as region_name
            FROM battles b
            LEFT JOIN "mapSolarSystems" s ON b.solar_system_id = s."solarSystemID"
            LEFT JOIN "mapRegions" r ON b.region_id = r."regionID"
            WHERE b.last_kill_at >= NOW() - INTERVAL '%s minutes'
              AND b.total_kills >= %s
            ORDER BY b.last_kill_at DESC
        """, (minutes, min_kills))
        battles = cur.fetchall()

        if not battles:
            return {
                "filter_minutes": minutes,
                "conflicts": [],
                "total_battles": 0,
                "total_kills": 0
            }

        battle_ids = [b["battle_id"] for b in battles]

        # 2. Get attacker alliances per battle
        cur.execute("""
            SELECT
                k.battle_id,
                ka.alliance_id,
                COUNT(*) as kills,
                SUM(k.ship_value) as isk_destroyed
            FROM killmails k
            JOIN killmail_attackers ka ON k.killmail_id = ka.killmail_id
                AND ka.is_final_blow = true
            WHERE k.battle_id = ANY(%s)
              AND ka.alliance_id IS NOT NULL
            GROUP BY k.battle_id, ka.alliance_id
        """, (battle_ids,))
        attacker_data = cur.fetchall()

        # 3. Get victim alliances per battle
        cur.execute("""
            SELECT
                k.battle_id,
                k.victim_alliance_id as alliance_id,
                COUNT(*) as losses,
                SUM(k.ship_value) as isk_lost
            FROM killmails k
            WHERE k.battle_id = ANY(%s)
              AND k.victim_alliance_id IS NOT NULL
            GROUP BY k.battle_id, k.victim_alliance_id
        """, (battle_ids,))
        victim_data = cur.fetchall()

        # 4. Get high-value kills for conflict details
        cur.execute("""
            SELECT
                k.killmail_id,
                k.battle_id,
                k.ship_type_id,
                k.ship_value,
                k.victim_alliance_id,
                k.final_blow_alliance_id,
                t."typeName" as ship_name,
                va.ticker as victim_ticker,
                aa.ticker as attacker_ticker
            FROM killmails k
            LEFT JOIN "invTypes" t ON k.ship_type_id = t."typeID"
            LEFT JOIN alliance_name_cache va ON k.victim_alliance_id = va.alliance_id
            LEFT JOIN alliance_name_cache aa ON k.final_blow_alliance_id = aa.alliance_id
            WHERE k.battle_id = ANY(%s)
              AND k.ship_value >= 100000000
            ORDER BY k.ship_value DESC
        """, (battle_ids,))
        high_value_kills = cur.fetchall()

        # 5. Get capital kill counts per battle
        cur.execute("""
            SELECT
                k.battle_id,
                COUNT(*) as capital_kills
            FROM killmails k
            JOIN "invTypes" t ON k.ship_type_id = t."typeID"
            JOIN "invGroups" g ON t."groupID" = g."groupID"
            WHERE k.battle_id = ANY(%s)
              AND g."groupID" IN (30, 659, 485, 547, 898, 883, 1538)
            GROUP BY k.battle_id
        """, (battle_ids,))
        capital_kills_data = {row["battle_id"]: row["capital_kills"] for row in cur.fetchall()}

        # 6. Get kills in last 30min vs previous 30min for trend calculation
        half_minutes = minutes // 2
        cur.execute("""
            SELECT
                k.battle_id,
                COUNT(*) FILTER (WHERE k.killmail_time >= NOW() - INTERVAL '%s minutes') as recent_kills,
                COUNT(*) FILTER (WHERE k.killmail_time < NOW() - INTERVAL '%s minutes'
                                   AND k.killmail_time >= NOW() - INTERVAL '%s minutes') as previous_kills
            FROM killmails k
            WHERE k.battle_id = ANY(%s)
            GROUP BY k.battle_id
        """, (half_minutes, half_minutes, minutes, battle_ids))
        trend_data = {row["battle_id"]: (row["recent_kills"], row["previous_kills"]) for row in cur.fetchall()}

        # Collect all alliance IDs for name resolution
        all_alliance_ids = set()
        for row in attacker_data:
            all_alliance_ids.add(row["alliance_id"])
        for row in victim_data:
            all_alliance_ids.add(row["alliance_id"])

        # Add coalition leader IDs
        for aid in list(all_alliance_ids):
            leader_id = coalition_memberships.get(aid)
            if leader_id:
                all_alliance_ids.add(leader_id)

        # 7. Get alliance names and tickers
        alliance_info = {}
        if all_alliance_ids:
            cur.execute("""
                SELECT alliance_id, alliance_name, ticker
                FROM alliance_name_cache
                WHERE alliance_id = ANY(%s)
            """, (list(all_alliance_ids),))
            for row in cur.fetchall():
                alliance_info[row["alliance_id"]] = {
                    "name": row["alliance_name"] or "Unknown Alliance",
                    "ticker": row["ticker"] or "????"
                }

    # Build per-battle coalition assignments
    battle_coalitions = {}  # battle_id -> (coalition_a, coalition_b, attacker_stats, victim_stats)

    # Build attacker stats per battle
    attackers_by_battle: Dict[int, Dict[int, dict]] = {}
    for row in attacker_data:
        bid = row["battle_id"]
        aid = row["alliance_id"]
        if bid not in attackers_by_battle:
            attackers_by_battle[bid] = {}
        attackers_by_battle[bid][aid] = {
            "kills": row["kills"],
            "isk_destroyed": float(row["isk_destroyed"] or 0)
        }

    # Build victim stats per battle
    victims_by_battle: Dict[int, Dict[int, dict]] = {}
    for row in victim_data:
        bid = row["battle_id"]
        aid = row["alliance_id"]
        if bid not in victims_by_battle:
            victims_by_battle[bid] = {}
        victims_by_battle[bid][aid] = {
            "losses": row["losses"],
            "isk_lost": float(row["isk_lost"] or 0)
        }

    # High-value kills by battle
    hvk_by_battle: Dict[int, List[dict]] = {}
    for row in high_value_kills:
        bid = row["battle_id"]
        if bid not in hvk_by_battle:
            hvk_by_battle[bid] = []
        hvk_by_battle[bid].append({
            "killmail_id": row["killmail_id"],
            "ship_name": row["ship_name"] or "Unknown Ship",
            "ship_type_id": row["ship_type_id"],
            "value": float(row["ship_value"] or 0),
            "victim_alliance_ticker": row["victim_ticker"] or "????",
            "attacker_alliance_ticker": row["attacker_ticker"] or "????"
        })

    # Determine coalition pairs per battle
    for battle in battles:
        bid = battle["battle_id"]

        attackers = attackers_by_battle.get(bid, {})
        victims = victims_by_battle.get(bid, {})

        if not attackers or not victims:
            continue

        # Map alliances to coalitions
        def get_coalition(alliance_id: int) -> int:
            """Get coalition leader ID, or alliance itself if not in coalition."""
            return coalition_memberships.get(alliance_id, alliance_id)

        # Find dominant attacker coalition (by kills)
        attacker_coalition_kills: Dict[int, int] = {}
        for aid, stats in attackers.items():
            cid = get_coalition(aid)
            attacker_coalition_kills[cid] = attacker_coalition_kills.get(cid, 0) + stats["kills"]

        if not attacker_coalition_kills:
            continue
        coalition_a = max(attacker_coalition_kills, key=attacker_coalition_kills.get)

        # Find dominant victim coalition (by losses)
        victim_coalition_losses: Dict[int, int] = {}
        for aid, stats in victims.items():
            cid = get_coalition(aid)
            victim_coalition_losses[cid] = victim_coalition_losses.get(cid, 0) + stats["losses"]

        if not victim_coalition_losses:
            continue
        coalition_b = max(victim_coalition_losses, key=victim_coalition_losses.get)

        # Skip if same coalition (internal conflict)
        if coalition_a == coalition_b:
            continue

        # Normalize: sort by ID to ensure consistent pair key
        if coalition_a > coalition_b:
            coalition_a, coalition_b = coalition_b, coalition_a

        battle_coalitions[bid] = {
            "coalition_a": coalition_a,
            "coalition_b": coalition_b,
            "attackers": attackers,
            "victims": victims
        }

    # Group battles by coalition pair
    conflict_groups: Dict[str, List[dict]] = {}

    for battle in battles:
        bid = battle["battle_id"]
        if bid not in battle_coalitions:
            continue

        bc = battle_coalitions[bid]
        pair_key = f"{bc['coalition_a']}_{bc['coalition_b']}"

        if pair_key not in conflict_groups:
            conflict_groups[pair_key] = []

        conflict_groups[pair_key].append({
            "battle": battle,
            "coalition_a": bc["coalition_a"],
            "coalition_b": bc["coalition_b"],
            "attackers": bc["attackers"],
            "victims": bc["victims"],
            "high_value_kills": hvk_by_battle.get(bid, [])[:5],
            "capital_kills": capital_kills_data.get(bid, 0),
            "trend_data": trend_data.get(bid, (0, 0))
        })

    # Build conflict objects
    conflicts = []
    total_battles_count = 0
    total_kills_count = 0

    for pair_key, battle_group in conflict_groups.items():
        coalition_a_id, coalition_b_id = pair_key.split("_")
        coalition_a_id = int(coalition_a_id)
        coalition_b_id = int(coalition_b_id)

        # Aggregate stats for each coalition
        coalition_a_stats = {
            "kills": 0, "losses": 0,
            "isk_destroyed": 0.0, "isk_lost": 0.0,
            "member_alliances": set()
        }
        coalition_b_stats = {
            "kills": 0, "losses": 0,
            "isk_destroyed": 0.0, "isk_lost": 0.0,
            "member_alliances": set()
        }

        all_regions = set()
        all_high_value_kills = []
        total_capital_kills = 0
        total_kills = 0
        total_isk = 0.0
        last_kill_at = None
        started_at = None
        recent_kills_sum = 0
        previous_kills_sum = 0

        conflict_battles = []

        for bg in battle_group:
            battle = bg["battle"]
            bid = battle["battle_id"]

            total_kills += battle["total_kills"]
            total_isk += float(battle["total_isk_destroyed"] or 0)
            total_capital_kills += bg["capital_kills"]

            if last_kill_at is None or battle["last_kill_at"] > last_kill_at:
                last_kill_at = battle["last_kill_at"]
            if started_at is None or battle["started_at"] < started_at:
                started_at = battle["started_at"]

            if battle["region_name"]:
                all_regions.add(battle["region_name"])

            all_high_value_kills.extend(bg["high_value_kills"])

            recent, previous = bg["trend_data"]
            recent_kills_sum += recent
            previous_kills_sum += previous

            # Calculate minutes ago
            now = datetime.now(timezone.utc)
            lka = battle["last_kill_at"]
            if lka.tzinfo is None:
                lka = lka.replace(tzinfo=timezone.utc)
            minutes_ago = int((now - lka).total_seconds() / 60)

            conflict_battles.append({
                "battle_id": bid,
                "system_name": battle["system_name"] or "Unknown",
                "region_name": battle["region_name"] or "Unknown",
                "status_level": battle["status_level"] or "gank",
                "total_kills": battle["total_kills"],
                "total_isk": float(battle["total_isk_destroyed"] or 0),
                "last_kill_at": lka.isoformat(),
                "minutes_ago": minutes_ago
            })

            # Aggregate coalition stats from this battle
            for aid, stats in bg["attackers"].items():
                cid = coalition_memberships.get(aid, aid)
                if cid == coalition_a_id:
                    coalition_a_stats["kills"] += stats["kills"]
                    coalition_a_stats["isk_destroyed"] += stats["isk_destroyed"]
                    coalition_a_stats["member_alliances"].add(aid)
                elif cid == coalition_b_id:
                    coalition_b_stats["kills"] += stats["kills"]
                    coalition_b_stats["isk_destroyed"] += stats["isk_destroyed"]
                    coalition_b_stats["member_alliances"].add(aid)

            for aid, stats in bg["victims"].items():
                cid = coalition_memberships.get(aid, aid)
                if cid == coalition_a_id:
                    coalition_a_stats["losses"] += stats["losses"]
                    coalition_a_stats["isk_lost"] += stats["isk_lost"]
                    coalition_a_stats["member_alliances"].add(aid)
                elif cid == coalition_b_id:
                    coalition_b_stats["losses"] += stats["losses"]
                    coalition_b_stats["isk_lost"] += stats["isk_lost"]
                    coalition_b_stats["member_alliances"].add(aid)

        total_battles_count += len(battle_group)
        total_kills_count += total_kills

        # Calculate efficiency
        def calc_efficiency(destroyed: float, lost: float) -> float:
            total = destroyed + lost
            if total == 0:
                return 0.0
            return round((destroyed / total) * 100, 1)

        # Build coalition info objects
        def build_coalition_info(cid: int, stats: dict) -> dict:
            info = alliance_info.get(cid, {"name": "Unknown Coalition", "ticker": "????"})
            return {
                "leader_id": cid,
                "leader_name": info["name"],
                "leader_ticker": info["ticker"],
                "member_count": len(stats["member_alliances"]),
                "kills": stats["kills"],
                "losses": stats["losses"],
                "isk_destroyed": stats["isk_destroyed"],
                "isk_lost": stats["isk_lost"],
                "efficiency": calc_efficiency(stats["isk_destroyed"], stats["isk_lost"])
            }

        # Sort high-value kills by value
        all_high_value_kills.sort(key=lambda x: x["value"], reverse=True)

        # Determine trend
        trend = _calculate_trend(recent_kills_sum, previous_kills_sum)

        # Build conflict object
        conflict = {
            "conflict_id": pair_key,
            "coalition_a": build_coalition_info(coalition_a_id, coalition_a_stats),
            "coalition_b": build_coalition_info(coalition_b_id, coalition_b_stats),
            "regions": sorted(all_regions),
            "total_kills": total_kills,
            "total_isk": total_isk,
            "capital_kills": total_capital_kills,
            "last_kill_at": last_kill_at.isoformat() if last_kill_at else None,
            "started_at": started_at.isoformat() if started_at else None,
            "time_status": _get_time_status(last_kill_at) if last_kill_at else "7d",
            "trend": trend,
            "battles": sorted(conflict_battles, key=lambda x: x["minutes_ago"]),
            "high_value_kills": all_high_value_kills[:5]
        }

        conflicts.append(conflict)

    # Sort conflicts by last_kill_at (most recent first)
    conflicts.sort(key=lambda x: x["last_kill_at"] or "", reverse=True)

    return {
        "filter_minutes": minutes,
        "conflicts": conflicts,
        "total_battles": total_battles_count,
        "total_kills": total_kills_count
    }
