"""Corporation Overview Intelligence - Summary extracts for dashboard.

Provides condensed intelligence summaries from each specialized tab:
- Offensive: Attack strength and efficiency
- Defensive: Vulnerability assessment
- Capitals: Capital warfare capabilities
- Pilots: Pilot strength and morale
- Geography: Territorial footprint
- Activity: Operational tempo and trends
- Hunting: Threat assessment and strike windows
"""

import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Query

from app.database import db_cursor
from app.utils.trends import calculate_trend
from eve_shared.utils.error_handling import handle_endpoint_errors

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/corporation/{corp_id}/basic-info")
@handle_endpoint_errors()
def get_basic_info(
    corp_id: int,
    days: int = Query(30, ge=1, le=90)
) -> Dict[str, Any]:
    """Get basic corporation info for header display.

    Returns:
    - Corporation name, ticker, alliance info
    - Basic stats: kills, deaths, efficiency (for header)
    """
    with db_cursor(cursor_factory=None) as cur:
        # Get corporation and alliance names
        sql_names = """
            SELECT
                c.corporation_name,
                c.ticker,
                c.alliance_id,
                a.alliance_name
            FROM corporations c
            LEFT JOIN alliance_name_cache a ON c.alliance_id = a.alliance_id
            WHERE c.corporation_id = %(corp_id)s
        """
        cur.execute(sql_names, {"corp_id": corp_id})
        name_row = cur.fetchone()

        if not name_row:
            raise HTTPException(status_code=404, detail="Corporation not found")

        # Get basic stats (kills, deaths, efficiency, trend)
        # Simplified query without expensive hourly_activity aggregation
        # FIXED: Use separate CTEs to avoid Cartesian Product inflation of ISK values
        half_days = days // 2  # Integer division for SQL INTERVAL
        sql_stats = """
            WITH unique_kills AS (
                -- Get DISTINCT killmails first to avoid inflating ISK when multiple corp members participate
                SELECT DISTINCT km.killmail_id, km.ship_value
                FROM killmails km
                JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
                WHERE ka.corporation_id = %(corp_id)s
                    AND km.killmail_time >= NOW() - INTERVAL '1 day' * %(days)s
            ),
            corp_kills AS (
                SELECT
                    COUNT(*) AS kills,
                    COALESCE(SUM(ship_value), 0) AS isk_destroyed
                FROM unique_kills
            ),
            corp_deaths AS (
                SELECT
                    COUNT(*) AS deaths,
                    COALESCE(SUM(ship_value), 0) AS isk_lost
                FROM killmails
                WHERE victim_corporation_id = %(corp_id)s
                    AND killmail_time >= NOW() - INTERVAL '1 day' * %(days)s
            ),
            recent_activity AS (
                SELECT COUNT(DISTINCT km.killmail_id) AS recent_kills
                FROM killmails km
                JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
                WHERE ka.corporation_id = %(corp_id)s
                    AND km.killmail_time >= NOW() - INTERVAL '1 day' * %(half_days)s
            ),
            previous_activity AS (
                SELECT COUNT(DISTINCT km.killmail_id) AS previous_kills
                FROM killmails km
                JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
                WHERE ka.corporation_id = %(corp_id)s
                    AND km.killmail_time BETWEEN NOW() - INTERVAL '1 day' * %(days)s
                    AND NOW() - INTERVAL '1 day' * %(half_days)s
            )
            SELECT
                k.kills,
                d.deaths,
                k.isk_destroyed,
                d.isk_lost,
                CASE
                    WHEN (k.isk_destroyed + d.isk_lost) > 0
                    THEN ROUND((k.isk_destroyed / (k.isk_destroyed + d.isk_lost) * 100)::numeric, 1)
                    ELSE 0
                END AS efficiency,
                CASE
                    WHEN prev.previous_kills > 0
                    THEN ROUND(((rec.recent_kills - prev.previous_kills)::numeric / prev.previous_kills * 100), 1)
                    ELSE 0
                END AS trend_pct
            FROM corp_kills k, corp_deaths d, recent_activity rec, previous_activity prev
        """

        cur.execute(sql_stats, {"corp_id": corp_id, "days": days, "half_days": half_days})
        stats_row = cur.fetchone()

        if stats_row:
            kills = stats_row[0] or 0
            deaths = stats_row[1] or 0
            isk_destroyed = float(stats_row[2] or 0)
            isk_lost = float(stats_row[3] or 0)

            # ISK metrics
            net_isk = isk_destroyed - isk_lost
            isk_efficiency = float(stats_row[4] or 0)

            # Kill metrics
            kill_balance = kills - deaths  # Saldo
            kill_efficiency = round(100.0 * kills / (kills + deaths), 1) if (kills + deaths) > 0 else 0.0
        else:
            kills = deaths = 0
            isk_destroyed = isk_lost = net_isk = 0.0
            kill_balance = 0
            isk_efficiency = kill_efficiency = 0.0

        return {
            "corporation_id": corp_id,
            "corporation_name": name_row[0],
            "ticker": name_row[1],
            "alliance_id": name_row[2],
            "alliance_name": name_row[3],
            "kills": kills,
            "deaths": deaths,
            "kill_balance": kill_balance,
            "isk_destroyed": isk_destroyed,
            "isk_lost": isk_lost,
            "net_isk": net_isk,
            "isk_efficiency": isk_efficiency,
            "kill_efficiency": kill_efficiency,
            "peak_hour": 12,  # Removed expensive hourly_activity CTE
            "trend_pct": float(stats_row[5]) if stats_row and stats_row[5] else 0.0,
        }


@router.get("/corporation/{corp_id}/offensive-summary")
@handle_endpoint_errors()
def get_offensive_summary(
    corp_id: int,
    days: int = Query(30, ge=1, le=90)
) -> Dict[str, Any]:
    """Get offensive intelligence summary for overview dashboard.

    Returns:
    - Efficiency and trend
    - ISK destroyed total and trend
    - Top target alliance
    - Primary doctrine (most used ship)
    - 7-day kill/death timeline for chart
    """
    with db_cursor(cursor_factory=None) as cur:
        # Summary stats
        # FIXED: Separate CTE to avoid Cartesian Product ISK inflation
        sql_summary = """
            WITH unique_kills AS (
                SELECT DISTINCT km.killmail_id, km.ship_value
                FROM killmails km
                JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
                WHERE ka.corporation_id = %(corp_id)s
                    AND km.killmail_time >= NOW() - INTERVAL '1 day' * %(days)s
            ),
            corp_kills AS (
                SELECT
                    COUNT(*) AS total_kills,
                    SUM(ship_value) AS isk_destroyed
                FROM unique_kills
            ),
            corp_deaths AS (
                SELECT COUNT(*) AS total_deaths
                FROM killmails km
                WHERE km.victim_corporation_id = %(corp_id)s
                    AND km.killmail_time >= NOW() - INTERVAL '1 day' * %(days)s
            )
            SELECT
                COALESCE(k.total_kills, 0) AS kills,
                COALESCE(d.total_deaths, 0) AS deaths,
                ROUND(100.0 * COALESCE(k.total_kills, 0) /
                      NULLIF(COALESCE(k.total_kills, 0) + COALESCE(d.total_deaths, 0), 0), 1) AS efficiency,
                COALESCE(k.isk_destroyed, 0) AS isk_destroyed
            FROM corp_kills k, corp_deaths d
        """

        cur.execute(sql_summary, {"corp_id": corp_id, "days": days})
        summary_row = cur.fetchone()
        kills, deaths, efficiency, isk_destroyed = summary_row

        # 7-day timeline for chart
        sql_timeline = """
            WITH daily_kills AS (
                SELECT
                    DATE(km.killmail_time) AS day,
                    COUNT(DISTINCT km.killmail_id) AS kills
                FROM killmails km
                JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
                WHERE ka.corporation_id = %(corp_id)s
                    AND km.killmail_time >= NOW() - INTERVAL '7 days'
                GROUP BY day
            ),
            daily_deaths AS (
                SELECT
                    DATE(km.killmail_time) AS day,
                    COUNT(*) AS deaths
                FROM killmails km
                WHERE km.victim_corporation_id = %(corp_id)s
                    AND km.killmail_time >= NOW() - INTERVAL '7 days'
                GROUP BY day
            )
            SELECT
                COALESCE(k.day, d.day)::text AS day,
                COALESCE(k.kills, 0) AS kills,
                COALESCE(d.deaths, 0) AS deaths
            FROM daily_kills k
            FULL OUTER JOIN daily_deaths d ON k.day = d.day
            ORDER BY COALESCE(k.day, d.day)
        """

        cur.execute(sql_timeline, {"corp_id": corp_id})
        timeline = [
            {"day": row[0], "kills": row[1], "deaths": row[2]}
            for row in cur.fetchall()
        ]

        # Calculate trend from timeline
        trend = calculate_trend(timeline, "kills")

        # ISK trend (last 3 days vs previous 4 days)
        # FIXED: Use DISTINCT to avoid ISK inflation
        sql_isk_trend = """
            WITH unique_kills AS (
                SELECT DISTINCT
                    km.killmail_id,
                    DATE(km.killmail_time) AS day,
                    km.ship_value
                FROM killmails km
                JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
                WHERE ka.corporation_id = %(corp_id)s
                    AND km.killmail_time >= NOW() - INTERVAL '7 days'
            ),
            daily_isk AS (
                SELECT day, SUM(ship_value) AS isk
                FROM unique_kills
                GROUP BY day
                ORDER BY day
            )
            SELECT
                COALESCE(AVG(isk) FILTER (WHERE day >= CURRENT_DATE - 2), 0) AS recent_isk,
                COALESCE(AVG(isk) FILTER (WHERE day < CURRENT_DATE - 2), 0) AS older_isk
            FROM daily_isk
        """

        cur.execute(sql_isk_trend, {"corp_id": corp_id})
        isk_trend_row = cur.fetchone()
        recent_isk, older_isk = isk_trend_row

        if older_isk > 0:
            isk_change_pct = ((recent_isk - older_isk) / older_isk) * 100
            if isk_change_pct > 15:
                isk_trend = f"↗ +{int(isk_change_pct)}%"
            elif isk_change_pct < -15:
                isk_trend = f"↘ {int(isk_change_pct)}%"
            else:
                isk_trend = "→ stable"
        else:
            isk_trend = "→ stable"

        # Top target alliance
        sql_top_target = """
            SELECT
                anc.alliance_name,
                COUNT(DISTINCT km.killmail_id) AS kills
            FROM killmails km
            JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
            LEFT JOIN alliance_name_cache anc ON km.victim_alliance_id = anc.alliance_id
            WHERE ka.corporation_id = %(corp_id)s
                AND km.victim_alliance_id IS NOT NULL
                AND km.killmail_time >= NOW() - INTERVAL '1 day' * %(days)s
            GROUP BY km.victim_alliance_id, anc.alliance_name
            ORDER BY kills DESC
            LIMIT 1
        """

        cur.execute(sql_top_target, {"corp_id": corp_id, "days": days})
        top_target_row = cur.fetchone()

        if top_target_row:
            top_target = {"name": top_target_row[0] or "Unknown", "kills": top_target_row[1]}
        else:
            top_target = {"name": "None", "kills": 0}

        # Primary doctrine (most used ship)
        sql_doctrine = """
            SELECT
                it."typeName",
                COUNT(DISTINCT km.killmail_id) AS kills
            FROM killmails km
            JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
            JOIN "invTypes" it ON ka.ship_type_id = it."typeID"
            JOIN "invGroups" ig ON it."groupID" = ig."groupID"
            WHERE ka.corporation_id = %(corp_id)s
                AND km.killmail_time >= NOW() - INTERVAL '1 day' * %(days)s
                AND ig."groupName" NOT IN ('Capsule', 'Rookie ship')
            GROUP BY it."typeName"
            ORDER BY kills DESC
            LIMIT 1
        """

        cur.execute(sql_doctrine, {"corp_id": corp_id, "days": days})
        doctrine_row = cur.fetchone()

        primary_doctrine = doctrine_row[0] if doctrine_row else "Unknown"

        return {
            "efficiency": float(efficiency) if efficiency else 0.0,
            "trend": trend,
            "isk_destroyed": float(isk_destroyed) if isk_destroyed else 0.0,
            "isk_trend": isk_trend,
            "top_target": top_target,
            "primary_doctrine": primary_doctrine,
            "timeline": timeline,
        }

@router.get("/corporation/{corp_id}/defensive-summary")
@handle_endpoint_errors()
def get_defensive_summary(
    corp_id: int,
    days: int = Query(30, ge=1, le=90)
) -> Dict[str, Any]:
    """Get defensive intelligence summary for overview dashboard.

    Returns:
    - K/D ratio and efficiency
    - Total deaths and ISK lost
    - Biggest threat (alliance killing us most)
    - Most lost ship type
    - 7-day death timeline for chart
    """
    with db_cursor(cursor_factory=None) as cur:
        # Summary stats
        sql_summary = """
            WITH corp_kills AS (
                SELECT COUNT(DISTINCT km.killmail_id) AS total_kills
                FROM killmails km
                JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
                WHERE ka.corporation_id = %(corp_id)s
                    AND km.killmail_time >= NOW() - INTERVAL '1 day' * %(days)s
            ),
            corp_deaths AS (
                SELECT
                    COUNT(*) AS total_deaths,
                    SUM(km.ship_value) AS isk_lost
                FROM killmails km
                WHERE km.victim_corporation_id = %(corp_id)s
                    AND km.killmail_time >= NOW() - INTERVAL '1 day' * %(days)s
            )
            SELECT
                COALESCE(k.total_kills, 0) AS kills,
                COALESCE(d.total_deaths, 0) AS deaths,
                CASE
                    WHEN COALESCE(d.total_deaths, 0) > 0
                    THEN ROUND(COALESCE(k.total_kills, 0)::numeric / d.total_deaths, 2)
                    ELSE 0
                END AS kd_ratio,
                ROUND(100.0 * COALESCE(k.total_kills, 0) /
                      NULLIF(COALESCE(k.total_kills, 0) + COALESCE(d.total_deaths, 0), 0), 1) AS efficiency,
                COALESCE(d.isk_lost, 0) AS isk_lost
            FROM corp_kills k, corp_deaths d
        """

        cur.execute(sql_summary, {"corp_id": corp_id, "days": days})
        summary_row = cur.fetchone()
        kills, deaths, kd_ratio, efficiency, isk_lost = summary_row

        # 7-day timeline for chart
        sql_timeline = """
            WITH daily_deaths AS (
                SELECT
                    DATE(km.killmail_time) AS day,
                    COUNT(*) AS deaths
                FROM killmails km
                WHERE km.victim_corporation_id = %(corp_id)s
                    AND km.killmail_time >= NOW() - INTERVAL '7 days'
                GROUP BY day
            )
            SELECT
                day::text AS day,
                deaths
            FROM daily_deaths
            ORDER BY day
        """

        cur.execute(sql_timeline, {"corp_id": corp_id})
        timeline = [
            {"day": row[0], "deaths": row[1]}
            for row in cur.fetchall()
        ]

        # Calculate trend from timeline
        trend = calculate_trend(timeline, "deaths")

        # ISK trend (last 3 days vs previous 4 days)
        sql_isk_trend = """
            WITH daily_isk AS (
                SELECT
                    DATE(km.killmail_time) AS day,
                    SUM(km.ship_value) AS isk
                FROM killmails km
                WHERE km.victim_corporation_id = %(corp_id)s
                    AND km.killmail_time >= NOW() - INTERVAL '7 days'
                GROUP BY day
                ORDER BY day
            )
            SELECT
                COALESCE(AVG(isk) FILTER (WHERE day >= CURRENT_DATE - 2), 0) AS recent_isk,
                COALESCE(AVG(isk) FILTER (WHERE day < CURRENT_DATE - 2), 0) AS older_isk
            FROM daily_isk
        """

        cur.execute(sql_isk_trend, {"corp_id": corp_id})
        isk_trend_row = cur.fetchone()
        recent_isk, older_isk = isk_trend_row

        if older_isk > 0:
            isk_change_pct = ((recent_isk - older_isk) / older_isk) * 100
            if isk_change_pct > 15:
                isk_trend = f"↗ +{int(isk_change_pct)}%"
            elif isk_change_pct < -15:
                isk_trend = f"↘ {int(isk_change_pct)}%"
            else:
                isk_trend = "→ stable"
        else:
            isk_trend = "→ stable"

        # Biggest threat (alliance killing us most)
        sql_top_threat = """
            SELECT
                anc.alliance_name,
                COUNT(*) AS kills_on_us
            FROM killmails km
            JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
            LEFT JOIN alliance_name_cache anc ON ka.alliance_id = anc.alliance_id
            WHERE km.victim_corporation_id = %(corp_id)s
                AND ka.alliance_id IS NOT NULL
                AND km.killmail_time >= NOW() - INTERVAL '1 day' * %(days)s
            GROUP BY ka.alliance_id, anc.alliance_name
            ORDER BY kills_on_us DESC
            LIMIT 1
        """

        cur.execute(sql_top_threat, {"corp_id": corp_id, "days": days})
        top_threat_row = cur.fetchone()

        if top_threat_row:
            top_threat = {"name": top_threat_row[0] or "Unknown", "kills": top_threat_row[1]}
        else:
            top_threat = {"name": "None", "kills": 0}

        # Most lost ship
        sql_most_lost = """
            SELECT
                it."typeName",
                COUNT(*) AS losses
            FROM killmails km
            JOIN "invTypes" it ON km.ship_type_id = it."typeID"
            JOIN "invGroups" ig ON it."groupID" = ig."groupID"
            WHERE km.victim_corporation_id = %(corp_id)s
                AND km.killmail_time >= NOW() - INTERVAL '1 day' * %(days)s
                AND ig."groupName" NOT IN ('Capsule', 'Rookie ship')
            GROUP BY it."typeName"
            ORDER BY losses DESC
            LIMIT 1
        """

        cur.execute(sql_most_lost, {"corp_id": corp_id, "days": days})
        most_lost_row = cur.fetchone()

        most_lost_ship = most_lost_row[0] if most_lost_row else "Unknown"

        return {
            "kd_ratio": float(kd_ratio) if kd_ratio else 0.0,
            "efficiency": float(efficiency) if efficiency else 0.0,
            "deaths": deaths or 0,
            "isk_lost": float(isk_lost) if isk_lost else 0.0,
            "isk_trend": isk_trend,
            "trend": trend,
            "top_threat": top_threat,
            "most_lost_ship": most_lost_ship,
            "timeline": timeline,
        }

@router.get("/corporation/{corp_id}/capital-summary")
@handle_endpoint_errors()
def get_capital_summary(
    corp_id: int,
    days: int = Query(30, ge=1, le=90)
) -> Dict[str, Any]:
    """Get capital warfare intelligence summary for overview dashboard.

    Returns:
    - Capital kills and losses
    - Capital efficiency
    - Top capital type destroyed
    - Primary capital used by corp
    - 7-day capital activity timeline
    """
    with db_cursor(cursor_factory=None) as cur:
        # Capital groups
        capital_groups = (
            'Carrier', 'Dreadnought', 'Supercarrier', 'Titan',
            'Force Auxiliary', 'Lancer Dreadnought'
        )

        # Summary stats
        sql_summary = """
            WITH capital_kills AS (
                SELECT COUNT(DISTINCT km.killmail_id) AS total_kills
                FROM killmails km
                JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
                JOIN "invTypes" it ON km.ship_type_id = it."typeID"
                JOIN "invGroups" ig ON it."groupID" = ig."groupID"
                WHERE ka.corporation_id = %(corp_id)s
                    AND ig."groupName" IN %(capital_groups)s
                    AND km.killmail_time >= NOW() - INTERVAL '1 day' * %(days)s
            ),
            capital_losses AS (
                SELECT COUNT(*) AS total_losses
                FROM killmails km
                JOIN "invTypes" it ON km.ship_type_id = it."typeID"
                JOIN "invGroups" ig ON it."groupID" = ig."groupID"
                WHERE km.victim_corporation_id = %(corp_id)s
                    AND ig."groupName" IN %(capital_groups)s
                    AND km.killmail_time >= NOW() - INTERVAL '1 day' * %(days)s
            )
            SELECT
                COALESCE(k.total_kills, 0) AS kills,
                COALESCE(l.total_losses, 0) AS losses,
                ROUND(100.0 * COALESCE(k.total_kills, 0) /
                      NULLIF(COALESCE(k.total_kills, 0) + COALESCE(l.total_losses, 0), 0), 1) AS efficiency
            FROM capital_kills k, capital_losses l
        """

        cur.execute(sql_summary, {"corp_id": corp_id, "capital_groups": capital_groups, "days": days})
        summary_row = cur.fetchone()
        kills, losses, efficiency = summary_row

        # 7-day timeline for chart
        sql_timeline = """
            WITH daily_capital_kills AS (
                SELECT
                    DATE(km.killmail_time) AS day,
                    COUNT(DISTINCT km.killmail_id) AS kills
                FROM killmails km
                JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
                JOIN "invTypes" it ON km.ship_type_id = it."typeID"
                JOIN "invGroups" ig ON it."groupID" = ig."groupID"
                WHERE ka.corporation_id = %(corp_id)s
                    AND ig."groupName" IN %(capital_groups)s
                    AND km.killmail_time >= NOW() - INTERVAL '7 days'
                GROUP BY day
            ),
            daily_capital_losses AS (
                SELECT
                    DATE(km.killmail_time) AS day,
                    COUNT(*) AS losses
                FROM killmails km
                JOIN "invTypes" it ON km.ship_type_id = it."typeID"
                JOIN "invGroups" ig ON it."groupID" = ig."groupID"
                WHERE km.victim_corporation_id = %(corp_id)s
                    AND ig."groupName" IN %(capital_groups)s
                    AND km.killmail_time >= NOW() - INTERVAL '7 days'
                GROUP BY day
            )
            SELECT
                COALESCE(k.day, l.day)::text AS day,
                COALESCE(k.kills, 0) AS kills,
                COALESCE(l.losses, 0) AS losses
            FROM daily_capital_kills k
            FULL OUTER JOIN daily_capital_losses l ON k.day = l.day
            ORDER BY COALESCE(k.day, l.day)
        """

        cur.execute(sql_timeline, {"corp_id": corp_id, "capital_groups": capital_groups})
        timeline = [
            {"day": row[0], "kills": row[1], "losses": row[2]}
            for row in cur.fetchall()
        ]

        # Calculate trend (kills only, from timeline)
        trend = calculate_trend(timeline, "kills")

        # Top capital type destroyed
        sql_top_capital = """
            SELECT
                ig."groupName",
                COUNT(DISTINCT km.killmail_id) AS kills
            FROM killmails km
            JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
            JOIN "invTypes" it ON km.ship_type_id = it."typeID"
            JOIN "invGroups" ig ON it."groupID" = ig."groupID"
            WHERE ka.corporation_id = %(corp_id)s
                AND ig."groupName" IN %(capital_groups)s
                AND km.killmail_time >= NOW() - INTERVAL '1 day' * %(days)s
            GROUP BY ig."groupName"
            ORDER BY kills DESC
            LIMIT 1
        """

        cur.execute(sql_top_capital, {"corp_id": corp_id, "capital_groups": capital_groups, "days": days})
        top_capital_row = cur.fetchone()

        top_capital_type = top_capital_row[0] if top_capital_row else "None"

        # Primary capital used
        sql_primary_capital = """
            SELECT
                it."typeName",
                COUNT(DISTINCT km.killmail_id) AS kills
            FROM killmails km
            JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
            JOIN "invTypes" it ON ka.ship_type_id = it."typeID"
            JOIN "invGroups" ig ON it."groupID" = ig."groupID"
            WHERE ka.corporation_id = %(corp_id)s
                AND ig."groupName" IN %(capital_groups)s
                AND km.killmail_time >= NOW() - INTERVAL '1 day' * %(days)s
            GROUP BY it."typeName"
            ORDER BY kills DESC
            LIMIT 1
        """

        cur.execute(sql_primary_capital, {"corp_id": corp_id, "capital_groups": capital_groups, "days": days})
        primary_capital_row = cur.fetchone()

        primary_capital = primary_capital_row[0] if primary_capital_row else "None"

        return {
            "kills": kills or 0,
            "losses": losses or 0,
            "efficiency": float(efficiency) if efficiency else 0.0,
            "trend": trend,
            "top_capital_type": top_capital_type,
            "primary_capital": primary_capital,
            "timeline": timeline,
        }

@router.get("/corporation/{corp_id}/pilot-summary")
@handle_endpoint_errors()
def get_pilot_summary(
    corp_id: int,
    days: int = Query(30, ge=1, le=90)
) -> Dict[str, Any]:
    """Get pilot intelligence summary for overview dashboard.

    Returns:
    - Total active pilots
    - Average morale score
    - Elite pilot count (morale >= 80)
    - Struggling pilot count (morale < 40)
    - 7-day pilot activity timeline
    """
    with db_cursor(cursor_factory=None) as cur:
        # Active pilots and morale calculation
        sql_pilot_stats = """
            WITH pilot_activity AS (
                SELECT
                    COALESCE(ka.character_id, km.victim_character_id) AS character_id,
                    COUNT(DISTINCT CASE WHEN ka.character_id IS NOT NULL THEN km.killmail_id END) AS kills,
                    COUNT(DISTINCT CASE WHEN km.victim_character_id = COALESCE(ka.character_id, km.victim_character_id)
                                      AND km.victim_corporation_id = %(corp_id)s THEN km.killmail_id END) AS deaths,
                    COUNT(DISTINCT DATE(km.killmail_time)) AS active_days
                FROM killmails km
                LEFT JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id AND ka.corporation_id = %(corp_id)s
                WHERE (ka.corporation_id = %(corp_id)s OR km.victim_corporation_id = %(corp_id)s)
                    AND km.killmail_time >= NOW() - INTERVAL '1 day' * %(days)s
                GROUP BY COALESCE(ka.character_id, km.victim_character_id)
            ),
            pilot_morale AS (
                SELECT
                    character_id,
                    -- Morale: 30pct activity consistency + 40pct efficiency + 30pct trend
                    ROUND(
                        (active_days::float / %(days)s * 30) +
                        (kills::float / NULLIF(kills + deaths, 0) * 40) +
                        30.0  -- Neutral trend for summary
                    ) AS morale
                FROM pilot_activity
            )
            SELECT
                COUNT(DISTINCT character_id) AS total_pilots,
                ROUND(AVG(morale)::numeric, 1) AS avg_morale,
                COUNT(CASE WHEN morale >= 80 THEN 1 END) AS elite_pilots,
                COUNT(CASE WHEN morale < 40 THEN 1 END) AS struggling_pilots
            FROM pilot_morale
        """

        cur.execute(sql_pilot_stats, {"corp_id": corp_id, "days": days})
        stats_row = cur.fetchone()
        total_pilots, avg_morale, elite_pilots, struggling_pilots = stats_row

        # 7-day pilot activity timeline (attackers only)
        sql_timeline = """
            SELECT
                DATE(km.killmail_time)::text AS day,
                COUNT(DISTINCT ka.character_id) AS active_pilots
            FROM killmails km
            JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
                AND ka.corporation_id = %(corp_id)s
            WHERE km.killmail_time >= NOW() - INTERVAL '7 days'
                AND ka.character_id IS NOT NULL
            GROUP BY DATE(km.killmail_time)
            ORDER BY DATE(km.killmail_time)
        """

        cur.execute(sql_timeline, {"corp_id": corp_id})
        timeline = [
            {"day": row[0], "active_pilots": row[1]}
            for row in cur.fetchall()
        ]

        # Calculate trend
        trend = calculate_trend(timeline, "active_pilots")

        # Top performing pilot (highest morale)
        sql_top_pilot = """
            WITH pilot_activity AS (
                SELECT
                    COALESCE(ka.character_id, km.victim_character_id) AS character_id,
                    COUNT(DISTINCT CASE WHEN ka.character_id IS NOT NULL THEN km.killmail_id END) AS kills,
                    COUNT(DISTINCT CASE WHEN km.victim_character_id = COALESCE(ka.character_id, km.victim_character_id)
                                      AND km.victim_corporation_id = %(corp_id)s THEN km.killmail_id END) AS deaths,
                    COUNT(DISTINCT DATE(km.killmail_time)) AS active_days
                FROM killmails km
                LEFT JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id AND ka.corporation_id = %(corp_id)s
                WHERE (ka.corporation_id = %(corp_id)s OR km.victim_corporation_id = %(corp_id)s)
                    AND km.killmail_time >= NOW() - INTERVAL '1 day' * %(days)s
                GROUP BY COALESCE(ka.character_id, km.victim_character_id)
            ),
            pilot_morale AS (
                SELECT
                    pa.character_id,
                    cn.character_name,
                    ROUND(
                        (pa.active_days::float / %(days)s * 30) +
                        (pa.kills::float / NULLIF(pa.kills + pa.deaths, 0) * 40) +
                        30.0
                    ) AS morale
                FROM pilot_activity pa
                LEFT JOIN character_name_cache cn ON pa.character_id = cn.character_id
            )
            SELECT character_name
            FROM pilot_morale
            WHERE morale IS NOT NULL
            ORDER BY morale DESC
            LIMIT 1
        """

        cur.execute(sql_top_pilot, {"corp_id": corp_id, "days": days})
        top_pilot_row = cur.fetchone()

        top_pilot = top_pilot_row[0] if top_pilot_row else "Unknown"

        return {
            "total_pilots": total_pilots or 0,
            "avg_morale": float(avg_morale) if avg_morale else 0.0,
            "elite_pilots": elite_pilots or 0,
            "struggling_pilots": struggling_pilots or 0,
            "trend": trend,
            "top_pilot": top_pilot,
            "timeline": timeline,
        }

@router.get("/corporation/{corp_id}/geography-summary")
@handle_endpoint_errors()
def get_geography_summary(
    corp_id: int,
    days: int = Query(30, ge=1, le=90)
) -> Dict[str, Any]:
    """Get geographic intelligence summary for overview dashboard.

    Returns:
    - Primary region and system (most activity)
    - Unique systems and regions count
    - Geographic spread metric
    - 7-day region diversity timeline
    """
    with db_cursor(cursor_factory=None) as cur:
        # Geographic stats
        sql_geo_stats = """
            WITH corp_activity AS (
                SELECT
                    ms."solarSystemID",
                    ms."solarSystemName",
                    mr."regionID",
                    mr."regionName",
                    COUNT(DISTINCT km.killmail_id) AS activity
                FROM killmails km
                LEFT JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
                JOIN "mapSolarSystems" ms ON km.solar_system_id = ms."solarSystemID"
                JOIN "mapRegions" mr ON ms."regionID" = mr."regionID"
                WHERE (ka.corporation_id = %(corp_id)s OR km.victim_corporation_id = %(corp_id)s)
                    AND km.killmail_time >= NOW() - INTERVAL '1 day' * %(days)s
                GROUP BY ms."solarSystemID", ms."solarSystemName", mr."regionID", mr."regionName"
            )
            SELECT
                COUNT(DISTINCT "solarSystemID") AS unique_systems,
                COUNT(DISTINCT "regionID") AS unique_regions
            FROM corp_activity
        """

        cur.execute(sql_geo_stats, {"corp_id": corp_id, "days": days})
        stats_row = cur.fetchone()
        unique_systems, unique_regions = stats_row

        # Primary region (most activity)
        sql_primary_region = """
            SELECT
                mr."regionName",
                COUNT(DISTINCT km.killmail_id) AS activity
            FROM killmails km
            LEFT JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
            JOIN "mapSolarSystems" ms ON km.solar_system_id = ms."solarSystemID"
            JOIN "mapRegions" mr ON ms."regionID" = mr."regionID"
            WHERE (ka.corporation_id = %(corp_id)s OR km.victim_corporation_id = %(corp_id)s)
                AND km.killmail_time >= NOW() - INTERVAL '1 day' * %(days)s
            GROUP BY mr."regionName"
            ORDER BY activity DESC
            LIMIT 1
        """

        cur.execute(sql_primary_region, {"corp_id": corp_id, "days": days})
        primary_region_row = cur.fetchone()

        primary_region = primary_region_row[0] if primary_region_row else "Unknown"

        # Primary system (most activity)
        sql_primary_system = """
            SELECT
                ms."solarSystemName",
                COUNT(DISTINCT km.killmail_id) AS activity
            FROM killmails km
            LEFT JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
            JOIN "mapSolarSystems" ms ON km.solar_system_id = ms."solarSystemID"
            WHERE (ka.corporation_id = %(corp_id)s OR km.victim_corporation_id = %(corp_id)s)
                AND km.killmail_time >= NOW() - INTERVAL '1 day' * %(days)s
            GROUP BY ms."solarSystemName"
            ORDER BY activity DESC
            LIMIT 1
        """

        cur.execute(sql_primary_system, {"corp_id": corp_id, "days": days})
        primary_system_row = cur.fetchone()

        primary_system = primary_system_row[0] if primary_system_row else "Unknown"

        # 7-day region diversity timeline
        sql_timeline = """
            WITH daily_regions AS (
                SELECT
                    DATE(km.killmail_time) AS day,
                    COUNT(DISTINCT mr."regionID") AS unique_regions
                FROM killmails km
                LEFT JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
                JOIN "mapSolarSystems" ms ON km.solar_system_id = ms."solarSystemID"
                JOIN "mapRegions" mr ON ms."regionID" = mr."regionID"
                WHERE (ka.corporation_id = %(corp_id)s OR km.victim_corporation_id = %(corp_id)s)
                    AND km.killmail_time >= NOW() - INTERVAL '7 days'
                GROUP BY day
            )
            SELECT
                day::text AS day,
                unique_regions
            FROM daily_regions
            ORDER BY day
        """

        cur.execute(sql_timeline, {"corp_id": corp_id})
        timeline = [
            {"day": row[0], "unique_regions": row[1]}
            for row in cur.fetchall()
        ]

        # Calculate trend
        trend = calculate_trend(timeline, "unique_regions", labels=("expanding", "contracting", "stable"))

        return {
            "unique_systems": unique_systems or 0,
            "unique_regions": unique_regions or 0,
            "primary_region": primary_region,
            "primary_system": primary_system,
            "trend": trend,
            "timeline": timeline,
        }

@router.get("/corporation/{corp_id}/activity-summary")
@handle_endpoint_errors()
def get_activity_summary(
    corp_id: int,
    days: int = Query(30, ge=1, le=90)
) -> Dict[str, Any]:
    """Get activity intelligence summary for overview dashboard.

    Returns:
    - Average daily activity
    - Peak activity hour (EVE time)
    - Activity trend
    - 7-day activity timeline
    """
    with db_cursor(cursor_factory=None) as cur:
        # Activity stats
        sql_activity_stats = """
            WITH daily_activity AS (
                SELECT
                    DATE(km.killmail_time) AS day,
                    COUNT(DISTINCT km.killmail_id) AS activity
                FROM killmails km
                LEFT JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
                WHERE (ka.corporation_id = %(corp_id)s OR km.victim_corporation_id = %(corp_id)s)
                    AND km.killmail_time >= NOW() - INTERVAL '1 day' * %(days)s
                GROUP BY day
            )
            SELECT
                COUNT(DISTINCT day) AS active_days,
                ROUND(AVG(activity), 1) AS avg_daily_activity
            FROM daily_activity
        """

        cur.execute(sql_activity_stats, {"corp_id": corp_id, "days": days})
        stats_row = cur.fetchone()
        active_days, avg_daily_activity = stats_row

        # Peak activity hour
        sql_peak_hour = """
            SELECT
                EXTRACT(HOUR FROM km.killmail_time AT TIME ZONE 'UTC') AS hour,
                COUNT(*) AS activity
            FROM killmails km
            LEFT JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
            WHERE (ka.corporation_id = %(corp_id)s OR km.victim_corporation_id = %(corp_id)s)
                AND km.killmail_time >= NOW() - INTERVAL '1 day' * %(days)s
            GROUP BY hour
            ORDER BY activity DESC
            LIMIT 1
        """

        cur.execute(sql_peak_hour, {"corp_id": corp_id, "days": days})
        peak_hour_row = cur.fetchone()

        peak_hour = int(peak_hour_row[0]) if peak_hour_row else 0

        # 7-day activity timeline
        sql_timeline = """
            SELECT
                DATE(km.killmail_time)::text AS day,
                COUNT(DISTINCT km.killmail_id) AS total_activity
            FROM killmails km
            LEFT JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
            WHERE (ka.corporation_id = %(corp_id)s OR km.victim_corporation_id = %(corp_id)s)
                AND km.killmail_time >= NOW() - INTERVAL '7 days'
            GROUP BY DATE(km.killmail_time)
            ORDER BY day
        """

        cur.execute(sql_timeline, {"corp_id": corp_id})
        timeline = [
            {"day": row[0], "activity": row[1]}
            for row in cur.fetchall()
        ]

        # Calculate trend
        trend = calculate_trend(timeline, "activity")

        return {
            "active_days": active_days or 0,
            "avg_daily_activity": float(avg_daily_activity) if avg_daily_activity else 0.0,
            "peak_hour": peak_hour,
            "trend": trend,
            "timeline": timeline,
        }

@router.get("/corporation/{corp_id}/hunting-summary")
@handle_endpoint_errors()
def get_hunting_summary(
    corp_id: int,
    days: int = Query(30, ge=1, le=90)
) -> Dict[str, Any]:
    """Get hunting intelligence summary for overview dashboard.

    Returns:
    - Threat level (low/medium/high)
    - Operational tempo (kills per active day)
    - Most hunted region
    - Strike efficiency
    - 7-day kill rate timeline
    """
    with db_cursor(cursor_factory=None) as cur:
        # Hunting stats
        # FIXED: Use DISTINCT to avoid ISK inflation
        sql_hunting_stats = """
            WITH unique_kills AS (
                SELECT DISTINCT
                    km.killmail_id,
                    km.ship_value,
                    km.killmail_time
                FROM killmails km
                JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
                WHERE ka.corporation_id = %(corp_id)s
                    AND km.killmail_time >= NOW() - INTERVAL '1 day' * %(days)s
            ),
            kill_stats AS (
                SELECT
                    COUNT(*) AS total_kills,
                    SUM(ship_value) AS isk_destroyed,
                    COUNT(DISTINCT DATE(killmail_time)) AS active_days
                FROM unique_kills
            )
            SELECT
                total_kills,
                isk_destroyed,
                active_days,
                CASE
                    WHEN active_days > 0 THEN ROUND(total_kills::numeric / active_days, 1)
                    ELSE 0
                END AS operational_tempo
            FROM kill_stats
        """

        cur.execute(sql_hunting_stats, {"corp_id": corp_id, "days": days})
        stats_row = cur.fetchone()
        total_kills, isk_destroyed, active_days, operational_tempo = stats_row

        # Threat level calculation (based on kills, ISK, activity)
        threat_score = 0

        if total_kills and total_kills > 100:
            threat_score += 40
        elif total_kills and total_kills > 30:
            threat_score += 20
        elif total_kills and total_kills > 10:
            threat_score += 10

        avg_kill_value = (isk_destroyed / total_kills) if total_kills else 0
        if avg_kill_value > 1e9:  # >1B ISK
            threat_score += 30
        elif avg_kill_value > 500e6:  # >500M ISK
            threat_score += 15
        elif avg_kill_value > 100e6:  # >100M ISK
            threat_score += 5

        if threat_score >= 60:
            threat_level = "high"
        elif threat_score >= 30:
            threat_level = "medium"
        else:
            threat_level = "low"

        # Most hunted region
        sql_hunted_region = """
            SELECT
                mr."regionName",
                COUNT(DISTINCT km.killmail_id) AS kills
            FROM killmails km
            JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
            JOIN "mapSolarSystems" ms ON km.solar_system_id = ms."solarSystemID"
            JOIN "mapRegions" mr ON ms."regionID" = mr."regionID"
            WHERE ka.corporation_id = %(corp_id)s
                AND km.killmail_time >= NOW() - INTERVAL '1 day' * %(days)s
            GROUP BY mr."regionName"
            ORDER BY kills DESC
            LIMIT 1
        """

        cur.execute(sql_hunted_region, {"corp_id": corp_id, "days": days})
        hunted_region_row = cur.fetchone()

        hunted_region = hunted_region_row[0] if hunted_region_row else "Unknown"

        # 7-day kill rate timeline
        sql_timeline = """
            SELECT
                DATE(km.killmail_time)::text AS day,
                COUNT(DISTINCT km.killmail_id) AS kills
            FROM killmails km
            JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
            WHERE ka.corporation_id = %(corp_id)s
                AND km.killmail_time >= NOW() - INTERVAL '7 days'
            GROUP BY DATE(km.killmail_time)
            ORDER BY day
        """

        cur.execute(sql_timeline, {"corp_id": corp_id})
        timeline = [
            {"day": row[0], "kills": row[1]}
            for row in cur.fetchall()
        ]

        # Calculate trend
        trend = calculate_trend(timeline, "kills", labels=("escalating", "declining", "steady"))

        return {
            "threat_level": threat_level,
            "operational_tempo": float(operational_tempo) if operational_tempo else 0.0,
            "hunted_region": hunted_region,
            "trend": trend,
            "timeline": timeline,
        }

# ============================================================================
# Shared Temporal Analysis Endpoints (used by multiple tabs)
# ============================================================================

@router.get("/corporation/{corp_id}/activity-timeline")
@handle_endpoint_errors()
def get_activity_timeline(
    corp_id: int,
    days: int = Query(30, ge=1, le=90)
):
    """
    Get daily activity timeline for corporation.
    Used by: Hunting Tab, Overview ActivityCard
    
    Returns:
    - days: Daily breakdown of kills, deaths, efficiency
    - trend: 'increasing', 'decreasing', or 'stable'
    - avg_daily_activity: Average daily kill+death count
    """
    with db_cursor() as cur:
        # Daily timeline with kills and deaths
        cur.execute("""
            WITH daily_kills AS (
                SELECT
                    DATE(km.killmail_time) AS day,
                    COUNT(DISTINCT km.killmail_id) AS kills
                FROM killmails km
                JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
                WHERE ka.corporation_id = %s
                  AND km.killmail_time >= NOW() - make_interval(days => %s)
                GROUP BY DATE(km.killmail_time)
            ),
            daily_deaths AS (
                SELECT
                    DATE(km.killmail_time) AS day,
                    COUNT(DISTINCT km.killmail_id) AS deaths
                FROM killmails km
                WHERE km.victim_corporation_id = %s
                  AND km.killmail_time >= NOW() - make_interval(days => %s)
                GROUP BY DATE(km.killmail_time)
            ),
            all_days AS (
                SELECT DISTINCT day FROM (
                    SELECT day FROM daily_kills
                    UNION
                    SELECT day FROM daily_deaths
                ) t
            )
            SELECT
                ad.day,
                COALESCE(dk.kills, 0) AS kills,
                COALESCE(dd.deaths, 0) AS deaths,
                COALESCE(dk.kills, 0) + COALESCE(dd.deaths, 0) AS total_activity,
                CASE
                    WHEN COALESCE(dk.kills, 0) + COALESCE(dd.deaths, 0) > 0
                    THEN ROUND((COALESCE(dk.kills, 0)::FLOAT / (COALESCE(dk.kills, 0) + COALESCE(dd.deaths, 0)) * 100)::numeric, 1)
                    ELSE 0
                END AS efficiency
            FROM all_days ad
            LEFT JOIN daily_kills dk ON ad.day = dk.day
            LEFT JOIN daily_deaths dd ON ad.day = dd.day
            ORDER BY ad.day ASC
        """, (corp_id, days, corp_id, days))

        timeline_data = []
        for row in cur.fetchall():
            timeline_data.append({
                "day": row['day'].strftime('%Y-%m-%d'),
                "kills": row['kills'],
                "deaths": row['deaths'],
                "total_activity": row['total_activity'],
                "efficiency": float(row['efficiency'] or 0)
            })

        # Calculate trend (compare last 7 days vs previous 7 days)
        trend = "stable"
        if len(timeline_data) >= 14:
            recent_avg = sum(d['total_activity'] for d in timeline_data[-7:]) / 7
            previous_avg = sum(d['total_activity'] for d in timeline_data[-14:-7]) / 7

            if previous_avg > 0:
                change = (recent_avg - previous_avg) / previous_avg
                if change > 0.15:
                    trend = "increasing"
                elif change < -0.15:
                    trend = "decreasing"

        # Calculate average daily activity
        avg_daily_activity = sum(d['total_activity'] for d in timeline_data) / len(timeline_data) if timeline_data else 0

        return {
            "days": timeline_data,
            "trend": trend,
            "avg_daily_activity": avg_daily_activity
        }

@router.get("/corporation/{corp_id}/timezone-activity")
@handle_endpoint_errors()
def get_timezone_activity(
    corp_id: int,
    days: int = Query(30, ge=1, le=90)
):
    """
    Get hourly activity distribution (EVE time).
    Used by: Hunting Tab
    
    Returns:
    - Array of 24 hourly activity records (0-23 EVE time)
    - Each with: hour, activity, kills, deaths
    """
    with db_cursor() as cur:
        # Hourly activity breakdown
        cur.execute("""
            WITH hourly_kills AS (
                SELECT
                    EXTRACT(HOUR FROM km.killmail_time)::INTEGER AS hour,
                    COUNT(DISTINCT km.killmail_id) AS kills
                FROM killmails km
                JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
                WHERE ka.corporation_id = %s
                  AND km.killmail_time >= NOW() - make_interval(days => %s)
                GROUP BY EXTRACT(HOUR FROM km.killmail_time)
            ),
            hourly_deaths AS (
                SELECT
                    EXTRACT(HOUR FROM km.killmail_time)::INTEGER AS hour,
                    COUNT(DISTINCT km.killmail_id) AS deaths
                FROM killmails km
                WHERE km.victim_corporation_id = %s
                  AND km.killmail_time >= NOW() - make_interval(days => %s)
                GROUP BY EXTRACT(HOUR FROM km.killmail_time)
            ),
            all_hours AS (
                SELECT generate_series(0, 23) AS hour
            )
            SELECT
                ah.hour,
                COALESCE(hk.kills, 0) AS kills,
                COALESCE(hd.deaths, 0) AS deaths,
                COALESCE(hk.kills, 0) + COALESCE(hd.deaths, 0) AS activity
            FROM all_hours ah
            LEFT JOIN hourly_kills hk ON ah.hour = hk.hour
            LEFT JOIN hourly_deaths hd ON ah.hour = hd.hour
            ORDER BY ah.hour ASC
        """, (corp_id, days, corp_id, days))

        timezone_data = []
        for row in cur.fetchall():
            timezone_data.append({
                "hour": row['hour'],
                "kills": row['kills'],
                "deaths": row['deaths'],
                "activity": row['activity']
            })

        return timezone_data
