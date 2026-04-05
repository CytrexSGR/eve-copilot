"""
Unit tests for War Economy data models.
"""

import pytest
from datetime import datetime, date
from services.war_economy.models import FuelSnapshot, SupercapTimer, ManipulationAlert


def test_fuel_snapshot_creation():
    """Test FuelSnapshot dataclass creation"""
    snapshot = FuelSnapshot(
        isotope_type='Hydrogen',
        isotope_id=16272,
        region_id=10000002,
        region_name='The Forge',
        current_volume=150000,
        baseline_volume=100000,
        volume_delta_percent=50.0,
        average_price=450.5,
        anomaly_detected=True,
        severity='medium',
        timestamp=datetime(2026, 1, 14, 12, 0, 0)
    )

    assert snapshot.isotope_type == 'Hydrogen'
    assert snapshot.anomaly_detected is True
    assert snapshot.severity == 'medium'


def test_fuel_snapshot_to_dict():
    """Test FuelSnapshot conversion to dict"""
    snapshot = FuelSnapshot(
        isotope_type='Helium',
        isotope_id=16273,
        region_id=10000043,
        region_name='Domain',
        current_volume=200000,
        baseline_volume=100000,
        volume_delta_percent=100.0,
        average_price=500.0,
        anomaly_detected=True,
        severity='critical',
        timestamp=datetime(2026, 1, 14, 12, 0, 0)
    )

    result = snapshot.to_dict()

    assert result['isotope_type'] == 'Helium'
    assert result['timestamp'] == '2026-01-14T12:00:00'
    assert 'alert_message' in result
    assert 'CRITICAL' in result['alert_message']


def test_fuel_snapshot_alert_message():
    """Test alert message generation"""
    snapshot = FuelSnapshot(
        isotope_type='Nitrogen',
        isotope_id=16274,
        region_id=10000002,
        region_name='The Forge',
        current_volume=50000,
        baseline_volume=100000,
        volume_delta_percent=-50.0,
        average_price=400.0,
        anomaly_detected=True,
        severity='high',
        timestamp=datetime.utcnow()
    )

    message = snapshot._get_alert_message()

    assert 'HIGH' in message
    assert '50.0%' in message
    assert 'drop' in message
    assert 'Nitrogen' in message


def test_supercap_timer_creation():
    """Test SupercapTimer dataclass creation"""
    timer = SupercapTimer(
        id=1,
        ship_type_id=671,
        ship_name='Erebus',
        solar_system_id=30004759,
        system_name='1DQ1-A',
        region_name='Delve',
        alliance_name='Goonswarm Federation',
        build_start_date=date(2026, 1, 1),
        estimated_completion=date(2026, 1, 29),
        days_remaining=15,
        hours_remaining=360,
        status='active',
        confidence_level='probable',
        notes='Spotted via structure scan'
    )

    assert timer.ship_name == 'Erebus'
    assert timer.days_remaining == 15
    assert timer.status == 'active'


def test_supercap_timer_strike_window():
    """Test strike window calculation"""
    # Critical window (3 days)
    timer_urgent = SupercapTimer(
        id=1, ship_type_id=671, ship_name='Erebus',
        solar_system_id=30004759, system_name='1DQ1-A', region_name='Delve',
        alliance_name='Test', build_start_date=date(2026, 1, 1),
        estimated_completion=date(2026, 1, 29), days_remaining=2, hours_remaining=48,
        status='active', confidence_level='confirmed', notes=None
    )

    assert 'URGENT' in timer_urgent._get_strike_window()
    assert timer_urgent._get_alert_level() == 'critical'

    # Medium window (14 days)
    timer_medium = SupercapTimer(
        id=2, ship_type_id=671, ship_name='Erebus',
        solar_system_id=30004759, system_name='1DQ1-A', region_name='Delve',
        alliance_name='Test', build_start_date=date(2026, 1, 1),
        estimated_completion=date(2026, 1, 29), days_remaining=10, hours_remaining=240,
        status='active', confidence_level='probable', notes=None
    )

    assert 'MEDIUM' in timer_medium._get_strike_window()
    assert timer_medium._get_alert_level() == 'medium'


def test_manipulation_alert_creation():
    """Test ManipulationAlert dataclass creation"""
    alert = ManipulationAlert(
        type_id=37615,
        type_name='Interdiction Nullifier',
        region_id=10000043,
        region_name='Domain',
        current_price=15000000,
        baseline_price=5000000,
        price_change_percent=200.0,
        current_volume=50,
        baseline_volume=200,
        volume_change_percent=-75.0,
        z_score=4.5,
        severity='confirmed',
        manipulation_type='combined',
        detected_at=datetime(2026, 1, 14, 12, 0, 0)
    )

    assert alert.type_name == 'Interdiction Nullifier'
    assert alert.z_score == 4.5
    assert alert.severity == 'confirmed'


def test_manipulation_alert_context():
    """Test context message generation"""
    alert = ManipulationAlert(
        type_id=37615, type_name='Interdiction Nullifier',
        region_id=10000043, region_name='Domain',
        current_price=15000000, baseline_price=5000000, price_change_percent=200.0,
        current_volume=50, baseline_volume=200, volume_change_percent=-75.0,
        z_score=4.5, severity='confirmed', manipulation_type='combined',
        detected_at=datetime.utcnow()
    )

    context = alert._get_context()

    assert 'Price and volume manipulation' in context
    assert 'pre-blockade' in context
