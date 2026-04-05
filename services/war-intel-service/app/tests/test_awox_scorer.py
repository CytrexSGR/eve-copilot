import pytest
from app.services.pilot_risk.awox_scorer import calculate_awox_score


class TestAwoxScorer:
    def test_clean_pilot_low_score(self):
        score, signals = calculate_awox_score(
            zkb_awox_count=0, loss_timing_correlation=0.0,
            char_age_days=365, corp_join_days=300,
            cross_km_count=0, fitting_anomaly_score=0.0
        )
        assert score < 10

    def test_awox_flags_raise_score(self):
        score, signals = calculate_awox_score(
            zkb_awox_count=2, loss_timing_correlation=0.0,
            char_age_days=365, corp_join_days=300,
            cross_km_count=0, fitting_anomaly_score=0.0
        )
        assert score > 20
        assert "zkb_awox" in signals

    def test_spy_alt_pattern(self):
        """Young char + quick join + timing correlation = high risk."""
        score, signals = calculate_awox_score(
            zkb_awox_count=0, loss_timing_correlation=0.8,
            char_age_days=40, corp_join_days=28,
            cross_km_count=3, fitting_anomaly_score=0.5
        )
        assert score > 50

    def test_score_capped_at_100(self):
        score, _ = calculate_awox_score(
            zkb_awox_count=10, loss_timing_correlation=1.0,
            char_age_days=10, corp_join_days=5,
            cross_km_count=20, fitting_anomaly_score=1.0
        )
        assert score <= 100

    def test_signals_dict_has_all_keys(self):
        _, signals = calculate_awox_score(
            zkb_awox_count=1, loss_timing_correlation=0.5,
            char_age_days=90, corp_join_days=60,
            cross_km_count=1, fitting_anomaly_score=0.3
        )
        assert "zkb_awox" in signals
        assert "timing_correlation" in signals
        assert "char_age" in signals
        assert "cross_km" in signals
        assert "fitting_anomaly" in signals
