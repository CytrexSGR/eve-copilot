# tests/integration/test_battle_report_service.py
"""Integration tests for battle report service."""

import pytest


@pytest.mark.integration
class TestBattleReportService:
    """Tests for BattleReportService fitting analysis."""

    def test_analyze_killmail_fitting_not_found(self):
        """Test that non-existent killmail returns None."""
        from src.services.battle_report.service import BattleReportService

        service = BattleReportService()
        analysis = service.analyze_killmail_fitting(killmail_id=999999999)

        assert analysis is None

    def test_analyze_killmail_fitting_with_real_data(self):
        """Test with a real killmail from the database if available."""
        from src.services.battle_report.service import BattleReportService
        from src.database import get_db_connection

        # Find a recent killmail with items
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT km.killmail_id
                    FROM killmails km
                    WHERE EXISTS (SELECT 1 FROM killmail_items ki WHERE ki.killmail_id = km.killmail_id)
                    ORDER BY km.killmail_time DESC
                    LIMIT 1
                """)
                row = cur.fetchone()

        if not row:
            pytest.skip("No killmails with items in database")

        killmail_id = row[0]
        service = BattleReportService()
        analysis = service.analyze_killmail_fitting(killmail_id)

        assert analysis is not None
        assert analysis.killmail_id == killmail_id
        assert analysis.ship_name is not None
        assert analysis.tank_type in ["shield", "armor", "unknown"]
