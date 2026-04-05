"""Trade route danger map endpoints — cached and live query versions."""

import logging
from typing import Dict, List

from fastapi import APIRouter, Query

from app.database import db_cursor
from ._helpers import get_stored_report_or_error

logger = logging.getLogger(__name__)

router = APIRouter()


# Trade hub system IDs (from route_service.py)
TRADE_HUB_SYSTEMS = {
    'jita': 30000142,
    'amarr': 30002187,
    'rens': 30002510,
    'dodixie': 30002659,
    'hek': 30002053,
}

# Major trade routes (all hub pairs)
TRADE_ROUTES = [
    ('jita', 'amarr'),
    ('jita', 'dodixie'),
    ('jita', 'rens'),
    ('jita', 'hek'),
    ('amarr', 'dodixie'),
    ('amarr', 'rens'),
    ('amarr', 'hek'),
    ('dodixie', 'rens'),
    ('dodixie', 'hek'),
    ('rens', 'hek'),
]


def _get_cached_route_systems(cur, from_hub: str, to_hub: str) -> List[Dict]:
    """
    Get pre-computed route systems from the cached trade routes report.
    Falls back to returning empty list if not available.
    """
    # Query the cached report from stored_reports table
    cur.execute("""
        SELECT report_data FROM stored_reports
        WHERE report_type = 'trade_routes'
        ORDER BY generated_at DESC
        LIMIT 1
    """)
    result = cur.fetchone()
    if not result:
        return []

    # report_data is already JSONB, no need to parse
    report = result['report_data']
    if not report:
        return []

    # Find matching route
    for route in report.get('routes', []):
        if route.get('origin_system', '').upper() == from_hub.upper() and \
           route.get('destination_system', '').upper() == to_hub.upper():
            systems = []
            for sys in route.get('systems', []):
                systems.append({
                    'system_id': sys['system_id'],
                    'system_name': sys['system_name'],
                    'security': sys['security_status']
                })
            return systems

    return []


@router.get("/trade-routes")
def get_trade_routes(
    limit: int = Query(default=5, ge=1, le=20),
    include_systems: bool = Query(default=True)
) -> Dict:
    """
    Trade Route Danger Map

    Analyzes danger levels along major HighSec trade routes between hubs.
    Shows danger scores per system based on recent kills and gate camps.

    Pre-generated every 6 hours.
    """
    report = get_stored_report_or_error('trade_routes')

    # Apply limit and include_systems filtering
    if report and 'routes' in report:
        routes = report['routes'][:limit]
        if not include_systems:
            # Remove systems array from each route
            for route in routes:
                route.pop('systems', None)
        report = {**report, 'routes': routes}

    return report


@router.get("/trade-routes/live")
def get_trade_routes_live(
    minutes: int = Query(default=1440, ge=10, le=10080, description="Time window in minutes (10-10080, max 7d)"),
    limit: int = Query(default=5, ge=1, le=20),
    include_systems: bool = Query(default=True)
) -> Dict:
    """
    Trade Route Danger Map (Live Query)

    Real-time danger analysis for trade routes based on recent kills.
    Supports variable time windows: 10m, 60m, 360m, 720m, 1440m (24h), 10080m (7d).

    Unlike the cached version, this queries the database directly.
    """
    timeframe_labels = {
        10: '10m',
        60: '1h',
        360: '6h',
        720: '12h',
        1440: '24h',
        10080: '7d'
    }
    period = timeframe_labels.get(minutes, f'{minutes}m')

    with db_cursor() as cur:
        # Get all kills in the time window along with system info and active battle
        cur.execute("""
            SELECT
                k.solar_system_id,
                s."solarSystemName" as system_name,
                s.security,
                COUNT(*) as kill_count,
                SUM(k.ship_value) as total_isk,
                SUM(CASE WHEN k.attacker_count >= 4 THEN 1 ELSE 0 END) as gate_camp_kills,
                (SELECT b.battle_id FROM battles b
                 WHERE b.solar_system_id = k.solar_system_id
                   AND b.last_kill_at >= NOW() - INTERVAL '%s minutes'
                 ORDER BY b.total_kills DESC
                 LIMIT 1) as battle_id
            FROM killmails k
            JOIN "mapSolarSystems" s ON k.solar_system_id = s."solarSystemID"
            WHERE k.killmail_time >= NOW() - INTERVAL '%s minutes'
              AND s.security >= 0.45
            GROUP BY k.solar_system_id, s."solarSystemName", s.security
        """, (minutes, minutes))

        system_stats = {}
        for row in cur.fetchall():
            system_id = row['solar_system_id']
            kill_count = row['kill_count']
            total_isk = float(row['total_isk']) if row['total_isk'] else 0
            gate_camp_kills = row['gate_camp_kills']

            # Danger score calculation (0-100)
            avg_isk = total_isk / kill_count if kill_count > 0 else 0
            gate_camp_ratio = gate_camp_kills / kill_count if kill_count > 0 else 0

            danger_score = min(40, kill_count) + \
                          min(30, int(avg_isk / 100_000_000)) + \
                          (30 if gate_camp_ratio > 0.2 else 0)

            system_stats[system_id] = {
                'system_name': row['system_name'],
                'security': float(row['security']),
                'kill_count': kill_count,
                'total_isk': total_isk,
                'danger_score': danger_score,
                'is_gate_camp': gate_camp_ratio > 0.2,
                'battle_id': row['battle_id']
            }

        routes_data = []
        total_gate_camps = 0

        for from_hub, to_hub in TRADE_ROUTES:
            # Get cached route systems (from pre-generated 24h report)
            route_systems = _get_cached_route_systems(cur, from_hub, to_hub)

            if not route_systems:
                continue

            # Analyze danger along route
            total_danger = 0
            total_kills = 0
            total_isk = 0
            route_systems_data = []

            for system in route_systems:
                system_id = system['system_id']
                stats = system_stats.get(system_id, {})

                danger = stats.get('danger_score', 0)
                kills = stats.get('kill_count', 0)
                isk = stats.get('total_isk', 0)
                is_gate_camp = stats.get('is_gate_camp', False)

                total_danger += danger
                total_kills += kills
                total_isk += isk

                if is_gate_camp:
                    total_gate_camps += 1

                route_systems_data.append({
                    'system_id': system_id,
                    'system_name': system['system_name'],
                    'security_status': system['security'],
                    'danger_score': danger,
                    'kills_24h': kills,  # Field name kept for compatibility
                    'isk_destroyed_24h': isk,
                    'is_gate_camp': is_gate_camp,
                    'battle_id': stats.get('battle_id')
                })

            avg_danger = total_danger / len(route_systems_data) if route_systems_data else 0

            route_data = {
                'origin_system': from_hub.upper(),
                'destination_system': to_hub.upper(),
                'jumps': len(route_systems_data),
                'danger_score': round(avg_danger, 1),
                'total_kills': total_kills,
                'total_isk_destroyed': total_isk,
            }

            if include_systems:
                route_data['systems'] = route_systems_data

            routes_data.append(route_data)

        # Sort by danger score descending
        routes_data.sort(key=lambda x: x['danger_score'], reverse=True)
        routes_data = routes_data[:limit]

        # Calculate global stats
        total_routes = len(routes_data)
        dangerous_count = sum(1 for r in routes_data if r['danger_score'] >= 5)
        avg_danger = sum(r['danger_score'] for r in routes_data) / total_routes if total_routes > 0 else 0

        return {
            'period': period,
            'minutes': minutes,
            'global': {
                'total_routes': total_routes,
                'dangerous_routes': dangerous_count,
                'avg_danger_score': round(avg_danger, 1),
                'gate_camps_detected': total_gate_camps
            },
            'routes': routes_data
        }
