"""Power assessment and strategic briefing endpoints."""

import logging
from typing import Dict, List

from fastapi import APIRouter, Query

from app.database import db_cursor
from app.utils.cache import get_cached, set_cached
from eve_shared.utils.error_handling import handle_endpoint_errors

from ._helpers import _fetch_alliance_names_from_esi, get_stored_report_or_error

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_alliance_net_isk(cur, start_interval: str, end_interval: str = None) -> Dict[int, float]:
    """Get net ISK per alliance for a specific time period."""
    from decimal import Decimal

    if end_interval:
        time_filter = f"k.killmail_time >= NOW() - INTERVAL '{start_interval}' AND k.killmail_time < NOW() - INTERVAL '{end_interval}'"
    else:
        time_filter = f"k.killmail_time >= NOW() - INTERVAL '{start_interval}'"

    cur.execute(f"""
        WITH kills AS (
            SELECT a.alliance_id, SUM(k.ship_value) as destroyed
            FROM killmails k
            JOIN killmail_attackers a ON k.killmail_id = a.killmail_id AND a.is_final_blow = TRUE
            WHERE {time_filter} AND a.alliance_id IS NOT NULL
            GROUP BY a.alliance_id
        ),
        losses AS (
            SELECT victim_alliance_id as alliance_id, SUM(ship_value) as lost
            FROM killmails k
            WHERE {time_filter} AND victim_alliance_id IS NOT NULL
            GROUP BY victim_alliance_id
        )
        SELECT
            COALESCE(k.alliance_id, l.alliance_id) as alliance_id,
            COALESCE(k.destroyed, 0) - COALESCE(l.lost, 0) as net_isk
        FROM kills k
        FULL OUTER JOIN losses l ON k.alliance_id = l.alliance_id
    """)

    result = {}
    for row in cur.fetchall():
        val = row['net_isk']
        if isinstance(val, Decimal):
            val = float(val)
        result[row['alliance_id']] = val
    return result


def _get_alliance_history_7d(cur, alliance_ids: List[int]) -> Dict[int, List[float]]:
    """Get 7-day net ISK history per alliance (one value per day)."""
    from decimal import Decimal

    if not alliance_ids:
        return {}

    # Get daily net ISK for last 7 days for specified alliances
    cur.execute("""
        WITH daily_kills AS (
            SELECT
                a.alliance_id,
                DATE(k.killmail_time) as day,
                SUM(k.ship_value) as destroyed
            FROM killmails k
            JOIN killmail_attackers a ON k.killmail_id = a.killmail_id AND a.is_final_blow = TRUE
            WHERE k.killmail_time >= NOW() - INTERVAL '7 days'
              AND a.alliance_id = ANY(%s)
            GROUP BY a.alliance_id, DATE(k.killmail_time)
        ),
        daily_losses AS (
            SELECT
                k.victim_alliance_id as alliance_id,
                DATE(k.killmail_time) as day,
                SUM(k.ship_value) as lost
            FROM killmails k
            WHERE k.killmail_time >= NOW() - INTERVAL '7 days'
              AND k.victim_alliance_id = ANY(%s)
            GROUP BY k.victim_alliance_id, DATE(k.killmail_time)
        ),
        days AS (
            SELECT generate_series(
                (NOW() - INTERVAL '6 days')::date,
                NOW()::date,
                '1 day'::interval
            )::date as day
        )
        SELECT
            a.alliance_id,
            d.day,
            COALESCE(dk.destroyed, 0) - COALESCE(dl.lost, 0) as net_isk
        FROM (SELECT DISTINCT alliance_id FROM unnest(%s::int[]) as alliance_id) a
        CROSS JOIN days d
        LEFT JOIN daily_kills dk ON dk.alliance_id = a.alliance_id AND dk.day = d.day
        LEFT JOIN daily_losses dl ON dl.alliance_id = a.alliance_id AND dl.day = d.day
        ORDER BY a.alliance_id, d.day
    """, (alliance_ids, alliance_ids, alliance_ids))

    result = {aid: [] for aid in alliance_ids}
    for row in cur.fetchall():
        alliance_id = row['alliance_id']
        val = row['net_isk']
        if isinstance(val, Decimal):
            val = float(val)
        if alliance_id in result:
            result[alliance_id].append(val)

    return result


def _build_power_assessment_local(minutes: int = 1440) -> Dict:
    """
    Build power assessment from live database metrics.
    Simplified version that runs in war-intel-service context.

    Args:
        minutes: Time window in minutes (default 1440 = 24 hours)
    """
    from decimal import Decimal

    def to_float(val):
        if isinstance(val, Decimal):
            return float(val)
        return val

    # Convert minutes to interval string
    interval_str = f'{minutes} minutes'

    # Minimum kills required scales with time window
    # 24h = 20, 1h = 1, 10m = 1
    min_kills = max(1, int(minutes / 72))  # ~20 for 24h, ~1 for 1h

    with db_cursor() as cur:
        # Get historical data for trends (only for 24h+ windows)
        if minutes >= 1440:
            prev_24h = _get_alliance_net_isk(cur, '48 hours', '24 hours')
            prev_30d = _get_alliance_net_isk(cur, '31 days', '30 days')
        else:
            prev_24h = {}
            prev_30d = {}

        # Get alliance power balance for the specified time window
        cur.execute(f"""
            WITH alliance_kills AS (
                SELECT
                    a.alliance_id,
                    COUNT(*) as kills,
                    SUM(k.ship_value) as isk_destroyed
                FROM killmails k
                JOIN killmail_attackers a ON k.killmail_id = a.killmail_id AND a.is_final_blow = TRUE
                WHERE k.killmail_time >= NOW() - INTERVAL '{interval_str}'
                  AND a.alliance_id IS NOT NULL
                GROUP BY a.alliance_id
            ),
            alliance_losses AS (
                SELECT
                    k.victim_alliance_id as alliance_id,
                    COUNT(*) as losses,
                    SUM(k.ship_value) as isk_lost
                FROM killmails k
                WHERE k.killmail_time >= NOW() - INTERVAL '{interval_str}'
                  AND k.victim_alliance_id IS NOT NULL
                GROUP BY k.victim_alliance_id
            ),
            alliance_pilots AS (
                SELECT alliance_id, COUNT(DISTINCT character_id) as pilots
                FROM (
                    SELECT a.alliance_id, a.character_id
                    FROM killmail_attackers a
                    JOIN killmails k ON a.killmail_id = k.killmail_id
                    WHERE k.killmail_time >= NOW() - INTERVAL '{interval_str}'
                      AND a.alliance_id IS NOT NULL
                    UNION
                    SELECT k.victim_alliance_id, k.victim_character_id
                    FROM killmails k
                    WHERE k.killmail_time >= NOW() - INTERVAL '{interval_str}'
                      AND k.victim_alliance_id IS NOT NULL
                ) sub
                GROUP BY alliance_id
            )
            SELECT
                COALESCE(ak.alliance_id, al.alliance_id) as alliance_id,
                COALESCE(ak.kills, 0) as kills,
                COALESCE(al.losses, 0) as losses,
                COALESCE(ak.isk_destroyed, 0) as isk_destroyed,
                COALESCE(al.isk_lost, 0) as isk_lost,
                COALESCE(ap.pilots, 0) as pilots,
                CASE WHEN COALESCE(ak.kills, 0) + COALESCE(al.losses, 0) > 0
                     THEN COALESCE(ak.kills, 0)::float / (COALESCE(ak.kills, 0) + COALESCE(al.losses, 0)) * 100
                     ELSE 0 END as efficiency,
                COALESCE(ak.isk_destroyed, 0) - COALESCE(al.isk_lost, 0) as net_isk
            FROM alliance_kills ak
            FULL OUTER JOIN alliance_losses al ON ak.alliance_id = al.alliance_id
            LEFT JOIN alliance_pilots ap ON COALESCE(ak.alliance_id, al.alliance_id) = ap.alliance_id
            WHERE COALESCE(ak.kills, 0) + COALESCE(al.losses, 0) >= {min_kills}
            ORDER BY isk_destroyed DESC
            LIMIT 100
        """)

        rows = cur.fetchall()

        # Get alliance names
        alliance_ids = [r['alliance_id'] for r in rows if r['alliance_id']]
        alliance_names = {}
        if alliance_ids:
            cur.execute("""
                SELECT alliance_id, alliance_name FROM alliance_name_cache WHERE alliance_id = ANY(%s)
            """, (alliance_ids,))
            for row in cur.fetchall():
                alliance_names[row['alliance_id']] = row['alliance_name']

            # Fetch missing alliance names from ESI
            missing_ids = [aid for aid in alliance_ids if aid not in alliance_names]
            if missing_ids:
                logger.info(f"Fetching {len(missing_ids)} missing alliance names from ESI")
                fetched = _fetch_alliance_names_from_esi(missing_ids, cur)
                alliance_names.update(fetched)

        # Get 7-day history for all alliances (only for 24h+ windows)
        if minutes >= 1440 and alliance_ids:
            history_7d = _get_alliance_history_7d(cur, alliance_ids)
        else:
            history_7d = {}

        gaining_power = []
        losing_power = []
        all_entries = []

        for row in rows:
            alliance_id = row['alliance_id']
            name = alliance_names.get(alliance_id, f"Alliance {alliance_id}")
            efficiency = to_float(row['efficiency'])
            net_isk = to_float(row['net_isk'])
            kills = row['kills']
            losses = row['losses']
            pilots = row['pilots'] or 1  # Avoid division by zero

            # Calculate ISK per pilot
            isk_per_pilot = net_isk / pilots if pilots > 0 else 0

            # Calculate trends
            prev_net_24h = prev_24h.get(alliance_id, 0)
            prev_net_30d = prev_30d.get(alliance_id, 0)

            # Trend: positive = improving, negative = declining
            trend_24h = net_isk - prev_net_24h if prev_net_24h != 0 else None
            trend_30d = net_isk - prev_net_30d if prev_net_30d != 0 else None

            entry = {
                "name": name,
                "alliance_id": alliance_id,
                "pilots": row['pilots'],
                "kills": kills,
                "losses": losses,
                "efficiency": efficiency,
                "net_isk": net_isk,
                "isk_destroyed": to_float(row['isk_destroyed']),
                "isk_lost": to_float(row['isk_lost']),
                "isk_per_pilot": isk_per_pilot,
                "trend_24h": trend_24h,
                "history_7d": history_7d.get(alliance_id, []),
            }

            all_entries.append(entry)

            # Classify for gaining/losing based on net ISK
            if net_isk > 0:
                gaining_power.append(entry)
            elif net_isk < 0:
                losing_power.append(entry)

        # Sort gaining/losing by net ISK
        gaining_power.sort(key=lambda x: x.get("net_isk", 0), reverse=True)
        losing_power.sort(key=lambda x: x.get("net_isk", 0))

        # Sort all entries by ISK per pilot (highest first)
        isk_efficiency = sorted(all_entries, key=lambda x: x.get("isk_per_pilot", 0), reverse=True)

        return {
            "isk_efficiency": isk_efficiency[:10],
            "gaining_power": gaining_power[:10],
            "losing_power": losing_power[:10],
        }


@router.get("/strategic-briefing")
def get_strategic_briefing() -> Dict:
    """
    Strategic Intelligence Briefing

    AI-powered strategic analysis of the current state of New Eden.
    Provides executive-level intelligence for alliance leaders and FCs.

    Includes:
    - Power balance assessment
    - Territorial control analysis
    - Capital fleet status
    - Momentum indicators
    - Escalation risk zones
    - Gate camp / chokepoint activity

    Pre-generated every 6 hours (LLM text), power_assessment refreshed live.
    """
    report = get_stored_report_or_error('strategic_briefing')

    # Always refresh power_assessment with latest metrics
    try:
        report['power_assessment'] = _build_power_assessment_local()
    except Exception as e:
        logger.warning(f"Failed to refresh power_assessment: {e}")

    return report


@router.get("/power-assessment")
@handle_endpoint_errors()
def get_power_assessment(
    minutes: int = Query(default=1440, ge=10, le=1440, description="Time window in minutes (10-1440)")
) -> Dict:
    """
    Alliance Power Assessment

    Real-time alliance power balance based on kills and losses.
    Supports configurable time windows (10m to 24h).

    Returns:
    - gaining_power: Alliances with positive net ISK
    - losing_power: Alliances with negative net ISK
    - isk_efficiency: Alliances ranked by ISK per pilot

    Use minutes=60 for 1h, minutes=10 for 10m snapshot.
    """
    # Check cache first (60s TTL)
    cache_key = f"power-assessment:{minutes}"
    cached = get_cached(cache_key, ttl_seconds=300)
    if cached:
        return cached

    assessment = _build_power_assessment_local(minutes=minutes)
    result = {
        "minutes": minutes,
        "timeframe": f"{minutes}m" if minutes < 60 else f"{minutes // 60}h",
        **assessment
    }

    # Cache result
    set_cached(cache_key, result)

    return result
