import pytest
from datetime import datetime, timedelta
from app.services.temporal.decay import (
    decay_weight, classify_window, WINDOW_ACTIVE, WINDOW_BASELINE, WINDOW_HISTORICAL,
    confidence_level, CONFIDENCE_CONFIRMED, CONFIDENCE_PROBABLE,
    CONFIDENCE_EMERGING, CONFIDENCE_ANOMALY
)


class TestDecayWeight:
    def test_today_weight_is_one(self):
        now = datetime.utcnow()
        assert decay_weight(now, now) == pytest.approx(1.0, abs=0.01)

    def test_half_life_weight(self):
        now = datetime.utcnow()
        half_life_ago = now - timedelta(days=7)
        assert decay_weight(half_life_ago, now) == pytest.approx(0.5, abs=0.01)

    def test_two_half_lives(self):
        now = datetime.utcnow()
        two_hl = now - timedelta(days=14)
        assert decay_weight(two_hl, now) == pytest.approx(0.25, abs=0.01)

    def test_30_days_nearly_zero(self):
        now = datetime.utcnow()
        old = now - timedelta(days=30)
        w = decay_weight(old, now)
        assert w < 0.1
        assert w > 0

    def test_custom_half_life(self):
        now = datetime.utcnow()
        ago = now - timedelta(days=14)
        assert decay_weight(ago, now, half_life_days=14) == pytest.approx(0.5, abs=0.01)

    def test_future_timestamp_clamps_to_one(self):
        now = datetime.utcnow()
        future = now + timedelta(days=1)
        assert decay_weight(future, now) == 1.0


class TestClassifyWindow:
    def test_active_window(self):
        now = datetime.utcnow()
        assert classify_window(now - timedelta(days=0), now) == WINDOW_ACTIVE
        assert classify_window(now - timedelta(days=13), now) == WINDOW_ACTIVE

    def test_baseline_window(self):
        now = datetime.utcnow()
        assert classify_window(now - timedelta(days=15), now) == WINDOW_BASELINE
        assert classify_window(now - timedelta(days=59), now) == WINDOW_BASELINE

    def test_historical_window(self):
        now = datetime.utcnow()
        assert classify_window(now - timedelta(days=61), now) == WINDOW_HISTORICAL
        assert classify_window(now - timedelta(days=180), now) == WINDOW_HISTORICAL

    def test_boundary_14_days(self):
        now = datetime.utcnow()
        assert classify_window(now - timedelta(days=14), now) == WINDOW_ACTIVE

    def test_boundary_60_days(self):
        now = datetime.utcnow()
        assert classify_window(now - timedelta(days=60), now) == WINDOW_BASELINE


class TestConfidenceLevel:
    def test_confirmed(self):
        assert confidence_level(30, 10) == CONFIDENCE_CONFIRMED
        assert confidence_level(50, 5) == CONFIDENCE_CONFIRMED

    def test_probable(self):
        assert confidence_level(15, 10) == CONFIDENCE_PROBABLE
        assert confidence_level(29, 5) == CONFIDENCE_PROBABLE

    def test_emerging(self):
        assert confidence_level(5, 5) == CONFIDENCE_EMERGING
        assert confidence_level(9, 3) == CONFIDENCE_EMERGING

    def test_anomaly(self):
        assert confidence_level(1, 10) == CONFIDENCE_ANOMALY
        assert confidence_level(2, 5) == CONFIDENCE_ANOMALY

    def test_zero_kills(self):
        assert confidence_level(0, 10) == CONFIDENCE_ANOMALY
