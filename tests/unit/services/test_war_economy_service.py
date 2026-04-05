"""Unit tests for WarEconomyService."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from services.war_economy.service import WarEconomyService


@pytest.fixture
def mock_db_pool():
    return Mock()


@pytest.fixture
def mock_market_service():
    return Mock()


@pytest.fixture
def service(mock_db_pool, mock_market_service):
    return WarEconomyService(mock_db_pool, mock_market_service)


def test_service_init(service, mock_db_pool, mock_market_service):
    """Test service initialization"""
    assert service.db_pool == mock_db_pool
    assert service.market_service == mock_market_service
    assert service.fuel_tracker is not None
    assert service.supercap_manager is not None
    assert service.manipulation_detector is not None


@patch('services.war_economy.service.FuelTracker.snapshot_all')
def test_scan_fuel_markets(mock_snapshot, service):
    """Test fuel market scanning"""
    mock_snapshot.return_value = []

    result = service.scan_fuel_markets([10000002])

    assert isinstance(result, list)
    mock_snapshot.assert_called_once()


@patch('services.war_economy.service.ManipulationDetector.scan_region')
def test_scan_manipulation(mock_scan, service):
    """Test manipulation scanning"""
    mock_scan.return_value = []

    result = service.scan_manipulation(10000002)

    assert isinstance(result, list)
    mock_scan.assert_called_once()


def test_get_fuel_trends(service):
    """Test getting fuel trends"""
    with patch.object(service.fuel_tracker, 'get_trends', return_value=[]):
        result = service.get_fuel_trends(10000002, hours=24)
        assert isinstance(result, list)


def test_get_active_supercap_timers(service):
    """Test getting active timers"""
    with patch.object(service.supercap_manager, 'get_active_timers', return_value=[]):
        result = service.get_active_supercap_timers()
        assert isinstance(result, list)
