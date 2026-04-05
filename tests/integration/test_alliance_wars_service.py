# tests/integration/test_alliance_wars_service.py
"""Integration tests for alliance wars service."""

import pytest


@pytest.mark.integration
class TestAllianceWarsService:
    def test_get_conflicts_returns_list(self):
        from src.services.alliance_wars.service import AllianceWarsService

        service = AllianceWarsService()
        conflicts = service.get_conflicts(days=30)

        assert isinstance(conflicts, list)

    def test_get_alliance_enemies(self):
        """Test finding who an alliance fights against."""
        from src.services.alliance_wars.service import AllianceWarsService
        from src.database import get_db_connection

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT DISTINCT ka.alliance_id
                    FROM killmail_attackers ka
                    WHERE ka.alliance_id IS NOT NULL
                    LIMIT 1
                """)
                row = cur.fetchone()

        if not row:
            pytest.skip("No alliance data in killmail_attackers")

        service = AllianceWarsService()
        enemies = service.get_alliance_enemies(alliance_id=row[0], days=30)

        assert isinstance(enemies, list)

    def test_conflict_has_required_fields(self):
        """Test conflict model has required fields."""
        from src.services.alliance_wars.service import AllianceWarsService

        service = AllianceWarsService()
        conflicts = service.get_conflicts(days=30, limit=1)

        if conflicts:
            conflict = conflicts[0]
            assert hasattr(conflict, 'alliance1_id')
            assert hasattr(conflict, 'alliance2_id')
            assert hasattr(conflict, 'kills')
