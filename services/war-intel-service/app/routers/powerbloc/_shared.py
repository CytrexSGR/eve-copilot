"""Power Bloc shared utilities - coalition member resolution and capital CTEs."""

import logging
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict
from fastapi import APIRouter, HTTPException, Query

from app.database import db_cursor
from app.services.intelligence.esi_utils import batch_resolve_alliance_info
from app.utils.cache import get_cached, set_cached

logger = logging.getLogger(__name__)

from eve_shared.constants.coalition import (
    WEIGHTED_TOGETHER_RATIO,
    WEIGHTED_ENEMY_THRESHOLD,
    TREND_OVERRIDE_RECENT_TOGETHER,
    TREND_OVERRIDE_RECENT_AGAINST_MAX,
    MIN_FIGHTS_TOGETHER,
    MIN_ACTIVITY_TOTAL,
)

COALITION_CACHE_TTL = 600  # 10 minutes - coalition structure changes rarely


def _get_coalition_members(leader_alliance_id: int, cur) -> tuple[list[int], str, dict[int, str], dict[int, str]]:
    """Get all alliance IDs in the coalition including the leader.
    Returns (member_ids, coalition_name, name_map, ticker_map).
    Uses Union-Find on alliance_fight_together with enemy exclusion.
    Results are cached for 10 minutes.
    """
    cache_key = f"pb-coalition:{leader_alliance_id}"
    cached = get_cached(cache_key, COALITION_CACHE_TTL)
    if cached:
        logger.debug(f"Coalition cache hit for {leader_alliance_id}")
        # JSON serialization converts int keys to strings, convert back
        name_map = {int(k): v for k, v in cached['name_map'].items()}
        ticker_map = {int(k): v for k, v in cached['ticker_map'].items()}
        return cached['member_ids'], cached['coalition_name'], name_map, ticker_map

    cur.execute("""
        SELECT t.alliance_a, t.alliance_b, t.fights_together,
               COALESCE(a.fights_against, 0) as fights_against
        FROM alliance_fight_together t
        LEFT JOIN alliance_fight_against a
            ON t.alliance_a = a.alliance_a AND t.alliance_b = a.alliance_b
        WHERE t.fights_together >= 200
          AND (t.alliance_a = %s OR t.alliance_b = %s)
        ORDER BY t.fights_together DESC
    """, (leader_alliance_id, leader_alliance_id))
    fight_pairs = cur.fetchall()

    cur.execute("""
        SELECT alliance_id, total_kills FROM alliance_activity_total
        WHERE total_kills >= 50 ORDER BY total_kills DESC
    """)
    alliance_activity = {r['alliance_id']: r['total_kills'] for r in cur.fetchall()}

    cur.execute("SELECT alliance_a, alliance_b FROM alliance_fight_against WHERE fights_against >= 100")
    confirmed_enemies = set()
    for row in cur.fetchall():
        confirmed_enemies.add((row['alliance_a'], row['alliance_b']))
        confirmed_enemies.add((row['alliance_b'], row['alliance_a']))

    parent = {}
    coalition_members_set = {}

    def find(x):
        if x not in parent:
            parent[x] = x
            coalition_members_set[x] = {x}
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]

    def safe_union(x, y):
        px, py = find(x), find(y)
        if px == py:
            return
        members_x = coalition_members_set.get(px, {px})
        members_y = coalition_members_set.get(py, {py})
        for mx in members_x:
            for my in members_y:
                if (mx, my) in confirmed_enemies:
                    return
        if alliance_activity.get(px, 0) >= alliance_activity.get(py, 0):
            parent[py] = px
            coalition_members_set[px] = members_x | members_y
        else:
            parent[px] = py
            coalition_members_set[py] = members_x | members_y

    for row in fight_pairs:
        a_id, b_id = row['alliance_a'], row['alliance_b']
        together, against = row['fights_together'], row['fights_against']
        if against > 0 and together / against < WEIGHTED_TOGETHER_RATIO:
            continue
        safe_union(a_id, b_id)

    leader_root = find(leader_alliance_id)
    members = list(coalition_members_set.get(leader_root, {leader_alliance_id}))
    members.sort(key=lambda x: alliance_activity.get(x, 0), reverse=True)

    if not members:
        raise HTTPException(status_code=404, detail="Power bloc not found")

    member_ids = members[:50]

    cur.execute("""
        SELECT alliance_id, alliance_name, ticker FROM alliance_name_cache
        WHERE alliance_id = ANY(%s)
    """, (member_ids,))
    name_map = {}
    ticker_map = {}
    for r in cur.fetchall():
        name_map[r['alliance_id']] = r['alliance_name']
        ticker_map[r['alliance_id']] = r.get('ticker', '')

    leader_name = name_map.get(members[0], f"Alliance {members[0]}")
    coalition_name = f"{leader_name} Coalition" if len(members) > 1 else leader_name

    # Cache the result
    set_cached(cache_key, {
        'member_ids': member_ids,
        'coalition_name': coalition_name,
        'name_map': name_map,
        'ticker_map': ticker_map
    }, COALITION_CACHE_TTL)
    logger.debug(f"Coalition cached for {leader_alliance_id}: {len(member_ids)} members")

    return member_ids, coalition_name, name_map, ticker_map


from eve_shared.constants import CAPITAL_GROUP_NAMES


def _capital_kills_cte(days: int) -> str:
    """Reusable CTE for distinct capital kills by coalition."""
    return f"""
        unique_capital_kills AS (
            SELECT DISTINCT
                km.killmail_id,
                km.ship_type_id,
                km.ship_value,
                km.solar_system_id,
                km.killmail_time
            FROM killmails km
            JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
            JOIN "invTypes" it ON km.ship_type_id = it."typeID"
            JOIN "invGroups" ig ON it."groupID" = ig."groupID"
            WHERE ka.alliance_id = ANY(%(member_ids)s)
                AND ig."groupName" IN %(capital_groups)s
                AND km.killmail_time >= NOW() - INTERVAL '{days} days'
        )"""


def _capital_losses_cte(days: int) -> str:
    """Reusable CTE for capital losses by coalition."""
    return f"""
        unique_capital_losses AS (
            SELECT
                km.killmail_id,
                km.ship_type_id,
                km.ship_value,
                km.solar_system_id,
                km.killmail_time,
                km.victim_character_id
            FROM killmails km
            JOIN "invTypes" it ON km.ship_type_id = it."typeID"
            JOIN "invGroups" ig ON it."groupID" = ig."groupID"
            WHERE km.victim_alliance_id = ANY(%(member_ids)s)
                AND ig."groupName" IN %(capital_groups)s
                AND km.killmail_time >= NOW() - INTERVAL '{days} days'
        )"""
