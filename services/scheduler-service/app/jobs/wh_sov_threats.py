"""
Wormhole SOV Threats Job

Analyzes wormhole activity in alliance sovereignty space.
Calculates threat levels, attacking alliances, regions hit, and time patterns.

Runs daily for all sov-holding alliances (only ~80 alliances).
"""

import logging
import os
from datetime import datetime
from typing import Dict, Any
from contextlib import contextmanager

import psycopg2
import psycopg2.extras
from psycopg2.extras import Json

logger = logging.getLogger(__name__)

# Database connection settings
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "eve_sde",
    "user": "eve",
    "password": os.environ.get("DB_PASSWORD", "")
}


@contextmanager
def db_cursor():
    """Database cursor context manager."""
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = True
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        yield cur
    finally:
        conn.close()


def refresh_wh_sov_threats(days: int = 30) -> Dict[str, Any]:
    """
    Refresh wormhole threat analysis for all sov-holding alliances.

    Args:
        days: Number of days to analyze (default 30)

    Returns:
        Dict with stats about the refresh operation
    """
    logger.info(f"Starting WH SOV threats refresh for last {days} days")
    start_time = datetime.now()

    stats = {
        "alliances_processed": 0,
        "alliances_with_threats": 0,
        "errors": 0
    }

    try:
        with db_cursor() as cur:
            # Get all alliances with sovereignty
            cur.execute("""
                SELECT DISTINCT alliance_id
                FROM sovereignty_map_cache
                WHERE alliance_id IS NOT NULL
            """)
            sov_alliances = [r["alliance_id"] for r in cur.fetchall()]
            logger.info(f"Found {len(sov_alliances)} alliances with sovereignty")

            for alliance_id in sov_alliances:
                stats["alliances_processed"] += 1

                try:
                    result = calculate_alliance_wh_threats(cur, alliance_id, days)

                    if result["total_kills"] > 0:
                        stats["alliances_with_threats"] += 1

                        # Upsert into wh_sov_threats
                        cur.execute("""
                            INSERT INTO wh_sov_threats (
                                alliance_id, total_wh_systems, total_kills, total_isk_destroyed,
                                critical_systems, high_systems, moderate_systems, low_systems,
                                top_attackers, top_regions, us_prime_pct, eu_prime_pct, au_prime_pct,
                                top_wh_systems, attacker_doctrines, period_days, updated_at
                            ) VALUES (
                                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW()
                            )
                            ON CONFLICT (alliance_id) DO UPDATE SET
                                total_wh_systems = EXCLUDED.total_wh_systems,
                                total_kills = EXCLUDED.total_kills,
                                total_isk_destroyed = EXCLUDED.total_isk_destroyed,
                                critical_systems = EXCLUDED.critical_systems,
                                high_systems = EXCLUDED.high_systems,
                                moderate_systems = EXCLUDED.moderate_systems,
                                low_systems = EXCLUDED.low_systems,
                                top_attackers = EXCLUDED.top_attackers,
                                top_regions = EXCLUDED.top_regions,
                                us_prime_pct = EXCLUDED.us_prime_pct,
                                eu_prime_pct = EXCLUDED.eu_prime_pct,
                                au_prime_pct = EXCLUDED.au_prime_pct,
                                top_wh_systems = EXCLUDED.top_wh_systems,
                                attacker_doctrines = EXCLUDED.attacker_doctrines,
                                period_days = EXCLUDED.period_days,
                                updated_at = NOW()
                        """, (
                            alliance_id,
                            result["total_wh_systems"],
                            result["total_kills"],
                            result["total_isk_destroyed"],
                            result["critical_systems"],
                            result["high_systems"],
                            result["moderate_systems"],
                            result["low_systems"],
                            Json(result["top_attackers"]),
                            Json(result["top_regions"]),
                            result["us_prime_pct"],
                            result["eu_prime_pct"],
                            result["au_prime_pct"],
                            Json(result["top_wh_systems"]),
                            Json(result["attacker_doctrines"]),
                            days
                        ))

                except Exception as e:
                    logger.error(f"Error processing alliance {alliance_id}: {e}")
                    stats["errors"] += 1

    except Exception as e:
        logger.exception(f"Failed to refresh WH SOV threats: {e}")
        raise

    elapsed = (datetime.now() - start_time).total_seconds()
    stats["elapsed_seconds"] = elapsed

    logger.info(
        f"WH SOV threats refresh complete: "
        f"{stats['alliances_with_threats']}/{stats['alliances_processed']} alliances with threats, "
        f"{stats['errors']} errors in {elapsed:.1f}s"
    )

    return stats


def calculate_alliance_wh_threats(cur, alliance_id: int, days: int) -> Dict[str, Any]:
    """Calculate WH threat data for a single alliance."""

    # Get total stats and threat level counts
    cur.execute("""
        WITH alliance_sov AS (
            SELECT solar_system_id FROM sovereignty_map_cache WHERE alliance_id = %s
        ),
        wh_threat AS (
            SELECT
                wr.system_id,
                COUNT(DISTINCT k.killmail_id) as kills,
                SUM(k.ship_value) as isk
            FROM killmails k
            JOIN killmail_attackers ka ON k.killmail_id = ka.killmail_id
            JOIN wormhole_residents wr ON ka.corporation_id = wr.corporation_id
            WHERE k.solar_system_id IN (SELECT solar_system_id FROM alliance_sov)
              AND k.killmail_time > NOW() - INTERVAL '%s days'
              AND wr.system_id >= 31000000 AND wr.system_id < 32000000
            GROUP BY wr.system_id
        ),
        categorized AS (
            SELECT
                CASE
                    WHEN kills >= 1000 THEN 'CRITICAL'
                    WHEN kills >= 500 THEN 'HIGH'
                    WHEN kills >= 100 THEN 'MODERATE'
                    ELSE 'LOW'
                END as threat_level,
                system_id, kills, isk
            FROM wh_threat
        )
        SELECT
            COUNT(DISTINCT system_id) as total_wh_systems,
            COALESCE(SUM(kills), 0) as total_kills,
            COALESCE(SUM(isk), 0) as total_isk,
            COUNT(*) FILTER (WHERE threat_level = 'CRITICAL') as critical_systems,
            COUNT(*) FILTER (WHERE threat_level = 'HIGH') as high_systems,
            COUNT(*) FILTER (WHERE threat_level = 'MODERATE') as moderate_systems,
            COUNT(*) FILTER (WHERE threat_level = 'LOW') as low_systems
        FROM categorized
    """, (alliance_id, days))
    summary = cur.fetchone()

    if not summary or summary["total_kills"] == 0:
        return {
            "total_wh_systems": 0,
            "total_kills": 0,
            "total_isk_destroyed": 0,
            "critical_systems": 0,
            "high_systems": 0,
            "moderate_systems": 0,
            "low_systems": 0,
            "top_attackers": [],
            "top_regions": [],
            "us_prime_pct": 0,
            "eu_prime_pct": 0,
            "au_prime_pct": 0,
            "top_wh_systems": [],
            "attacker_doctrines": []
        }

    # Get top attacking alliances
    cur.execute("""
        WITH alliance_sov AS (
            SELECT solar_system_id FROM sovereignty_map_cache WHERE alliance_id = %s
        )
        SELECT
            ka.alliance_id,
            anc.alliance_name,
            COUNT(DISTINCT wr.system_id) as wh_systems_used,
            COUNT(DISTINCT k.killmail_id) as kills,
            COALESCE(SUM(k.ship_value), 0) as isk_destroyed
        FROM killmails k
        JOIN killmail_attackers ka ON k.killmail_id = ka.killmail_id
        JOIN wormhole_residents wr ON ka.corporation_id = wr.corporation_id
        LEFT JOIN alliance_name_cache anc ON ka.alliance_id = anc.alliance_id
        WHERE k.solar_system_id IN (SELECT solar_system_id FROM alliance_sov)
          AND k.killmail_time > NOW() - INTERVAL '%s days'
          AND wr.system_id >= 31000000 AND wr.system_id < 32000000
          AND ka.alliance_id IS NOT NULL
          AND ka.alliance_id != %s
        GROUP BY ka.alliance_id, anc.alliance_name
        ORDER BY kills DESC
        LIMIT 10
    """, (alliance_id, days, alliance_id))
    top_attackers = [
        {
            "alliance_id": r["alliance_id"],
            "alliance_name": r["alliance_name"] or f"Alliance {r['alliance_id']}",
            "wh_systems": r["wh_systems_used"],
            "kills": r["kills"],
            "isk_destroyed": float(r["isk_destroyed"] or 0)
        }
        for r in cur.fetchall()
    ]

    # Get top regions hit
    cur.execute("""
        WITH alliance_sov AS (
            SELECT solar_system_id FROM sovereignty_map_cache WHERE alliance_id = %s
        )
        SELECT
            r."regionName" as region,
            COUNT(DISTINCT k.killmail_id) as kills,
            COUNT(DISTINCT k.solar_system_id) as systems_hit,
            COALESCE(SUM(k.ship_value), 0) as isk_destroyed
        FROM killmails k
        JOIN killmail_attackers ka ON k.killmail_id = ka.killmail_id
        JOIN wormhole_residents wr ON ka.corporation_id = wr.corporation_id
        JOIN "mapSolarSystems" ss ON k.solar_system_id = ss."solarSystemID"
        JOIN "mapRegions" r ON ss."regionID" = r."regionID"
        WHERE k.solar_system_id IN (SELECT solar_system_id FROM alliance_sov)
          AND k.killmail_time > NOW() - INTERVAL '%s days'
          AND wr.system_id >= 31000000 AND wr.system_id < 32000000
        GROUP BY r."regionName"
        ORDER BY kills DESC
        LIMIT 10
    """, (alliance_id, days))
    top_regions = [
        {
            "region": r["region"],
            "kills": r["kills"],
            "systems_hit": r["systems_hit"],
            "isk_destroyed": float(r["isk_destroyed"] or 0)
        }
        for r in cur.fetchall()
    ]

    # Get timezone distribution
    cur.execute("""
        WITH alliance_sov AS (
            SELECT solar_system_id FROM sovereignty_map_cache WHERE alliance_id = %s
        ),
        tz_data AS (
            SELECT
                CASE
                    WHEN EXTRACT(HOUR FROM k.killmail_time) BETWEEN 7 AND 15 THEN 'EU'
                    WHEN EXTRACT(HOUR FROM k.killmail_time) BETWEEN 16 AND 23 THEN 'US'
                    ELSE 'AU'
                END as tz,
                k.killmail_id
            FROM killmails k
            JOIN killmail_attackers ka ON k.killmail_id = ka.killmail_id
            JOIN wormhole_residents wr ON ka.corporation_id = wr.corporation_id
            WHERE k.solar_system_id IN (SELECT solar_system_id FROM alliance_sov)
              AND k.killmail_time > NOW() - INTERVAL '%s days'
              AND wr.system_id >= 31000000 AND wr.system_id < 32000000
        )
        SELECT
            ROUND(100.0 * COUNT(*) FILTER (WHERE tz = 'US') / NULLIF(COUNT(*), 0), 1) as us_pct,
            ROUND(100.0 * COUNT(*) FILTER (WHERE tz = 'EU') / NULLIF(COUNT(*), 0), 1) as eu_pct,
            ROUND(100.0 * COUNT(*) FILTER (WHERE tz = 'AU') / NULLIF(COUNT(*), 0), 1) as au_pct
        FROM tz_data
    """, (alliance_id, days))
    tz_row = cur.fetchone()

    # Get top WH systems
    cur.execute("""
        WITH alliance_sov AS (
            SELECT solar_system_id FROM sovereignty_map_cache WHERE alliance_id = %s
        )
        SELECT
            wr.system_id,
            ss."solarSystemName" as wh_name,
            COUNT(DISTINCT k.killmail_id) as kills,
            COUNT(DISTINCT k.solar_system_id) as sov_systems_hit,
            COALESCE(SUM(k.ship_value), 0) as isk_destroyed
        FROM killmails k
        JOIN killmail_attackers ka ON k.killmail_id = ka.killmail_id
        JOIN wormhole_residents wr ON ka.corporation_id = wr.corporation_id
        JOIN "mapSolarSystems" ss ON wr.system_id = ss."solarSystemID"
        WHERE k.solar_system_id IN (SELECT solar_system_id FROM alliance_sov)
          AND k.killmail_time > NOW() - INTERVAL '%s days'
          AND wr.system_id >= 31000000 AND wr.system_id < 32000000
        GROUP BY wr.system_id, ss."solarSystemName"
        ORDER BY kills DESC
        LIMIT 15
    """, (alliance_id, days))
    top_wh_systems = [
        {
            "system_id": r["system_id"],
            "system_name": r["wh_name"],
            "kills": r["kills"],
            "sov_systems_hit": r["sov_systems_hit"],
            "isk_destroyed": float(r["isk_destroyed"] or 0)
        }
        for r in cur.fetchall()
    ]

    # Get attacker doctrines (ship classes used)
    cur.execute("""
        WITH alliance_sov AS (
            SELECT solar_system_id FROM sovereignty_map_cache WHERE alliance_id = %s
        )
        SELECT
            g."groupName" as ship_class,
            COUNT(*) as uses
        FROM killmails k
        JOIN killmail_attackers ka ON k.killmail_id = ka.killmail_id
        JOIN wormhole_residents wr ON ka.corporation_id = wr.corporation_id
        LEFT JOIN "invTypes" t ON ka.ship_type_id = t."typeID"
        LEFT JOIN "invGroups" g ON t."groupID" = g."groupID"
        WHERE k.solar_system_id IN (SELECT solar_system_id FROM alliance_sov)
          AND k.killmail_time > NOW() - INTERVAL '%s days'
          AND wr.system_id >= 31000000 AND wr.system_id < 32000000
          AND ka.ship_type_id IS NOT NULL
          AND g."groupID" NOT IN (29, 31)
        GROUP BY g."groupName"
        ORDER BY uses DESC
        LIMIT 10
    """, (alliance_id, days))
    attacker_doctrines = [
        {"ship_class": r["ship_class"], "uses": r["uses"]}
        for r in cur.fetchall()
    ]

    return {
        "total_wh_systems": summary["total_wh_systems"] or 0,
        "total_kills": summary["total_kills"] or 0,
        "total_isk_destroyed": float(summary["total_isk"] or 0),
        "critical_systems": summary["critical_systems"] or 0,
        "high_systems": summary["high_systems"] or 0,
        "moderate_systems": summary["moderate_systems"] or 0,
        "low_systems": summary["low_systems"] or 0,
        "top_attackers": top_attackers,
        "top_regions": top_regions,
        "us_prime_pct": float(tz_row["us_pct"] or 0) if tz_row else 0,
        "eu_prime_pct": float(tz_row["eu_pct"] or 0) if tz_row else 0,
        "au_prime_pct": float(tz_row["au_pct"] or 0) if tz_row else 0,
        "top_wh_systems": top_wh_systems,
        "attacker_doctrines": attacker_doctrines
    }


if __name__ == "__main__":
    # Allow running directly for testing
    logging.basicConfig(level=logging.INFO)
    result = refresh_wh_sov_threats(30)
    print(result)
