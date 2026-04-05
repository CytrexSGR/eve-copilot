"""AWOX Risk Scoring — multi-signal detection for internal threats."""

from typing import Tuple, Dict


def calculate_awox_score(
    zkb_awox_count: int,
    loss_timing_correlation: float,
    char_age_days: int,
    corp_join_days: int,
    cross_km_count: int,
    fitting_anomaly_score: float,
) -> Tuple[float, Dict[str, float]]:
    """Calculate AWOX risk score 0-100 from multiple signals.

    Returns (total_score, {signal_name: signal_score}).
    """
    signals = {}

    # Signal 1: zkb_awox kills (25% weight, 0-25 points)
    awox_pts = min(25, zkb_awox_count * 12.5)
    signals["zkb_awox"] = awox_pts

    # Signal 2: Loss timing correlation (25% weight, 0-25 points)
    timing_pts = loss_timing_correlation * 25
    signals["timing_correlation"] = timing_pts

    # Signal 3: Character age vs corp join (15% weight, 0-15 points)
    if char_age_days < 60 and corp_join_days < 30:
        age_pts = 15  # Young char, quick join = max risk
    elif char_age_days < 90:
        age_pts = 8
    elif char_age_days < 180:
        age_pts = 3
    else:
        age_pts = 0
    signals["char_age"] = age_pts

    # Signal 4: Cross-KM presence (20% weight, 0-20 points)
    cross_pts = min(20, cross_km_count * 5)
    signals["cross_km"] = cross_pts

    # Signal 5: Fitting anomalies (15% weight, 0-15 points)
    fitting_pts = fitting_anomaly_score * 15
    signals["fitting_anomaly"] = fitting_pts

    total = min(100, awox_pts + timing_pts + age_pts + cross_pts + fitting_pts)
    return total, signals
