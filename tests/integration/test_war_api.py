# tests/integration/test_war_api.py
"""Integration tests for war API endpoints."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from main import app
    return TestClient(app)


@pytest.mark.integration
class TestWarDoctrineAPI:
    def test_get_doctrine_templates(self, client):
        response = client.get("/api/war/doctrine-templates")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 14

    def test_get_fleet_analysis_not_found(self, client):
        response = client.get("/api/war/fleet-analysis/999999999")

        assert response.status_code == 200
        assert response.json() is None

    def test_get_conflicts(self, client):
        response = client.get("/api/war/conflicts-enhanced?days=30")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


@pytest.mark.integration
class TestWarDoctrineMatchup:
    def test_get_doctrine_matchup(self, client):
        response = client.get("/api/war/doctrine-matchup/99000001/99000002")

        assert response.status_code == 200
        data = response.json()
        assert "alliance1_id" in data
        assert "alliance2_id" in data
        assert "overall_advantage" in data
