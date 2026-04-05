# tests/integration/test_doctrine_service.py
"""Integration tests for doctrine service."""

import pytest


@pytest.mark.integration
class TestDoctrineService:
    def test_get_templates(self):
        from src.services.doctrine.service import DoctrineService

        service = DoctrineService()
        templates = service.get_templates()

        assert len(templates) >= 14
        assert any(t.name == "ferox_fleet" for t in templates)

    def test_detect_doctrine_for_fitting(self):
        from src.services.doctrine.service import DoctrineService
        from src.services.battle_report.models import KillmailFittingAnalysis

        service = DoctrineService()

        fitting = KillmailFittingAnalysis(
            killmail_id=1,
            ship_type_id=37480,
            ship_name="Ferox",
            tank_type="shield",
            weapon_type="railgun",
            high_slots=6,
            med_slots=5,
            low_slots=4,
            rig_slots=2
        )

        doctrine = service.detect_doctrine(fitting)

        assert doctrine is not None
        assert doctrine.name == "ferox_fleet"

    def test_analyze_fleet(self):
        from src.services.doctrine.service import DoctrineService
        from src.database import get_db_connection

        service = DoctrineService()

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT ka.killmail_id
                    FROM killmail_attackers ka
                    WHERE ka.alliance_id IS NOT NULL
                    GROUP BY ka.killmail_id
                    HAVING COUNT(*) >= 5
                    LIMIT 1
                """)
                row = cur.fetchone()

        if not row:
            pytest.skip("No killmails with 5+ attackers")

        result = service.analyze_fleet(row[0])
        # analyze_fleet groups by alliance and takes largest group
        # MIN_FLEET_SIZE is 3, so result either None or has at least 3 pilots
        assert result is None or result.estimated_fleet_size >= 3
