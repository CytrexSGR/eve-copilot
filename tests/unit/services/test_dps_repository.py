# tests/unit/services/test_dps_repository.py
"""Unit tests for DPS Repository."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from src.services.dps.repository import DPSRepository
from src.services.dps.models import WeaponAttributes, AmmoAttributes, ShipBonus


class TestDPSRepository:
    """Test DPSRepository database queries."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database connection with proper context manager."""
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.cursor.return_value.__exit__ = Mock(return_value=None)

        # Create context manager for get_db_connection
        mock_context = MagicMock()
        mock_context.__enter__ = Mock(return_value=mock_conn)
        mock_context.__exit__ = Mock(return_value=None)

        return mock_context, mock_cursor

    def test_get_weapon_attributes(self, mock_db):
        """Test fetching weapon attributes."""
        mock_context, cursor = mock_db
        cursor.fetchone.return_value = {
            'typeID': 2961,
            'typeName': '200mm Autocannon II',
            'rate_of_fire': 3000.0,
            'damage_modifier': 3.0,
            'optimal': 1200.0,
            'falloff': 8000.0,
            'tracking': 0.35
        }

        with patch('src.services.dps.repository.get_db_connection', return_value=mock_context):
            repo = DPSRepository()
            result = repo.get_weapon_attributes(2961)

        assert result is not None
        assert result.type_id == 2961
        assert result.rate_of_fire_ms == 3000.0

    def test_get_ammo_attributes(self, mock_db):
        """Test fetching ammo damage attributes."""
        mock_context, cursor = mock_db
        cursor.fetchone.return_value = {
            'typeID': 178,
            'typeName': 'EMP S',
            'em_damage': 9.0,
            'thermal_damage': 0.0,
            'kinetic_damage': 2.0,
            'explosive_damage': 0.0,
            'damage_modifier': 1.0
        }

        with patch('src.services.dps.repository.get_db_connection', return_value=mock_context):
            repo = DPSRepository()
            result = repo.get_ammo_attributes(178)

        assert result is not None
        assert result.damage.em == 9.0
        assert result.damage.kinetic == 2.0

    def test_get_ship_damage_bonuses(self, mock_db):
        """Test fetching ship damage bonuses from invTraits."""
        mock_context, cursor = mock_db
        cursor.fetchall.return_value = [
            {
                'typeID': 28710,
                'typeName': 'Golem',
                'skillID': -1,
                'skill_name': None,
                'bonus': 100.0,
                'bonusText': 'bonus to missile damage'
            }
        ]

        with patch('src.services.dps.repository.get_db_connection', return_value=mock_context):
            repo = DPSRepository()
            result = repo.get_ship_damage_bonuses(28710)

        assert len(result) == 1
        assert result[0].bonus_value == 100.0
        assert result[0].is_role_bonus == True
