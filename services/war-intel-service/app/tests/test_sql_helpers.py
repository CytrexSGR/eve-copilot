"""Tests for SQL helper functions - string generation and pattern builders."""

import pytest
from app.routers.intelligence.corp_sql_helpers import (
    get_ship_classification_case,
    get_corp_activity_filter,
    build_performance_stats_cte,
    get_sde_joins,
    get_capital_filter,
    calculate_efficiency_sql,
    solo_kills_detection_case,
    CAPITAL_GROUPS,
)


# ============================================================================
# Ship Classification SQL CASE
# ============================================================================

class TestShipClassificationCase:
    def test_returns_string(self):
        result = get_ship_classification_case()
        assert isinstance(result, str)

    def test_starts_with_case(self):
        result = get_ship_classification_case()
        assert result.strip().startswith("CASE")

    def test_ends_with_end(self):
        result = get_ship_classification_case()
        assert result.strip().endswith("END")

    def test_contains_all_12_categories(self):
        result = get_ship_classification_case()
        categories = [
            'Frigate', 'Destroyer', 'Cruiser', 'Battlecruiser', 'Battleship',
            'Capital', 'Capsule', 'Structure', 'Industrial', 'Fighter/Drone',
            'Deployable', 'Other',
        ]
        for cat in categories:
            assert f"'{cat}'" in result or f"THEN '{cat}'" in result or f"ELSE '{cat}'" in result, f"Missing category: {cat}"

    def test_contains_key_ship_groups(self):
        """Spot-check specific ship groups are in the SQL."""
        result = get_ship_classification_case()
        for group in ['Heavy Assault Cruiser', 'Stealth Bomber', 'Marauder',
                       'Dreadnought', 'Supercarrier', 'Citadel', 'Exhumer',
                       'Expedition Command Ship', 'Mobile Phase Anchor']:
            assert group in result, f"Missing ship group: {group}"


# ============================================================================
# Corp Activity Filter
# ============================================================================

class TestCorpActivityFilter:
    def test_default_param(self):
        result = get_corp_activity_filter()
        assert "%(corp_id)s" in result
        assert "ka.corporation_id" in result
        assert "km.victim_corporation_id" in result

    def test_custom_param(self):
        result = get_corp_activity_filter("$1")
        assert "$1" in result
        assert "%(corp_id)s" not in result


# ============================================================================
# Performance Stats CTE
# ============================================================================

class TestPerformanceStatsCTE:
    def test_contains_aggregations(self):
        result = build_performance_stats_cte()
        assert "COUNT(CASE" in result
        assert "SUM(CASE" in result
        assert "kills" in result
        assert "deaths" in result
        assert "isk_killed" in result
        assert "isk_lost" in result

    def test_uses_corp_filter(self):
        result = build_performance_stats_cte()
        assert "%(corp_id)s" in result

    def test_custom_param(self):
        result = build_performance_stats_cte(":corp")
        assert ":corp" in result


# ============================================================================
# SDE Joins
# ============================================================================

class TestSDEJoins:
    def test_returns_dict(self):
        result = get_sde_joins()
        assert isinstance(result, dict)

    def test_all_join_keys(self):
        result = get_sde_joins()
        expected_keys = {'ship_type', 'ship_group', 'solar_system', 'region', 'constellation'}
        assert set(result.keys()) == expected_keys

    def test_join_syntax(self):
        result = get_sde_joins()
        for key, sql in result.items():
            assert "JOIN" in sql, f"Missing JOIN in {key}"

    def test_ship_type_references_invTypes(self):
        result = get_sde_joins()
        assert '"invTypes"' in result['ship_type']

    def test_region_references_mapRegions(self):
        result = get_sde_joins()
        assert '"mapRegions"' in result['region']


# ============================================================================
# Capital Filter
# ============================================================================

class TestCapitalFilter:
    def test_contains_all_capital_groups(self):
        result = get_capital_filter()
        for group in CAPITAL_GROUPS:
            assert f"'{group}'" in result

    def test_sql_in_clause(self):
        result = get_capital_filter()
        assert 'ig."groupName" IN' in result

    def test_capital_groups_tuple(self):
        assert 'Carrier' in CAPITAL_GROUPS
        assert 'Dreadnought' in CAPITAL_GROUPS
        assert 'Titan' in CAPITAL_GROUPS
        assert 'Supercarrier' in CAPITAL_GROUPS
        assert 'Force Auxiliary' in CAPITAL_GROUPS
        assert 'Capital Industrial Ship' in CAPITAL_GROUPS
        assert 'Jump Freighter' in CAPITAL_GROUPS
        assert 'Lancer Dreadnought' in CAPITAL_GROUPS
        assert len(CAPITAL_GROUPS) == 8


# ============================================================================
# Efficiency SQL
# ============================================================================

class TestEfficiencySQL:
    def test_default_columns(self):
        result = calculate_efficiency_sql()
        assert "kills" in result
        assert "deaths" in result
        assert "NULLIF" in result
        assert "100.0" in result

    def test_custom_columns(self):
        result = calculate_efficiency_sql("total_kills", "total_deaths")
        assert "total_kills" in result
        assert "total_deaths" in result

    def test_prevents_division_by_zero(self):
        """NULLIF should prevent division by zero."""
        result = calculate_efficiency_sql()
        assert "NULLIF" in result


# ============================================================================
# Solo Kills Detection
# ============================================================================

class TestSoloKillsDetection:
    def test_returns_sql(self):
        result = solo_kills_detection_case()
        assert isinstance(result, str)
        assert "CASE" in result
        assert "killmail_attackers" in result

    def test_threshold_5(self):
        result = solo_kills_detection_case()
        assert "<= 5" in result
