"""
Unit tests for PI Schematic Service
Tests production chain building and flat input calculations.
"""

from unittest.mock import Mock, MagicMock, patch

import pytest

from src.services.pi.schematic_service import PISchematicService
from src.services.pi.models import (
    PISchematic,
    PISchematicInput,
    PIChainNode,
)


@pytest.fixture
def mock_repo():
    """Create a mock PIRepository."""
    return Mock()


@pytest.fixture
def schematic_service(mock_repo):
    """Create PISchematicService with mocked repository."""
    return PISchematicService(mock_repo)


class TestPISchematicServiceInit:
    """Test PISchematicService initialization."""

    def test_init_with_repo(self, mock_repo):
        """Test initialization with repository."""
        service = PISchematicService(mock_repo)
        assert service.repo == mock_repo


class TestGetProductionChainP1:
    """Test get_production_chain for P1 products (single level)."""

    def test_chain_for_p1_product(self, schematic_service, mock_repo):
        """Test building chain for P1 product (e.g., Bacteria from Microorganisms)."""
        # P1 Bacteria (tier 1) requires P0 Microorganisms (tier 0)
        mock_repo.get_item_tier.side_effect = lambda tid: 1 if tid == 2393 else 0

        mock_repo.get_schematic_for_output.return_value = PISchematic(
            schematic_id=65,
            schematic_name="Bacteria",
            cycle_time=1800,
            tier=1,
            inputs=[PISchematicInput(type_id=2073, type_name="Microorganisms", quantity=40)],
            output_type_id=2393,
            output_name="Bacteria",
            output_quantity=20,
        )

        # Mock _get_type_name for P0 material
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=False)
        mock_cursor.fetchone.return_value = {"typeName": "Microorganisms"}
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor
        mock_repo.db.get_connection.return_value = mock_conn

        result = schematic_service.get_production_chain(2393, quantity=20)

        assert result is not None
        assert isinstance(result, PIChainNode)
        assert result.type_id == 2393
        assert result.type_name == "Bacteria"
        assert result.tier == 1
        assert result.quantity_needed == 20
        assert result.schematic_id == 65
        assert len(result.children) == 1

        # Check P0 child
        child = result.children[0]
        assert child.type_id == 2073
        assert child.type_name == "Microorganisms"
        assert child.tier == 0
        assert child.quantity_needed == 40.0  # 40 per run, 1 run needed
        assert child.children == []

    def test_chain_for_p1_multiple_quantity(self, schematic_service, mock_repo):
        """Test chain calculation with quantity multiplier."""
        mock_repo.get_item_tier.side_effect = lambda tid: 1 if tid == 2393 else 0

        mock_repo.get_schematic_for_output.return_value = PISchematic(
            schematic_id=65,
            schematic_name="Bacteria",
            cycle_time=1800,
            tier=1,
            inputs=[PISchematicInput(type_id=2073, type_name="Microorganisms", quantity=40)],
            output_type_id=2393,
            output_name="Bacteria",
            output_quantity=20,
        )

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=False)
        mock_cursor.fetchone.return_value = {"typeName": "Microorganisms"}
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor
        mock_repo.db.get_connection.return_value = mock_conn

        # Request 60 Bacteria (3 runs needed)
        result = schematic_service.get_production_chain(2393, quantity=60)

        assert result.quantity_needed == 60
        assert len(result.children) == 1
        # 3 runs * 40 input = 120 Microorganisms
        assert result.children[0].quantity_needed == 120.0


class TestGetProductionChainP2:
    """Test get_production_chain for P2 products (two levels)."""

    def test_chain_for_p2_product(self, schematic_service, mock_repo):
        """Test building chain for P2 product (e.g., Coolant)."""
        # P2 Coolant requires P1 Electrolytes and P1 Water
        # P1 Electrolytes requires P0 Ionic Solutions
        # P1 Water requires P0 Aqueous Liquids

        def mock_get_tier(type_id):
            tiers = {
                9832: 2,   # Coolant - P2
                2389: 1,   # Electrolytes - P1
                2390: 1,   # Water - P1
                2309: 0,   # Ionic Solutions - P0
                2268: 0,   # Aqueous Liquids - P0
            }
            return tiers.get(type_id, -1)

        mock_repo.get_item_tier.side_effect = mock_get_tier

        def mock_get_schematic(type_id):
            schematics = {
                9832: PISchematic(
                    schematic_id=126,
                    schematic_name="Coolant",
                    cycle_time=3600,
                    tier=2,
                    inputs=[
                        PISchematicInput(type_id=2389, type_name="Electrolytes", quantity=40),
                        PISchematicInput(type_id=2390, type_name="Water", quantity=40),
                    ],
                    output_type_id=9832,
                    output_name="Coolant",
                    output_quantity=5,
                ),
                2389: PISchematic(
                    schematic_id=100,
                    schematic_name="Electrolytes",
                    cycle_time=1800,
                    tier=1,
                    inputs=[PISchematicInput(type_id=2309, type_name="Ionic Solutions", quantity=40)],
                    output_type_id=2389,
                    output_name="Electrolytes",
                    output_quantity=20,
                ),
                2390: PISchematic(
                    schematic_id=101,
                    schematic_name="Water",
                    cycle_time=1800,
                    tier=1,
                    inputs=[PISchematicInput(type_id=2268, type_name="Aqueous Liquids", quantity=40)],
                    output_type_id=2390,
                    output_name="Water",
                    output_quantity=20,
                ),
            }
            return schematics.get(type_id)

        mock_repo.get_schematic_for_output.side_effect = mock_get_schematic

        # Mock _get_type_name for P0 materials
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=False)

        def mock_fetchone():
            # Called for P0 materials
            return {"typeName": "Mock P0 Material"}

        mock_cursor.fetchone.side_effect = [
            {"typeName": "Ionic Solutions"},
            {"typeName": "Aqueous Liquids"},
        ]
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor
        mock_repo.db.get_connection.return_value = mock_conn

        result = schematic_service.get_production_chain(9832, quantity=5)

        assert result is not None
        assert result.type_id == 9832
        assert result.type_name == "Coolant"
        assert result.tier == 2
        assert result.quantity_needed == 5
        assert result.schematic_id == 126
        assert len(result.children) == 2

        # Check P1 children
        electrolytes = result.children[0]
        assert electrolytes.type_id == 2389
        assert electrolytes.tier == 1
        assert electrolytes.quantity_needed == 40.0  # 40 input per run

        water = result.children[1]
        assert water.type_id == 2390
        assert water.tier == 1
        assert water.quantity_needed == 40.0

        # Check P0 grandchildren
        assert len(electrolytes.children) == 1
        ionic = electrolytes.children[0]
        assert ionic.type_id == 2309
        assert ionic.tier == 0
        # 40 Electrolytes needed / 20 output per run = 2 runs
        # 2 runs * 40 input = 80 Ionic Solutions
        assert ionic.quantity_needed == 80.0

        assert len(water.children) == 1
        aqueous = water.children[0]
        assert aqueous.type_id == 2268
        assert aqueous.tier == 0
        assert aqueous.quantity_needed == 80.0


class TestGetProductionChainEdgeCases:
    """Test edge cases for get_production_chain."""

    def test_chain_for_non_pi_item(self, schematic_service, mock_repo):
        """Test returns None for non-PI item."""
        mock_repo.get_item_tier.return_value = -1

        result = schematic_service.get_production_chain(999999)

        assert result is None

    def test_chain_for_p0_item(self, schematic_service, mock_repo):
        """Test chain for P0 item returns leaf node."""
        mock_repo.get_item_tier.return_value = 0

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=False)
        mock_cursor.fetchone.return_value = {"typeName": "Microorganisms"}
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor
        mock_repo.db.get_connection.return_value = mock_conn

        result = schematic_service.get_production_chain(2073, quantity=100)

        assert result is not None
        assert result.type_id == 2073
        assert result.tier == 0
        assert result.quantity_needed == 100
        assert result.children == []
        assert result.schematic_id is None

    def test_chain_no_schematic_found(self, schematic_service, mock_repo):
        """Test returns None when schematic not found for PI item."""
        mock_repo.get_item_tier.return_value = 1
        mock_repo.get_schematic_for_output.return_value = None

        result = schematic_service.get_production_chain(12345)

        assert result is None

    def test_chain_default_quantity(self, schematic_service, mock_repo):
        """Test default quantity is 1.0."""
        mock_repo.get_item_tier.return_value = 0

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=False)
        mock_cursor.fetchone.return_value = {"typeName": "Test Material"}
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor
        mock_repo.db.get_connection.return_value = mock_conn

        result = schematic_service.get_production_chain(2073)

        assert result.quantity_needed == 1.0


class TestGetFlatInputs:
    """Test get_flat_inputs method."""

    def test_flat_inputs_for_p1(self, schematic_service, mock_repo):
        """Test flat inputs for P1 product returns single P0."""
        mock_repo.get_item_tier.side_effect = lambda tid: 1 if tid == 2393 else 0

        mock_repo.get_schematic_for_output.return_value = PISchematic(
            schematic_id=65,
            schematic_name="Bacteria",
            cycle_time=1800,
            tier=1,
            inputs=[PISchematicInput(type_id=2073, type_name="Microorganisms", quantity=40)],
            output_type_id=2393,
            output_name="Bacteria",
            output_quantity=20,
        )

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=False)
        mock_cursor.fetchone.return_value = {"typeName": "Microorganisms"}
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor
        mock_repo.db.get_connection.return_value = mock_conn

        result = schematic_service.get_flat_inputs(2393, quantity=20)

        assert len(result) == 1
        assert result[0]["type_id"] == 2073
        assert result[0]["type_name"] == "Microorganisms"
        assert result[0]["quantity"] == 40.0

    def test_flat_inputs_aggregates_same_material(self, schematic_service, mock_repo):
        """Test that flat inputs aggregates quantities for same materials."""
        # Create a scenario where same P0 material is needed through different paths
        # P2 product needs 2x P1 products that both need same P0

        def mock_get_tier(type_id):
            tiers = {
                100: 2,  # P2 product
                101: 1,  # P1 product A
                102: 1,  # P1 product B
                200: 0,  # P0 material (used by both P1s)
            }
            return tiers.get(type_id, -1)

        mock_repo.get_item_tier.side_effect = mock_get_tier

        def mock_get_schematic(type_id):
            schematics = {
                100: PISchematic(
                    schematic_id=1,
                    schematic_name="P2 Product",
                    cycle_time=3600,
                    tier=2,
                    inputs=[
                        PISchematicInput(type_id=101, type_name="P1A", quantity=20),
                        PISchematicInput(type_id=102, type_name="P1B", quantity=20),
                    ],
                    output_type_id=100,
                    output_name="P2 Product",
                    output_quantity=5,
                ),
                101: PISchematic(
                    schematic_id=2,
                    schematic_name="P1A",
                    cycle_time=1800,
                    tier=1,
                    inputs=[PISchematicInput(type_id=200, type_name="Raw Material", quantity=40)],
                    output_type_id=101,
                    output_name="P1A",
                    output_quantity=20,
                ),
                102: PISchematic(
                    schematic_id=3,
                    schematic_name="P1B",
                    cycle_time=1800,
                    tier=1,
                    inputs=[PISchematicInput(type_id=200, type_name="Raw Material", quantity=40)],
                    output_type_id=102,
                    output_name="P1B",
                    output_quantity=20,
                ),
            }
            return schematics.get(type_id)

        mock_repo.get_schematic_for_output.side_effect = mock_get_schematic

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=False)
        mock_cursor.fetchone.return_value = {"typeName": "Raw Material"}
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor
        mock_repo.db.get_connection.return_value = mock_conn

        result = schematic_service.get_flat_inputs(100, quantity=5)

        # Both P1 products need 40 of the same P0 material per run
        # 20 P1A needed / 20 output = 1 run -> 40 P0
        # 20 P1B needed / 20 output = 1 run -> 40 P0
        # Total: 80 P0
        assert len(result) == 1
        assert result[0]["type_id"] == 200
        assert result[0]["quantity"] == 80.0

    def test_flat_inputs_for_non_pi(self, schematic_service, mock_repo):
        """Test flat inputs returns empty list for non-PI item."""
        mock_repo.get_item_tier.return_value = -1

        result = schematic_service.get_flat_inputs(999999)

        assert result == []

    def test_flat_inputs_for_p0(self, schematic_service, mock_repo):
        """Test flat inputs for P0 returns itself."""
        mock_repo.get_item_tier.return_value = 0

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=False)
        mock_cursor.fetchone.return_value = {"typeName": "Microorganisms"}
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor
        mock_repo.db.get_connection.return_value = mock_conn

        result = schematic_service.get_flat_inputs(2073, quantity=100)

        assert len(result) == 1
        assert result[0]["type_id"] == 2073
        assert result[0]["quantity"] == 100.0


class TestGetSchematicsByTier:
    """Test get_schematics_by_tier method."""

    def test_get_schematics_by_tier_calls_repo(self, schematic_service, mock_repo):
        """Test that get_schematics_by_tier delegates to repository."""
        mock_schematics = [
            PISchematic(
                schematic_id=65,
                schematic_name="Bacteria",
                cycle_time=1800,
                tier=1,
                inputs=[],
                output_type_id=2393,
                output_name="Bacteria",
                output_quantity=20,
            )
        ]
        mock_repo.get_all_schematics.return_value = mock_schematics

        result = schematic_service.get_schematics_by_tier(1)

        mock_repo.get_all_schematics.assert_called_once_with(tier=1)
        assert result == mock_schematics

    def test_get_schematics_by_tier_empty(self, schematic_service, mock_repo):
        """Test get_schematics_by_tier with no results."""
        mock_repo.get_all_schematics.return_value = []

        result = schematic_service.get_schematics_by_tier(4)

        assert result == []


class TestGetTypeName:
    """Test _get_type_name helper method."""

    def test_get_type_name_found(self, schematic_service, mock_repo):
        """Test getting type name from database."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=False)
        mock_cursor.fetchone.return_value = {"typeName": "Microorganisms"}
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor
        mock_repo.db.get_connection.return_value = mock_conn

        result = schematic_service._get_type_name(2073)

        assert result == "Microorganisms"

    def test_get_type_name_not_found(self, schematic_service, mock_repo):
        """Test getting type name for unknown item."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=False)
        mock_cursor.fetchone.return_value = None
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor
        mock_repo.db.get_connection.return_value = mock_conn

        result = schematic_service._get_type_name(999999)

        assert result == "Unknown"
