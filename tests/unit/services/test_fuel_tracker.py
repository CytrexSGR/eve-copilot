"""Unit tests for FuelTracker subsystem."""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch
from services.war_economy.fuel_tracker import FuelTracker
from services.war_economy.models import FuelSnapshot
from services.war_economy.config import ISOTOPES


@pytest.fixture
def mock_db_pool():
    return Mock()


@pytest.fixture
def mock_market_service():
    return Mock()


@pytest.fixture
def tracker(mock_db_pool, mock_market_service):
    return FuelTracker(mock_db_pool, mock_market_service)


def test_fuel_tracker_init(tracker, mock_db_pool, mock_market_service):
    """Test FuelTracker initialization"""
    assert tracker.db_pool == mock_db_pool
    assert tracker.market == mock_market_service


def test_classify_anomaly_critical(tracker):
    """Test anomaly classification - critical (150%+)"""
    anomaly, severity = tracker._classify_anomaly(150.0)
    assert anomaly is True
    assert severity == 'critical'

    anomaly, severity = tracker._classify_anomaly(200.0)
    assert anomaly is True
    assert severity == 'critical'


def test_classify_anomaly_high(tracker):
    """Test anomaly classification - high (60-99%)"""
    anomaly, severity = tracker._classify_anomaly(60.0)
    assert anomaly is True
    assert severity == 'high'

    anomaly, severity = tracker._classify_anomaly(80.0)
    assert anomaly is True
    assert severity == 'high'

    anomaly, severity = tracker._classify_anomaly(99.0)
    assert anomaly is True
    assert severity == 'high'


def test_classify_anomaly_medium(tracker):
    """Test anomaly classification - medium (30-59%)"""
    anomaly, severity = tracker._classify_anomaly(30.0)
    assert anomaly is True
    assert severity == 'medium'

    anomaly, severity = tracker._classify_anomaly(45.0)
    assert anomaly is True
    assert severity == 'medium'

    anomaly, severity = tracker._classify_anomaly(59.0)
    assert anomaly is True
    assert severity == 'medium'


def test_classify_anomaly_low(tracker):
    """Test anomaly classification - low (15-29%)"""
    anomaly, severity = tracker._classify_anomaly(15.0)
    assert anomaly is True
    assert severity == 'low'

    anomaly, severity = tracker._classify_anomaly(20.0)
    assert anomaly is True
    assert severity == 'low'

    anomaly, severity = tracker._classify_anomaly(29.0)
    assert anomaly is True
    assert severity == 'low'


def test_classify_anomaly_normal(tracker):
    """Test anomaly classification - normal (<15%)"""
    anomaly, severity = tracker._classify_anomaly(0.0)
    assert anomaly is False
    assert severity == 'normal'

    anomaly, severity = tracker._classify_anomaly(5.0)
    assert anomaly is False
    assert severity == 'normal'

    anomaly, severity = tracker._classify_anomaly(14.9)
    assert anomaly is False
    assert severity == 'normal'


def test_classify_anomaly_negative_spike(tracker):
    """Test anomaly classification - negative spikes"""
    # Critical negative spike
    anomaly, severity = tracker._classify_anomaly(-150.0)
    assert anomaly is True
    assert severity == 'critical'

    # High negative spike
    anomaly, severity = tracker._classify_anomaly(-70.0)
    assert anomaly is True
    assert severity == 'high'

    # Medium negative spike
    anomaly, severity = tracker._classify_anomaly(-40.0)
    assert anomaly is True
    assert severity == 'medium'


@patch('services.war_economy.fuel_tracker.get_db_connection')
def test_bulk_fetch_current(mock_get_db, tracker):
    """Test bulk fetch of current market data"""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    # Mock database response
    mock_cursor.fetchall.return_value = [
        (10000002, 16272, 150000, 450.5),  # The Forge, Hydrogen
        (10000002, 16273, 120000, 500.0),  # The Forge, Helium
        (10000043, 16272, 100000, 460.0),  # Domain, Hydrogen
    ]

    mock_conn.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_get_db.return_value = mock_conn

    region_ids = [10000002, 10000043]
    type_ids = [16272, 16273]

    result = tracker._bulk_fetch_current(region_ids, type_ids)

    assert len(result) == 3
    assert result[(10000002, 16272)]['volume'] == 150000
    assert result[(10000002, 16272)]['price'] == 450.5
    assert result[(10000002, 16273)]['volume'] == 120000
    assert result[(10000043, 16272)]['volume'] == 100000


@patch('services.war_economy.fuel_tracker.get_db_connection')
def test_bulk_fetch_baselines(mock_get_db, tracker):
    """Test bulk fetch of 7-day baselines"""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    # Mock database response
    mock_cursor.fetchall.return_value = [
        (10000002, 16272, 100000, 440.0, 5000.0),  # The Forge, Hydrogen
        (10000002, 16273, 110000, 490.0, 6000.0),  # The Forge, Helium
        (10000043, 16272, 95000, 450.0, 4500.0),   # Domain, Hydrogen
    ]

    mock_conn.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_get_db.return_value = mock_conn

    region_ids = [10000002, 10000043]
    type_ids = [16272, 16273]

    result = tracker._bulk_fetch_baselines(region_ids, type_ids)

    assert len(result) == 3
    assert result[(10000002, 16272)]['volume'] == 100000
    assert result[(10000002, 16272)]['price'] == 440.0
    assert result[(10000002, 16272)]['stddev'] == 5000.0
    assert result[(10000002, 16273)]['volume'] == 110000


def test_calculate_snapshots(tracker):
    """Test snapshot calculation with anomaly detection"""
    # Use actual isotope IDs from config: Hydrogen=17889, Helium=16274, Nitrogen=17888, Oxygen=17887
    current_data = {
        (10000002, 17889): {'volume': 180000, 'price': 450.5},  # +80% spike (high) - Hydrogen
        (10000002, 16274): {'volume': 110000, 'price': 500.0},  # No anomaly - Helium
        (10000043, 17889): {'volume': 30000, 'price': 460.0},   # -70% drop (high) - Hydrogen
    }

    baselines = {
        (10000002, 17889): {'volume': 100000, 'price': 440.0, 'stddev': 5000.0},
        (10000002, 16274): {'volume': 110000, 'price': 490.0, 'stddev': 6000.0},
        (10000043, 17889): {'volume': 100000, 'price': 450.0, 'stddev': 4500.0},
    }

    region_ids = [10000002, 10000043]

    snapshots = tracker._calculate_snapshots(current_data, baselines, region_ids)

    # Should create snapshots for all regions × all isotopes (2 × 4 = 8 total)
    assert len(snapshots) == 8

    # Find the high anomaly (Hydrogen in The Forge - 80% spike)
    forge_hydrogen = next(
        s for s in snapshots
        if s.region_id == 10000002 and s.isotope_id == 17889
    )
    assert forge_hydrogen.anomaly_detected is True
    assert forge_hydrogen.severity == 'high'
    assert forge_hydrogen.volume_delta_percent == 80.0

    # Find the high drop (Hydrogen in Domain - 70% drop)
    domain_hydrogen = next(
        s for s in snapshots
        if s.region_id == 10000043 and s.isotope_id == 17889
    )
    assert domain_hydrogen.anomaly_detected is True
    assert domain_hydrogen.severity == 'high'
    assert domain_hydrogen.volume_delta_percent == -70.0

    # Find the normal one (Helium in The Forge - 0% change)
    forge_helium = next(
        s for s in snapshots
        if s.region_id == 10000002 and s.isotope_id == 16274
    )
    assert forge_helium.anomaly_detected is False
    assert forge_helium.severity == 'normal'
    assert forge_helium.volume_delta_percent == 0.0
