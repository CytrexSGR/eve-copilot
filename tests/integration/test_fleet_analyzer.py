# tests/integration/test_fleet_analyzer.py
"""Integration tests for fleet analyzer."""

import pytest


@pytest.mark.integration
class TestFleetAnalyzer:
    def test_analyze_killmail_no_fleet(self):
        """Solo kill should return None (no fleet detected)."""
        from src.services.doctrine.fleet_analyzer import FleetAnalyzer

        analyzer = FleetAnalyzer()
        result = analyzer.analyze_killmail(killmail_id=999999999)

        assert result is None

    def test_analyze_killmail_with_real_data(self):
        """Test with real killmail from database if available."""
        from src.services.doctrine.fleet_analyzer import FleetAnalyzer
        from src.database import get_db_connection

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT ka.killmail_id, COUNT(*) as attacker_count
                    FROM killmail_attackers ka
                    WHERE ka.alliance_id IS NOT NULL
                    GROUP BY ka.killmail_id, ka.alliance_id
                    HAVING COUNT(*) >= 5
                    ORDER BY ka.killmail_id DESC
                    LIMIT 1
                """)
                row = cur.fetchone()

        if not row:
            pytest.skip("No killmails with 5+ attackers from same alliance")

        killmail_id = row[0]
        analyzer = FleetAnalyzer()
        result = analyzer.analyze_killmail(killmail_id)

        assert result is not None
        assert result.estimated_fleet_size >= 5
        assert result.primary_alliance_id is not None

    def test_group_by_alliance(self):
        """Test grouping attackers by alliance."""
        from src.services.doctrine.fleet_analyzer import FleetAnalyzer

        analyzer = FleetAnalyzer()

        attackers = [
            {"alliance_id": 1, "ship_type_id": 100, "weapon_type_id": 200},
            {"alliance_id": 1, "ship_type_id": 100, "weapon_type_id": 200},
            {"alliance_id": 1, "ship_type_id": 100, "weapon_type_id": 200},
            {"alliance_id": 2, "ship_type_id": 101, "weapon_type_id": 201},
        ]

        alliance_groups = analyzer._group_by_alliance(attackers)

        assert 1 in alliance_groups
        assert len(alliance_groups[1]) == 3
