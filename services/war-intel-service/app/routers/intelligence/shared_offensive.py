"""Shared offensive intelligence queries for Alliance, Corporation, and PowerBloc.

All sections are parameterized by EntityContext. Where SQL differs
fundamentally between entity types (hourly_stats vs raw killmails),
the helper branches internally.
Uses tuple cursor (cursor_factory=None) and named parameters.
"""

import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional

from .entity_context import EntityContext, EntityType
from .corp_sql_helpers import classify_ship_group
from ._shared_filters import _victim_filter, _attacker_filter, _params, _params_with_days

logger = logging.getLogger(__name__)

# Capital ship groups for summary capital_kills counting
CAPITAL_GROUPS = {'Carrier', 'Dreadnought', 'Force Auxiliary', 'Supercarrier', 'Titan'}


def _now() -> datetime:
    """Return current UTC time. Extracted for testability."""
    return datetime.now(timezone.utc)


def _parse_jsonb(value) -> dict:
    """Parse a JSONB column value to a Python dict.

    psycopg2 auto-parses JSONB to dict, but handle string fallback.
    """
    if value is None:
        return {}
    if isinstance(value, str):
        return json.loads(value)
    return value


def fetch_hourly_stats_batch(cur, ctx: EntityContext, days: int) -> dict:
    """Fetch all hourly stats rows + SDE lookups in up to 3 queries (was 8).

    Returns a dict with:
        rows: list of raw hourly stats tuples
        type_info: {type_id: {"name", "group", "group_id"}}
        system_info: {system_id: {"name", "security", "region", "constellation"}}
    """
    hs = _hourly_stats_table(ctx)
    hf = _hourly_stats_filter(ctx)
    p = _params(ctx)

    extra_cols = ""
    if ctx.entity_type == EntityType.CORPORATION:
        extra_cols = ", avg_kill_value, max_kill_value"

    sql = f"""SELECT hour_bucket, kills, deaths, isk_destroyed, isk_lost,
                     ships_killed, ships_lost, systems_kills, systems_deaths,
                     solo_kills{extra_cols}
              FROM {hs}
              WHERE {hf}
                AND hour_bucket >= NOW() - INTERVAL '{days} days'"""
    cur.execute(sql, p)
    rows = cur.fetchall()

    # Collect all unique type_ids and system_ids from JSONB columns
    type_ids = set()
    system_ids = set()
    for row in rows:
        ships_killed = _parse_jsonb(row[5])
        ships_lost = _parse_jsonb(row[6])
        systems_kills = _parse_jsonb(row[7])
        systems_deaths = _parse_jsonb(row[8])

        for tid in ships_killed:
            type_ids.add(int(tid))
        for tid in ships_lost:
            type_ids.add(int(tid))
        for sid in systems_kills:
            system_ids.add(int(sid))
        for sid in systems_deaths:
            system_ids.add(int(sid))

    # Query 2: SDE type info (ships)
    type_info = {}
    if type_ids:
        cur.execute('''
            SELECT it."typeID", it."typeName", ig."groupName", ig."groupID"
            FROM "invTypes" it
            JOIN "invGroups" ig ON it."groupID" = ig."groupID"
            WHERE it."typeID" = ANY(%(type_ids)s)
        ''', {"type_ids": list(type_ids)})
        for r in cur.fetchall():
            type_info[r[0]] = {"name": r[1], "group": r[2], "group_id": r[3]}

    # Query 3: SDE system info
    system_info = {}
    if system_ids:
        cur.execute('''
            SELECT ms."solarSystemID", ms."solarSystemName", ms."security",
                   mr."regionName", mc."constellationName"
            FROM "mapSolarSystems" ms
            JOIN "mapRegions" mr ON ms."regionID" = mr."regionID"
            JOIN "mapConstellations" mc ON ms."constellationID" = mc."constellationID"
            WHERE ms."solarSystemID" = ANY(%(system_ids)s)
        ''', {"system_ids": list(system_ids)})
        for r in cur.fetchall():
            system_info[r[0]] = {
                "name": r[1],
                "security": float(r[2] or 0),
                "region": r[3],
                "constellation": r[4],
            }

    return {
        "rows": rows,
        "type_info": type_info,
        "system_info": system_info,
    }


def fetch_killmail_attacker_batch(cur, ctx: EntityContext, days: int) -> bool:
    """Create temp table _km_batch with all killmail+attacker data for the period.

    Returns True when temp table is created. Individual build_* functions
    then query _km_batch instead of scanning killmails+killmail_attackers.

    The temp table is automatically cleaned up at transaction end (COMMIT).
    """
    af = _attacker_filter(ctx)
    p = _params(ctx)

    # Drop if exists from previous call in same transaction
    cur.execute("DROP TABLE IF EXISTS _km_batch")

    cur.execute(f"""
        CREATE TEMP TABLE _km_batch AS
        SELECT
            km.killmail_id, km.killmail_time, km.ship_value,
            km.victim_corporation_id, km.victim_alliance_id,
            km.victim_character_id, km.solar_system_id,
            km.ship_type_id AS victim_ship_type_id,
            ka.character_id AS attacker_character_id,
            ka.corporation_id AS attacker_corp_id,
            ka.alliance_id AS attacker_alliance_id,
            ka.ship_type_id AS attacker_ship_type_id,
            ka.weapon_type_id, ka.damage_done, ka.is_final_blow
        FROM killmails km
        JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
        WHERE {af}
          AND km.killmail_time >= NOW() - INTERVAL '{days} days'
    """, p)

    # Add index for common lookups
    cur.execute("CREATE INDEX ON _km_batch(killmail_id)")

    return True


def _hourly_stats_filter(ctx: EntityContext) -> str:
    """WHERE clause for hourly_stats table filtering."""
    if ctx.entity_type == EntityType.CORPORATION:
        return "corporation_id = %(entity_id)s"
    elif ctx.entity_type == EntityType.POWERBLOC:
        return "alliance_id = ANY(%(entity_id)s)"
    return "alliance_id = %(entity_id)s"


def _hourly_stats_table(ctx: EntityContext) -> str:
    """Return the hourly stats table name for the entity type."""
    if ctx.entity_type == EntityType.CORPORATION:
        return "corporation_hourly_stats"
    # Both Alliance and PowerBloc use intelligence_hourly_stats
    return "intelligence_hourly_stats"




# ---------------------------------------------------------------------------
# Section helpers -- each computes one part of the offensive intel result.
# All take tuple-cursor `cur`, EntityContext `ctx`, and `days` period.
# ---------------------------------------------------------------------------


def _build_summary_from_batch(ctx: EntityContext, hs_batch: dict) -> tuple:
    """Build summary from pre-fetched batch data (Python-side aggregation)."""
    rows = hs_batch["rows"]
    type_info = hs_batch["type_info"]

    total_kills = 0
    total_deaths = 0
    total_isk_destroyed = 0
    total_isk_lost = 0
    total_solo_kills = 0
    capital_kills = 0
    # Corp-only
    weighted_avg_sum = 0
    max_kill_value = 0

    is_corp = ctx.entity_type == EntityType.CORPORATION

    for row in rows:
        kills = row[1] or 0
        deaths = row[2] or 0
        isk_d = row[3] or 0
        isk_l = row[4] or 0
        solo = row[9] or 0

        total_kills += kills
        total_deaths += deaths
        total_isk_destroyed += isk_d
        total_isk_lost += isk_l

        # PowerBloc doesn't use solo_kills
        if ctx.entity_type != EntityType.POWERBLOC:
            total_solo_kills += solo

        if is_corp:
            avg_kv = row[10] or 0
            max_kv = row[11] or 0
            weighted_avg_sum += avg_kv * kills
            if max_kv > max_kill_value:
                max_kill_value = max_kv

        # Count capital kills from ships_killed JSONB
        ships_killed = _parse_jsonb(row[5])
        for tid_str, count_val in ships_killed.items():
            tid = int(tid_str)
            info = type_info.get(tid)
            if info and info["group"] in CAPITAL_GROUPS:
                if is_corp:
                    # Corp: COUNT(DISTINCT type_id) — unique capital types
                    capital_kills = 1  # Will be set properly below
                else:
                    # Alliance/PB: SUM of counts
                    capital_kills += int(count_val)

    # Corp capital kills: count distinct capital type_ids that appeared
    if is_corp:
        cap_type_ids = set()
        for row in rows:
            ships_killed = _parse_jsonb(row[5])
            for tid_str in ships_killed:
                tid = int(tid_str)
                info = type_info.get(tid)
                if info and info["group"] in CAPITAL_GROUPS:
                    cap_type_ids.add(tid)
        capital_kills = len(cap_type_ids)

    # Compute derived values
    if is_corp:
        avg_kill_value = int(weighted_avg_sum / total_kills) if total_kills > 0 else 0
    else:
        avg_kill_value = total_isk_destroyed // total_kills if total_kills > 0 else 0
        max_kill_value = 0  # Alliance/PB: placeholder, overridden by high_value_kills

    kd_ratio = round(total_kills / total_deaths, 2) if total_deaths > 0 else 0
    solo_kill_pct = round(100.0 * total_solo_kills / total_kills, 1) if total_kills > 0 else 0
    total = total_kills + total_deaths
    efficiency = round(100.0 * total_kills / total, 1) if total > 0 else 0

    summary = {
        "total_kills": total_kills,
        "isk_destroyed": str(total_isk_destroyed),
        "avg_kill_value": str(avg_kill_value),
        "max_kill_value": max_kill_value,
        "kd_ratio": float(kd_ratio),
        "solo_kill_pct": float(solo_kill_pct),
        "capital_kills": capital_kills,
        "efficiency": float(efficiency),
    }
    return summary, total_deaths


def build_summary(cur, ctx: EntityContext, days: int, *, hs_batch: dict = None) -> dict:
    """Section 1: Enhanced kill summary.

    Alliance/PowerBloc: Uses intelligence_hourly_stats for speed.
    Corporation: Uses corporation_hourly_stats (has avg/max kill value).
    Returns summary dict + deaths count for efficiency validation.

    When hs_batch is provided, processes pre-fetched data in Python.
    """
    if hs_batch is not None:
        return _build_summary_from_batch(ctx, hs_batch)

    hs = _hourly_stats_table(ctx)
    hf = _hourly_stats_filter(ctx)
    p = _params(ctx)

    if ctx.entity_type == EntityType.CORPORATION:
        # Corporation hourly stats has avg_kill_value and max_kill_value
        sql = f"""
            WITH summary_stats AS (
                SELECT
                    SUM(kills) as total_kills,
                    SUM(deaths) as total_deaths,
                    SUM(isk_destroyed) as isk_destroyed,
                    SUM(isk_lost) as isk_lost,
                    SUM(solo_kills) as solo_kills,
                    COALESCE(SUM(avg_kill_value * kills) / NULLIF(SUM(kills), 0), 0)::BIGINT as avg_kill_value,
                    COALESCE(MAX(max_kill_value), 0)::BIGINT as max_kill_value
                FROM {hs}
                WHERE {hf}
                  AND hour_bucket >= NOW() - INTERVAL '{days} days'
            ),
            capital_kills_cte AS (
                SELECT COUNT(DISTINCT ships.ship_type_id::INT) as capital_kills
                FROM {hs}
                CROSS JOIN LATERAL jsonb_each_text(ships_killed) as ships(ship_type_id, value)
                JOIN "invTypes" it ON ships.ship_type_id::INT = it."typeID"
                JOIN "invGroups" ig ON it."groupID" = ig."groupID"
                WHERE {hf}
                  AND hour_bucket >= NOW() - INTERVAL '{days} days'
                  AND ig."groupName" IN ('Carrier', 'Dreadnought', 'Force Auxiliary', 'Supercarrier', 'Titan')
            )
            SELECT
                s.total_kills,
                s.total_deaths,
                s.isk_destroyed,
                s.avg_kill_value,
                s.max_kill_value,
                s.solo_kills,
                c.capital_kills,
                ROUND(s.total_kills::numeric / NULLIF(s.total_deaths, 0), 2) AS kd_ratio,
                ROUND(100.0 * s.solo_kills / NULLIF(s.total_kills, 0), 1) AS solo_kill_pct,
                ROUND(100.0 * s.total_kills / NULLIF(s.total_kills + s.total_deaths, 0), 1) AS efficiency
            FROM summary_stats s, capital_kills_cte c
        """
    else:
        # Alliance / PowerBloc: intelligence_hourly_stats
        # solo_kills column exists for alliance, not for powerbloc (use 0)
        solo_expr = "COALESCE(SUM(solo_kills), 0)" if ctx.entity_type == EntityType.ALLIANCE else "0"
        sql = f"""
            WITH summary_stats AS (
                SELECT
                    SUM(kills) as total_kills,
                    SUM(deaths) as total_deaths,
                    SUM(isk_destroyed) as isk_destroyed,
                    SUM(isk_lost) as isk_lost,
                    {solo_expr} as solo_kills
                FROM {hs}
                WHERE {hf}
                  AND hour_bucket >= NOW() - INTERVAL '{days} days'
            ),
            capital_kills_stats AS (
                SELECT COALESCE(SUM(value::INT), 0) as capital_kills
                FROM {hs},
                LATERAL jsonb_each_text(ships_killed) as ships(ship_type_id, value)
                JOIN "invTypes" it ON ships.ship_type_id::INT = it."typeID"
                JOIN "invGroups" ig ON it."groupID" = ig."groupID"
                WHERE {hf}
                  AND hour_bucket >= NOW() - INTERVAL '{days} days'
                  AND ig."groupName" IN ('Carrier', 'Dreadnought', 'Force Auxiliary', 'Supercarrier', 'Titan')
            )
            SELECT
                ss.total_kills,
                ss.total_deaths,
                ss.isk_destroyed,
                ss.isk_destroyed / NULLIF(ss.total_kills, 0) as avg_kill_value,
                0 as max_kill_value,
                ss.solo_kills,
                cks.capital_kills,
                ROUND(ss.total_kills::numeric / NULLIF(ss.total_deaths, 0), 2) as kd_ratio,
                ROUND(100.0 * ss.solo_kills / NULLIF(ss.total_kills, 0), 1) as solo_kill_pct,
                ROUND(100.0 * ss.total_kills / NULLIF(ss.total_kills + ss.total_deaths, 0), 1) as efficiency
            FROM summary_stats ss, capital_kills_stats cks
        """

    cur.execute(sql, p)
    sr = cur.fetchone()

    summary = {
        "total_kills": sr[0] or 0,
        "isk_destroyed": str(sr[2] or 0),
        "avg_kill_value": str(sr[3] or 0),
        "max_kill_value": sr[4] or 0,
        "kd_ratio": float(sr[7] or 0),
        "solo_kill_pct": float(sr[8] or 0),
        "capital_kills": sr[6] or 0,
        "efficiency": float(sr[9] or 0),
    }
    deaths = sr[1] or 0
    return summary, deaths


def build_powerbloc_isk_dedup(cur, ctx: EntityContext, days: int, summary: dict,
                              *, km_batch: bool = False) -> None:
    """PowerBloc-only: Deduplicate ISK via killmail-based query.

    hourly_stats counts each kill once per participating member alliance,
    causing coalition overlap inflation. This corrects isk_destroyed + avg_kill_value.
    Mutates summary in-place.
    """
    if ctx.entity_type != EntityType.POWERBLOC:
        return

    if km_batch:
        sql = """
            SELECT COALESCE(SUM(ship_value), 0) AS isk_destroyed
            FROM (
                SELECT DISTINCT killmail_id, ship_value
                FROM _km_batch
            ) sub
        """
        cur.execute(sql)
    else:
        p = _params(ctx)
        sql = f"""
            SELECT COALESCE(SUM(km.ship_value), 0) AS isk_destroyed
            FROM (
                SELECT DISTINCT km.killmail_id, km.ship_value
                FROM killmails km
                JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
                WHERE ka.alliance_id = ANY(%(entity_id)s)
                    AND km.killmail_time >= NOW() - INTERVAL '{days} days'
            ) km
        """
        cur.execute(sql, p)
    isk_row = cur.fetchone()
    if isk_row and isk_row[0]:
        summary["isk_destroyed"] = str(isk_row[0])
        if summary["total_kills"] > 0:
            summary["avg_kill_value"] = str(round(isk_row[0] / summary["total_kills"]))


def build_powerbloc_max_kill_value(cur, ctx: EntityContext, days: int, summary: dict,
                                   *, km_batch: bool = False) -> None:
    """PowerBloc-only: Get max_kill_value from killmails (hourly_stats doesn't store it)."""
    if ctx.entity_type != EntityType.POWERBLOC:
        return

    if km_batch:
        sql = """
            SELECT COALESCE(MAX(ship_value), 0) AS max_value
            FROM (
                SELECT DISTINCT killmail_id, ship_value
                FROM _km_batch
            ) sub
        """
        cur.execute(sql)
    else:
        p = _params(ctx)
        sql = f"""
            SELECT COALESCE(MAX(km.ship_value), 0) AS max_value
            FROM killmails km
            JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
            WHERE ka.alliance_id = ANY(%(entity_id)s)
                AND km.killmail_time >= NOW() - INTERVAL '{days} days'
        """
        cur.execute(sql, p)
    row = cur.fetchone()
    if row and row[0]:
        summary["max_kill_value"] = row[0]


def build_engagement_profile(cur, ctx: EntityContext, days: int,
                             *, km_batch: bool = False) -> dict:
    """Section 2: Engagement profile (solo/small/medium/large/blob breakdown)."""
    if km_batch:
        sql = """
            WITH attacker_counts AS (
                SELECT killmail_id, COUNT(*) AS attacker_count
                FROM _km_batch GROUP BY killmail_id
            )
            SELECT
                CASE
                    WHEN attacker_count <= 3 THEN 'solo'
                    WHEN attacker_count <= 10 THEN 'small'
                    WHEN attacker_count <= 30 THEN 'medium'
                    WHEN attacker_count <= 100 THEN 'large'
                    ELSE 'blob'
                END AS engagement_type,
                COUNT(*) AS kills,
                ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS percentage
            FROM attacker_counts
            GROUP BY engagement_type
        """
        cur.execute(sql)
    else:
        af = _attacker_filter(ctx)
        p = _params(ctx)

        sql = f"""
            WITH attacker_counts AS (
                SELECT DISTINCT
                    km.killmail_id,
                    (SELECT COUNT(*) FROM killmail_attackers ka2 WHERE ka2.killmail_id = km.killmail_id) AS attacker_count
                FROM killmails km
                JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
                WHERE {af}
                    AND km.killmail_time >= NOW() - INTERVAL '{days} days'
            )
            SELECT
                CASE
                    WHEN attacker_count <= 3 THEN 'solo'
                    WHEN attacker_count <= 10 THEN 'small'
                    WHEN attacker_count <= 30 THEN 'medium'
                    WHEN attacker_count <= 100 THEN 'large'
                    ELSE 'blob'
                END AS engagement_type,
                COUNT(*) AS kills,
                ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS percentage
            FROM attacker_counts
            GROUP BY engagement_type
        """

        cur.execute(sql, p)

    profile = {
        "solo": {"kills": 0, "percentage": 0.0},
        "small": {"kills": 0, "percentage": 0.0},
        "medium": {"kills": 0, "percentage": 0.0},
        "large": {"kills": 0, "percentage": 0.0},
        "blob": {"kills": 0, "percentage": 0.0},
    }
    for engagement_type, kills, percentage in cur.fetchall():
        profile[engagement_type] = {
            "kills": kills,
            "percentage": float(percentage or 0)
        }
    return profile


def build_fleet_profile(cur, ctx: EntityContext, days: int,
                        *, km_batch: bool = False) -> Optional[dict]:
    """Section 3: Fleet profile (avg/median/max fleet size). Alliance-only."""
    if ctx.entity_type != EntityType.ALLIANCE:
        return None

    if km_batch:
        # _km_batch already filtered by alliance attackers;
        # use is_final_blow to identify kills where this alliance got final blow,
        # then count all attackers on those kills from killmail_attackers table
        sql = """
            SELECT
                AVG(sub.ac)::numeric(10,1) as avg_fleet_size,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY sub.ac)::int as median_fleet_size,
                MAX(sub.ac) as max_fleet_size
            FROM (
                SELECT b.killmail_id, COUNT(*) as ac
                FROM _km_batch b
                WHERE b.is_final_blow = true
                GROUP BY b.killmail_id
            ) fb
            JOIN LATERAL (
                SELECT fb.killmail_id, COUNT(*) as ac
                FROM killmail_attackers ka2
                WHERE ka2.killmail_id = fb.killmail_id
                GROUP BY ka2.killmail_id
            ) sub ON true
        """
        cur.execute(sql)
    else:
        p = _params(ctx)
        sql = f"""
            SELECT
                AVG(sub.ac)::numeric(10,1) as avg_fleet_size,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY sub.ac)::int as median_fleet_size,
                MAX(sub.ac) as max_fleet_size
            FROM (
                SELECT ka2.killmail_id, COUNT(*) as ac
                FROM killmail_attackers ka2
                JOIN killmails k ON k.killmail_id = ka2.killmail_id
                JOIN killmail_attackers ka_fb ON ka_fb.killmail_id = k.killmail_id
                    AND ka_fb.is_final_blow = true
                    AND ka_fb.alliance_id = %(entity_id)s
                WHERE k.killmail_time >= NOW() - INTERVAL '{days} days'
                GROUP BY ka2.killmail_id
            ) sub
        """
        cur.execute(sql, p)
    row = cur.fetchone()
    if row and row[0]:
        return {
            "avg_fleet_size": float(row[0]),
            "median_fleet_size": int(row[1]) if row[1] else None,
            "max_fleet_size": int(row[2]) if row[2] else None,
        }
    return None


def build_solo_killers(cur, ctx: EntityContext, days: int,
                       *, km_batch: bool = False) -> list:
    """Section 4: Solo killers (dangerous pilots with >=5 solo kills)."""
    if km_batch:
        sql = """
            WITH solo_kills AS (
                SELECT b.killmail_id, b.attacker_character_id, b.ship_value,
                       b.attacker_ship_type_id
                FROM _km_batch b
                JOIN (
                    SELECT killmail_id, COUNT(*) AS ac
                    FROM _km_batch GROUP BY killmail_id
                ) ac ON b.killmail_id = ac.killmail_id
                WHERE ac.ac <= 3
            ),
            pilot_stats AS (
                SELECT
                    sk.attacker_character_id AS character_id,
                    COUNT(DISTINCT sk.killmail_id) AS solo_kills,
                    ROUND(AVG(sk.ship_value)) AS avg_solo_kill_value
                FROM solo_kills sk
                GROUP BY sk.attacker_character_id
                HAVING COUNT(DISTINCT sk.killmail_id) >= 5
            ),
            primary_ships AS (
                SELECT DISTINCT ON (sk.attacker_character_id)
                    sk.attacker_character_id,
                    it."typeName" AS primary_ship
                FROM solo_kills sk
                JOIN "invTypes" it ON sk.attacker_ship_type_id = it."typeID"
                GROUP BY sk.attacker_character_id, it."typeName"
                ORDER BY sk.attacker_character_id, COUNT(*) DESC
            )
            SELECT
                ps.character_id,
                cn.character_name,
                ps.solo_kills,
                ps.avg_solo_kill_value,
                psh.primary_ship
            FROM pilot_stats ps
            LEFT JOIN character_name_cache cn ON ps.character_id = cn.character_id
            LEFT JOIN primary_ships psh ON ps.character_id = psh.attacker_character_id
            ORDER BY ps.solo_kills DESC
            LIMIT 20
        """
        cur.execute(sql)
    else:
        af = _attacker_filter(ctx)
        p = _params(ctx)

        sql = f"""
            SELECT
                ka.character_id,
                cn.character_name,
                COUNT(DISTINCT km.killmail_id) AS solo_kills,
                ROUND(AVG(km.ship_value)) AS avg_solo_kill_value,
                (
                    SELECT it2."typeName"
                    FROM killmail_attackers ka3
                    JOIN "invTypes" it2 ON ka3.ship_type_id = it2."typeID"
                    WHERE ka3.character_id = ka.character_id
                        AND ka3.killmail_id IN (
                            SELECT km2.killmail_id
                            FROM killmails km2
                            JOIN killmail_attackers ka4 ON km2.killmail_id = ka4.killmail_id
                            WHERE ka4.character_id = ka.character_id
                                AND (SELECT COUNT(*) FROM killmail_attackers ka5 WHERE ka5.killmail_id = km2.killmail_id) <= 3
                        )
                    GROUP BY it2."typeName"
                    ORDER BY COUNT(*) DESC
                    LIMIT 1
                ) AS primary_ship
            FROM killmails km
            JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
            LEFT JOIN character_name_cache cn ON ka.character_id = cn.character_id
            WHERE {af}
                AND km.killmail_time >= NOW() - INTERVAL '{days} days'
                AND (SELECT COUNT(*) FROM killmail_attackers ka2 WHERE ka2.killmail_id = km.killmail_id) <= 3
            GROUP BY ka.character_id, cn.character_name
            HAVING COUNT(DISTINCT km.killmail_id) >= 5
            ORDER BY solo_kills DESC
            LIMIT 20
        """

        cur.execute(sql, p)
    return [
        {
            "character_id": cid, "character_name": cn, "solo_kills": sk,
            "avg_solo_kill_value": float(avg or 0), "primary_ship": ps,
        }
        for cid, cn, sk, avg, ps in cur.fetchall()
    ]


def build_doctrine_profile(cur, ctx: EntityContext, days: int,
                           *, km_batch: bool = False) -> list:
    """Section 5: Doctrine profile (top 15 ships used when attacking)."""
    if km_batch:
        sql = """
            SELECT
                it."typeName" AS ship_name,
                ig."groupName" AS ship_class,
                COUNT(DISTINCT b.killmail_id) AS count,
                ROUND(100.0 * COUNT(DISTINCT b.killmail_id) / SUM(COUNT(DISTINCT b.killmail_id)) OVER (), 1) AS percentage
            FROM _km_batch b
            JOIN "invTypes" it ON b.attacker_ship_type_id = it."typeID"
            JOIN "invGroups" ig ON it."groupID" = ig."groupID"
            WHERE b.attacker_ship_type_id IS NOT NULL
                AND ig."groupName" NOT IN ('Capsule', 'Rookie ship')
            GROUP BY it."typeName", ig."groupName"
            ORDER BY count DESC
            LIMIT 15
        """
        cur.execute(sql)
    else:
        af = _attacker_filter(ctx)
        p = _params(ctx)

        sql = f"""
            SELECT
                it."typeName" AS ship_name,
                ig."groupName" AS ship_class,
                COUNT(DISTINCT km.killmail_id) AS count,
                ROUND(100.0 * COUNT(DISTINCT km.killmail_id) / SUM(COUNT(DISTINCT km.killmail_id)) OVER (), 1) AS percentage
            FROM killmails km
            JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
            JOIN "invTypes" it ON ka.ship_type_id = it."typeID"
            JOIN "invGroups" ig ON it."groupID" = ig."groupID"
            WHERE {af}
                AND km.killmail_time >= NOW() - INTERVAL '{days} days'
                AND ig."groupName" NOT IN ('Capsule', 'Rookie ship')
            GROUP BY it."typeName", ig."groupName"
            ORDER BY count DESC
            LIMIT 15
        """

        cur.execute(sql, p)
    return [
        {"ship_name": sn, "ship_class": sc, "count": c, "percentage": float(pct or 0)}
        for sn, sc, c, pct in cur.fetchall()
    ]


def build_ship_losses_inflicted(cur, ctx: EntityContext, days: int, *, hs_batch: dict = None) -> list:
    """Section 6: Ship losses inflicted (victim ship class distribution).

    Uses hourly_stats JSONB ships_killed for Alliance/PowerBloc.
    Corporation uses corporation_hourly_stats similarly.

    When hs_batch is provided, processes pre-fetched data in Python.
    """
    if hs_batch is not None:
        type_info = hs_batch["type_info"]
        ship_class_counts: dict[str, int] = defaultdict(int)
        for row in hs_batch["rows"]:
            ships_killed = _parse_jsonb(row[5])
            for tid_str, count_val in ships_killed.items():
                tid = int(tid_str)
                info = type_info.get(tid)
                if info:
                    ship_class_counts[classify_ship_group(info["group"])] += int(count_val)

        total = sum(ship_class_counts.values())
        return [
            {"ship_class": sc, "count": c, "percentage": round(100.0 * c / total, 1) if total > 0 else 0.0}
            for sc, c in sorted(ship_class_counts.items(), key=lambda x: x[1], reverse=True)
        ]

    hs = _hourly_stats_table(ctx)
    hf = _hourly_stats_filter(ctx)
    p = _params(ctx)

    sql = f"""
        SELECT
            it."typeID",
            ig."groupName",
            SUM(ships.value::INT) AS count
        FROM {hs},
        LATERAL jsonb_each_text(ships_killed) as ships(ship_type_id, value)
        JOIN "invTypes" it ON ships.ship_type_id::INT = it."typeID"
        JOIN "invGroups" ig ON it."groupID" = ig."groupID"
        WHERE {hf}
          AND hour_bucket >= NOW() - INTERVAL '{days} days'
        GROUP BY it."typeID", ig."groupName"
    """

    cur.execute(sql, p)

    ship_class_counts: dict[str, int] = defaultdict(int)
    for type_id, group_name, count in cur.fetchall():
        ship_class_counts[classify_ship_group(group_name)] += count

    total = sum(ship_class_counts.values())
    return [
        {"ship_class": sc, "count": c, "percentage": round(100.0 * c / total, 1) if total > 0 else 0.0}
        for sc, c in sorted(ship_class_counts.items(), key=lambda x: x[1], reverse=True)
    ]


def build_victim_analysis(cur, ctx: EntityContext, days: int,
                          *, km_batch: bool = False) -> dict:
    """Section 7: Victim analysis (PvP vs PvE profiling)."""
    if km_batch:
        sql = """
            WITH victim_kills AS (
                SELECT DISTINCT ON (b.killmail_id)
                    b.killmail_id,
                    b.ship_value,
                    ig."groupName" AS victim_ship_group,
                    ac.attacker_count
                FROM _km_batch b
                LEFT JOIN "invTypes" it ON b.victim_ship_type_id = it."typeID"
                LEFT JOIN "invGroups" ig ON it."groupID" = ig."groupID"
                JOIN (
                    SELECT killmail_id, COUNT(*) AS attacker_count
                    FROM _km_batch GROUP BY killmail_id
                ) ac ON b.killmail_id = ac.killmail_id
            )
            SELECT
                COUNT(*) AS total_kills,
                COUNT(CASE WHEN attacker_count > 2 AND NOT (attacker_count > 5 AND ship_value > 500000000) THEN 1 END) AS pvp_kills,
                COUNT(CASE WHEN attacker_count <= 2 THEN 1 END) AS pve_kills,
                COUNT(CASE WHEN attacker_count > 5 AND ship_value > 500000000 THEN 1 END) AS gank_kills,
                ROUND(AVG(ship_value)) AS avg_victim_value,
                COUNT(CASE WHEN victim_ship_group IN ('Carrier', 'Dreadnought', 'Force Auxiliary', 'Supercarrier', 'Titan') THEN 1 END) AS capital_kills
            FROM victim_kills
        """
        cur.execute(sql)
    else:
        af = _attacker_filter(ctx)
        p = _params(ctx)

        sql = f"""
            WITH victim_kills AS (
                SELECT DISTINCT
                    km.killmail_id,
                    km.ship_value,
                    ig."groupName" AS victim_ship_group,
                    (SELECT COUNT(*) FROM killmail_attackers ka2 WHERE ka2.killmail_id = km.killmail_id) AS attacker_count
                FROM killmails km
                JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
                LEFT JOIN "invTypes" it ON km.ship_type_id = it."typeID"
                LEFT JOIN "invGroups" ig ON it."groupID" = ig."groupID"
                WHERE {af}
                    AND km.killmail_time >= NOW() - INTERVAL '{days} days'
            )
            SELECT
                COUNT(*) AS total_kills,
                COUNT(CASE WHEN attacker_count > 2 AND NOT (attacker_count > 5 AND ship_value > 500000000) THEN 1 END) AS pvp_kills,
                COUNT(CASE WHEN attacker_count <= 2 THEN 1 END) AS pve_kills,
                COUNT(CASE WHEN attacker_count > 5 AND ship_value > 500000000 THEN 1 END) AS gank_kills,
                ROUND(AVG(ship_value)) AS avg_victim_value,
                COUNT(CASE WHEN victim_ship_group IN ('Carrier', 'Dreadnought', 'Force Auxiliary', 'Supercarrier', 'Titan') THEN 1 END) AS capital_kills
            FROM victim_kills
        """

        cur.execute(sql, p)
    r = cur.fetchone()
    return {
        "total_kills": r[0] or 0,
        "pvp_kills": r[1] or 0,
        "pve_kills": r[2] or 0,
        "gank_kills": r[3] or 0,
        "avg_victim_value": float(r[4] or 0),
        "capital_kills": r[5] or 0,
    }


def _extract_system_kills(systems_kills_jsonb, is_alliance: bool = False) -> dict:
    """Extract system kills from JSONB value, handling both flat and nested formats.

    Returns {system_id: {"kills": int, "solo_kills": int}}.
    """
    data = _parse_jsonb(systems_kills_jsonb)
    result = {}
    for sid_str, val in data.items():
        sid = int(sid_str)
        if isinstance(val, dict):
            # Nested format: {"kills": N, "solo_kills": M, "total_value": V}
            result[sid] = {
                "kills": int(val.get("kills", 0)),
                "solo_kills": int(val.get("solo_kills", 0)),
                "total_value": int(val.get("total_value", 0)),
            }
        else:
            # Flat format: just a count
            result[sid] = {"kills": int(val), "solo_kills": 0, "total_value": 0}
    return result


def build_kill_heatmap(cur, ctx: EntityContext, days: int, *, hs_batch: dict = None) -> list:
    """Section 8: Kill heatmap (top 20 systems, gatecamp detection).

    Alliance: Uses hourly_stats systems_kills JSONB with solo_kills sub-field.
    Corporation: Uses corporation_hourly_stats systems_kills + solo_ratio.
    PowerBloc: Uses hourly_stats systems_kills JSONB (no solo detection).

    When hs_batch is provided (Alliance/PowerBloc only), processes pre-fetched data.
    Corporation always uses SQL due to solo_ratio column dependency.
    """
    if hs_batch is not None and ctx.entity_type != EntityType.CORPORATION:
        system_info = hs_batch["system_info"]
        # Aggregate system kills across all rows
        sys_agg: dict[int, dict] = defaultdict(lambda: {"kills": 0, "solo_kills": 0})
        for row in hs_batch["rows"]:
            sys_data = _extract_system_kills(row[7], is_alliance=(ctx.entity_type == EntityType.ALLIANCE))
            for sid, vals in sys_data.items():
                sys_agg[sid]["kills"] += vals["kills"]
                sys_agg[sid]["solo_kills"] += vals["solo_kills"]

        result = []
        for sid, agg in sorted(sys_agg.items(), key=lambda x: x[1]["kills"], reverse=True)[:20]:
            info = system_info.get(sid)
            if not info:
                continue
            kills = agg["kills"]
            solo = agg["solo_kills"]
            if ctx.entity_type == EntityType.ALLIANCE:
                is_gatecamp = kills > 0 and (solo / kills) > 0.6
            else:
                is_gatecamp = False  # PowerBloc: no gatecamp detection
            result.append({
                "system_id": sid,
                "system_name": info["name"],
                "region_name": info["region"],
                "kills": kills,
                "kills_per_day": round(kills / days, 1) if days > 0 else 0.0,
                "is_gatecamp": is_gatecamp,
            })
        return result

    p = _params_with_days(ctx, days)

    if ctx.entity_type == EntityType.CORPORATION:
        sql = f"""
            WITH system_activity AS (
                SELECT
                    systems.system_id::INT AS system_id,
                    SUM(systems.value::INT) AS kills,
                    AVG(solo_ratio) AS avg_solo_ratio
                FROM corporation_hourly_stats
                CROSS JOIN LATERAL jsonb_each_text(systems_kills) as systems(system_id, value)
                WHERE corporation_id = %(entity_id)s
                  AND hour_bucket >= NOW() - INTERVAL '{days} days'
                GROUP BY systems.system_id::INT
            )
            SELECT
                sa.system_id,
                ms."solarSystemName" AS system_name,
                mr."regionName" AS region_name,
                sa.kills,
                ROUND(sa.kills::numeric / %(days)s, 1) AS kills_per_day,
                CASE WHEN sa.avg_solo_ratio > 0.6 THEN true ELSE false END AS is_gatecamp
            FROM system_activity sa
            JOIN "mapSolarSystems" ms ON sa.system_id = ms."solarSystemID"
            JOIN "mapRegions" mr ON ms."regionID" = mr."regionID"
            ORDER BY sa.kills DESC
            LIMIT 20
        """
    elif ctx.entity_type == EntityType.ALLIANCE:
        sql = f"""
            WITH system_agg AS (
                SELECT
                    systems.system_id::INT AS system_id,
                    SUM(CASE
                        WHEN jsonb_typeof(systems.data) = 'object'
                        THEN (systems.data->>'kills')::INT
                        ELSE systems.data::TEXT::INT
                    END) AS kills,
                    SUM(CASE
                        WHEN jsonb_typeof(systems.data) = 'object'
                        THEN COALESCE((systems.data->>'solo_kills')::INT, 0)
                        ELSE 0
                    END) AS solo_kills
                FROM intelligence_hourly_stats,
                LATERAL jsonb_each(systems_kills) as systems(system_id, data)
                WHERE alliance_id = %(entity_id)s
                  AND hour_bucket >= NOW() - INTERVAL '{days} days'
                GROUP BY systems.system_id
            )
            SELECT
                sa.system_id,
                ms."solarSystemName" AS system_name,
                mr."regionName" AS region_name,
                sa.kills,
                ROUND(sa.kills::numeric / {days}, 1) AS kills_per_day,
                CASE WHEN sa.kills > 0 AND (sa.solo_kills::float / sa.kills) > 0.6 THEN true ELSE false END AS is_gatecamp
            FROM system_agg sa
            JOIN "mapSolarSystems" ms ON sa.system_id = ms."solarSystemID"
            JOIN "mapRegions" mr ON ms."regionID" = mr."regionID"
            ORDER BY sa.kills DESC
            LIMIT 20
        """
    else:
        # PowerBloc: no solo detection
        sql = f"""
            WITH system_agg AS (
                SELECT
                    systems.system_id::INT AS system_id,
                    SUM(CASE
                        WHEN jsonb_typeof(systems.data) = 'object'
                        THEN (systems.data->>'kills')::INT
                        ELSE systems.data::TEXT::INT
                    END) AS kills
                FROM intelligence_hourly_stats,
                LATERAL jsonb_each(systems_kills) as systems(system_id, data)
                WHERE alliance_id = ANY(%(entity_id)s)
                  AND hour_bucket >= NOW() - INTERVAL '{days} days'
                GROUP BY systems.system_id
            )
            SELECT
                sa.system_id,
                ms."solarSystemName" AS system_name,
                mr."regionName" AS region_name,
                sa.kills,
                ROUND(sa.kills::numeric / {days}, 1) AS kills_per_day,
                false AS is_gatecamp
            FROM system_agg sa
            JOIN "mapSolarSystems" ms ON sa.system_id = ms."solarSystemID"
            JOIN "mapRegions" mr ON ms."regionID" = mr."regionID"
            ORDER BY sa.kills DESC
            LIMIT 20
        """

    cur.execute(sql, p)
    return [
        {
            "system_id": sid, "system_name": sn, "region_name": rn,
            "kills": k, "kills_per_day": float(kpd or 0), "is_gatecamp": gc,
        }
        for sid, sn, rn, k, kpd, gc in cur.fetchall()
    ]


def build_hunting_regions(cur, ctx: EntityContext, days: int, *, hs_batch: dict = None) -> list:
    """Section 9: Hunting regions (top 15 regions).

    Alliance/PowerBloc: Uses hourly_stats systems_kills JSONB.
    Corporation: Uses corporation_hourly_stats systems_kills.

    When hs_batch is provided (Alliance/PowerBloc only), processes pre-fetched data.
    Corporation always uses SQL due to different JSONB format.
    """
    if hs_batch is not None and ctx.entity_type != EntityType.CORPORATION:
        system_info = hs_batch["system_info"]
        # Aggregate kills per region from system_kills JSONB
        region_agg: dict[str, dict] = {}  # region_name -> {kills, systems set}
        for row in hs_batch["rows"]:
            sys_data = _extract_system_kills(row[7])
            for sid, vals in sys_data.items():
                info = system_info.get(sid)
                if not info:
                    continue
                region = info["region"]
                if region not in region_agg:
                    region_agg[region] = {"kills": 0, "systems": set()}
                region_agg[region]["kills"] += vals["kills"]
                region_agg[region]["systems"].add(sid)

        total_kills = sum(r["kills"] for r in region_agg.values())
        result = []
        for region, agg in sorted(region_agg.items(), key=lambda x: x[1]["kills"], reverse=True)[:15]:
            result.append({
                "region_id": None,  # Not available from system_info (no regionID stored)
                "region_name": region,
                "kills": agg["kills"],
                "percentage": round(100.0 * agg["kills"] / total_kills, 1) if total_kills > 0 else 0.0,
                "unique_systems": len(agg["systems"]),
            })
        return result

    p = _params(ctx)

    if ctx.entity_type == EntityType.CORPORATION:
        sql = f"""
            WITH region_kills AS (
                SELECT
                    mr."regionID" AS region_id,
                    mr."regionName" AS region_name,
                    SUM(systems.value::INT) AS kills,
                    COUNT(DISTINCT systems.system_id::INT) AS unique_systems
                FROM corporation_hourly_stats
                CROSS JOIN LATERAL jsonb_each_text(systems_kills) as systems(system_id, value)
                JOIN "mapSolarSystems" ms ON systems.system_id::INT = ms."solarSystemID"
                JOIN "mapRegions" mr ON ms."regionID" = mr."regionID"
                WHERE corporation_id = %(entity_id)s
                  AND hour_bucket >= NOW() - INTERVAL '{days} days'
                GROUP BY mr."regionID", mr."regionName"
            )
            SELECT
                region_id, region_name, kills,
                ROUND(100.0 * kills / SUM(kills) OVER (), 1) AS percentage,
                unique_systems
            FROM region_kills
            ORDER BY kills DESC LIMIT 15
        """
    else:
        # Alliance / PowerBloc: intelligence_hourly_stats with JSONB
        hf = _hourly_stats_filter(ctx)
        sql = f"""
            WITH system_region_kills AS (
                SELECT
                    ms."regionID" AS region_id,
                    mr."regionName" AS region_name,
                    SUM(CASE
                        WHEN jsonb_typeof(systems.data) = 'object'
                        THEN (systems.data->>'kills')::INT
                        ELSE systems.data::TEXT::INT
                    END) AS kills,
                    COUNT(DISTINCT systems.system_id::INT) AS unique_systems
                FROM intelligence_hourly_stats,
                LATERAL jsonb_each(systems_kills) as systems(system_id, data)
                JOIN "mapSolarSystems" ms ON systems.system_id::INT = ms."solarSystemID"
                JOIN "mapRegions" mr ON ms."regionID" = mr."regionID"
                WHERE {hf}
                  AND hour_bucket >= NOW() - INTERVAL '{days} days'
                GROUP BY ms."regionID", mr."regionName"
            )
            SELECT
                region_id, region_name, kills,
                ROUND(100.0 * kills / SUM(kills) OVER (), 1) AS percentage,
                unique_systems
            FROM system_region_kills
            ORDER BY kills DESC LIMIT 15
        """

    cur.execute(sql, p)
    return [
        {
            "region_id": rid, "region_name": rn, "kills": k,
            "percentage": float(pct or 0), "unique_systems": us,
        }
        for rid, rn, k, pct, us in cur.fetchall()
    ]


def build_kill_timeline(cur, ctx: EntityContext, days: int) -> list:
    """Section 10: Kill timeline (daily kill counts + active pilots).

    Alliance: hourly_stats for kills, killmail_attackers for pilots.
    Corporation: corporation_hourly_stats (has active_pilots column).
    PowerBloc: killmail-based with DISTINCT to avoid coalition overlap inflation.
    """
    p = _params(ctx)

    if ctx.entity_type == EntityType.CORPORATION:
        sql = f"""
            SELECT
                DATE(hour_bucket) AS day,
                SUM(kills) AS kills,
                SUM(active_pilots) AS active_pilots
            FROM corporation_hourly_stats
            WHERE corporation_id = %(entity_id)s
              AND hour_bucket >= NOW() - INTERVAL '{days} days'
            GROUP BY DATE(hour_bucket)
            ORDER BY DATE(hour_bucket)
        """
    elif ctx.entity_type == EntityType.ALLIANCE:
        sql = f"""
            WITH daily_kills AS (
                SELECT
                    DATE(hour_bucket) AS day,
                    SUM(kills) AS kills
                FROM intelligence_hourly_stats
                WHERE alliance_id = %(entity_id)s
                    AND hour_bucket >= NOW() - INTERVAL '{days} days'
                GROUP BY DATE(hour_bucket)
            ),
            daily_pilots AS (
                SELECT
                    DATE(km.killmail_time) AS day,
                    COUNT(DISTINCT ka.character_id) AS active_pilots
                FROM killmails km
                JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
                WHERE ka.alliance_id = %(entity_id)s
                    AND km.killmail_time >= NOW() - INTERVAL '{days} days'
                GROUP BY DATE(km.killmail_time)
            )
            SELECT
                dk.day, dk.kills, COALESCE(dp.active_pilots, 0) AS active_pilots
            FROM daily_kills dk
            LEFT JOIN daily_pilots dp ON dk.day = dp.day
            ORDER BY dk.day
        """
    else:
        # PowerBloc: killmail-based with DISTINCT
        sql = f"""
            WITH daily_kills AS (
                SELECT DATE(km.killmail_time) AS day,
                    COUNT(DISTINCT km.killmail_id) AS kills
                FROM killmails km
                JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
                WHERE ka.alliance_id = ANY(%(entity_id)s)
                    AND km.killmail_time >= NOW() - INTERVAL '{days} days'
                GROUP BY DATE(km.killmail_time)
            ),
            daily_pilots AS (
                SELECT DATE(km.killmail_time) AS day,
                    COUNT(DISTINCT ka.character_id) AS active_pilots
                FROM killmails km
                JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
                WHERE ka.alliance_id = ANY(%(entity_id)s)
                    AND km.killmail_time >= NOW() - INTERVAL '{days} days'
                GROUP BY DATE(km.killmail_time)
            )
            SELECT dk.day, dk.kills, COALESCE(dp.active_pilots, 0) AS active_pilots
            FROM daily_kills dk
            LEFT JOIN daily_pilots dp ON dk.day = dp.day
            ORDER BY dk.day
        """

    cur.execute(sql, p)
    return [
        {"day": d.isoformat(), "kills": k, "active_pilots": ap}
        for d, k, ap in cur.fetchall()
    ]


def build_capital_threat(cur, ctx: EntityContext, days: int, total_kills: int) -> Optional[dict]:
    """Section 11: Capital threat (capital kill breakdown).

    Alliance: Uses distinct killmails with alliance filter.
    Corporation: Uses distinct killmails with corporation filter + total_kills subquery.
    PowerBloc: Uses distinct killmails with ANY() + ep_total parameter.
    """
    af = _attacker_filter(ctx)
    p = _params(ctx)

    if ctx.entity_type == EntityType.CORPORATION:
        sql = f"""
            WITH capital_kills AS (
                SELECT
                    COUNT(*) AS total_capital_kills,
                    (SELECT COUNT(*) FROM killmails km2 JOIN killmail_attackers ka2 ON km2.killmail_id = ka2.killmail_id
                     WHERE ka2.corporation_id = %(entity_id)s AND km2.killmail_time >= NOW() - INTERVAL '{days} days') AS total_kills,
                    COUNT(CASE WHEN ig."groupName" = 'Carrier' THEN 1 END) AS carrier_kills,
                    COUNT(CASE WHEN ig."groupName" = 'Dreadnought' THEN 1 END) AS dread_kills,
                    COUNT(CASE WHEN ig."groupName" IN ('Supercarrier', 'Titan') THEN 1 END) AS super_titan_kills,
                    ROUND(AVG(km.ship_value)) AS avg_capital_kill_value
                FROM killmails km
                JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
                JOIN "invTypes" it ON km.ship_type_id = it."typeID"
                JOIN "invGroups" ig ON it."groupID" = ig."groupID"
                WHERE ka.corporation_id = %(entity_id)s
                    AND ig."groupName" IN ('Carrier', 'Dreadnought', 'Force Auxiliary', 'Supercarrier', 'Titan')
                    AND km.killmail_time >= NOW() - INTERVAL '{days} days'
            )
            SELECT
                total_capital_kills,
                CASE WHEN total_kills > 0 THEN ROUND(100.0 * total_capital_kills / total_kills, 1) ELSE 0 END AS capital_kill_pct,
                carrier_kills, dread_kills, super_titan_kills, avg_capital_kill_value
            FROM capital_kills WHERE total_capital_kills > 0
        """
        cur.execute(sql, p)
        row = cur.fetchone()
        if row:
            return {
                "capital_kills": row[0],
                "capital_kill_pct": float(row[1] or 0),
                "carrier_kills": row[2],
                "dread_kills": row[3],
                "super_titan_kills": row[4],
                "avg_capital_kill_value": float(row[5] or 0),
            }
        return None

    elif ctx.entity_type == EntityType.ALLIANCE:
        sql = f"""
            WITH capital_kills AS (
                SELECT DISTINCT
                    km.killmail_id, ig."groupName", km.ship_value
                FROM killmails km
                JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
                JOIN "invTypes" it ON km.ship_type_id = it."typeID"
                JOIN "invGroups" ig ON it."groupID" = ig."groupID"
                WHERE ka.alliance_id = %(entity_id)s
                    AND km.killmail_time >= NOW() - INTERVAL '{days} days'
                    AND ig."groupName" IN ('Carrier', 'Dreadnought', 'Force Auxiliary', 'Supercarrier', 'Titan')
            )
            SELECT
                COUNT(*) AS total_capital_kills,
                ROUND(AVG(ship_value)) AS avg_capital_kill_value,
                COUNT(CASE WHEN "groupName" = 'Carrier' THEN 1 END) AS carrier_kills,
                COUNT(CASE WHEN "groupName" = 'Dreadnought' THEN 1 END) AS dread_kills,
                COUNT(CASE WHEN "groupName" IN ('Supercarrier', 'Titan') THEN 1 END) AS super_titan_kills
            FROM capital_kills
        """
        cur.execute(sql, p)
        row = cur.fetchone()
        if row and row[0] > 0:
            capital_kill_pct = round(100.0 * row[0] / total_kills, 1) if total_kills > 0 else 0.0
            return {
                "capital_kills": row[0],
                "capital_kill_pct": capital_kill_pct,
                "carrier_kills": row[2],
                "dread_kills": row[3],
                "super_titan_kills": row[4],
                "avg_capital_kill_value": float(row[1] or 0),
            }
        return None

    else:
        # PowerBloc: uses ep_total passed in as total_kills
        p_ext = {**p, "ep_total": total_kills}
        sql = f"""
            WITH capital_kills AS (
                SELECT DISTINCT
                    km.killmail_id, km.ship_value, ig."groupName"
                FROM killmails km
                JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
                JOIN "invTypes" it ON km.ship_type_id = it."typeID"
                JOIN "invGroups" ig ON it."groupID" = ig."groupID"
                WHERE ka.alliance_id = ANY(%(entity_id)s)
                    AND km.killmail_time >= NOW() - INTERVAL '{days} days'
                    AND ig."groupName" IN ('Carrier', 'Dreadnought', 'Force Auxiliary', 'Supercarrier', 'Titan')
            )
            SELECT
                COUNT(*) AS total_capital_kills,
                ROUND(100.0 * COUNT(*) / NULLIF(%(ep_total)s, 0), 1) AS capital_kill_pct,
                COUNT(CASE WHEN "groupName" = 'Carrier' THEN 1 END) AS carrier_kills,
                COUNT(CASE WHEN "groupName" = 'Dreadnought' THEN 1 END) AS dread_kills,
                COUNT(CASE WHEN "groupName" IN ('Supercarrier', 'Titan') THEN 1 END) AS super_titan_kills,
                ROUND(AVG(ship_value)) AS avg_capital_kill_value
            FROM capital_kills
        """
        cur.execute(sql, p_ext)
        row = cur.fetchone()
        if row and row[0] > 0:
            return {
                "capital_kills": row[0],
                "capital_kill_pct": float(row[1] or 0),
                "carrier_kills": row[2],
                "dread_kills": row[3],
                "super_titan_kills": row[4],
                "avg_capital_kill_value": float(row[5] or 0),
            }
        return None


def build_top_victims(cur, ctx: EntityContext, days: int,
                      *, km_batch: bool = False) -> list:
    """Section 12: Top victims (top 30 corps killed)."""
    if km_batch:
        sql = """
            WITH unique_victim_kills AS (
                SELECT DISTINCT killmail_id, victim_corporation_id, ship_value
                FROM _km_batch
                WHERE victim_corporation_id IS NOT NULL
            )
            SELECT
                uvk.victim_corporation_id,
                cn.corporation_name,
                COUNT(*) AS kills_on_them,
                SUM(uvk.ship_value) AS isk_destroyed
            FROM unique_victim_kills uvk
            LEFT JOIN corp_name_cache cn ON uvk.victim_corporation_id = cn.corporation_id
            GROUP BY uvk.victim_corporation_id, cn.corporation_name
            ORDER BY kills_on_them DESC
            LIMIT 30
        """
        cur.execute(sql)
    else:
        af = _attacker_filter(ctx)
        p = _params(ctx)

        sql = f"""
            WITH unique_victim_kills AS (
                SELECT DISTINCT
                    km.killmail_id, km.victim_corporation_id, km.ship_value
                FROM killmails km
                JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
                WHERE {af}
                    AND km.killmail_time >= NOW() - INTERVAL '{days} days'
                    AND km.victim_corporation_id IS NOT NULL
            )
            SELECT
                uvk.victim_corporation_id,
                cn.corporation_name,
                COUNT(*) AS kills_on_them,
                SUM(uvk.ship_value) AS isk_destroyed
            FROM unique_victim_kills uvk
            LEFT JOIN corp_name_cache cn ON uvk.victim_corporation_id = cn.corporation_id
            GROUP BY uvk.victim_corporation_id, cn.corporation_name
            ORDER BY kills_on_them DESC
            LIMIT 30
        """

        cur.execute(sql, p)
    return [
        {
            "corporation_id": cid, "corporation_name": cn,
            "kills_on_them": k, "isk_destroyed": isk or 0.0,
        }
        for cid, cn, k, isk in cur.fetchall()
    ]


def build_high_value_kills(cur, ctx: EntityContext, days: int,
                           *, km_batch: bool = False) -> list:
    """Section 13: High-value kills (top 10 most expensive kills)."""
    if km_batch:
        sql = """
            WITH unique_kills AS (
                SELECT DISTINCT killmail_id
                FROM _km_batch
            )
            SELECT
                km.killmail_id, km.killmail_time, km.ship_value,
                km.victim_character_id,
                vc.character_name AS victim_name,
                km.ship_type_id,
                it."typeName" AS ship_name,
                ms."solarSystemName" AS system_name
            FROM unique_kills uk
            JOIN killmails km ON uk.killmail_id = km.killmail_id
            LEFT JOIN character_name_cache vc ON km.victim_character_id = vc.character_id
            LEFT JOIN "invTypes" it ON km.ship_type_id = it."typeID"
            LEFT JOIN "mapSolarSystems" ms ON km.solar_system_id = ms."solarSystemID"
            ORDER BY km.ship_value DESC
            LIMIT 10
        """
        cur.execute(sql)
    else:
        af = _attacker_filter(ctx)
        p = _params(ctx)

        sql = f"""
            WITH unique_kills AS (
                SELECT DISTINCT km.killmail_id
                FROM killmails km
                JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
                WHERE {af}
                    AND km.killmail_time >= NOW() - INTERVAL '{days} days'
            )
            SELECT
                km.killmail_id, km.killmail_time, km.ship_value,
                km.victim_character_id,
                vc.character_name AS victim_name,
                km.ship_type_id,
                it."typeName" AS ship_name,
                ms."solarSystemName" AS system_name
            FROM unique_kills uk
            JOIN killmails km ON uk.killmail_id = km.killmail_id
            LEFT JOIN character_name_cache vc ON km.victim_character_id = vc.character_id
            LEFT JOIN "invTypes" it ON km.ship_type_id = it."typeID"
            LEFT JOIN "mapSolarSystems" ms ON km.solar_system_id = ms."solarSystemID"
            ORDER BY km.ship_value DESC
            LIMIT 10
        """

        cur.execute(sql, p)
    return [
        {
            "killmail_id": kid, "killmail_time": kt.isoformat() if kt else None,
            "isk_value": iv, "victim_character_id": vcid, "victim_name": vn,
            "ship_type_id": stid, "ship_name": sn, "system_name": sys_n,
        }
        for kid, kt, iv, vcid, vn, stid, sn, sys_n in cur.fetchall()
    ]


def _compute_hunting_hours_windows(hourly_data: list, ctx: EntityContext) -> dict:
    """Compute peak/safe 4-hour windows from hourly kill data."""
    # Find peak 4-hour window
    max_sum, peak_start = 0, 0
    for h in range(24):
        ws = sum(hourly_data[h:(h + 4)] if h <= 20 else hourly_data[h:] + hourly_data[:(h + 4 - 24)])
        if ws > max_sum:
            max_sum, peak_start = ws, h
    peak_end = (peak_start + 4) % 24

    # Find safe 4-hour window
    min_sum, safe_start = float('inf'), 0
    for h in range(24):
        ws = sum(hourly_data[h:(h + 4)] if h <= 20 else hourly_data[h:] + hourly_data[:(h + 4 - 24)])
        if ws < min_sum:
            min_sum, safe_start = ws, h
    safe_end = (safe_start + 4) % 24

    result = {
        "peak_start": peak_start, "peak_end": peak_end,
        "safe_start": safe_start, "safe_end": safe_end,
    }

    # Alliance and Corporation include hourly_activity, PowerBloc does not
    if ctx.entity_type != EntityType.POWERBLOC:
        result["hourly_activity"] = hourly_data

    return result


def build_hunting_hours(cur, ctx: EntityContext, days: int, *, hs_batch: dict = None,
                        km_batch: bool = False) -> dict:
    """Section 14: Peak hunting hours (hourly kill distribution + 4h window analysis).

    Alliance: Uses hourly_stats hour_bucket EXTRACT.
    Corporation: Uses raw killmail_time EXTRACT (corp hourly_stats lacks hour granularity).
    PowerBloc: Uses hourly_stats hour_bucket EXTRACT.
    Returns dict with peak/safe windows and optionally hourly_activity list.

    When hs_batch is provided (Alliance/PowerBloc only), processes pre-fetched data.
    When km_batch is True (Corporation), uses _km_batch temp table.
    """
    if hs_batch is not None and ctx.entity_type != EntityType.CORPORATION:
        hourly_data = [0] * 24
        for row in hs_batch["rows"]:
            hour = row[0].hour  # hour_bucket datetime
            kills = row[1] or 0
            hourly_data[hour] += kills
        return _compute_hunting_hours_windows(hourly_data, ctx)

    p = _params(ctx)

    if km_batch and ctx.entity_type == EntityType.CORPORATION:
        sql = """
            WITH hourly_kills AS (
                SELECT
                    EXTRACT(HOUR FROM killmail_time) AS hour,
                    COUNT(DISTINCT killmail_id) AS kills
                FROM _km_batch
                GROUP BY EXTRACT(HOUR FROM killmail_time)
            )
            SELECT hour, kills FROM hourly_kills ORDER BY hour
        """
        cur.execute(sql)
        hourly_data = [0] * 24
        for hour, kills in cur.fetchall():
            hourly_data[int(hour)] = kills
        return _compute_hunting_hours_windows(hourly_data, ctx)

    if ctx.entity_type == EntityType.CORPORATION:
        sql = f"""
            WITH hourly_kills AS (
                SELECT
                    EXTRACT(HOUR FROM km.killmail_time) AS hour,
                    COUNT(*) AS kills
                FROM killmails km
                JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
                WHERE ka.corporation_id = %(entity_id)s
                    AND km.killmail_time >= NOW() - INTERVAL '{days} days'
                GROUP BY EXTRACT(HOUR FROM km.killmail_time)
            )
            SELECT hour, kills FROM hourly_kills ORDER BY hour
        """
    else:
        # Alliance / PowerBloc: intelligence_hourly_stats
        hf = _hourly_stats_filter(ctx)
        sql = f"""
            SELECT
                EXTRACT(HOUR FROM hour_bucket) AS hour,
                SUM(kills) AS kills
            FROM intelligence_hourly_stats
            WHERE {hf}
                AND hour_bucket >= NOW() - INTERVAL '{days} days'
            GROUP BY EXTRACT(HOUR FROM hour_bucket)
            ORDER BY hour
        """

    cur.execute(sql, p)
    hourly_data = [0] * 24
    for hour, kills in cur.fetchall():
        hourly_data[int(hour)] = kills

    return _compute_hunting_hours_windows(hourly_data, ctx)


def build_damage_dealt(cur, ctx: EntityContext, days: int,
                       *, km_batch: bool = False) -> list:
    """Section 15: Damage dealt profile (weapon damage type distribution)."""
    damage_case = """
                CASE
                    WHEN wdp.weapon_class = 'Hybrid' THEN 'mixed'
                    WHEN wdp.primary_damage_type IS NOT NULL THEN wdp.primary_damage_type
                    WHEN ig."groupName" ILIKE '%%missile%%' THEN
                        CASE
                            WHEN it."typeName" ILIKE '%%mjolnir%%' OR it."typeName" ILIKE '%%wrath%%' OR it."typeName" ILIKE '%%thunderbolt%%' THEN 'em'
                            WHEN it."typeName" ILIKE '%%inferno%%' OR it."typeName" ILIKE '%%hellfire%%' OR it."typeName" ILIKE '%%scoria%%' THEN 'thermal'
                            WHEN it."typeName" ILIKE '%%scourge%%' OR it."typeName" ILIKE '%%juror%%' OR it."typeName" ILIKE '%%concussion%%' THEN 'kinetic'
                            WHEN it."typeName" ILIKE '%%nova%%' OR it."typeName" ILIKE '%%havoc%%' OR it."typeName" ILIKE '%%bane%%' OR it."typeName" ILIKE '%%shrapnel%%' THEN 'explosive'
                            ELSE NULL
                        END
                    WHEN ig."groupName" = 'Hybrid Weapon' THEN 'mixed'
                    WHEN ig."groupName" = 'Energy Weapon' THEN 'em'
                    WHEN ig."groupName" = 'Projectile Weapon' THEN 'explosive'
                    WHEN ig."groupName" = 'Precursor Weapon' THEN 'thermal'
                    WHEN ig."groupName" = 'Bomb' THEN
                        CASE
                            WHEN it."typeName" ILIKE '%%electron%%' THEN 'em'
                            WHEN it."typeName" ILIKE '%%scoria%%' THEN 'thermal'
                            WHEN it."typeName" ILIKE '%%concussion%%' THEN 'kinetic'
                            WHEN it."typeName" ILIKE '%%shrapnel%%' THEN 'explosive'
                            ELSE NULL
                        END
                    ELSE NULL
                END AS damage_type"""

    if km_batch:
        sql = f"""
            WITH classified_weapons AS (
                SELECT {damage_case}
                FROM _km_batch b
                LEFT JOIN weapon_damage_profiles wdp ON b.weapon_type_id = wdp.type_id
                LEFT JOIN "invTypes" it ON b.weapon_type_id = it."typeID"
                LEFT JOIN "invGroups" ig ON it."groupID" = ig."groupID"
                WHERE b.weapon_type_id IS NOT NULL
            )
            SELECT damage_type, COUNT(*) AS count
            FROM classified_weapons
            WHERE damage_type IS NOT NULL
            GROUP BY damage_type
        """
        cur.execute(sql)
    else:
        af = _attacker_filter(ctx)
        p = _params(ctx)

        sql = f"""
            WITH classified_weapons AS (
                SELECT {damage_case}
                FROM killmails km
                JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
                LEFT JOIN weapon_damage_profiles wdp ON ka.weapon_type_id = wdp.type_id
                LEFT JOIN "invTypes" it ON ka.weapon_type_id = it."typeID"
                LEFT JOIN "invGroups" ig ON it."groupID" = ig."groupID"
                WHERE {af}
                    AND ka.weapon_type_id IS NOT NULL
                    AND km.killmail_time >= NOW() - INTERVAL '{days} days'
            )
            SELECT damage_type, COUNT(*) AS count
            FROM classified_weapons
            WHERE damage_type IS NOT NULL
            GROUP BY damage_type
        """
        cur.execute(sql, p)
    damage_counts = {"EM": 0, "Thermal": 0, "Kinetic": 0, "Explosive": 0, "Mixed": 0}
    total_weapons = 0

    for row in cur.fetchall():
        dt = row[0]
        cnt = row[1]
        if dt:
            dt = 'EM' if dt.lower() == 'em' else dt.capitalize()
            if dt in damage_counts:
                damage_counts[dt] += cnt
                total_weapons += cnt

    return [
        {"damage_type": dt, "count": c, "percentage": round(100.0 * c / max(total_weapons, 1), 1)}
        for dt, c in damage_counts.items() if c > 0
    ]


def build_ewar_usage(cur, ctx: EntityContext, days: int,
                     *, km_batch: bool = False) -> list:
    """Section 16: E-War usage (electronic warfare module distribution)."""
    if km_batch:
        sql = """
            SELECT ig."groupName", COUNT(*) AS count
            FROM _km_batch b
            JOIN "invTypes" it ON b.weapon_type_id = it."typeID"
            JOIN "invGroups" ig ON it."groupID" = ig."groupID"
            WHERE ig."categoryID" = 7
                AND ig."groupName" IN ('Target Painter', 'Warp Scrambler', 'Stasis Web', 'Energy Neutralizer',
                                       'Warp Disrupt Field Generator', 'Weapon Disruptor', 'ECM', 'Sensor Dampener',
                                       'Remote Sensor Dampener', 'Remote ECM Burst', 'Tracking Disruptor')
            GROUP BY ig."groupName"
        """
        cur.execute(sql)
    else:
        af = _attacker_filter(ctx)
        p = _params(ctx)

        sql = f"""
            SELECT ig."groupName", COUNT(*) AS count
            FROM killmails km
            JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
            JOIN "invTypes" it ON ka.weapon_type_id = it."typeID"
            JOIN "invGroups" ig ON it."groupID" = ig."groupID"
            WHERE {af}
                AND ig."categoryID" = 7
                AND ig."groupName" IN ('Target Painter', 'Warp Scrambler', 'Stasis Web', 'Energy Neutralizer',
                                       'Warp Disrupt Field Generator', 'Weapon Disruptor', 'ECM', 'Sensor Dampener',
                                       'Remote Sensor Dampener', 'Remote ECM Burst', 'Tracking Disruptor')
                AND km.killmail_time >= NOW() - INTERVAL '{days} days'
            GROUP BY ig."groupName"
        """
        cur.execute(sql, p)
    ewar_data: dict[str, int] = {}
    total_ewar = 0
    for group_name, count in cur.fetchall():
        total_ewar += count
        if 'Disrupt Field' in group_name:
            etype = 'Warp Disruption Bubble'
        elif 'Neutraliz' in group_name:
            etype = 'Energy Neutralizer'
        elif 'ECM' in group_name:
            etype = 'ECM Jammer'
        elif 'Damp' in group_name:
            etype = 'Sensor Dampener'
        elif 'Stasis' in group_name or group_name == 'Stasis Web':
            etype = 'Stasis Webifier'
        elif 'Scrambler' in group_name:
            etype = 'Warp Scrambler'
        elif 'Target Painter' in group_name:
            etype = 'Target Painter'
        elif 'Weapon' in group_name or 'Tracking' in group_name:
            etype = 'Tracking Disruptor'
        else:
            etype = 'Other E-War'
        ewar_data[etype] = ewar_data.get(etype, 0) + count

    return [
        {"ewar_type": et, "count": c, "percentage": round(100.0 * c / max(total_ewar, 1), 1)}
        for et, c in sorted(ewar_data.items(), key=lambda x: x[1], reverse=True)
    ]


def build_hot_systems(cur, ctx: EntityContext, days: int, *, hs_batch: dict = None) -> list:
    """Section 17: Hot systems analysis (top systems with high kill density).

    Alliance: Uses hourly_stats systems_kills JSONB with solo_kills + total_value + deaths.
    Corporation: Uses raw killmails with solo detection + deaths subquery.
    PowerBloc: Uses hourly_stats systems_kills JSONB with solo_kills + total_value + deaths.

    When hs_batch is provided (Alliance/PowerBloc only), processes pre-fetched data.
    Corporation always uses SQL (raw killmails).
    """
    if hs_batch is not None and ctx.entity_type != EntityType.CORPORATION:
        system_info = hs_batch["system_info"]
        # Aggregate kills per system from systems_kills JSONB
        sys_kills: dict[int, dict] = defaultdict(lambda: {"kills": 0, "solo_kills": 0, "total_value": 0})
        sys_deaths: dict[int, int] = defaultdict(int)

        for row in hs_batch["rows"]:
            kills_data = _extract_system_kills(row[7])
            for sid, vals in kills_data.items():
                sys_kills[sid]["kills"] += vals["kills"]
                sys_kills[sid]["solo_kills"] += vals["solo_kills"]
                sys_kills[sid]["total_value"] += vals["total_value"]

            deaths_data = _parse_jsonb(row[8])
            for sid_str, val in deaths_data.items():
                sys_deaths[int(sid_str)] += int(val)

        result = []
        # Filter >= 5 kills, sort by kills desc, limit 15
        filtered = [(sid, agg) for sid, agg in sys_kills.items() if agg["kills"] >= 5]
        for sid, agg in sorted(filtered, key=lambda x: x[1]["kills"], reverse=True)[:15]:
            info = system_info.get(sid)
            if not info:
                continue
            kills = agg["kills"]
            deaths = sys_deaths.get(sid, 0)
            total = kills + deaths
            kill_score = round(100.0 * kills / total, 1) if total > 0 else 0.0
            solo = agg["solo_kills"]
            is_gatecamp = kills > 0 and (solo / kills) > 0.6
            avg_kill_value = agg["total_value"] / kills if kills > 0 else 0
            result.append({
                "system_id": sid,
                "system_name": info["name"],
                "region_name": info["region"],
                "security": info["security"],
                "kills": kills,
                "deaths": deaths,
                "kill_score": kill_score,
                "is_gatecamp": is_gatecamp,
                "avg_kill_value": float(avg_kill_value),
            })
        return result

    p = _params(ctx)

    if ctx.entity_type == EntityType.CORPORATION:
        sql = f"""
            WITH unique_system_kills AS (
                SELECT DISTINCT km.killmail_id, km.solar_system_id, km.ship_value,
                    (SELECT COUNT(*) FROM killmail_attackers ka2 WHERE ka2.killmail_id = km.killmail_id) AS attacker_count
                FROM killmails km
                JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
                WHERE ka.corporation_id = %(entity_id)s
                    AND km.killmail_time >= NOW() - INTERVAL '{days} days'
            ),
            system_kills AS (
                SELECT solar_system_id,
                    COUNT(*) AS kills,
                    COUNT(CASE WHEN attacker_count <= 3 THEN 1 END) AS solo_kills,
                    AVG(ship_value) AS avg_kill_value
                FROM unique_system_kills
                GROUP BY solar_system_id HAVING COUNT(*) >= 5
            ),
            system_deaths AS (
                SELECT solar_system_id, COUNT(*) AS deaths FROM killmails
                WHERE victim_corporation_id = %(entity_id)s
                    AND killmail_time >= NOW() - INTERVAL '{days} days'
                GROUP BY solar_system_id
            )
            SELECT ms."solarSystemID", ms."solarSystemName", mr."regionName", ms.security,
                sk.kills, COALESCE(sd.deaths, 0) AS deaths,
                ROUND(100.0 * sk.kills / NULLIF(sk.kills + COALESCE(sd.deaths, 0), 0), 1) AS kill_score,
                CASE WHEN (sk.solo_kills::float / sk.kills) > 0.6 THEN true ELSE false END AS is_gatecamp,
                sk.avg_kill_value
            FROM system_kills sk
            JOIN "mapSolarSystems" ms ON sk.solar_system_id = ms."solarSystemID"
            JOIN "mapRegions" mr ON ms."regionID" = mr."regionID"
            LEFT JOIN system_deaths sd ON sk.solar_system_id = sd.solar_system_id
            ORDER BY sk.kills DESC LIMIT 15
        """
    else:
        # Alliance / PowerBloc: hourly_stats JSONB
        hf = _hourly_stats_filter(ctx)
        sql = f"""
            WITH system_kills AS (
                SELECT
                    systems.system_id::INT AS solar_system_id,
                    CASE
                        WHEN jsonb_typeof(systems.data) = 'object'
                        THEN (systems.data->>'kills')::INT
                        ELSE systems.data::TEXT::INT
                    END AS kills,
                    CASE
                        WHEN jsonb_typeof(systems.data) = 'object'
                        THEN (systems.data->>'solo_kills')::INT
                        ELSE 0
                    END AS solo_kills,
                    CASE
                        WHEN jsonb_typeof(systems.data) = 'object'
                        THEN (systems.data->>'total_value')::BIGINT
                        ELSE 0
                    END AS total_value
                FROM intelligence_hourly_stats,
                LATERAL jsonb_each(systems_kills) as systems(system_id, data)
                WHERE {hf}
                  AND hour_bucket >= NOW() - INTERVAL '{days} days'
            ),
            aggregated_systems AS (
                SELECT
                    solar_system_id,
                    SUM(kills) AS kills,
                    SUM(solo_kills) AS solo_kills,
                    SUM(total_value) AS total_value,
                    AVG(total_value::FLOAT / NULLIF(kills, 0)) AS avg_kill_value
                FROM system_kills
                GROUP BY solar_system_id
                HAVING SUM(kills) >= 5
            ),
            system_deaths AS (
                SELECT
                    systems.system_id::INT AS solar_system_id,
                    SUM(systems.value::INT) AS deaths
                FROM intelligence_hourly_stats,
                LATERAL jsonb_each_text(systems_deaths) as systems(system_id, value)
                WHERE {hf}
                  AND hour_bucket >= NOW() - INTERVAL '{days} days'
                GROUP BY solar_system_id
            )
            SELECT ms."solarSystemID", ms."solarSystemName", mr."regionName", ms.security,
                sk.kills, COALESCE(sd.deaths, 0) AS deaths,
                ROUND(100.0 * sk.kills / NULLIF(sk.kills + COALESCE(sd.deaths, 0), 0), 1) AS kill_score,
                CASE WHEN (sk.solo_kills::float / sk.kills) > 0.6 THEN true ELSE false END AS is_gatecamp,
                sk.avg_kill_value
            FROM aggregated_systems sk
            JOIN "mapSolarSystems" ms ON sk.solar_system_id = ms."solarSystemID"
            JOIN "mapRegions" mr ON ms."regionID" = mr."regionID"
            LEFT JOIN system_deaths sd ON sk.solar_system_id = sd.solar_system_id
            ORDER BY sk.kills DESC LIMIT 15
        """

    cur.execute(sql, p)
    return [
        {
            "system_id": sid, "system_name": sn, "region_name": rn,
            "security": float(sec or 0), "kills": k, "deaths": d,
            "kill_score": float(score or 0), "is_gatecamp": gc,
            "avg_kill_value": float(avg or 0),
        }
        for sid, sn, rn, sec, k, d, score, gc, avg in cur.fetchall()
    ]


def build_effective_doctrines(cur, ctx: EntityContext, days: int, *, hs_batch: dict = None) -> list:
    """Section 18: Effective doctrines (ship classes with KD >= 2.0).

    Alliance/PowerBloc: Uses hourly_stats ships_killed/ships_lost JSONB.
    Corporation: Uses raw killmails with LEFT JOIN for kill/death attribution.

    When hs_batch is provided (Alliance/PowerBloc only), processes pre-fetched data.
    Corporation always uses SQL (raw killmails).
    """
    if hs_batch is not None and ctx.entity_type != EntityType.CORPORATION:
        type_info = hs_batch["type_info"]
        # Aggregate kills and deaths by ship group
        kills_by_group: dict[str, int] = defaultdict(int)
        deaths_by_group: dict[str, int] = defaultdict(int)

        for row in hs_batch["rows"]:
            ships_killed = _parse_jsonb(row[5])
            for tid_str, count_val in ships_killed.items():
                tid = int(tid_str)
                info = type_info.get(tid)
                if info:
                    kills_by_group[info["group"]] += int(count_val)

            ships_lost = _parse_jsonb(row[6])
            for tid_str, count_val in ships_lost.items():
                tid = int(tid_str)
                info = type_info.get(tid)
                if info:
                    deaths_by_group[info["group"]] += int(count_val)

        # Combine kills and deaths by group
        all_groups = set(kills_by_group.keys()) | set(deaths_by_group.keys())
        result = []
        for group in all_groups:
            kills = kills_by_group.get(group, 0)
            deaths = deaths_by_group.get(group, 0)
            if kills < 5:
                continue
            if deaths == 0:
                kd_ratio = float(kills)  # Infinite, use kills as proxy
            else:
                kd_ratio = round(kills / deaths, 2)
            if kd_ratio < 2.0:
                continue
            total = kills + deaths
            isk_efficiency = round(100.0 * kills / total, 1) if total > 0 else 0.0
            result.append({
                "ship_class": group,
                "kills": kills,
                "deaths": deaths,
                "kd_ratio": kd_ratio,
                "isk_efficiency": isk_efficiency,
            })

        result.sort(key=lambda x: x["kd_ratio"], reverse=True)
        return result[:12]

    p = _params(ctx)

    if ctx.entity_type == EntityType.CORPORATION:
        sql = f"""
            WITH ship_performance AS (
                SELECT ig."groupName" AS ship_class,
                    COUNT(CASE WHEN ka.corporation_id = %(entity_id)s THEN 1 END) AS kills,
                    COUNT(CASE WHEN km.victim_corporation_id = %(entity_id)s THEN 1 END) AS deaths,
                    SUM(CASE WHEN ka.corporation_id = %(entity_id)s THEN km.ship_value ELSE 0 END) AS isk_killed,
                    SUM(CASE WHEN km.victim_corporation_id = %(entity_id)s THEN km.ship_value ELSE 0 END) AS isk_lost
                FROM killmails km
                LEFT JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
                JOIN "invTypes" it ON COALESCE(ka.ship_type_id, km.ship_type_id) = it."typeID"
                JOIN "invGroups" ig ON it."groupID" = ig."groupID"
                WHERE (ka.corporation_id = %(entity_id)s OR km.victim_corporation_id = %(entity_id)s)
                    AND km.killmail_time >= NOW() - INTERVAL '{days} days'
                GROUP BY ig."groupName"
                HAVING COUNT(CASE WHEN ka.corporation_id = %(entity_id)s THEN 1 END) >= 5
            )
            SELECT ship_class, kills, deaths,
                ROUND(kills::numeric / NULLIF(deaths, 0), 2) AS kd_ratio,
                ROUND(100.0 * isk_killed / NULLIF(isk_killed + isk_lost, 0), 1) AS isk_efficiency
            FROM ship_performance
            WHERE (kills::float / NULLIF(deaths, 0)) >= 2.0
            ORDER BY kd_ratio DESC LIMIT 12
        """
    else:
        # Alliance / PowerBloc: hourly_stats JSONB
        hf = _hourly_stats_filter(ctx)
        sql = f"""
            WITH kills_by_group AS (
                SELECT
                    ig."groupName" AS ship_class,
                    SUM(ships.value::INT) AS kills
                FROM intelligence_hourly_stats,
                LATERAL jsonb_each_text(ships_killed) as ships(ship_type_id, value)
                JOIN "invTypes" it ON ships.ship_type_id::INT = it."typeID"
                JOIN "invGroups" ig ON it."groupID" = ig."groupID"
                WHERE {hf}
                  AND hour_bucket >= NOW() - INTERVAL '{days} days'
                GROUP BY ig."groupName"
                HAVING SUM(ships.value::INT) >= 5
            ),
            deaths_by_group AS (
                SELECT
                    ig."groupName" AS ship_class,
                    SUM(ships.value::INT) AS deaths
                FROM intelligence_hourly_stats,
                LATERAL jsonb_each_text(ships_lost) as ships(ship_type_id, value)
                JOIN "invTypes" it ON ships.ship_type_id::INT = it."typeID"
                JOIN "invGroups" ig ON it."groupID" = ig."groupID"
                WHERE {hf}
                  AND hour_bucket >= NOW() - INTERVAL '{days} days'
                GROUP BY ig."groupName"
            )
            SELECT
                COALESCE(k.ship_class, d.ship_class) AS ship_class,
                COALESCE(k.kills, 0) AS kills,
                COALESCE(d.deaths, 0) AS deaths,
                ROUND(COALESCE(k.kills, 0)::numeric / NULLIF(COALESCE(d.deaths, 0), 0), 2) AS kd_ratio,
                ROUND(100.0 * COALESCE(k.kills, 0) / NULLIF(COALESCE(k.kills, 0) + COALESCE(d.deaths, 0), 0), 1) AS isk_efficiency
            FROM kills_by_group k
            FULL OUTER JOIN deaths_by_group d ON k.ship_class = d.ship_class
            WHERE (COALESCE(k.kills, 0)::float / NULLIF(COALESCE(d.deaths, 0), 0)) >= 2.0
            ORDER BY kd_ratio DESC LIMIT 12
        """

    cur.execute(sql, p)
    return [
        {
            "ship_class": sc, "kills": k, "deaths": d,
            "kd_ratio": float(kd or 0), "isk_efficiency": float(eff or 0),
        }
        for sc, k, d, kd, eff in cur.fetchall()
    ]


def build_kill_velocity(cur, ctx: EntityContext, days: int, *, hs_batch: dict = None) -> list:
    """Section 19: Kill velocity (trend analysis recent vs previous half-period).

    Alliance: Uses hourly_stats ships_killed JSONB (no ISK data).
    Corporation: Uses raw killmails (has ISK data).
    PowerBloc: Uses hourly_stats ships_killed JSONB (no ISK data).

    When hs_batch is provided (Alliance/PowerBloc only), processes pre-fetched data.
    Corporation always uses SQL (raw killmails with ISK data).
    """
    half_days = days // 2

    if hs_batch is not None and ctx.entity_type != EntityType.CORPORATION:
        type_info = hs_batch["type_info"]
        now = _now()
        half_cutoff = now - timedelta(days=half_days)

        recent_by_group: dict[str, int] = defaultdict(int)
        previous_by_group: dict[str, int] = defaultdict(int)

        for row in hs_batch["rows"]:
            hour_bucket = row[0]
            # Make both timezone-aware or both naive for comparison
            if hour_bucket.tzinfo is None and now.tzinfo is not None:
                hour_bucket = hour_bucket.replace(tzinfo=timezone.utc)
            ships_killed = _parse_jsonb(row[5])
            for tid_str, count_val in ships_killed.items():
                tid = int(tid_str)
                info = type_info.get(tid)
                if not info:
                    continue
                group = info["group"]
                count = int(count_val)
                if hour_bucket > half_cutoff:
                    recent_by_group[group] += count
                else:
                    previous_by_group[group] += count

        all_groups = set(recent_by_group.keys()) | set(previous_by_group.keys())
        result = []
        for group in all_groups:
            recent = recent_by_group.get(group, 0)
            previous = previous_by_group.get(group, 0)
            total = recent + previous
            if total < 10:
                continue
            if previous > 0:
                velocity_pct = round(((recent - previous) / previous) * 100, 1)
            else:
                velocity_pct = 0.0
            if velocity_pct > 20:
                status = "ESCALATING"
            elif velocity_pct < -20:
                status = "DECLINING"
            else:
                status = "STEADY"
            result.append({
                "ship_class": group,
                "recent_kills": recent,
                "previous_kills": previous,
                "recent_isk": 0.0,
                "previous_isk": 0.0,
                "velocity_pct": velocity_pct,
                "status": status,
            })

        result.sort(key=lambda x: x["recent_kills"], reverse=True)
        return result[:15]

    p = _params(ctx)

    if ctx.entity_type == EntityType.CORPORATION:
        sql = f"""
            WITH time_split AS (
                SELECT ig."groupName" AS ship_class,
                    COUNT(CASE WHEN km.killmail_time > NOW() - INTERVAL '{half_days} days' THEN 1 END) AS recent_kills,
                    COUNT(CASE WHEN km.killmail_time BETWEEN NOW() - INTERVAL '{days} days'
                        AND NOW() - INTERVAL '{half_days} days' THEN 1 END) AS previous_kills,
                    SUM(CASE WHEN km.killmail_time > NOW() - INTERVAL '{half_days} days'
                        THEN km.ship_value ELSE 0 END) AS recent_isk,
                    SUM(CASE WHEN km.killmail_time BETWEEN NOW() - INTERVAL '{days} days'
                        AND NOW() - INTERVAL '{half_days} days' THEN km.ship_value ELSE 0 END) AS previous_isk
                FROM killmails km
                JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
                JOIN "invTypes" it ON ka.ship_type_id = it."typeID"
                JOIN "invGroups" ig ON it."groupID" = ig."groupID"
                WHERE ka.corporation_id = %(entity_id)s AND km.killmail_time >= NOW() - INTERVAL '{days} days'
                GROUP BY ig."groupName" HAVING COUNT(*) >= 10
            )
            SELECT ship_class, recent_kills, previous_kills, recent_isk, previous_isk,
                ROUND(((recent_kills::float - previous_kills) / NULLIF(previous_kills, 0) * 100)::numeric, 1) AS velocity_pct,
                CASE WHEN ((recent_kills::float - previous_kills) / NULLIF(previous_kills, 0) * 100) > 20 THEN 'ESCALATING'
                    WHEN ((recent_kills::float - previous_kills) / NULLIF(previous_kills, 0) * 100) < -20 THEN 'DECLINING'
                    ELSE 'STEADY' END AS status
            FROM time_split ORDER BY recent_kills DESC LIMIT 15
        """
        cur.execute(sql, p)
        return [
            {
                "ship_class": sc, "recent_kills": rk, "previous_kills": pk,
                "recent_isk": float(ri or 0), "previous_isk": float(pi or 0),
                "velocity_pct": float(vp or 0), "status": st,
            }
            for sc, rk, pk, ri, pi, vp, st in cur.fetchall()
        ]

    else:
        # Alliance / PowerBloc: hourly_stats JSONB
        hf = _hourly_stats_filter(ctx)
        sql = f"""
            WITH recent_kills AS (
                SELECT
                    ig."groupName" AS ship_class,
                    SUM(ships.value::INT) AS kills
                FROM intelligence_hourly_stats,
                LATERAL jsonb_each_text(ships_killed) as ships(ship_type_id, value)
                JOIN "invTypes" it ON ships.ship_type_id::INT = it."typeID"
                JOIN "invGroups" ig ON it."groupID" = ig."groupID"
                WHERE {hf}
                  AND hour_bucket > NOW() - INTERVAL '{half_days} days'
                GROUP BY ig."groupName"
            ),
            previous_kills AS (
                SELECT
                    ig."groupName" AS ship_class,
                    SUM(ships.value::INT) AS kills
                FROM intelligence_hourly_stats,
                LATERAL jsonb_each_text(ships_killed) as ships(ship_type_id, value)
                JOIN "invTypes" it ON ships.ship_type_id::INT = it."typeID"
                JOIN "invGroups" ig ON it."groupID" = ig."groupID"
                WHERE {hf}
                  AND hour_bucket BETWEEN NOW() - INTERVAL '{days} days' AND NOW() - INTERVAL '{half_days} days'
                GROUP BY ig."groupName"
            )
            SELECT
                COALESCE(r.ship_class, p.ship_class) AS ship_class,
                COALESCE(r.kills, 0) AS recent_kills,
                COALESCE(p.kills, 0) AS previous_kills,
                0 AS recent_isk,
                0 AS previous_isk,
                ROUND(((COALESCE(r.kills, 0)::float - COALESCE(p.kills, 0)) / NULLIF(COALESCE(p.kills, 0), 0) * 100)::numeric, 1) AS velocity_pct,
                CASE WHEN ((COALESCE(r.kills, 0)::float - COALESCE(p.kills, 0)) / NULLIF(COALESCE(p.kills, 0), 0) * 100) > 20 THEN 'ESCALATING'
                    WHEN ((COALESCE(r.kills, 0)::float - COALESCE(p.kills, 0)) / NULLIF(COALESCE(p.kills, 0), 0) * 100) < -20 THEN 'DECLINING'
                    ELSE 'STEADY' END AS status
            FROM recent_kills r
            FULL OUTER JOIN previous_kills p ON r.ship_class = p.ship_class
            WHERE (COALESCE(r.kills, 0) + COALESCE(p.kills, 0)) >= 10
            ORDER BY recent_kills DESC LIMIT 15
        """
        cur.execute(sql, p)
        return [
            {
                "ship_class": sc, "recent_kills": rk, "previous_kills": pk,
                "recent_isk": float(ri or 0), "previous_isk": float(pi or 0),
                "velocity_pct": float(vp or 0), "status": st,
            }
            for sc, rk, pk, ri, pi, vp, st in cur.fetchall()
        ]
