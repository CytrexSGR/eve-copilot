"""Unit tests for SupercapTimerManager."""

import pytest
from datetime import date, datetime
from unittest.mock import Mock, MagicMock, patch
from services.war_economy.supercap_manager import SupercapTimerManager
from services.war_economy.models import SupercapTimer


@pytest.fixture
def mock_db_pool():
    return Mock()


@pytest.fixture
def manager(mock_db_pool):
    return SupercapTimerManager(mock_db_pool)


def test_manager_init(manager, mock_db_pool):
    """Test manager initialization"""
    assert manager.db_pool == mock_db_pool


@patch('services.war_economy.supercap_manager.get_db_connection')
def test_add_timer(mock_get_db, manager):
    """Test adding new timer"""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = (1,)
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_get_db.return_value = mock_conn

    timer_id = manager.add_timer(
        solar_system_id=30004759,
        ship_type_id=671,
        build_start_date=date(2026, 1, 1),
        estimated_completion_date=date(2026, 1, 29),
        alliance_id=1354830081,
        confidence_level='probable'
    )

    assert timer_id == 1
    mock_cursor.execute.assert_called_once()


@patch('services.war_economy.supercap_manager.get_db_connection')
def test_get_active_timers(mock_get_db, manager):
    """Test fetching active timers"""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [
        {
            'id': 1,
            'ship_type_id': 671,
            'ship_name': 'Erebus',
            'solar_system_id': 30004759,
            'system_name': '1DQ1-A',
            'region_name': 'Delve',
            'alliance_name': 'Goonswarm Federation',
            'build_start_date': date(2026, 1, 1),
            'estimated_completion_date': date(2026, 1, 29),
            'status': 'active',
            'confidence_level': 'probable',
            'notes': None
        }
    ]
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_get_db.return_value = mock_conn

    timers = manager.get_active_timers()

    assert len(timers) == 1
    assert timers[0].ship_name == 'Erebus'
    assert timers[0].days_remaining >= 0


@patch('services.war_economy.supercap_manager.get_db_connection')
def test_update_status(mock_get_db, manager):
    """Test updating timer status"""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_get_db.return_value = mock_conn

    manager.update_status(1, 'completed')

    mock_cursor.execute.assert_called_once()
    assert 'UPDATE war_economy_supercap_timers' in mock_cursor.execute.call_args[0][0]


def test_calculate_days_remaining(manager):
    """Test days remaining calculation"""
    days, hours = manager._calculate_time_remaining(date(2026, 1, 29))

    assert days >= 0
    assert hours >= 0
