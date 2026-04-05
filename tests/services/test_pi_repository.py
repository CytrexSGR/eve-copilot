"""
Unit tests for PI Repository
Tests schematic and colony database queries
"""

from datetime import datetime
from typing import Dict, List
from unittest.mock import Mock, MagicMock

import pytest

from src.services.pi.repository import PIRepository
from src.services.pi.models import (
    PISchematic,
    PISchematicInput,
    PIColony,
    PIPin,
    PIRoute,
    PIColonyDetail,
)


@pytest.fixture
def mock_db_pool():
    """Mock DatabasePool."""
    pool = Mock()
    pool.get_connection.return_value.__enter__ = Mock()
    pool.get_connection.return_value.__exit__ = Mock(return_value=False)
    return pool


@pytest.fixture
def pi_repository(mock_db_pool):
    """Create PIRepository with mocked database pool."""
    return PIRepository(mock_db_pool)


def create_mock_connection(mock_db_pool):
    """Helper to create a mock connection with cursor."""
    mock_cursor = MagicMock()
    mock_cursor.__enter__ = Mock(return_value=mock_cursor)
    mock_cursor.__exit__ = Mock(return_value=False)

    mock_conn = MagicMock()
    mock_conn.__enter__ = Mock(return_value=mock_conn)
    mock_conn.__exit__ = Mock(return_value=False)
    mock_conn.cursor.return_value = mock_cursor

    mock_db_pool.get_connection.return_value = mock_conn

    return mock_cursor


class TestPIRepositoryInit:
    """Test PIRepository initialization"""

    def test_init_with_db_pool(self, mock_db_pool):
        """Test initialization with database pool"""
        repo = PIRepository(mock_db_pool)
        assert repo.db == mock_db_pool
        assert repo.TIER_0_INDICATOR == "Raw Resource"


class TestGetAllSchematics:
    """Test get_all_schematics method"""

    def test_get_all_schematics_returns_schematics(self, pi_repository, mock_db_pool):
        """Test that get_all_schematics returns PISchematic objects"""
        mock_cursor = create_mock_connection(mock_db_pool)

        # Schematic data
        schematics_data = [
            {
                'schematic_id': 65,
                'schematic_name': 'Bacteria',
                'cycle_time': 1800,
                'output_type_id': 2393,
                'output_name': 'Bacteria',
                'output_quantity': 20,
                'tier': 1
            }
        ]

        # Input data
        inputs_data = [
            {
                'schematic_id': 65,
                'type_id': 2073,
                'type_name': 'Microorganisms',
                'quantity': 40
            }
        ]

        mock_cursor.fetchall.side_effect = [schematics_data, inputs_data]

        result = pi_repository.get_all_schematics()

        assert len(result) == 1
        assert isinstance(result[0], PISchematic)
        assert result[0].schematic_id == 65
        assert result[0].schematic_name == 'Bacteria'
        assert result[0].cycle_time == 1800
        assert result[0].tier == 1
        assert result[0].output_type_id == 2393
        assert result[0].output_name == 'Bacteria'
        assert result[0].output_quantity == 20
        assert len(result[0].inputs) == 1
        assert result[0].inputs[0].type_id == 2073
        assert result[0].inputs[0].type_name == 'Microorganisms'
        assert result[0].inputs[0].quantity == 40

    def test_get_all_schematics_with_tier_filter(self, pi_repository, mock_db_pool):
        """Test filtering schematics by tier"""
        mock_cursor = create_mock_connection(mock_db_pool)

        # Multiple schematics with different tiers
        schematics_data = [
            {
                'schematic_id': 65,
                'schematic_name': 'Bacteria',
                'cycle_time': 1800,
                'output_type_id': 2393,
                'output_name': 'Bacteria',
                'output_quantity': 20,
                'tier': 1
            },
            {
                'schematic_id': 126,
                'schematic_name': 'Coolant',
                'cycle_time': 3600,
                'output_type_id': 9832,
                'output_name': 'Coolant',
                'output_quantity': 5,
                'tier': 2
            }
        ]

        inputs_data = [
            {'schematic_id': 65, 'type_id': 2073, 'type_name': 'Microorganisms', 'quantity': 40},
            {'schematic_id': 126, 'type_id': 2389, 'type_name': 'Electrolytes', 'quantity': 40},
            {'schematic_id': 126, 'type_id': 2390, 'type_name': 'Water', 'quantity': 40}
        ]

        mock_cursor.fetchall.side_effect = [schematics_data, inputs_data]

        # Filter for tier 2 only
        result = pi_repository.get_all_schematics(tier=2)

        assert len(result) == 1
        assert result[0].schematic_name == 'Coolant'
        assert result[0].tier == 2

    def test_get_all_schematics_empty_database(self, pi_repository, mock_db_pool):
        """Test get_all_schematics with empty database"""
        mock_cursor = create_mock_connection(mock_db_pool)
        mock_cursor.fetchall.return_value = []

        result = pi_repository.get_all_schematics()

        assert result == []


class TestGetSchematic:
    """Test get_schematic method"""

    def test_get_schematic_found(self, pi_repository, mock_db_pool):
        """Test getting a specific schematic by ID"""
        mock_cursor = create_mock_connection(mock_db_pool)

        schematic_data = {
            'schematic_id': 65,
            'schematic_name': 'Bacteria',
            'cycle_time': 1800,
            'output_type_id': 2393,
            'output_name': 'Bacteria',
            'output_quantity': 20,
            'tier': 1
        }

        inputs_data = [
            {
                'type_id': 2073,
                'type_name': 'Microorganisms',
                'quantity': 40
            }
        ]

        mock_cursor.fetchone.return_value = schematic_data
        mock_cursor.fetchall.return_value = inputs_data

        result = pi_repository.get_schematic(65)

        assert result is not None
        assert isinstance(result, PISchematic)
        assert result.schematic_id == 65
        assert result.schematic_name == 'Bacteria'
        assert len(result.inputs) == 1

    def test_get_schematic_not_found(self, pi_repository, mock_db_pool):
        """Test getting a non-existent schematic"""
        mock_cursor = create_mock_connection(mock_db_pool)
        mock_cursor.fetchone.return_value = None

        result = pi_repository.get_schematic(999999)

        assert result is None


class TestSearchSchematics:
    """Test search_schematics method"""

    def test_search_schematics_by_name(self, pi_repository, mock_db_pool):
        """Test searching schematics by name"""
        mock_cursor = create_mock_connection(mock_db_pool)

        search_results = [
            {
                'schematic_id': 65,
                'schematic_name': 'Bacteria',
                'cycle_time': 1800,
                'output_type_id': 2393,
                'output_name': 'Bacteria',
                'output_quantity': 20,
                'tier': 1
            }
        ]

        inputs_data = [
            {'schematic_id': 65, 'type_id': 2073, 'type_name': 'Microorganisms', 'quantity': 40}
        ]

        mock_cursor.fetchall.side_effect = [search_results, inputs_data]

        result = pi_repository.search_schematics("bacteria")

        assert len(result) == 1
        assert isinstance(result[0], PISchematic)
        assert result[0].schematic_name == 'Bacteria'

    def test_search_schematics_empty_result(self, pi_repository, mock_db_pool):
        """Test searching with no results"""
        mock_cursor = create_mock_connection(mock_db_pool)
        mock_cursor.fetchall.return_value = []

        result = pi_repository.search_schematics("nonexistent")

        assert result == []


class TestGetSchematicForOutput:
    """Test get_schematic_for_output method"""

    def test_get_schematic_for_output_found(self, pi_repository, mock_db_pool):
        """Test finding schematic by output type"""
        mock_cursor = create_mock_connection(mock_db_pool)

        # First call to find schematic ID
        mock_cursor.fetchone.side_effect = [
            {'schematicID': 65},  # Find schematic by output
            {  # Get schematic details
                'schematic_id': 65,
                'schematic_name': 'Bacteria',
                'cycle_time': 1800,
                'output_type_id': 2393,
                'output_name': 'Bacteria',
                'output_quantity': 20,
                'tier': 1
            }
        ]
        mock_cursor.fetchall.return_value = [
            {'type_id': 2073, 'type_name': 'Microorganisms', 'quantity': 40}
        ]

        result = pi_repository.get_schematic_for_output(2393)

        assert result is not None
        assert result.schematic_id == 65

    def test_get_schematic_for_output_not_found(self, pi_repository, mock_db_pool):
        """Test finding schematic for non-PI output"""
        mock_cursor = create_mock_connection(mock_db_pool)
        mock_cursor.fetchone.return_value = None

        result = pi_repository.get_schematic_for_output(999999)

        assert result is None


class TestGetItemTier:
    """Test get_item_tier method"""

    def test_get_item_tier_p0(self, pi_repository, mock_db_pool):
        """Test tier detection for P0 raw resource"""
        mock_cursor = create_mock_connection(mock_db_pool)
        mock_cursor.fetchone.return_value = {'groupName': 'Planet Raw Resource'}

        result = pi_repository.get_item_tier(2073)

        assert result == 0

    def test_get_item_tier_p1(self, pi_repository, mock_db_pool):
        """Test tier detection for P1 item"""
        mock_cursor = create_mock_connection(mock_db_pool)
        mock_cursor.fetchone.return_value = {'groupName': 'Planet Tier 1 Materials'}

        result = pi_repository.get_item_tier(2393)

        assert result == 1

    def test_get_item_tier_p2(self, pi_repository, mock_db_pool):
        """Test tier detection for P2 item"""
        mock_cursor = create_mock_connection(mock_db_pool)
        mock_cursor.fetchone.return_value = {'groupName': 'Planet Tier 2 Materials'}

        result = pi_repository.get_item_tier(9832)

        assert result == 2

    def test_get_item_tier_p3(self, pi_repository, mock_db_pool):
        """Test tier detection for P3 item"""
        mock_cursor = create_mock_connection(mock_db_pool)
        mock_cursor.fetchone.return_value = {'groupName': 'Planet Tier 3 Materials'}

        result = pi_repository.get_item_tier(2867)

        assert result == 3

    def test_get_item_tier_p4(self, pi_repository, mock_db_pool):
        """Test tier detection for P4 item"""
        mock_cursor = create_mock_connection(mock_db_pool)
        mock_cursor.fetchone.return_value = {'groupName': 'Planet Tier 4 Advanced'}

        result = pi_repository.get_item_tier(2876)

        assert result == 4

    def test_get_item_tier_not_found(self, pi_repository, mock_db_pool):
        """Test tier detection for unknown item"""
        mock_cursor = create_mock_connection(mock_db_pool)
        mock_cursor.fetchone.return_value = None

        result = pi_repository.get_item_tier(999999)

        assert result == 1  # Default to P1


class TestGetColonies:
    """Test get_colonies method"""

    def test_get_colonies_returns_colonies(self, pi_repository, mock_db_pool):
        """Test getting colonies for a character"""
        mock_cursor = create_mock_connection(mock_db_pool)

        colonies_data = [
            {
                'id': 1,
                'character_id': 12345,
                'planet_id': 40000001,
                'planet_type': 'temperate',
                'solar_system_id': 30000142,
                'solar_system_name': 'Jita',
                'upgrade_level': 5,
                'num_pins': 12,
                'last_update': datetime(2024, 1, 15, 10, 30, 0),
                'last_sync': datetime(2024, 1, 15, 12, 0, 0)
            }
        ]

        mock_cursor.fetchall.return_value = colonies_data

        result = pi_repository.get_colonies(12345)

        assert len(result) == 1
        assert isinstance(result[0], PIColony)
        assert result[0].id == 1
        assert result[0].character_id == 12345
        assert result[0].planet_id == 40000001
        assert result[0].planet_type == 'temperate'
        assert result[0].solar_system_name == 'Jita'
        assert result[0].upgrade_level == 5
        assert result[0].num_pins == 12

    def test_get_colonies_empty(self, pi_repository, mock_db_pool):
        """Test getting colonies for character with no colonies"""
        mock_cursor = create_mock_connection(mock_db_pool)
        mock_cursor.fetchall.return_value = []

        result = pi_repository.get_colonies(99999)

        assert result == []


class TestGetColonyDetail:
    """Test get_colony_detail method"""

    def test_get_colony_detail_found(self, pi_repository, mock_db_pool):
        """Test getting full colony details"""
        mock_cursor = create_mock_connection(mock_db_pool)

        colony_data = {
            'id': 1,
            'character_id': 12345,
            'planet_id': 40000001,
            'planet_type': 'temperate',
            'solar_system_id': 30000142,
            'solar_system_name': 'Jita',
            'upgrade_level': 5,
            'num_pins': 2,
            'last_update': datetime(2024, 1, 15, 10, 30, 0),
            'last_sync': datetime(2024, 1, 15, 12, 0, 0)
        }

        pins_data = [
            {
                'pin_id': 1001,
                'type_id': 2254,
                'type_name': 'Command Center',
                'schematic_id': None,
                'schematic_name': None,
                'product_type_id': None,
                'product_name': None,
                'expiry_time': None,
                'qty_per_cycle': None,
                'cycle_time': None,
                'latitude': 0.5,
                'longitude': 0.3
            },
            {
                'pin_id': 1002,
                'type_id': 2469,
                'type_name': 'Extractor Head',
                'schematic_id': None,
                'schematic_name': None,
                'product_type_id': 2073,
                'product_name': 'Microorganisms',
                'expiry_time': datetime(2024, 1, 20, 10, 0, 0),
                'qty_per_cycle': 100,
                'cycle_time': 900,
                'latitude': 0.6,
                'longitude': 0.4
            }
        ]

        routes_data = [
            {
                'route_id': 2001,
                'source_pin_id': 1002,
                'destination_pin_id': 1003,
                'content_type_id': 2073,
                'content_name': 'Microorganisms',
                'quantity': 100
            }
        ]

        mock_cursor.fetchone.return_value = colony_data
        mock_cursor.fetchall.side_effect = [pins_data, routes_data]

        result = pi_repository.get_colony_detail(1)

        assert result is not None
        assert isinstance(result, PIColonyDetail)
        assert result.colony.id == 1
        assert len(result.pins) == 2
        assert len(result.routes) == 1
        assert result.pins[0].type_name == 'Command Center'
        assert result.pins[1].product_name == 'Microorganisms'
        assert result.routes[0].content_name == 'Microorganisms'

    def test_get_colony_detail_not_found(self, pi_repository, mock_db_pool):
        """Test getting details for non-existent colony"""
        mock_cursor = create_mock_connection(mock_db_pool)
        mock_cursor.fetchone.return_value = None

        result = pi_repository.get_colony_detail(999999)

        assert result is None


class TestUpsertColony:
    """Test upsert_colony method"""

    def test_upsert_colony_insert(self, pi_repository, mock_db_pool):
        """Test inserting a new colony"""
        mock_cursor = create_mock_connection(mock_db_pool)
        mock_cursor.fetchone.return_value = {'id': 1}

        result = pi_repository.upsert_colony(
            character_id=12345,
            planet_id=40000001,
            planet_type='temperate',
            solar_system_id=30000142,
            upgrade_level=5,
            num_pins=12,
            last_update=datetime(2024, 1, 15, 10, 30, 0)
        )

        assert result == 1
        mock_cursor.execute.assert_called_once()

    def test_upsert_colony_update(self, pi_repository, mock_db_pool):
        """Test updating an existing colony"""
        mock_cursor = create_mock_connection(mock_db_pool)
        mock_cursor.fetchone.return_value = {'id': 1}

        # Update with different values
        result = pi_repository.upsert_colony(
            character_id=12345,
            planet_id=40000001,
            planet_type='temperate',
            solar_system_id=30000142,
            upgrade_level=5,  # Changed from previous
            num_pins=15,      # Changed from previous
            last_update=None
        )

        assert result == 1


class TestUpsertPins:
    """Test upsert_pins method"""

    def test_upsert_pins_replace(self, pi_repository, mock_db_pool):
        """Test replacing pins for a colony"""
        mock_cursor = create_mock_connection(mock_db_pool)

        pins = [
            {
                'pin_id': 1001,
                'type_id': 2254,
                'schematic_id': None,
                'latitude': 0.5,
                'longitude': 0.3,
                'install_time': None,
                'expiry_time': None,
                'last_cycle_start': None,
                'product_type_id': None,
                'qty_per_cycle': None,
                'cycle_time': None
            },
            {
                'pin_id': 1002,
                'type_id': 2469,
                'schematic_id': None,
                'latitude': 0.6,
                'longitude': 0.4,
                'install_time': None,
                'expiry_time': datetime(2024, 1, 20, 10, 0, 0),
                'last_cycle_start': datetime(2024, 1, 15, 10, 0, 0),
                'product_type_id': 2073,
                'qty_per_cycle': 100,
                'cycle_time': 900
            }
        ]

        result = pi_repository.upsert_pins(1, pins)

        assert result == 2
        # Should have DELETE + 2 INSERTs
        assert mock_cursor.execute.call_count == 3

    def test_upsert_pins_empty(self, pi_repository, mock_db_pool):
        """Test clearing all pins"""
        mock_cursor = create_mock_connection(mock_db_pool)

        result = pi_repository.upsert_pins(1, [])

        assert result == 0
        # Should only have DELETE
        mock_cursor.execute.assert_called_once()


class TestUpsertRoutes:
    """Test upsert_routes method"""

    def test_upsert_routes_replace(self, pi_repository, mock_db_pool):
        """Test replacing routes for a colony"""
        mock_cursor = create_mock_connection(mock_db_pool)

        routes = [
            {
                'route_id': 2001,
                'source_pin_id': 1002,
                'destination_pin_id': 1003,
                'content_type_id': 2073,
                'quantity': 100
            }
        ]

        result = pi_repository.upsert_routes(1, routes)

        assert result == 1
        # Should have DELETE + 1 INSERT
        assert mock_cursor.execute.call_count == 2

    def test_upsert_routes_empty(self, pi_repository, mock_db_pool):
        """Test clearing all routes"""
        mock_cursor = create_mock_connection(mock_db_pool)

        result = pi_repository.upsert_routes(1, [])

        assert result == 0
        # Should only have DELETE
        mock_cursor.execute.assert_called_once()


class TestDeleteColony:
    """Test delete_colony method"""

    def test_delete_colony_found(self, pi_repository, mock_db_pool):
        """Test deleting an existing colony"""
        mock_cursor = create_mock_connection(mock_db_pool)
        mock_cursor.fetchone.return_value = (1,)

        result = pi_repository.delete_colony(1)

        assert result is True

    def test_delete_colony_not_found(self, pi_repository, mock_db_pool):
        """Test deleting a non-existent colony"""
        mock_cursor = create_mock_connection(mock_db_pool)
        mock_cursor.fetchone.return_value = None

        result = pi_repository.delete_colony(999999)

        assert result is False


class TestPIModels:
    """Test Pydantic model behavior"""

    def test_pi_schematic_creation(self):
        """Test PISchematic model creation"""
        schematic = PISchematic(
            schematic_id=65,
            schematic_name='Bacteria',
            cycle_time=1800,
            tier=1,
            inputs=[
                PISchematicInput(type_id=2073, type_name='Microorganisms', quantity=40)
            ],
            output_type_id=2393,
            output_name='Bacteria',
            output_quantity=20
        )

        assert schematic.schematic_id == 65
        assert schematic.tier == 1
        assert len(schematic.inputs) == 1

    def test_pi_colony_with_optional_fields(self):
        """Test PIColony with optional fields"""
        colony = PIColony(
            id=1,
            character_id=12345,
            planet_id=40000001,
            planet_type='temperate',
            solar_system_id=30000142,
            upgrade_level=5,
            num_pins=12,
            last_sync=datetime.now()
        )

        assert colony.solar_system_name is None
        assert colony.last_update is None

    def test_pi_colony_detail_structure(self):
        """Test PIColonyDetail composite model"""
        colony = PIColony(
            id=1,
            character_id=12345,
            planet_id=40000001,
            planet_type='temperate',
            solar_system_id=30000142,
            upgrade_level=5,
            num_pins=1,
            last_sync=datetime.now()
        )

        pin = PIPin(
            pin_id=1001,
            type_id=2254
        )

        route = PIRoute(
            route_id=2001,
            source_pin_id=1001,
            destination_pin_id=1002,
            content_type_id=2073,
            quantity=100
        )

        detail = PIColonyDetail(
            colony=colony,
            pins=[pin],
            routes=[route]
        )

        assert detail.colony.id == 1
        assert len(detail.pins) == 1
        assert len(detail.routes) == 1
