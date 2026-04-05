"""
SQL Helper Functions for Corporation Intelligence Endpoints

Provides reusable SQL patterns and utilities to reduce code duplication
in corporations_detail.py.
"""

from typing import Dict, Any


# ============================================================================
# Ship Classification
# ============================================================================

def classify_ship_group(group_name: str) -> str:
    """
    Classify EVE ship group into broader categories.

    Args:
        group_name: EVE ship group name (e.g. "Heavy Assault Cruiser")

    Returns:
        Ship class category (Frigate, Destroyer, Cruiser, Battlecruiser, Battleship, Capital, Capsule, Structure, Industrial, Fighter/Drone, Deployable, Other)
    """
    frigates = {
        'Frigate', 'Assault Frigate', 'Interceptor', 'Covert Ops',
        'Electronic Attack Ship', 'Stealth Bomber', 'Expedition Frigate',
        'Logistics Frigate', 'Prototype Exploration Ship'
    }
    destroyers = {
        'Destroyer', 'Interdictor', 'Tactical Destroyer', 'Command Destroyer'
    }
    cruisers = {
        'Cruiser', 'Heavy Assault Cruiser', 'Strategic Cruiser', 'Recon Ship',
        'Heavy Interdiction Cruiser', 'Logistics Cruiser', 'Logistics',
        'Combat Recon Ship', 'Force Recon Ship', 'Flag Cruiser',
        'Expedition Command Ship'
    }
    battlecruisers = {
        'Battlecruiser', 'Command Ship', 'Attack Battlecruiser', 'Combat Battlecruiser'
    }
    battleships = {
        'Battleship', 'Black Ops', 'Marauder', 'Elite Battleship'
    }
    capitals = {
        'Carrier', 'Dreadnought', '♦ Dreadnought', 'Lancer Dreadnought',
        'Force Auxiliary', 'Supercarrier', 'Titan',
        'Capital Industrial Ship', 'Jump Freighter'
    }
    capsules = {
        'Capsule', 'Rookie ship', 'Shuttle', 'Corvette'
    }
    structures = {
        'Citadel', 'Engineering Complex', '♦ Engineering Complex', 'Refinery',
        'Administration Hub', 'Observatory', 'Stargate', 'Upwell Jump Gate',
        'Control Tower', 'Infrastructure Upgrades'
    }
    industrials = {
        'Mining Barge', 'Exhumer', 'Industrial', 'Transport Ship',
        'Deep Space Transport', 'Blockade Runner', 'Freighter',
        'Industrial Command Ship'
    }
    fighters_drones = {
        'Fighter', 'Fighter-Bomber', 'Light Fighter', 'Heavy Fighter',
        'Structure Fighter', 'Structure Heavy Fighter', 'Structure Light Fighter',
        'Combat Drone', 'Logistic Drone', 'Mining Drone', 'Electronic Warfare Drone'
    }
    deployables = {
        'Mobile Warp Disruptor', 'Mobile Cyno Inhibitor', 'Mobile Depot',
        'Mobile Siphon Unit', 'Mobile Scan Inhibitor', 'Mobile Micro Jump Unit',
        'Mercenary Den', 'Upwell Moon Drill', 'Upwell Cyno Jammer',
        'Upwell Cyno Beacon', 'Deployable', 'Mobile Tractor Unit', 'Skyhook',
        'Mobile Phase Anchor'
    }

    if group_name in frigates:
        return 'Frigate'
    elif group_name in destroyers:
        return 'Destroyer'
    elif group_name in cruisers:
        return 'Cruiser'
    elif group_name in battlecruisers:
        return 'Battlecruiser'
    elif group_name in battleships:
        return 'Battleship'
    elif group_name in capitals:
        return 'Capital'
    elif group_name in capsules:
        return 'Capsule'
    elif group_name in structures:
        return 'Structure'
    elif group_name in industrials:
        return 'Industrial'
    elif group_name in fighters_drones:
        return 'Fighter/Drone'
    elif group_name in deployables:
        return 'Deployable'
    else:
        return 'Other'


# ============================================================================
# SQL Pattern Builders
# ============================================================================

def get_ship_classification_case() -> str:
    """
    Returns SQL CASE statement for ship classification.

    Use this in SELECT clauses to classify ships by group.

    Returns:
        SQL CASE statement as string
    """
    return """
        CASE
            WHEN ig."groupName" IN ('Frigate', 'Assault Frigate', 'Interceptor', 'Covert Ops', 'Electronic Attack Ship', 'Stealth Bomber', 'Expedition Frigate', 'Logistics Frigate', 'Prototype Exploration Ship') THEN 'Frigate'
            WHEN ig."groupName" IN ('Destroyer', 'Interdictor', 'Tactical Destroyer', 'Command Destroyer') THEN 'Destroyer'
            WHEN ig."groupName" IN ('Cruiser', 'Heavy Assault Cruiser', 'Strategic Cruiser', 'Recon Ship', 'Heavy Interdiction Cruiser', 'Logistics Cruiser', 'Logistics', 'Combat Recon Ship', 'Force Recon Ship', 'Flag Cruiser', 'Expedition Command Ship') THEN 'Cruiser'
            WHEN ig."groupName" IN ('Battlecruiser', 'Command Ship', 'Attack Battlecruiser', 'Combat Battlecruiser') THEN 'Battlecruiser'
            WHEN ig."groupName" IN ('Battleship', 'Black Ops', 'Marauder', 'Elite Battleship') THEN 'Battleship'
            WHEN ig."groupName" IN ('Carrier', 'Dreadnought', '♦ Dreadnought', 'Lancer Dreadnought', 'Force Auxiliary', 'Supercarrier', 'Titan', 'Capital Industrial Ship', 'Jump Freighter') THEN 'Capital'
            WHEN ig."groupName" IN ('Capsule', 'Rookie ship', 'Shuttle', 'Corvette') THEN 'Capsule'
            WHEN ig."groupName" IN ('Citadel', 'Engineering Complex', '♦ Engineering Complex', 'Refinery', 'Administration Hub', 'Observatory', 'Stargate', 'Upwell Jump Gate', 'Control Tower', 'Infrastructure Upgrades') THEN 'Structure'
            WHEN ig."groupName" IN ('Mining Barge', 'Exhumer', 'Industrial', 'Transport Ship', 'Deep Space Transport', 'Blockade Runner', 'Freighter', 'Industrial Command Ship', 'Expedition Frigate') THEN 'Industrial'
            WHEN ig."groupName" IN ('Fighter', 'Fighter-Bomber', 'Light Fighter', 'Heavy Fighter', 'Structure Fighter', 'Structure Heavy Fighter', 'Structure Light Fighter', 'Combat Drone', 'Logistic Drone', 'Mining Drone', 'Electronic Warfare Drone') THEN 'Fighter/Drone'
            WHEN ig."groupName" IN ('Mobile Warp Disruptor', 'Mobile Cyno Inhibitor', 'Mobile Depot', 'Mobile Siphon Unit', 'Mobile Scan Inhibitor', 'Mobile Micro Jump Unit', 'Mercenary Den', 'Upwell Moon Drill', 'Upwell Cyno Jammer', 'Upwell Cyno Beacon', 'Deployable', 'Mobile Tractor Unit', 'Skyhook', 'Mobile Phase Anchor') THEN 'Deployable'
            ELSE 'Other'
        END
    """.strip()


def get_corp_activity_filter(corp_id_param: str = "%(corp_id)s") -> str:
    """
    Returns standard WHERE filter for corporation activity.

    Includes both kills (as attacker) and deaths (as victim).

    Args:
        corp_id_param: Parameter name for corporation ID (default: %(corp_id)s)

    Returns:
        SQL WHERE clause as string
    """
    return f"""
        (ka.corporation_id = {corp_id_param} OR km.victim_corporation_id = {corp_id_param})
    """.strip()


def build_performance_stats_cte(corp_id_param: str = "%(corp_id)s") -> str:
    """
    Returns CTE for basic performance statistics (kills, deaths, ISK).

    Usage:
        sql = f'''
            WITH corp_stats AS (
                {build_performance_stats_cte()}
            )
            SELECT * FROM corp_stats
        '''

    Args:
        corp_id_param: Parameter name for corporation ID

    Returns:
        CTE SQL as string (without WITH keyword)
    """
    return f"""
        SELECT
            COUNT(CASE WHEN ka.corporation_id = {corp_id_param} THEN 1 END) AS kills,
            COUNT(CASE WHEN km.victim_corporation_id = {corp_id_param} THEN 1 END) AS deaths,
            SUM(CASE WHEN ka.corporation_id = {corp_id_param} THEN km.ship_value ELSE 0 END) AS isk_killed,
            SUM(CASE WHEN km.victim_corporation_id = {corp_id_param} THEN km.ship_value ELSE 0 END) AS isk_lost
        FROM killmails km
        LEFT JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
        WHERE {get_corp_activity_filter(corp_id_param)}
    """.strip()


def get_sde_joins() -> Dict[str, str]:
    """
    Returns common SDE table JOINs as dict.

    Returns:
        Dictionary with JOIN clauses:
        - 'ship_type': JOIN for ship types
        - 'ship_group': JOIN for ship groups
        - 'solar_system': JOIN for solar systems
        - 'region': JOIN for regions
        - 'constellation': JOIN for constellations
    """
    return {
        'ship_type': 'JOIN "invTypes" it ON ship_type_id = it."typeID"',
        'ship_group': 'JOIN "invGroups" ig ON it."groupID" = ig."groupID"',
        'solar_system': 'JOIN "mapSolarSystems" ms ON km.solar_system_id = ms."solarSystemID"',
        'region': 'JOIN "mapRegions" mr ON ms."regionID" = mr."regionID"',
        'constellation': 'JOIN "mapConstellations" mc ON ms."constellationID" = mc."constellationID"',
    }


# ============================================================================
# Capital Ship Filters
# ============================================================================

from eve_shared.constants import CAPITAL_GROUP_NAMES as CAPITAL_GROUPS


def get_capital_filter() -> str:
    """
    Returns SQL filter for capital ships.

    Returns:
        SQL WHERE clause for capital ship groups
    """
    groups_str = ', '.join(f"'{g}'" for g in CAPITAL_GROUPS)
    return f'ig."groupName" IN ({groups_str})'


# ============================================================================
# Common Aggregations
# ============================================================================

def calculate_efficiency_sql(kills_col: str = "kills", deaths_col: str = "deaths") -> str:
    """
    Returns SQL expression for efficiency calculation.

    Args:
        kills_col: Column name for kills count
        deaths_col: Column name for deaths count

    Returns:
        SQL expression: ROUND(100.0 * kills / NULLIF(kills + deaths, 0), 1)
    """
    return f"ROUND(100.0 * {kills_col} / NULLIF({kills_col} + {deaths_col}, 0), 1)"


def solo_kills_detection_case() -> str:
    """
    Returns SQL CASE for solo/small gang kill detection.

    Detects kills with ≤5 attackers.

    Returns:
        SQL CASE statement for solo kill detection
    """
    return """
        COUNT(DISTINCT CASE
            WHEN (
                SELECT COUNT(*)
                FROM killmail_attackers ka2
                WHERE ka2.killmail_id = km.killmail_id
            ) <= 5 THEN km.killmail_id
        END)
    """.strip()
