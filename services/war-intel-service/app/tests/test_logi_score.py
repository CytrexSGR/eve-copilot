import pytest
from app.routers.intelligence.logi_score import _calculate_logi_score


class TestLogiScoreCalc:
    def test_no_logi_low_score(self):
        score = _calculate_logi_score(
            our_kills=10, their_kills=5, our_damage_dealt=100000,
            their_logi_count=0, their_fleet_size=20
        )
        assert score < 15  # Low score without logi present

    def test_high_logi_high_score(self):
        score = _calculate_logi_score(
            our_kills=2, their_kills=15, our_damage_dealt=500000,
            their_logi_count=5, their_fleet_size=20
        )
        assert score > 50

    def test_score_capped_at_100(self):
        score = _calculate_logi_score(
            our_kills=0, their_kills=50, our_damage_dealt=9999999,
            their_logi_count=10, their_fleet_size=15
        )
        assert score <= 100

    def test_score_min_zero(self):
        score = _calculate_logi_score(
            our_kills=50, their_kills=0, our_damage_dealt=10000,
            their_logi_count=0, their_fleet_size=50
        )
        assert score >= 0
