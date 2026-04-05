# tests/integration/test_doctrine_repository.py
"""Integration tests for doctrine repository."""

import pytest


@pytest.mark.integration
class TestDoctrineRepository:
    def test_get_templates_returns_seeded_doctrines(self):
        from src.services.doctrine.repository import DoctrineRepository

        repo = DoctrineRepository()
        templates = repo.get_templates()

        assert len(templates) >= 14
        ferox = next((t for t in templates if t.name == "ferox_fleet"), None)
        assert ferox is not None
        assert ferox.tank_type == "shield"

    def test_get_templates_active_only(self):
        from src.services.doctrine.repository import DoctrineRepository

        repo = DoctrineRepository()
        templates = repo.get_templates(active_only=True)

        assert all(t.is_active for t in templates)

    def test_get_alliance_doctrines_empty_for_unknown(self):
        from src.services.doctrine.repository import DoctrineRepository

        repo = DoctrineRepository()
        doctrines = repo.get_alliance_doctrines(alliance_id=999999999, days=30)

        assert doctrines == []
