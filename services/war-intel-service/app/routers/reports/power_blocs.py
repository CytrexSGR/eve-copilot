"""Power Blocs live detection — listing and detail endpoints."""

import logging
from datetime import datetime
from typing import Dict

from fastapi import APIRouter, HTTPException, Query

from app.database import db_cursor
from app.utils.cache import get_cached, set_cached
from eve_shared.utils.error_handling import handle_endpoint_errors
from eve_shared.constants.coalition import (
    WEIGHTED_TOGETHER_RATIO,
    WEIGHTED_ENEMY_THRESHOLD,
    TREND_OVERRIDE_RECENT_TOGETHER,
    TREND_OVERRIDE_RECENT_AGAINST_MAX,
    MIN_FIGHTS_TOGETHER,
    MIN_ACTIVITY_TOTAL,
)
import math

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/power-blocs/live")
@handle_endpoint_errors()
def get_power_blocs_live(
    minutes: int = Query(default=1440, ge=10, le=43200, description="Time window in minutes (10m to 30d)")
) -> Dict:
    """
    Live Power Blocs Detection

    Returns auto-detected coalitions based on combat patterns.
    Coalition membership is based on 90-day fight relationships.
    Stats (kills, losses, ISK) are calculated for the specified time window.

    Parameters:
    - minutes: Time window for stats (default 1440 = 24h)
    """
    from datetime import datetime

    MIN_SOLO_ACTIVITY = 1000

    timeframe_labels = {10: "10m", 60: "1h", 360: "6h", 720: "12h", 1440: "24h", 10080: "7d"}
    timeframe = timeframe_labels.get(minutes, f"{minutes}m")

    # Check cache first
    cache_key = f"power-blocs-live:{minutes}"
    cached = get_cached(cache_key, ttl_seconds=300)
    if cached is not None:
        return cached

    with db_cursor() as cur:
        # Step 1: Get alliance pairs with time-weighted scores
        cur.execute("""
            SELECT t.alliance_a, t.alliance_b, t.fights_together,
                   COALESCE(t.weighted_together, t.fights_together) as weighted_together,
                   COALESCE(t.recent_together, 0) as recent_together,
                   COALESCE(a.fights_against, 0) as fights_against,
                   COALESCE(a.weighted_against, a.fights_against, 0) as weighted_against,
                   COALESCE(a.recent_against, 0) as recent_against
            FROM alliance_fight_together t
            LEFT JOIN alliance_fight_against a
                ON t.alliance_a = a.alliance_a AND t.alliance_b = a.alliance_b
            WHERE t.fights_together >= %s
            ORDER BY COALESCE(t.weighted_together, t.fights_together) DESC
        """, (MIN_FIGHTS_TOGETHER,))
        fight_pairs = cur.fetchall()

        # Step 2: Get alliance activity with weighted scores
        cur.execute("""
            SELECT alliance_id, total_kills,
                   COALESCE(weighted_kills, total_kills) as weighted_kills
            FROM alliance_activity_total
            WHERE total_kills >= %s ORDER BY total_kills DESC
        """, (MIN_ACTIVITY_TOTAL,))
        _activity_rows = cur.fetchall()
        alliance_activity = {r['alliance_id']: r['total_kills'] for r in _activity_rows}
        weighted_activity = {r['alliance_id']: r['weighted_kills'] for r in _activity_rows}

        # Step 3: Build confirmed enemies (time-weighted threshold)
        cur.execute("""
            SELECT alliance_a, alliance_b,
                   COALESCE(weighted_against, fights_against) as weighted_against,
                   COALESCE(recent_against, 0) as recent_against
            FROM alliance_fight_against
            WHERE COALESCE(weighted_against, fights_against) >= %s
        """, (WEIGHTED_ENEMY_THRESHOLD,))
        confirmed_enemies = set()
        enemy_recent = {}
        for row in cur.fetchall():
            confirmed_enemies.add((row['alliance_a'], row['alliance_b']))
            confirmed_enemies.add((row['alliance_b'], row['alliance_a']))
            pair = (min(row['alliance_a'], row['alliance_b']),
                    max(row['alliance_a'], row['alliance_b']))
            enemy_recent[pair] = row['recent_against']

        # Step 4: Union-Find clustering with trend-awareness
        parent = {}
        coalition_members = {}

        def find(x):
            if x not in parent:
                parent[x] = x
                coalition_members[x] = {x}
            if parent[x] != x:
                parent[x] = find(parent[x])
            return parent[x]

        def safe_union(x, y):
            px, py = find(x), find(y)
            if px == py:
                return
            members_x = coalition_members.get(px, {px})
            members_y = coalition_members.get(py, {py})
            for mx in members_x:
                for my in members_y:
                    if (mx, my) in confirmed_enemies:
                        pair = (min(mx, my), max(mx, my))
                        recent = enemy_recent.get(pair, 999)
                        if recent > TREND_OVERRIDE_RECENT_AGAINST_MAX:
                            return  # Still actively hostile
            if alliance_activity.get(px, 0) >= alliance_activity.get(py, 0):
                parent[py] = px
                coalition_members[px] = members_x | members_y
            else:
                parent[px] = py
                coalition_members[py] = members_x | members_y

        # Process pairs with weighted ratios and trend override
        for row in fight_pairs:
            a_id, b_id = row['alliance_a'], row['alliance_b']
            w_together = row['weighted_together']
            w_against = row['weighted_against']
            recent_t = row['recent_together']
            recent_a = row['recent_against']

            # Trend override: recent data overwhelmingly positive
            trend_override = (recent_t >= TREND_OVERRIDE_RECENT_TOGETHER
                              and recent_a <= TREND_OVERRIDE_RECENT_AGAINST_MAX)

            if not trend_override:
                if w_against > 0 and w_together / w_against < WEIGHTED_TOGETHER_RATIO:
                    continue

            safe_union(a_id, b_id)

        # Build coalitions
        coalitions_raw = {}
        for alliance_id in alliance_activity:
            root = find(alliance_id)
            if root not in coalitions_raw:
                coalitions_raw[root] = []
            coalitions_raw[root].append(alliance_id)

        # Get alliance names
        all_ids = list(alliance_activity.keys())
        if all_ids:
            cur.execute("""
                SELECT alliance_id, alliance_name FROM alliance_name_cache
                WHERE alliance_id = ANY(%s)
            """, (all_ids,))
            name_map = {r['alliance_id']: r['alliance_name'] for r in cur.fetchall()}
        else:
            name_map = {}

        coalitions = []
        for root, members in coalitions_raw.items():
            members.sort(key=lambda x: alliance_activity.get(x, 0), reverse=True)
            total_activity = sum(alliance_activity.get(m, 0) for m in members)

            if len(members) < 2 and total_activity < MIN_SOLO_ACTIVITY:
                continue

            leader_name = name_map.get(members[0], f"Alliance {members[0]}")
            member_ids = tuple(members[:50])

            # Get stats from hourly_stats
            cur.execute("""
                SELECT
                    COALESCE(SUM(kills), 0) as kills,
                    COALESCE(SUM(deaths), 0) as deaths,
                    COALESCE(SUM(isk_destroyed), 0) as isk_destroyed,
                    COALESCE(SUM(isk_lost), 0) as isk_lost
                FROM intelligence_hourly_stats
                WHERE alliance_id = ANY(%s)
                  AND hour_bucket >= NOW() - INTERVAL '%s minutes'
            """, (list(members[:50]), minutes))
            stats_row = cur.fetchone()

            total_kills = stats_row['kills'] or 0
            total_losses = stats_row['deaths'] or 0
            isk_destroyed = int(stats_row['isk_destroyed'] or 0)
            isk_lost = int(stats_row['isk_lost'] or 0)
            efficiency = (isk_destroyed / (isk_destroyed + isk_lost) * 100) if (isk_destroyed + isk_lost) > 0 else 50

            # Get timeseries data (12 buckets for sparkline) from hourly_stats
            bucket_minutes = max(minutes // 12, 1)
            cur.execute("""
                WITH buckets AS (
                    SELECT generate_series(
                        NOW() - INTERVAL '%s minutes',
                        NOW(),
                        INTERVAL '%s minutes'
                    ) AS bucket_start
                )
                SELECT
                    b.bucket_start,
                    COALESCE(SUM(h.kills), 0) as kills,
                    COALESCE(SUM(h.deaths), 0) as deaths,
                    COALESCE(SUM(h.isk_destroyed), 0) as isk_killed
                FROM buckets b
                LEFT JOIN intelligence_hourly_stats h
                    ON h.hour_bucket >= b.bucket_start
                    AND h.hour_bucket < b.bucket_start + INTERVAL '%s minutes'
                    AND h.alliance_id = ANY(%s)
                    AND h.hour_bucket >= NOW() - INTERVAL '%s minutes'
                GROUP BY b.bucket_start
                ORDER BY b.bucket_start
            """, (minutes, bucket_minutes, bucket_minutes, list(members[:50]), minutes))
            timeseries_rows = cur.fetchall()

            kills_series = [int(r['kills'] or 0) for r in timeseries_rows]
            deaths_series = [int(r['deaths'] or 0) for r in timeseries_rows]
            isk_series = [int(r['isk_killed'] or 0) for r in timeseries_rows]

            # Get ESI member count from corporations table
            cur.execute("""
                SELECT COALESCE(SUM(member_count), 0) as total_members
                FROM corporations WHERE alliance_id IN %s
            """, (member_ids,))
            esi_members = cur.fetchone()['total_members'] or 0

            # Get active pilots = attackers + victims (all PvP participants)
            cur.execute("""
                SELECT COUNT(DISTINCT character_id) as active_pilots
                FROM (
                    SELECT ka.character_id
                    FROM killmail_attackers ka
                    JOIN killmails k ON ka.killmail_id = k.killmail_id
                    WHERE ka.alliance_id = ANY(%s)
                      AND k.killmail_time >= NOW() - INTERVAL '%s minutes'
                      AND ka.character_id IS NOT NULL
                    UNION
                    SELECT k.victim_character_id
                    FROM killmails k
                    WHERE k.victim_alliance_id = ANY(%s)
                      AND k.killmail_time >= NOW() - INTERVAL '%s minutes'
                      AND k.victim_character_id IS NOT NULL
                ) all_pilots
            """, (list(members[:50]), minutes, list(members[:50]), minutes))
            active_pilots = cur.fetchone()['active_pilots'] or 0

            coalition_name = f"{leader_name} Coalition" if len(members) > 1 else leader_name
            coalitions.append({
                "name": coalition_name,
                "leader_alliance_id": members[0],
                "leader_name": leader_name,
                "member_count": len(members),
                "members": [{"alliance_id": m, "name": name_map.get(m, f"Alliance {m}"), "activity": alliance_activity.get(m, 0)} for m in members[:10]],
                "total_kills": total_kills,
                "total_losses": total_losses,
                "isk_destroyed": isk_destroyed,
                "isk_lost": isk_lost,
                "efficiency": round(efficiency, 1),
                "total_activity": total_activity,
                "kills_series": kills_series,
                "deaths_series": deaths_series,
                "isk_series": isk_series,
                "esi_members": esi_members,
                "active_pilots": active_pilots
            })

        coalitions.sort(key=lambda x: x['total_activity'], reverse=True)

        result = {
            "coalitions": coalitions[:10],
            "minutes": minutes,
            "timeframe": timeframe,
            "generated_at": datetime.utcnow().isoformat() + "Z"
        }
        set_cached(cache_key, result)
        return result



@router.get("/powerbloc/{leader_alliance_id}")
@handle_endpoint_errors()
def get_powerbloc_detail(
    leader_alliance_id: int,
    minutes: int = Query(default=10080, ge=60, le=43200, description="Time window in minutes (1h to 30d)")
) -> Dict:
    """
    Power Bloc Detail Page Data

    Returns complete intelligence for a power bloc identified by its leader alliance.
    Aggregates stats across all coalition members.
    Uses shared coalition detection with time-weighted scoring.
    """
    from app.routers.powerbloc._shared import _get_coalition_members

    timeframe_labels = {60: "1h", 360: "6h", 720: "12h", 1440: "24h", 10080: "7d"}
    timeframe = timeframe_labels.get(minutes, f"{minutes}m")

    # Check cache first
    cache_key = f"powerbloc-detail:{leader_alliance_id}:{minutes}"
    cached = get_cached(cache_key, ttl_seconds=300)
    if cached is not None:
        return cached

    with db_cursor() as cur:
        # Use shared coalition detection (time-weighted Union-Find)
        members, coalition_name, name_map, ticker_map = _get_coalition_members(leader_alliance_id, cur)
        member_ids = tuple(members[:50])
        leader_name = name_map.get(members[0], f"Alliance {members[0]}")

        # Get alliance activity for member stats
        cur.execute("""
            SELECT alliance_id, total_kills FROM alliance_activity_total
            WHERE alliance_id = ANY(%s)
        """, (list(member_ids),))
        alliance_activity = {r['alliance_id']: r['total_kills'] for r in cur.fetchall()}

        # Get aggregated stats from intelligence_hourly_stats (consistent with Alliance view)
        cur.execute("""
            SELECT COALESCE(SUM(kills), 0) as kills,
                   COALESCE(SUM(deaths), 0) as deaths,
                   COALESCE(SUM(isk_destroyed), 0) as isk_destroyed,
                   COALESCE(SUM(isk_lost), 0) as isk_lost
            FROM intelligence_hourly_stats
            WHERE alliance_id = ANY(%s)
              AND hour_bucket >= NOW() - INTERVAL '%s minutes'
        """, (list(members), minutes))
        stats_row = cur.fetchone()

        total_kills = stats_row['kills'] or 0
        total_losses = stats_row['deaths'] or 0
        isk_destroyed = int(stats_row['isk_destroyed'] or 0)
        isk_lost = int(stats_row['isk_lost'] or 0)
        total_isk = isk_destroyed + isk_lost
        isk_efficiency = round((isk_destroyed / total_isk) * 100, 1) if total_isk > 0 else 50
        kill_efficiency = round(100.0 * total_kills / (total_kills + total_losses), 1) if (total_kills + total_losses) > 0 else 50
        net_isk = isk_destroyed - isk_lost

        # Get ESI member count
        cur.execute("""
            SELECT COALESCE(SUM(member_count), 0) as total_members
            FROM corporations WHERE alliance_id IN %s
        """, (member_ids,))
        esi_members = cur.fetchone()['total_members'] or 0

        # Get active pilots = attackers + victims (all PvP participants)
        cur.execute("""
            SELECT COUNT(DISTINCT character_id) as active_pilots
            FROM (
                SELECT ka.character_id
                FROM killmail_attackers ka
                JOIN killmails k ON ka.killmail_id = k.killmail_id
                WHERE ka.alliance_id = ANY(%s)
                  AND k.killmail_time >= NOW() - INTERVAL '%s minutes'
                  AND ka.character_id IS NOT NULL
                UNION
                SELECT k.victim_character_id
                FROM killmails k
                WHERE k.victim_alliance_id = ANY(%s)
                  AND k.killmail_time >= NOW() - INTERVAL '%s minutes'
                  AND k.victim_character_id IS NOT NULL
            ) all_pilots
        """, (list(members), minutes, list(members), minutes))
        active_pilots = cur.fetchone()['active_pilots'] or 0

        # Get peak hour from hourly_stats
        cur.execute("""
            SELECT EXTRACT(HOUR FROM hour_bucket)::int as hour,
                   SUM(kills) as cnt
            FROM intelligence_hourly_stats
            WHERE alliance_id = ANY(%s)
              AND hour_bucket >= NOW() - INTERVAL '%s minutes'
            GROUP BY hour ORDER BY cnt DESC LIMIT 1
        """, (list(members), minutes))
        peak_row = cur.fetchone()
        peak_hour = peak_row['hour'] if peak_row else 19

        # Get member stats from hourly_stats
        cur.execute("""
            SELECT
                alliance_id,
                COALESCE(SUM(kills), 0) as kills,
                COALESCE(SUM(deaths), 0) as losses,
                COALESCE(SUM(isk_destroyed), 0) as isk_destroyed,
                COALESCE(SUM(isk_lost), 0) as isk_lost
            FROM intelligence_hourly_stats
            WHERE alliance_id = ANY(%s)
              AND hour_bucket >= NOW() - INTERVAL '%s minutes'
            GROUP BY alliance_id
            ORDER BY SUM(kills) DESC
        """, (list(members), minutes))
        member_stats = {r['alliance_id']: r for r in cur.fetchall()}

        # Build members list
        members_list = []
        for m_id in members[:50]:
            stats = member_stats.get(m_id, {})
            m_kills = stats.get('kills', 0) or 0
            m_losses = stats.get('losses', 0) or 0
            m_isk_d = int(stats.get('isk_destroyed', 0) or 0)
            m_isk_l = int(stats.get('isk_lost', 0) or 0)
            m_eff = (m_isk_d / (m_isk_d + m_isk_l) * 100) if (m_isk_d + m_isk_l) > 0 else 50

            members_list.append({
                "alliance_id": m_id,
                "name": name_map.get(m_id, f"Alliance {m_id}"),
                "ticker": ticker_map.get(m_id, ""),
                "kills": m_kills,
                "losses": m_losses,
                "isk_destroyed": m_isk_d,
                "isk_lost": m_isk_l,
                "efficiency": round(m_eff, 1),
                "activity": alliance_activity.get(m_id, 0)
            })

        # Get top ships used
        cur.execute("""
            SELECT
                ka.ship_type_id,
                t."typeName" as ship_name,
                g."groupName" as ship_class,
                COUNT(*) as uses
            FROM killmail_attackers ka
            JOIN killmails k ON ka.killmail_id = k.killmail_id
            JOIN "invTypes" t ON ka.ship_type_id = t."typeID"
            JOIN "invGroups" g ON t."groupID" = g."groupID"
            WHERE k.killmail_time >= NOW() - INTERVAL '%s minutes'
            AND ka.alliance_id IN %s
            AND ka.ship_type_id IS NOT NULL
            AND ka.ship_type_id != 670
            GROUP BY ka.ship_type_id, t."typeName", g."groupName"
            ORDER BY uses DESC
            LIMIT 15
        """, (minutes, member_ids))
        top_ships = [dict(r) for r in cur.fetchall()]

        # Get top victims (alliances they kill most) - using killmail_attackers for full participation
        cur.execute("""
            SELECT
                k.victim_alliance_id as alliance_id,
                anc.alliance_name as name,
                COUNT(DISTINCT k.killmail_id) as kills,
                SUM(k.ship_value) as isk_destroyed
            FROM killmails k
            JOIN killmail_attackers ka ON k.killmail_id = ka.killmail_id
            LEFT JOIN alliance_name_cache anc ON k.victim_alliance_id = anc.alliance_id
            WHERE k.killmail_time >= NOW() - INTERVAL '%s minutes'
            AND ka.alliance_id = ANY(%s)
            AND k.victim_alliance_id IS NOT NULL
            AND k.victim_alliance_id != ALL(%s)
            GROUP BY k.victim_alliance_id, anc.alliance_name
            ORDER BY kills DESC
            LIMIT 10
        """, (minutes, list(members), list(members)))
        top_victims = [{"alliance_id": r['alliance_id'], "name": r['name'] or f"Alliance {r['alliance_id']}", "kills": r['kills'], "isk_destroyed": int(r['isk_destroyed'] or 0)} for r in cur.fetchall()]

        # Get top enemies (alliances that kill them most)
        cur.execute("""
            SELECT
                ka.alliance_id,
                anc.alliance_name as name,
                COUNT(DISTINCT k.killmail_id) as kills,
                SUM(k.ship_value) as isk_destroyed
            FROM killmails k
            JOIN killmail_attackers ka ON k.killmail_id = ka.killmail_id AND ka.is_final_blow = TRUE
            LEFT JOIN alliance_name_cache anc ON ka.alliance_id = anc.alliance_id
            WHERE k.killmail_time >= NOW() - INTERVAL '%s minutes'
            AND k.victim_alliance_id IN %s
            AND ka.alliance_id IS NOT NULL
            AND ka.alliance_id NOT IN %s
            GROUP BY ka.alliance_id, anc.alliance_name
            ORDER BY kills DESC
            LIMIT 10
        """, (minutes, member_ids, member_ids))
        top_enemies = [{"alliance_id": r['alliance_id'], "name": r['name'] or f"Alliance {r['alliance_id']}", "kills": r['kills'], "isk_destroyed": int(r['isk_destroyed'] or 0)} for r in cur.fetchall()]

        # Get active regions - using killmail_attackers for full participation
        cur.execute("""
            SELECT
                r."regionName" as region_name,
                COUNT(DISTINCT k.killmail_id) as kills,
                SUM(k.ship_value) as isk_destroyed
            FROM killmails k
            JOIN killmail_attackers ka ON k.killmail_id = ka.killmail_id
            JOIN "mapSolarSystems" s ON k.solar_system_id = s."solarSystemID"
            JOIN "mapRegions" r ON s."regionID" = r."regionID"
            WHERE k.killmail_time >= NOW() - INTERVAL '%s minutes'
            AND ka.alliance_id = ANY(%s)
            GROUP BY r."regionName"
            ORDER BY kills DESC
            LIMIT 10
        """, (minutes, list(members)))
        active_regions = [dict(r) for r in cur.fetchall()]

        # Get daily activity for sparkline from hourly_stats
        cur.execute("""
            WITH days AS (
                SELECT generate_series(
                    (NOW() - INTERVAL '%s minutes')::date,
                    NOW()::date,
                    '1 day'::interval
                )::date as day
            )
            SELECT
                d.day,
                COALESCE(SUM(h.kills), 0) as kills,
                COALESCE(SUM(h.deaths), 0) as deaths,
                COALESCE(SUM(h.isk_destroyed), 0) as isk_destroyed,
                COALESCE(SUM(h.isk_lost), 0) as isk_lost
            FROM days d
            LEFT JOIN intelligence_hourly_stats h
                ON h.hour_bucket::date = d.day
                AND h.alliance_id = ANY(%s)
                AND h.hour_bucket >= NOW() - INTERVAL '%s minutes'
            GROUP BY d.day
            ORDER BY d.day
        """, (minutes, list(members), minutes))
        daily_activity = [dict(r) for r in cur.fetchall()]

        # Get capital activity
        cur.execute("""
            SELECT
                g."groupName" as ship_class,
                COUNT(DISTINCT ka.character_id) as pilots,
                COUNT(*) as uses
            FROM killmail_attackers ka
            JOIN killmails k ON ka.killmail_id = k.killmail_id
            JOIN "invTypes" t ON ka.ship_type_id = t."typeID"
            JOIN "invGroups" g ON t."groupID" = g."groupID"
            WHERE k.killmail_time >= NOW() - INTERVAL '%s minutes'
            AND ka.alliance_id IN %s
            AND g."groupName" IN ('Titan', 'Supercarrier', 'Dreadnought', 'Carrier', 'Force Auxiliary')
            GROUP BY g."groupName"
            ORDER BY uses DESC
        """, (minutes, member_ids))
        capitals_used = [dict(r) for r in cur.fetchall()]

        cur.execute("""
            SELECT
                g."groupName" as ship_class,
                COUNT(*) as losses,
                SUM(k.ship_value) as isk_lost
            FROM killmails k
            JOIN "invTypes" t ON k.ship_type_id = t."typeID"
            JOIN "invGroups" g ON t."groupID" = g."groupID"
            WHERE k.killmail_time >= NOW() - INTERVAL '%s minutes'
            AND k.victim_alliance_id IN %s
            AND g."groupName" IN ('Titan', 'Supercarrier', 'Dreadnought', 'Carrier', 'Force Auxiliary')
            GROUP BY g."groupName"
            ORDER BY losses DESC
        """, (minutes, member_ids))
        capitals_lost = [dict(r) for r in cur.fetchall()]

        result = {
            "leader_alliance_id": members[0],
            "coalition_name": coalition_name,
            "leader_name": leader_name,
            "member_count": len(members),
            "total_pilots": esi_members,
            "active_pilots": active_pilots,
            "minutes": minutes,
            "timeframe": timeframe,
            "header": {
                "kills": total_kills,
                "deaths": total_losses,
                "efficiency": isk_efficiency,
                "isk_efficiency": isk_efficiency,
                "kill_efficiency": kill_efficiency,
                "net_isk": net_isk,
                "isk_destroyed": isk_destroyed,
                "isk_lost": isk_lost,
                "peak_hour": peak_hour,
            },
            "members": members_list,
            "combat": {
                "top_ships": top_ships,
                "top_victims": top_victims,
                "top_enemies": top_enemies,
                "active_regions": active_regions,
                "daily_activity": daily_activity,
            },
            "capitals": {
                "used": capitals_used,
                "lost": capitals_lost,
            }
        }
        set_cached(cache_key, result)
        return result
