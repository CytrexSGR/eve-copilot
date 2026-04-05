"""Live doctrine operations endpoint - time-filtered doctrine intelligence."""

import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Query

from app.database import db_cursor

logger = logging.getLogger(__name__)

router = APIRouter()

# Ship classes relevant for doctrine analysis (exclude non-combat)
COMBAT_CLASSES = (
    'battlecruiser', 'battleship', 'capital', 'carrier', 'cruiser',
    'destroyer', 'dreadnought', 'force_auxiliary', 'frigate',
    'logistics', 'stealth_bomber', 'supercarrier', 'titan'
)

# Ship class display names
CLASS_LABELS = {
    'battlecruiser': 'Battlecruiser',
    'battleship': 'Battleship',
    'capital': 'Capital',
    'carrier': 'Carrier',
    'cruiser': 'Cruiser',
    'destroyer': 'Destroyer',
    'dreadnought': 'Dreadnought',
    'force_auxiliary': 'Force Auxiliary',
    'frigate': 'Frigate',
    'logistics': 'Logistics',
    'stealth_bomber': 'Stealth Bomber',
    'supercarrier': 'Supercarrier',
    'titan': 'Titan',
}

# Threat level thresholds (scale with timeframe)
def get_threat_thresholds(minutes: int) -> dict:
    """Scale threat thresholds based on timeframe."""
    scale = max(minutes / 60, 1)
    return {
        'critical': int(100 * scale),
        'hot': int(40 * scale),
        'active': int(10 * scale),
    }


def _label(ship_class: str) -> str:
    return CLASS_LABELS.get(ship_class, ship_class.replace('_', ' ').title())


def _timeframe_label(minutes: int) -> str:
    if minutes >= 10080:
        return f"{minutes // 10080}W"
    if minutes >= 1440:
        return f"{minutes // 1440}D"
    if minutes >= 60:
        return f"{minutes // 60}H"
    return f"{minutes}M"


@router.get("/fingerprints/live-ops")
def get_live_ops(
    minutes: int = Query(60, ge=10, le=10080, description="Time window in minutes")
):
    """Get live doctrine operations data for the specified timeframe."""
    with db_cursor() as cur:
        summary = _query_summary(cur, minutes)
        active_doctrines = _query_active_doctrines(cur, minutes)
        hotspots = _query_hotspots(cur, minutes)
        counter_matrix = _query_counter_matrix(cur, minutes)
        trends = _query_trends(cur, minutes)
        ship_distribution = _query_ship_distribution(cur, minutes)
        efficiency_ranking = _query_efficiency_ranking(cur, minutes)
        alerts = _query_alerts(cur)

    return {
        "timeframe": {
            "minutes": minutes,
            "label": _timeframe_label(minutes),
        },
        "summary": summary,
        "active_doctrines": active_doctrines,
        "hotspots": hotspots,
        "counter_matrix": counter_matrix,
        "trends": trends,
        "ship_distribution": ship_distribution,
        "efficiency_ranking": efficiency_ranking,
        "alerts": alerts,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def _query_summary(cur, minutes: int) -> dict:
    """Hero section summary stats - uses alliance_doctrine_fingerprints."""
    # Count alliances with known doctrines that are active in timeframe
    cur.execute("""
        WITH active_alliances AS (
            SELECT DISTINCT ka.alliance_id
            FROM killmail_attackers ka
            JOIN killmails k ON ka.killmail_id = k.killmail_id
            WHERE k.killmail_time >= NOW() - INTERVAL '%s minutes'
              AND ka.alliance_id IS NOT NULL
        )
        SELECT
            COUNT(DISTINCT adf.primary_doctrine) as active_doctrines,
            COUNT(DISTINCT adf.alliance_id) as alliances_tracked
        FROM active_alliances aa
        JOIN alliance_doctrine_fingerprints adf ON aa.alliance_id = adf.alliance_id
    """, (minutes,))
    doctrine_stats = cur.fetchone()

    # General combat stats
    cur.execute("""
        SELECT
            COUNT(DISTINCT k.battle_id) FILTER (WHERE k.battle_id IS NOT NULL) as total_fleets,
            COUNT(DISTINCT k.region_id) as hot_regions,
            ROUND(AVG(k.attacker_count) FILTER (WHERE k.battle_id IS NOT NULL)) as avg_fleet_size
        FROM killmails k
        WHERE k.killmail_time >= NOW() - INTERVAL '%s minutes'
          AND k.ship_class = ANY(%s)
    """, (minutes, list(COMBAT_CLASSES)))
    combat_stats = cur.fetchone()

    # Most deployed doctrine in timeframe
    cur.execute("""
        WITH active_alliances AS (
            SELECT ka.alliance_id, COUNT(*) as ship_count
            FROM killmail_attackers ka
            JOIN killmails k ON ka.killmail_id = k.killmail_id
            WHERE k.killmail_time >= NOW() - INTERVAL '%s minutes'
              AND ka.alliance_id IS NOT NULL
            GROUP BY ka.alliance_id
        )
        SELECT adf.primary_doctrine, SUM(aa.ship_count) as total_deployed
        FROM active_alliances aa
        JOIN alliance_doctrine_fingerprints adf ON aa.alliance_id = adf.alliance_id
        WHERE adf.primary_doctrine IS NOT NULL
        GROUP BY adf.primary_doctrine
        ORDER BY total_deployed DESC
        LIMIT 1
    """, (minutes,))
    dominant = cur.fetchone()

    # Hottest region
    cur.execute("""
        SELECT srm.region_name, COUNT(*) as kills
        FROM killmails k
        JOIN system_region_map srm ON k.region_id = srm.region_id
        WHERE k.killmail_time >= NOW() - INTERVAL '%s minutes'
          AND k.ship_class = ANY(%s)
        GROUP BY srm.region_name
        ORDER BY kills DESC
        LIMIT 1
    """, (minutes, list(COMBAT_CLASSES)))
    hottest = cur.fetchone()

    # Peak hour
    cur.execute("""
        SELECT EXTRACT(HOUR FROM killmail_time)::int as hour, COUNT(*) as kills
        FROM killmails
        WHERE killmail_time >= NOW() - INTERVAL '%s minutes'
          AND ship_class = ANY(%s)
        GROUP BY hour
        ORDER BY kills DESC
        LIMIT 1
    """, (minutes, list(COMBAT_CLASSES)))
    peak = cur.fetchone()

    return {
        "active_doctrines": doctrine_stats['active_doctrines'] or 0,
        "total_fleets": combat_stats['total_fleets'] or 0,
        "alliances_active": doctrine_stats['alliances_tracked'] or 0,
        "hot_regions": combat_stats['hot_regions'] or 0,
        "dominant_doctrine": dominant['primary_doctrine'] if dominant else "None",
        "hottest_region": hottest['region_name'] if hottest else "None",
        "peak_hour": peak['hour'] if peak else 0,
        "avg_fleet_size": int(combat_stats['avg_fleet_size'] or 0),
    }


def _query_active_doctrines(cur, minutes: int) -> list:
    """Active alliances with their known doctrines and live combat stats.

    Uses alliance_doctrine_fingerprints for doctrine classification,
    killmail data for live activity in the timeframe.
    """
    cur.execute("""
        WITH live_kills AS (
            -- Kills each alliance scored in timeframe (final blow)
            SELECT
                ka.alliance_id,
                COUNT(DISTINCT ka.killmail_id) as kills,
                COALESCE(SUM(k.ship_value), 0) as isk_destroyed
            FROM killmail_attackers ka
            JOIN killmails k ON ka.killmail_id = k.killmail_id
            WHERE k.killmail_time >= NOW() - INTERVAL '%s minutes'
              AND ka.alliance_id IS NOT NULL
              AND ka.is_final_blow = true
            GROUP BY ka.alliance_id
        ),
        live_losses AS (
            -- Losses each alliance suffered in timeframe
            SELECT
                victim_alliance_id as alliance_id,
                COUNT(*) as losses,
                COALESCE(SUM(ship_value), 0) as isk_lost
            FROM killmails
            WHERE killmail_time >= NOW() - INTERVAL '%s minutes'
              AND victim_alliance_id IS NOT NULL
            GROUP BY victim_alliance_id
        ),
        live_top_ships AS (
            -- Top 3 ships used per alliance in timeframe
            SELECT
                alliance_id,
                jsonb_agg(
                    jsonb_build_object('type_name', type_name, 'uses', uses)
                    ORDER BY uses DESC
                ) as top_ships
            FROM (
                SELECT
                    ka.alliance_id,
                    it."typeName" as type_name,
                    COUNT(*) as uses,
                    ROW_NUMBER() OVER (PARTITION BY ka.alliance_id ORDER BY COUNT(*) DESC) as rn
                FROM killmail_attackers ka
                JOIN killmails k ON ka.killmail_id = k.killmail_id
                JOIN "invTypes" it ON ka.ship_type_id = it."typeID"
                JOIN "invGroups" ig ON it."groupID" = ig."groupID"
                WHERE k.killmail_time >= NOW() - INTERVAL '%s minutes'
                  AND ka.alliance_id IS NOT NULL
                  AND ig."categoryID" = 6
                  AND ig."groupID" NOT IN (29, 31, 237, 1972)
                GROUP BY ka.alliance_id, it."typeName"
            ) sub
            WHERE rn <= 3
            GROUP BY alliance_id
        )
        SELECT
            adf.alliance_id,
            adf.alliance_name,
            adf.primary_doctrine,
            adf.ship_fingerprint,
            COALESCE(lk.kills, 0) as kills,
            COALESCE(ll.losses, 0) as losses,
            COALESCE(lk.kills, 0) + COALESCE(ll.losses, 0) as activity,
            COALESCE(lk.isk_destroyed, 0) as isk_destroyed,
            COALESCE(ll.isk_lost, 0) as isk_lost,
            CASE
                WHEN COALESCE(ll.isk_lost, 0) > 0
                THEN ROUND(COALESCE(lk.isk_destroyed, 0)::numeric / ll.isk_lost, 2)
                ELSE 0
            END as isk_efficiency,
            CASE
                WHEN COALESCE(ll.losses, 0) > 0
                THEN ROUND(COALESCE(lk.kills, 0)::numeric / ll.losses, 1)
                ELSE COALESCE(lk.kills, 0)::numeric
            END as kd_ratio,
            lts.top_ships
        FROM alliance_doctrine_fingerprints adf
        JOIN live_kills lk ON adf.alliance_id = lk.alliance_id
        LEFT JOIN live_losses ll ON adf.alliance_id = ll.alliance_id
        LEFT JOIN live_top_ships lts ON adf.alliance_id = lts.alliance_id
        WHERE COALESCE(lk.kills, 0) >= 3
        ORDER BY lk.kills DESC
        LIMIT 15
    """, (minutes, minutes, minutes))

    results = []
    for row in cur.fetchall():
        kills = row['kills'] or 0
        losses = row['losses'] or 0
        total = kills + losses

        # Extract top 3 ship names from fingerprint for display
        top_ships = []
        if row['top_ships']:
            for ship in row['top_ships'][:3]:
                top_ships.append(ship.get('type_name', ''))

        results.append({
            "ship_class": row['primary_doctrine'] or 'Unknown',
            "alliance_name": row['alliance_name'],
            "alliance_id": row['alliance_id'],
            "top_ships": top_ships,
            "activity": row['activity'],
            "isk_destroyed": row['isk_destroyed'],
            "isk_lost": row['isk_lost'],
            "isk_efficiency": float(row['isk_efficiency']),
            "kills": kills,
            "losses": losses,
            "kd_ratio": float(row['kd_ratio']),
            "survival_rate": round((kills / total) * 100, 1) if total > 0 else 0,
        })
    return results


def _query_hotspots(cur, minutes: int) -> list:
    """Top regions by combat activity."""
    thresholds = get_threat_thresholds(minutes)

    cur.execute("""
        SELECT
            k.region_id,
            srm.region_name,
            COUNT(DISTINCT k.solar_system_id) as system_count,
            COUNT(DISTINCT k.battle_id) FILTER (WHERE k.battle_id IS NOT NULL) as fleet_count,
            COUNT(*) as total_kills,
            MODE() WITHIN GROUP (ORDER BY k.ship_class) as dominant_ship_class,
            MODE() WITHIN GROUP (ORDER BY k.final_blow_alliance_id)
                FILTER (WHERE k.final_blow_alliance_id IS NOT NULL) as top_alliance_id
        FROM killmails k
        JOIN system_region_map srm ON k.region_id = srm.region_id
        WHERE k.killmail_time >= NOW() - INTERVAL '%s minutes'
          AND k.ship_class = ANY(%s)
        GROUP BY k.region_id, srm.region_name
        ORDER BY total_kills DESC
        LIMIT 10
    """, (minutes, list(COMBAT_CLASSES)))

    results = []
    for row in cur.fetchall():
        kills = row['total_kills']
        if kills >= thresholds['critical']:
            threat = 'critical'
        elif kills >= thresholds['hot']:
            threat = 'hot'
        elif kills >= thresholds['active']:
            threat = 'active'
        else:
            threat = 'low'

        # Resolve alliance name
        alliance_name = None
        if row['top_alliance_id']:
            cur.execute(
                "SELECT alliance_name FROM alliance_name_cache WHERE alliance_id = %s",
                (row['top_alliance_id'],)
            )
            arow = cur.fetchone()
            alliance_name = arow['alliance_name'] if arow else None

        results.append({
            "region_id": row['region_id'],
            "region_name": row['region_name'],
            "system_count": row['system_count'],
            "fleet_count": row['fleet_count'],
            "total_kills": kills,
            "threat_level": threat,
            "dominant_ship_class": _label(row['dominant_ship_class']) if row['dominant_ship_class'] else "Mixed",
            "top_alliance_id": row['top_alliance_id'],
            "top_alliance_name": alliance_name,
        })
    return results


def _query_counter_matrix(cur, minutes: int) -> list:
    """Which ship classes are most effective against which others."""
    cur.execute("""
        WITH attacker_resolved AS (
            SELECT
                ka.killmail_id,
                CASE
                    WHEN ig."groupName" IN ('Frigate','Assault Frigate','Covert Ops','Interceptor','Electronic Attack Ship') THEN 'frigate'
                    WHEN ig."groupName" IN ('Destroyer','Interdictor','Command Destroyer') THEN 'destroyer'
                    WHEN ig."groupName" IN ('Cruiser','Heavy Assault Cruiser','Recon Ship','Strategic Cruiser',
                                            'Heavy Interdiction Cruiser','Combat Recon Ship','Force Recon Ship') THEN 'cruiser'
                    WHEN ig."groupName" IN ('Battlecruiser','Command Ship','Combat Battlecruiser','Attack Battlecruiser') THEN 'battlecruiser'
                    WHEN ig."groupName" IN ('Battleship','Marauder','Black Ops') THEN 'battleship'
                    WHEN ig."groupName" = 'Carrier' THEN 'carrier'
                    WHEN ig."groupName" = 'Dreadnought' THEN 'dreadnought'
                    WHEN ig."groupName" = 'Force Auxiliary' THEN 'force_auxiliary'
                    WHEN ig."groupName" = 'Supercarrier' THEN 'supercarrier'
                    WHEN ig."groupName" = 'Titan' THEN 'titan'
                    WHEN ig."groupName" IN ('Logistics','Logistics Frigate') THEN 'logistics'
                    WHEN ig."groupName" = 'Stealth Bomber' THEN 'stealth_bomber'
                END as attacker_class
            FROM killmail_attackers ka
            JOIN "invTypes" it ON ka.ship_type_id = it."typeID"
            JOIN "invGroups" ig ON it."groupID" = ig."groupID"
            WHERE ka.is_final_blow = true
        )
        SELECT
            ar.attacker_class,
            k.ship_class as victim_class,
            COUNT(*) as kills
        FROM attacker_resolved ar
        JOIN killmails k ON ar.killmail_id = k.killmail_id
        WHERE k.killmail_time >= NOW() - INTERVAL '%s minutes'
          AND k.ship_class = ANY(%s)
          AND ar.attacker_class = ANY(%s)
          AND k.ship_class != ar.attacker_class
        GROUP BY ar.attacker_class, k.ship_class
        HAVING COUNT(*) >= 3
        ORDER BY kills DESC
        LIMIT 30
    """, (minutes, list(COMBAT_CLASSES), list(COMBAT_CLASSES)))

    return [{
        "attacker_class": _label(row['attacker_class']),
        "victim_class": _label(row['victim_class']),
        "kills": row['kills'],
    } for row in cur.fetchall()]


def _query_trends(cur, minutes: int) -> list:
    """Compare current period with previous same-length period."""
    cur.execute("""
        WITH current_period AS (
            SELECT ship_class, COUNT(*) as activity
            FROM killmails
            WHERE killmail_time >= NOW() - INTERVAL '%s minutes'
              AND ship_class = ANY(%s)
            GROUP BY ship_class
        ),
        previous_period AS (
            SELECT ship_class, COUNT(*) as activity
            FROM killmails
            WHERE killmail_time >= NOW() - INTERVAL '%s minutes' - INTERVAL '%s minutes'
              AND killmail_time < NOW() - INTERVAL '%s minutes'
              AND ship_class = ANY(%s)
            GROUP BY ship_class
        )
        SELECT
            COALESCE(c.ship_class, p.ship_class) as ship_class,
            COALESCE(c.activity, 0) as current_activity,
            COALESCE(p.activity, 0) as previous_activity,
            CASE
                WHEN COALESCE(p.activity, 0) > 0
                THEN ROUND(((COALESCE(c.activity, 0) - p.activity)::numeric / p.activity) * 100, 1)
                WHEN COALESCE(c.activity, 0) > 0 THEN 100.0
                ELSE 0.0
            END as change_percent,
            CASE
                WHEN COALESCE(p.activity, 0) = 0 AND COALESCE(c.activity, 0) > 0 THEN 'up'
                WHEN COALESCE(c.activity, 0) > COALESCE(p.activity, 0) * 1.05 THEN 'up'
                WHEN COALESCE(c.activity, 0) < COALESCE(p.activity, 0) * 0.95 THEN 'down'
                ELSE 'stable'
            END as trend
        FROM current_period c
        FULL OUTER JOIN previous_period p ON c.ship_class = p.ship_class
        WHERE COALESCE(c.activity, 0) + COALESCE(p.activity, 0) > 0
        ORDER BY COALESCE(c.activity, 0) DESC
        LIMIT 15
    """, (minutes, list(COMBAT_CLASSES), minutes, minutes, minutes, list(COMBAT_CLASSES)))

    return [{
        "ship_class": _label(row['ship_class']),
        "current_activity": row['current_activity'],
        "previous_activity": row['previous_activity'],
        "change_percent": float(row['change_percent']),
        "trend": row['trend'],
    } for row in cur.fetchall()]


def _query_ship_distribution(cur, minutes: int) -> list:
    """Ship class breakdown by count and percentage."""
    cur.execute("""
        WITH class_counts AS (
            SELECT ship_class, COUNT(*) as count
            FROM killmails
            WHERE killmail_time >= NOW() - INTERVAL '%s minutes'
              AND ship_class = ANY(%s)
            GROUP BY ship_class
        ),
        total AS (
            SELECT SUM(count) as total FROM class_counts
        )
        SELECT
            cc.ship_class,
            cc.count,
            ROUND((cc.count::numeric / GREATEST(t.total, 1)) * 100, 1) as percent
        FROM class_counts cc
        CROSS JOIN total t
        ORDER BY cc.count DESC
        LIMIT 10
    """, (minutes, list(COMBAT_CLASSES)))

    return [{
        "ship_class": _label(row['ship_class']),
        "count": row['count'],
        "percent": float(row['percent']),
    } for row in cur.fetchall()]


def _query_efficiency_ranking(cur, minutes: int) -> dict:
    """Top 5 and bottom 3 ship classes by ISK efficiency."""
    cur.execute("""
        WITH attacker_isk AS (
            SELECT
                k.ship_class,
                COALESCE(SUM(k.ship_value), 0) as isk_destroyed,
                COUNT(DISTINCT ka.killmail_id) as kills
            FROM killmail_attackers ka
            JOIN killmails k ON ka.killmail_id = k.killmail_id
            WHERE k.killmail_time >= NOW() - INTERVAL '%s minutes'
              AND k.ship_class = ANY(%s)
            GROUP BY k.ship_class
        ),
        victim_isk AS (
            SELECT
                ship_class,
                COALESCE(SUM(ship_value), 0) as isk_lost,
                COUNT(*) as losses
            FROM killmails
            WHERE killmail_time >= NOW() - INTERVAL '%s minutes'
              AND ship_class = ANY(%s)
            GROUP BY ship_class
        ),
        combined AS (
            SELECT
                COALESCE(a.ship_class, v.ship_class) as ship_class,
                COALESCE(a.kills, 0) as kills,
                COALESCE(v.losses, 0) as losses,
                CASE
                    WHEN COALESCE(a.isk_destroyed, 0) + COALESCE(v.isk_lost, 0) > 0
                    THEN ROUND((COALESCE(a.isk_destroyed, 0)::numeric /
                          (COALESCE(a.isk_destroyed, 0) + COALESCE(v.isk_lost, 0))) * 200, 1)
                    ELSE 100.0
                END as efficiency
            FROM attacker_isk a
            FULL OUTER JOIN victim_isk v ON a.ship_class = v.ship_class
            WHERE COALESCE(a.kills, 0) + COALESCE(v.losses, 0) >= 5
        )
        SELECT ship_class, kills, losses, efficiency,
               CASE
                   WHEN kills > losses * 1.1 THEN 'up'
                   WHEN losses > kills * 1.1 THEN 'down'
                   ELSE 'stable'
               END as trend
        FROM combined
        ORDER BY efficiency DESC
    """, (minutes, list(COMBAT_CLASSES), minutes, list(COMBAT_CLASSES)))

    rows = cur.fetchall()
    top = [{
        "ship_class": _label(r['ship_class']),
        "efficiency": float(r['efficiency']),
        "kills": r['kills'],
        "losses": r['losses'],
        "trend": r['trend'],
    } for r in rows[:5]]

    bottom = [{
        "ship_class": _label(r['ship_class']),
        "efficiency": float(r['efficiency']),
        "kills": r['kills'],
        "losses": r['losses'],
        "trend": r['trend'],
    } for r in rows[-3:]] if len(rows) > 5 else []

    return {"top": top, "bottom": bottom}


def _query_alerts(cur) -> list:
    """Recent significant events (fixed 30-minute window for freshness)."""
    alerts = []

    # Large battles in last 30 minutes
    cur.execute("""
        SELECT
            b.battle_id,
            srm.region_name,
            srm.solar_system_name,
            b.total_kills,
            b.started_at
        FROM battles b
        JOIN system_region_map srm ON b.solar_system_id = srm.solar_system_id
        WHERE b.last_kill_at >= NOW() - INTERVAL '30 minutes'
          AND b.total_kills >= 20
        ORDER BY b.total_kills DESC
        LIMIT 5
    """)
    for row in cur.fetchall():
        alerts.append({
            "type": "detection",
            "message": f"Battle in {row['solar_system_name']} ({row['region_name']}): {row['total_kills']} kills",
            "timestamp": row['started_at'].isoformat() + "Z" if row['started_at'] else None,
        })

    # Doctrine spikes in last 30 minutes
    cur.execute("""
        SELECT
            k.ship_class,
            k.final_blow_alliance_id as alliance_id,
            anc.alliance_name,
            COUNT(*) as uses,
            MAX(k.killmail_time) as last_use
        FROM killmails k
        LEFT JOIN alliance_name_cache anc ON k.final_blow_alliance_id = anc.alliance_id
        WHERE k.killmail_time >= NOW() - INTERVAL '30 minutes'
          AND k.ship_class = ANY(%s)
          AND k.final_blow_alliance_id IS NOT NULL
        GROUP BY k.ship_class, k.final_blow_alliance_id, anc.alliance_name
        HAVING COUNT(*) >= 5
        ORDER BY uses DESC
        LIMIT 5
    """, (list(COMBAT_CLASSES),))
    for row in cur.fetchall():
        name = row['alliance_name'] or f"Alliance {row['alliance_id']}"
        alerts.append({
            "type": "detection",
            "message": f"{name} deploying {_label(row['ship_class'])} doctrine ({row['uses']} ships)",
            "timestamp": row['last_use'].isoformat() + "Z" if row['last_use'] else None,
        })

    # Capital/supercap sightings
    cur.execute("""
        SELECT
            k.ship_class,
            k.final_blow_alliance_id,
            anc.alliance_name,
            COUNT(*) as count,
            MAX(k.killmail_time) as last_seen
        FROM killmails k
        LEFT JOIN alliance_name_cache anc ON k.final_blow_alliance_id = anc.alliance_id
        WHERE k.killmail_time >= NOW() - INTERVAL '30 minutes'
          AND k.ship_class IN ('dreadnought', 'carrier', 'supercarrier', 'titan', 'force_auxiliary')
          AND k.final_blow_alliance_id IS NOT NULL
        GROUP BY k.ship_class, k.final_blow_alliance_id, anc.alliance_name
        HAVING COUNT(*) >= 2
        ORDER BY count DESC
        LIMIT 3
    """)
    for row in cur.fetchall():
        name = row['alliance_name'] or f"Alliance {row['final_blow_alliance_id']}"
        alerts.append({
            "type": "counter",
            "message": f"{name} fielding {row['count']}x {_label(row['ship_class'])}",
            "timestamp": row['last_seen'].isoformat() + "Z" if row['last_seen'] else None,
        })

    # Sort by timestamp descending
    alerts.sort(key=lambda a: a.get('timestamp') or '', reverse=True)
    return alerts[:10]
