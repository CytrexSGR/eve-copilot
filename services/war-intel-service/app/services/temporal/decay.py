"""Temporal Intelligence Layer — decay functions and window classification."""

import math
from datetime import datetime

# Window constants
WINDOW_ACTIVE = "active"          # 0-14 days
WINDOW_BASELINE = "baseline"      # 14-60 days
WINDOW_HISTORICAL = "historical"  # 60-180 days

# Confidence constants
CONFIDENCE_CONFIRMED = "CONFIRMED"   # 30+ kills, <14 days
CONFIDENCE_PROBABLE = "PROBABLE"     # 10-29 kills
CONFIDENCE_EMERGING = "EMERGING"     # 3-9 kills
CONFIDENCE_ANOMALY = "ANOMALY"       # 1-2 kills

# Window boundaries (days)
ACTIVE_BOUNDARY = 14
BASELINE_BOUNDARY = 60


def decay_weight(
    timestamp: datetime,
    reference: datetime,
    half_life_days: float = 7.0,
) -> float:
    """Calculate exponential decay weight for a timestamp.

    w(t) = e^(-λt) where λ = ln(2) / half_life
    """
    delta_days = (reference - timestamp).total_seconds() / 86400.0
    if delta_days <= 0:
        return 1.0
    lam = math.log(2) / half_life_days
    return math.exp(-lam * delta_days)


def classify_window(timestamp: datetime, reference: datetime) -> str:
    """Classify a timestamp into Active/Baseline/Historical window."""
    delta_days = (reference - timestamp).total_seconds() / 86400.0
    if delta_days <= ACTIVE_BOUNDARY:
        return WINDOW_ACTIVE
    elif delta_days <= BASELINE_BOUNDARY:
        return WINDOW_BASELINE
    else:
        return WINDOW_HISTORICAL


def confidence_level(observation_count: int, max_age_days: float = 14) -> str:
    """Determine confidence level based on observation count."""
    if observation_count >= 30:
        return CONFIDENCE_CONFIRMED
    elif observation_count >= 10:
        return CONFIDENCE_PROBABLE
    elif observation_count >= 3:
        return CONFIDENCE_EMERGING
    else:
        return CONFIDENCE_ANOMALY
