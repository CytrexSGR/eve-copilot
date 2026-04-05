"""Intelligence-related executor functions."""

import logging
import os

from ._helpers import _call_service

logger = logging.getLogger(__name__)

__all__ = [
    "run_aggregate_hourly_stats",
    "run_aggregate_corp_hourly_stats",
    "run_alliance_fingerprints",
    "run_pilot_skill_estimates",
    "run_coalition_refresh",
    "run_battle_cleanup",
    "run_battle_event_detector",
    "run_doctrine_clustering",
    "run_sov_tracker",
    "run_fw_tracker",
]


def run_aggregate_hourly_stats():
    """
    Aggregate killmails into intelligence_hourly_stats (Alliance level).

    Phase 2 aggregator that processes killmails into hourly buckets with:
    - Core stats: kills, deaths, ISK destroyed/lost
    - Ship breakdowns: ships_killed, ships_lost
    - Geographic data: systems_kills, systems_deaths
    - Enemy tracking: enemies_killed, killed_by
    - NEW Phase 2 fields: damage_types, ship_effectiveness, ewar_threats, expensive_losses

    Processes last 2 hours by default (incremental mode).
    Run every 30 minutes to keep data fresh.
    """
    logger.info("Starting aggregate_hourly_stats job (Alliance)")
    try:
        from app.jobs.aggregate_hourly_stats import run_aggregator
        result = run_aggregator(verbose=False)  # Last 2 hours by default

        if result["success"]:
            logger.info(
                f"Alliance hourly stats: {result['rows_processed']} killmails → "
                f"{result['alliances_updated']} alliance-hour buckets updated"
            )
            return True
        else:
            logger.error(f"Alliance hourly stats failed: {result.get('error')}")
            return False

    except Exception as e:
        logger.exception("Alliance hourly stats error")
        return False


def run_aggregate_corp_hourly_stats():
    """
    Aggregate killmails into corporation_hourly_stats (Corporation level).

    Phase 1 - Bottom-Up Optimization aggregator that processes killmails into hourly buckets with:
    - Core stats: kills, deaths, ISK destroyed/lost
    - Ship breakdowns: ships_killed, ships_lost
    - Geographic data: systems_kills, systems_deaths
    - Enemy tracking: enemies_killed, killed_by
    - Phase 2 fields: damage_types, ship_effectiveness, ewar_threats, expensive_losses, equipment_summary
    - Phase 3 fields: solo_kills, solo_deaths, active_pilots, engagement_distribution, solo_ratio, damage_dealt, ewar_used

    Enables Corporation endpoints to achieve 5.5s -> 0.1s (55x faster) performance.

    Processes last 2 hours by default (incremental mode).
    Run every 30 minutes to keep data fresh.
    """
    logger.info("Starting aggregate_corp_hourly_stats job (Corporation)")
    try:
        from app.jobs.aggregate_corp_hourly_stats import run_aggregator
        result = run_aggregator(verbose=False)  # Last 2 hours by default

        if result["success"]:
            logger.info(
                f"Corporation hourly stats: {result['rows_processed']} killmails → "
                f"{result['corporations_updated']} corporation-hour buckets updated"
            )
            return True
        else:
            logger.error(f"Corporation hourly stats failed: {result.get('error')}")
            return False

    except Exception as e:
        logger.exception("Corporation hourly stats error")
        return False


def run_alliance_fingerprints():
    """Build alliance doctrine fingerprints from killmail data."""
    logger.info("Starting alliance_fingerprints job")
    try:
        from app.jobs.alliance_fingerprints import refresh_alliance_fingerprints
        result = refresh_alliance_fingerprints(days=30)
        logger.info(f"Alliance fingerprints: {result['alliances_updated']} updated")
        return result["errors"] == 0
    except Exception as e:
        logger.exception(f"Alliance fingerprints error: {e}")
        return False


def run_pilot_skill_estimates():
    """Calculate minimum skillpoints for active pilots.

    Analyzes ships and modules used by pilots to determine
    minimum skillpoints required:
    - Scans killmail_attackers for ships and weapons
    - Looks up skill requirements from SDE
    - Calculates SP using training multipliers
    - Caches results in pilot_skill_estimates table

    Processes up to 5000 pilots per run (stale-first).
    """
    logger.info("Starting pilot_skill_estimates job")
    try:
        from app.jobs.pilot_skill_estimates import refresh_pilot_skill_estimates
        result = refresh_pilot_skill_estimates(days=90, limit=5000)
        if result["success"]:
            stats = result["stats"]
            logger.info(
                f"Pilot skill estimates: {stats['pilots_processed']} pilots, "
                f"{stats['pilots_with_skills']} with skills, "
                f"{stats['total_sp_calculated']:,} total SP calculated, "
                f"{stats['errors']} errors"
            )
            return stats["errors"] == 0
        else:
            logger.error(f"Pilot skill estimates failed: {result.get('error')}")
            return False
    except Exception as e:
        logger.exception(f"Pilot skill estimates error: {e}")
        return False


def run_coalition_refresh():
    """Update alliance fight relationship tables with recent data (90 days).

    Updates:
    - alliance_fight_together: Alliances that fight on the same side
    - alliance_fight_against: Alliances that fight against each other
    - alliance_activity_total: Total kills per alliance

    Uses only last 90 days to reflect current political landscape.
    """
    logger.info("Starting coalition_refresh job (fight tables update)")

    # SQL to update fight_together (alliances fighting on same side)
    # Includes time-weighted score (half-life 14 days) and recent 14-day count
    sql_together = """
    WITH distinct_pairs AS (
        SELECT DISTINCT
            LEAST(ka1.alliance_id, ka2.alliance_id) as alliance_a,
            GREATEST(ka1.alliance_id, ka2.alliance_id) as alliance_b,
            ka1.killmail_id,
            k.killmail_time
        FROM killmail_attackers ka1
        JOIN killmail_attackers ka2
            ON ka1.killmail_id = ka2.killmail_id
            AND ka1.alliance_id < ka2.alliance_id
        JOIN killmails k ON k.killmail_id = ka1.killmail_id
        WHERE ka1.alliance_id IS NOT NULL
          AND ka2.alliance_id IS NOT NULL
          AND k.killmail_time >= NOW() - INTERVAL '90 days'
    )
    INSERT INTO alliance_fight_together
        (alliance_a, alliance_b, fights_together, weighted_together, recent_together, first_seen, last_seen)
    SELECT
        alliance_a, alliance_b,
        COUNT(*) as fights_together,
        SUM(POWER(2.0, -EXTRACT(EPOCH FROM (NOW() - killmail_time)) / (14.0 * 86400))) as weighted_together,
        COUNT(*) FILTER (WHERE killmail_time >= NOW() - INTERVAL '14 days') as recent_together,
        MIN(killmail_time) as first_seen,
        MAX(killmail_time) as last_seen
    FROM distinct_pairs
    GROUP BY alliance_a, alliance_b
    HAVING COUNT(*) >= 10
    ON CONFLICT (alliance_a, alliance_b) DO UPDATE SET
        fights_together = EXCLUDED.fights_together,
        weighted_together = EXCLUDED.weighted_together,
        recent_together = EXCLUDED.recent_together,
        first_seen = LEAST(alliance_fight_together.first_seen, EXCLUDED.first_seen),
        last_seen = GREATEST(alliance_fight_together.last_seen, EXCLUDED.last_seen);
    """

    # SQL to update fight_against (alliances killing each other)
    # Includes time-weighted score (half-life 14 days) and recent 14-day count
    sql_against = """
    WITH distinct_kills AS (
        SELECT DISTINCT
            LEAST(ka.alliance_id, k.victim_alliance_id) as alliance_a,
            GREATEST(ka.alliance_id, k.victim_alliance_id) as alliance_b,
            k.killmail_id,
            k.killmail_time
        FROM killmail_attackers ka
        JOIN killmails k ON k.killmail_id = ka.killmail_id
        WHERE ka.alliance_id IS NOT NULL
          AND k.victim_alliance_id IS NOT NULL
          AND ka.alliance_id <> k.victim_alliance_id
          AND k.killmail_time >= NOW() - INTERVAL '90 days'
    )
    INSERT INTO alliance_fight_against
        (alliance_a, alliance_b, fights_against, weighted_against, recent_against, first_seen, last_seen)
    SELECT
        alliance_a, alliance_b,
        COUNT(*) as fights_against,
        SUM(POWER(2.0, -EXTRACT(EPOCH FROM (NOW() - killmail_time)) / (14.0 * 86400))) as weighted_against,
        COUNT(*) FILTER (WHERE killmail_time >= NOW() - INTERVAL '14 days') as recent_against,
        MIN(killmail_time) as first_seen,
        MAX(killmail_time) as last_seen
    FROM distinct_kills
    GROUP BY alliance_a, alliance_b
    HAVING COUNT(*) >= 5
    ON CONFLICT (alliance_a, alliance_b) DO UPDATE SET
        fights_against = EXCLUDED.fights_against,
        weighted_against = EXCLUDED.weighted_against,
        recent_against = EXCLUDED.recent_against,
        first_seen = LEAST(alliance_fight_against.first_seen, EXCLUDED.first_seen),
        last_seen = GREATEST(alliance_fight_against.last_seen, EXCLUDED.last_seen);
    """

    # SQL to update activity totals (with time-weighted kills)
    sql_activity = """
    WITH distinct_kills AS (
        SELECT DISTINCT
            ka.alliance_id,
            ka.killmail_id,
            k.killmail_time
        FROM killmail_attackers ka
        JOIN killmails k ON k.killmail_id = ka.killmail_id
        WHERE ka.alliance_id IS NOT NULL
          AND k.killmail_time >= NOW() - INTERVAL '90 days'
    )
    INSERT INTO alliance_activity_total (alliance_id, total_kills, weighted_kills, first_seen, last_seen)
    SELECT
        alliance_id,
        COUNT(*) as total_kills,
        SUM(POWER(2.0, -EXTRACT(EPOCH FROM (NOW() - killmail_time)) / (14.0 * 86400))) as weighted_kills,
        MIN(killmail_time) as first_seen,
        MAX(killmail_time) as last_seen
    FROM distinct_kills
    GROUP BY alliance_id
    ON CONFLICT (alliance_id) DO UPDATE SET
        total_kills = EXCLUDED.total_kills,
        weighted_kills = EXCLUDED.weighted_kills,
        first_seen = LEAST(alliance_activity_total.first_seen, EXCLUDED.first_seen),
        last_seen = GREATEST(alliance_activity_total.last_seen, EXCLUDED.last_seen);
    """

    try:
        import psycopg2
        conn = psycopg2.connect(
            host=os.environ.get('POSTGRES_HOST', 'eve_db'),
            port=int(os.environ.get('POSTGRES_PORT', '5432')),
            database=os.environ.get('POSTGRES_DB', 'eve_sde'),
            user=os.environ.get('POSTGRES_USER', 'eve'),
            password=os.environ.get('POSTGRES_PASSWORD', ''),
        )
        conn.autocommit = True
        cur = conn.cursor()

        # Run all three updates
        for name, sql in [("fight_together", sql_together),
                          ("fight_against", sql_against),
                          ("activity_total", sql_activity)]:
            try:
                cur.execute(sql)
                logger.info(f"Updated {name} successfully")
            except Exception as e:
                logger.error(f"Failed to update {name}: {e}")
                cur.close()
                conn.close()
                return False

        cur.close()
        conn.close()

        logger.info("Coalition fight tables refreshed successfully (90-day window)")
        return True
    except Exception as e:
        logger.exception(f"Coalition refresh error: {e}")
        return False


def run_battle_cleanup():
    """Clean up stale battles (>2h old or 0 kills) via inline SQL.

    Marks old active battles as ended and reports active battle count.
    """
    logger.info("Starting battle_cleanup job")

    sql_cleanup = """
        UPDATE battles
        SET
            status = 'ended',
            ended_at = last_kill_at,
            duration_minutes = EXTRACT(EPOCH FROM (last_kill_at - started_at)) / 60
        WHERE status = 'active'
          AND (
            last_kill_at < NOW() - INTERVAL '2 hours'
            OR total_kills = 0
          )
    """

    try:
        import psycopg2
        conn = psycopg2.connect(
            host=os.environ.get('POSTGRES_HOST', 'eve_db'),
            port=int(os.environ.get('POSTGRES_PORT', '5432')),
            database=os.environ.get('POSTGRES_DB', 'eve_sde'),
            user=os.environ.get('POSTGRES_USER', 'eve'),
            password=os.environ.get('POSTGRES_PASSWORD', ''),
        )
        conn.autocommit = False
        cur = conn.cursor()

        cur.execute(sql_cleanup)
        ended_count = cur.rowcount

        # Count remaining active battles
        cur.execute("SELECT COUNT(*) FROM battles WHERE status = 'active'")
        active_count = cur.fetchone()[0]

        conn.commit()
        cur.close()
        conn.close()

        logger.info(
            f"Battle cleanup: {ended_count} battles ended, {active_count} still active"
        )
        return True
    except Exception as e:
        logger.exception(f"Battle cleanup error: {e}")
        return False


def run_battle_event_detector():
    """Detect battle events (capital kills, hot zones, high-value kills).

    Runs every minute to scan for new battle events and store them
    in the database for real-time notification.
    """
    logger.info("Starting battle_event_detector job")
    try:
        from app.jobs.battle_event_detector import detect_battle_events
        result = detect_battle_events()
        logger.info(f"Battle event detector completed: {result}")
        return True
    except ImportError:
        # Fallback: call war-intel-service API
        try:
            import httpx
            api_url = os.environ.get('API_GATEWAY_URL', 'http://api-gateway:8000')
            response = httpx.post(f"{api_url}/api/war/events/detect", timeout=55)
            if response.status_code == 200:
                logger.info("Battle event detector completed via API")
                return True
            else:
                logger.error(f"Battle event detector API failed: HTTP {response.status_code}")
                return False
        except Exception as e:
            logger.exception(f"Battle event detector execution failed: {e}")
            return False
    except Exception as e:
        logger.exception(f"Battle event detector error: {e}")
        return False


def run_doctrine_clustering():
    """Execute doctrine clustering via monolith subprocess.

    This job has complex dependencies (DoctrineClusteringService, ItemsDeriver,
    DoctrineTemplate models) that live in the monolith, so it continues to run
    as a subprocess until those are migrated to a dedicated service.
    """
    logger.info("Starting doctrine_clustering job")
    from ._helpers import _run_python_script
    return _run_python_script("doctrine_clustering.py", timeout=300)


def run_sov_tracker():
    """Track sovereignty campaigns from ESI via war-intel-service."""
    war_intel_url = os.environ.get("WAR_INTEL_SERVICE_URL", "http://war-intel-service:8000")
    logger.info("Starting sov_tracker job")
    try:
        result = _call_service(f"{war_intel_url}/api/internal/refresh-sov-campaigns", timeout=120)
        details = result.get("details", {})
        logger.info(
            f"Sov tracker: {details.get('total_campaigns', 0)} campaigns "
            f"({details.get('new', 0)} new, {details.get('updated', 0)} updated, "
            f"{details.get('deleted', 0)} deleted)"
        )
        return result.get("status") == "completed"
    except Exception as e:
        logger.error(f"Sov tracker failed: {e}")
        return False


def run_fw_tracker():
    """Track faction warfare system status via war-intel-service."""
    war_intel_url = os.environ.get("WAR_INTEL_SERVICE_URL", "http://war-intel-service:8000")
    logger.info("Starting fw_tracker job")
    try:
        result = _call_service(f"{war_intel_url}/api/internal/refresh-fw-status", timeout=120)
        details = result.get("details", {})
        logger.info(
            f"FW tracker: {details.get('systems_updated', 0)} systems, "
            f"{details.get('hotspots', 0)} hotspots, "
            f"{details.get('snapshots_deleted', 0)} old snapshots deleted"
        )
        return result.get("status") == "completed"
    except Exception as e:
        logger.error(f"FW tracker failed: {e}")
        return False
