import pytest
from app.services.temporal.drift import (
    detect_drift, DriftSignal,
    DRIFT_NEW, DRIFT_DECLINING, DRIFT_RECYCLED, DRIFT_ADAPTING, DRIFT_STABLE
)


class TestDetectDrift:
    def test_new_doctrine_in_active_only(self):
        active = [{"cluster_id": 0, "ship_type_id": 621, "observation_count": 15}]
        baseline = []
        historical = []
        signals = detect_drift(active, baseline, historical)
        assert len(signals) == 1
        assert signals[0].drift_type == DRIFT_NEW
        assert signals[0].ship_type_id == 621

    def test_declining_doctrine(self):
        active = []
        baseline = [{"cluster_id": 0, "ship_type_id": 621, "observation_count": 40}]
        historical = []
        signals = detect_drift(active, baseline, historical)
        assert len(signals) == 1
        assert signals[0].drift_type == DRIFT_DECLINING

    def test_recycled_doctrine(self):
        active = [{"cluster_id": 0, "ship_type_id": 621, "observation_count": 20}]
        baseline = []
        historical = [{"cluster_id": 0, "ship_type_id": 621, "observation_count": 50}]
        signals = detect_drift(active, baseline, historical)
        assert any(s.drift_type == DRIFT_RECYCLED for s in signals)

    def test_stable_doctrine(self):
        cluster = {"cluster_id": 0, "ship_type_id": 621, "observation_count": 30}
        active = [cluster]
        baseline = [cluster]
        historical = []
        signals = detect_drift(active, baseline, historical)
        assert len(signals) == 1
        assert signals[0].drift_type == DRIFT_STABLE

    def test_empty_all_windows(self):
        signals = detect_drift([], [], [])
        assert signals == []

    def test_multiple_doctrines(self):
        active = [
            {"cluster_id": 0, "ship_type_id": 621, "observation_count": 30},
            {"cluster_id": 1, "ship_type_id": 24690, "observation_count": 10},
        ]
        baseline = [
            {"cluster_id": 0, "ship_type_id": 621, "observation_count": 40},
        ]
        signals = detect_drift(active, baseline, [])
        assert len(signals) == 2
        stable = [s for s in signals if s.ship_type_id == 621]
        new = [s for s in signals if s.ship_type_id == 24690]
        assert stable[0].drift_type == DRIFT_STABLE
        assert new[0].drift_type == DRIFT_NEW
