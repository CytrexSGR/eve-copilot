# tests/integration/test_pi_integration.py
"""
Integration tests for PI module.

Tests the full stack: API -> Service -> Database
"""

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.mark.integration
class TestPIFormulasEndpoints:
    """Test /api/pi/formulas endpoints."""

    def test_get_all_formulas(self, client):
        """Test GET /api/pi/formulas returns schematics."""
        response = client.get("/api/pi/formulas")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 68  # All PI schematics
        # Check structure
        if data:
            assert "schematic_id" in data[0]
            assert "inputs" in data[0]
            assert "tier" in data[0]
            assert "schematic_name" in data[0]
            assert "output_type_id" in data[0]

    def test_get_formulas_by_tier_1(self, client):
        """Test filtering by tier 1 (P1 products)."""
        response = client.get("/api/pi/formulas?tier=1")
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert all(s["tier"] == 1 for s in data)

    def test_get_formulas_by_tier_4(self, client):
        """Test filtering by tier 4 (P4 products)."""
        response = client.get("/api/pi/formulas?tier=4")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 8  # 8 P4 products in EVE
        assert all(s["tier"] == 4 for s in data)

    def test_search_formulas_bacteria(self, client):
        """Test search endpoint with 'Bacteria'."""
        response = client.get("/api/pi/formulas/search?q=Bacteria")
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert any("Bacteria" in s["schematic_name"] for s in data)

    def test_search_formulas_coolant(self, client):
        """Test search for Coolant."""
        response = client.get("/api/pi/formulas/search?q=Coolant")
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert any("Coolant" in s["schematic_name"] for s in data)

    def test_search_formulas_min_length(self, client):
        """Test search rejects too short queries."""
        response = client.get("/api/pi/formulas/search?q=A")
        assert response.status_code == 422  # Validation error

    def test_get_formula_by_id(self, client):
        """Test getting single schematic."""
        # First get all to find a valid ID
        all_response = client.get("/api/pi/formulas")
        schematic_id = all_response.json()[0]["schematic_id"]

        response = client.get(f"/api/pi/formulas/{schematic_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["schematic_id"] == schematic_id
        assert "inputs" in data
        assert isinstance(data["inputs"], list)

    def test_get_formula_not_found(self, client):
        """Test 404 for non-existent schematic."""
        response = client.get("/api/pi/formulas/999999")
        assert response.status_code == 404


@pytest.mark.integration
class TestPIChainEndpoints:
    """Test /api/pi/chain endpoints."""

    def test_get_chain_for_p1_bacteria(self, client):
        """Test chain for Bacteria (P1)."""
        # Bacteria type_id = 2393
        response = client.get("/api/pi/chain/2393")
        assert response.status_code == 200
        data = response.json()
        assert data["tier"] == 1
        assert len(data["children"]) > 0
        assert data["children"][0]["tier"] == 0  # P0 input

    def test_get_chain_for_p2_coolant(self, client):
        """Test chain for Coolant (P2)."""
        # Coolant type_id = 9832
        response = client.get("/api/pi/chain/9832")
        assert response.status_code == 200
        data = response.json()
        assert data["tier"] == 2
        # P2 should have P1 inputs which have P0 inputs
        assert len(data["children"]) >= 2

    def test_get_chain_with_quantity(self, client):
        """Test chain with custom quantity."""
        response = client.get("/api/pi/chain/2393?quantity=100")
        assert response.status_code == 200
        data = response.json()
        assert data["quantity_needed"] == 100.0

    def test_get_flat_inputs_p1(self, client):
        """Test getting P0 inputs for P1 product."""
        # Bacteria (P1) type_id = 2393
        response = client.get("/api/pi/chain/2393/inputs")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        # All inputs should be P0 materials
        for item in data:
            assert "type_id" in item
            assert "type_name" in item
            assert "quantity" in item

    def test_get_flat_inputs_p2(self, client):
        """Test getting P0 inputs for P2 product."""
        # Coolant (P2) type_id = 9832
        response = client.get("/api/pi/chain/9832/inputs")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # P2 should have multiple P0 inputs
        assert len(data) >= 2

    def test_chain_not_found(self, client):
        """Test 404 for non-PI item."""
        # Tritanium type_id = 34 (not a PI product)
        response = client.get("/api/pi/chain/34")
        assert response.status_code == 404


@pytest.mark.integration
class TestPIProfitabilityEndpoints:
    """Test /api/pi/profitability endpoints."""

    def test_get_opportunities_default(self, client):
        """Test getting profitable products with default params."""
        response = client.get("/api/pi/opportunities")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_opportunities_with_limit(self, client):
        """Test limiting results."""
        response = client.get("/api/pi/opportunities?limit=10")
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 10

    def test_get_opportunities_by_tier(self, client):
        """Test filtering by tier."""
        response = client.get("/api/pi/opportunities?tier=4")
        assert response.status_code == 200
        data = response.json()
        # All results should be tier 4
        for item in data:
            assert item["tier"] == 4

    def test_get_opportunities_sorted_by_profit(self, client):
        """Test that results are sorted by profit_per_hour descending."""
        response = client.get("/api/pi/opportunities?limit=10")
        assert response.status_code == 200
        data = response.json()
        # Results should be sorted by profit_per_hour descending
        if len(data) > 1:
            for i in range(len(data) - 1):
                assert data[i]["profit_per_hour"] >= data[i + 1]["profit_per_hour"]

    def test_get_opportunities_with_min_roi(self, client):
        """Test filtering by minimum ROI."""
        response = client.get("/api/pi/opportunities?min_roi=10")
        assert response.status_code == 200
        data = response.json()
        # All results should have ROI >= 10%
        for item in data:
            assert item["roi_percent"] >= 10.0

    def test_get_profitability_single_item(self, client):
        """Test getting profitability for a specific item."""
        # Bacteria type_id = 2393
        response = client.get("/api/pi/profitability/2393")
        # May return 404 if no market prices available
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            assert "type_id" in data
            assert "profit_per_hour" in data
            assert "roi_percent" in data


@pytest.mark.integration
class TestPICharacterEndpoints:
    """Test /api/pi/characters endpoints."""

    def test_get_colonies_empty(self, client):
        """Test getting colonies for character with no data."""
        # Use a character ID that doesn't exist
        response = client.get("/api/pi/characters/999999999/colonies")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0  # No colonies for non-existent character

    def test_get_colony_detail_not_found(self, client):
        """Test 404 for non-existent colony."""
        response = client.get("/api/pi/characters/999999999/colonies/999999999")
        assert response.status_code == 404

    def test_get_summary_not_found(self, client):
        """Test 404 for character with no PI."""
        response = client.get("/api/pi/characters/999999999/summary")
        assert response.status_code == 404


@pytest.mark.integration
class TestPIServiceDirectCalls:
    """Test services directly (not via API)."""

    def test_repository_get_all_schematics(self):
        """Test PIRepository.get_all_schematics()."""
        from src.core.config import get_settings
        from src.core.database import DatabasePool
        from src.services.pi import PIRepository

        settings = get_settings()
        db = DatabasePool(settings)
        repo = PIRepository(db)

        schematics = repo.get_all_schematics()
        assert len(schematics) == 68

    def test_repository_tier_detection(self):
        """Test that tier detection works correctly."""
        from src.core.config import get_settings
        from src.core.database import DatabasePool
        from src.services.pi import PIRepository

        settings = get_settings()
        db = DatabasePool(settings)
        repo = PIRepository(db)

        schematics = repo.get_all_schematics()

        # Count schematics per tier
        tier_counts = {}
        for s in schematics:
            tier_counts[s.tier] = tier_counts.get(s.tier, 0) + 1

        # Verify tier distribution
        assert tier_counts.get(1, 0) == 15  # P1: 15 schematics
        # P2, P3, P4 counts vary but should be > 0
        assert tier_counts.get(2, 0) > 0
        assert tier_counts.get(3, 0) > 0
        assert tier_counts.get(4, 0) == 8  # P4: 8 schematics

    def test_schematic_service_chain_depth(self):
        """Test that chain calculation has correct depth."""
        from src.core.config import get_settings
        from src.core.database import DatabasePool
        from src.services.pi import PIRepository, PISchematicService

        settings = get_settings()
        db = DatabasePool(settings)
        repo = PIRepository(db)
        service = PISchematicService(repo)

        # P4 product should have depth 4 (P4 -> P3 -> P2 -> P1 -> P0)
        # Let's test with a P2 product first (Coolant = 9832)
        chain = service.get_production_chain(9832, 1)

        assert chain is not None
        assert chain.tier == 2

        # P2 children should be P1
        for child in chain.children:
            assert child.tier == 1
            # P1 children should be P0
            for grandchild in child.children:
                assert grandchild.tier == 0
