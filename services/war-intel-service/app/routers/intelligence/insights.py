"""
Alliance Intelligence Insights - Advanced Analytics Endpoints

Provides:
1. Corp Activity Heatmap - Timezone coverage analysis
2. Participation Trends - Alliance momentum tracking
3. Burnout Index - Pilot overload detection
4. Attrition Tracker - Pilot retention analysis
"""

from fastapi import APIRouter, Query
from typing import Dict, Any, List, Optional

from app.database import db_cursor
from app.utils.cache import get_cached, set_cached

router = APIRouter()


# ============================================================================
# 1. CORP ACTIVITY HEATMAP
# ============================================================================

@router.get("/{alliance_id}/corp-activity-heatmap")
def get_corp_activity_heatmap(
    alliance_id: int,
    days: int = Query(7, ge=1, le=30)
) -> Dict[str, Any]:
    """
    Get hourly activity heatmap for all corps in alliance.
    Shows which corps are active at which hours (UTC).

    Use Case: Timezone coverage analysis, prime time identification
    """
    cache_key = f"corp-heatmap:{alliance_id}:{days}"
    cached = get_cached(cache_key)
    if cached:
        return cached

    with db_cursor() as cur:
        # Get top 30 most active corps
        cur.execute("""
            SELECT
                chs.corporation_id,
                cn.corporation_name,
                cn.ticker,
                SUM(chs.kills) AS total_kills
            FROM corporation_hourly_stats chs
            JOIN corporations c ON chs.corporation_id = c.corporation_id
            LEFT JOIN corp_name_cache cn ON chs.corporation_id = cn.corporation_id
            WHERE c.alliance_id = %(alliance_id)s
              AND chs.hour_bucket >= NOW() - make_interval(days => %(days)s)
            GROUP BY chs.corporation_id, cn.corporation_name, cn.ticker
            ORDER BY SUM(chs.kills) DESC
            LIMIT 30
        """, {"alliance_id": alliance_id, "days": days})

        top_corps = cur.fetchall()

        corps = []
        for corp_row in top_corps:
            corp_id = corp_row[0]
            corp_name = corp_row[1]
            ticker = corp_row[2]
            total = corp_row[3]

            # Get hourly breakdown for this corp
            cur.execute("""
                SELECT
                    EXTRACT(HOUR FROM hour_bucket)::INT AS hour,
                    SUM(kills) AS kills
                FROM corporation_hourly_stats chs
                JOIN corporations c ON chs.corporation_id = c.corporation_id
                WHERE c.alliance_id = %(alliance_id)s
                  AND chs.corporation_id = %(corp_id)s
                  AND chs.hour_bucket >= NOW() - make_interval(days => %(days)s)
                GROUP BY EXTRACT(HOUR FROM hour_bucket)
                ORDER BY EXTRACT(HOUR FROM hour_bucket)
            """, {"alliance_id": alliance_id, "corp_id": corp_id, "days": days})

            hourly_data = cur.fetchall()

            # Build 24-hour array (fill missing hours with 0)
            hours = [0] * 24
            for h_row in hourly_data:
                hour_idx = h_row[0]
                kills = h_row[1]
                hours[hour_idx] = kills

            corps.append({
                "corp_id": corp_id,
                "corp_name": corp_name,
                "ticker": ticker,
                "hours": hours,
                "total": total
            })

    result = {
        "alliance_id": alliance_id,
        "period_days": days,
        "corps": corps
    }

    set_cached(cache_key, result)
    return result


# ============================================================================
# 2. PARTICIPATION TRENDS
# ============================================================================

@router.get("/{alliance_id}/participation-trends")
def get_participation_trends(
    alliance_id: int,
    days: int = Query(14, ge=7, le=90)
) -> Dict[str, Any]:
    """
    Get daily participation trends with momentum analysis.
    Shows if alliance activity is rising, falling, or stable.

    Use Case: Alliance health check, war campaign success tracking
    """
    cache_key = f"participation-trends:{alliance_id}:{days}"
    cached = get_cached(cache_key)
    if cached:
        return cached

    with db_cursor() as cur:
        cur.execute("""
            SELECT
                DATE(hour_bucket) AS day,
                SUM(kills) AS kills,
                SUM(deaths) AS deaths,
                MAX(active_pilots) AS active_pilots,
                SUM(isk_destroyed) AS isk_destroyed,
                SUM(isk_lost) AS isk_lost
            FROM intelligence_hourly_stats
            WHERE alliance_id = %(alliance_id)s
              AND hour_bucket >= NOW() - make_interval(days => %(days)s)
            GROUP BY DATE(hour_bucket)
            ORDER BY DATE(hour_bucket)
        """, {"alliance_id": alliance_id, "days": days})

        rows = cur.fetchall()

        daily = [
            {
                "day": row[0].isoformat(),
                "kills": row[1],
                "deaths": row[2],
                "active_pilots": row[3] or 0,
                "isk_destroyed": str(row[4] or 0),
                "isk_lost": str(row[5] or 0)
            }
            for row in rows
        ]

        # Calculate trend (first half vs second half)
        if len(daily) >= 7:
            mid = len(daily) // 2
            first_half = daily[:mid]
            second_half = daily[mid:]

            first_kills = sum(d['kills'] for d in first_half)
            second_kills = sum(d['kills'] for d in second_half)
            first_pilots = sum(d['active_pilots'] for d in first_half) / max(len(first_half), 1)
            second_pilots = sum(d['active_pilots'] for d in second_half) / max(len(second_half), 1)

            kills_change = ((second_kills - first_kills) / max(first_kills, 1)) * 100
            pilots_change = ((second_pilots - first_pilots) / max(first_pilots, 1)) * 100

            # Determine direction
            if kills_change > 15:
                direction = "rising"
            elif kills_change < -15:
                direction = "falling"
            else:
                direction = "stable"

            trend = {
                "direction": direction,
                "kills_change_pct": round(kills_change, 1),
                "pilots_change_pct": round(pilots_change, 1)
            }
        else:
            trend = {
                "direction": "insufficient_data",
                "kills_change_pct": 0.0,
                "pilots_change_pct": 0.0
            }

    result = {
        "alliance_id": alliance_id,
        "period_days": days,
        "daily": daily,
        "trend": trend
    }

    set_cached(cache_key, result)
    return result


# ============================================================================
# 3. BURNOUT INDEX
# ============================================================================

@router.get("/{alliance_id}/burnout-index")
def get_burnout_index(
    alliance_id: int,
    days: int = Query(14, ge=7, le=30)
) -> Dict[str, Any]:
    """
    Measure pilot burnout risk based on kills-per-pilot ratio.
    High KPP = small core group carrying alliance = burnout risk.

    Use Case: Leadership alert, recruitment need identification
    """
    cache_key = f"burnout-index:{alliance_id}:{days}"
    cached = get_cached(cache_key)
    if cached:
        return cached

    with db_cursor() as cur:
        cur.execute("""
            SELECT
                DATE(hour_bucket) AS day,
                SUM(kills) AS kills,
                MAX(active_pilots) AS active_pilots
            FROM intelligence_hourly_stats
            WHERE alliance_id = %(alliance_id)s
              AND hour_bucket >= NOW() - make_interval(days => %(days)s)
            GROUP BY DATE(hour_bucket)
            ORDER BY DATE(hour_bucket)
        """, {"alliance_id": alliance_id, "days": days})

        rows = cur.fetchall()

        daily = []
        for row in rows:
            pilots = row[2] or 1
            kills = row[1]
            kpp = kills / pilots if pilots > 0 else 0

            daily.append({
                "day": row[0].isoformat(),
                "kills": kills,
                "active_pilots": pilots,
                "kills_per_pilot": round(kpp, 2)
            })

        # Calculate summary metrics
        if daily:
            avg_kpp = sum(d['kills_per_pilot'] for d in daily) / len(daily)

            # Trend: first half vs second half
            if len(daily) >= 7:
                mid = len(daily) // 2
                first_kpp = sum(d['kills_per_pilot'] for d in daily[:mid]) / mid
                second_kpp = sum(d['kills_per_pilot'] for d in daily[mid:]) / (len(daily) - mid)
                first_pilots = sum(d['active_pilots'] for d in daily[:mid]) / mid
                second_pilots = sum(d['active_pilots'] for d in daily[mid:]) / (len(daily) - mid)

                kpp_trend = ((second_kpp - first_kpp) / max(first_kpp, 0.1)) * 100
                pilot_trend = ((second_pilots - first_pilots) / max(first_pilots, 1)) * 100
            else:
                kpp_trend = 0.0
                pilot_trend = 0.0

            # Burnout risk assessment
            if avg_kpp > 15:
                risk = "critical"
            elif avg_kpp > 10:
                risk = "high"
            elif avg_kpp > 5:
                risk = "moderate"
            else:
                risk = "low"

            summary = {
                "avg_kills_per_pilot": round(avg_kpp, 2),
                "kpp_trend_pct": round(kpp_trend, 1),
                "pilot_trend_pct": round(pilot_trend, 1),
                "burnout_risk": risk
            }
        else:
            summary = {
                "avg_kills_per_pilot": 0.0,
                "kpp_trend_pct": 0.0,
                "pilot_trend_pct": 0.0,
                "burnout_risk": "unknown"
            }

    result = {
        "alliance_id": alliance_id,
        "period_days": days,
        "daily": daily,
        "summary": summary
    }

    set_cached(cache_key, result)
    return result


# ============================================================================
# 4. ATTRITION TRACKER (SIMPLIFIED)
# ============================================================================

@router.get("/{alliance_id}/attrition-tracker")
def get_attrition_tracker(
    alliance_id: int,
    days: int = Query(30, ge=14, le=90)
) -> Dict[str, Any]:
    """
    Track pilot retention and identify where departed pilots went.

    SIMPLIFIED VERSION: Tracks active pilots over time, estimates retention.
    Destination tracking uses recent killmail activity.

    Use Case: Retention monitoring, poaching detection
    """
    cache_key = f"attrition-tracker:{alliance_id}:{days}"
    cached = get_cached(cache_key)
    if cached:
        return cached

    with db_cursor() as cur:
        # Get active pilots in OLD period (days ago to days/2 ago)
        old_period_start = days
        old_period_end = days // 2

        cur.execute("""
            SELECT DISTINCT character_id
            FROM killmail_attackers ka
            JOIN killmails km ON ka.killmail_id = km.killmail_id
            JOIN corporations c ON ka.corporation_id = c.corporation_id
            WHERE c.alliance_id = %(alliance_id)s
              AND km.killmail_time >= NOW() - make_interval(days => %(old_start)s)
              AND km.killmail_time < NOW() - make_interval(days => %(old_end)s)
        """, {"alliance_id": alliance_id, "old_start": old_period_start, "old_end": old_period_end})

        old_pilot_ids = {row[0] for row in cur.fetchall()}

        # Get active pilots in CURRENT period (recent days/2)
        cur.execute("""
            SELECT DISTINCT character_id
            FROM killmail_attackers ka
            JOIN killmails km ON ka.killmail_id = km.killmail_id
            JOIN corporations c ON ka.corporation_id = c.corporation_id
            WHERE c.alliance_id = %(alliance_id)s
              AND km.killmail_time >= NOW() - make_interval(days => %(days)s)
        """, {"alliance_id": alliance_id, "days": old_period_end})

        current_pilot_ids = {row[0] for row in cur.fetchall()}

        # Calculate departed pilots
        departed_pilot_ids = list(old_pilot_ids - current_pilot_ids)

        # Find where departed pilots are now (simplified - recent activity)
        destinations = []
        if departed_pilot_ids:
            # Convert to tuple for SQL IN clause
            cur.execute("""
                SELECT
                    c.alliance_id,
                    an.alliance_name,
                    c.ticker,
                    COUNT(DISTINCT ka.character_id) AS pilot_count,
                    COUNT(*) AS total_activity
                FROM killmail_attackers ka
                JOIN killmails km ON ka.killmail_id = km.killmail_id
                JOIN corporations c ON ka.corporation_id = c.corporation_id
                LEFT JOIN alliance_name_cache an ON c.alliance_id = an.alliance_id
                WHERE ka.character_id = ANY(%(departed_ids)s::BIGINT[])
                  AND c.alliance_id != %(alliance_id)s
                  AND km.killmail_time >= NOW() - make_interval(days => %(days)s)
                GROUP BY c.alliance_id, an.alliance_name, c.ticker
                HAVING COUNT(DISTINCT ka.character_id) >= 2
                ORDER BY COUNT(DISTINCT ka.character_id) DESC
                LIMIT 10
            """, {"departed_ids": departed_pilot_ids, "alliance_id": alliance_id, "days": old_period_end})

            destinations = [
                {
                    "alliance_id": row[0],
                    "alliance_name": row[1],
                    "ticker": row[2],
                    "pilot_count": row[3],
                    "total_activity": row[4]
                }
                for row in cur.fetchall()
            ]

        # Calculate metrics
        old_count = len(old_pilot_ids)
        current_count = len(current_pilot_ids)
        departed_count = len(departed_pilot_ids)
        retention_rate = (current_count / max(old_count, 1)) * 100 if old_count > 0 else 0.0

    result = {
        "alliance_id": alliance_id,
        "period_days": days,
        "summary": {
            "old_active_pilots": old_count,
            "current_active_pilots": current_count,
            "departed_pilots": departed_count,
            "retention_rate": round(retention_rate, 1),
            "tracked_destinations": len(destinations)
        },
        "destinations": destinations
    }

    set_cached(cache_key, result)
    return result
