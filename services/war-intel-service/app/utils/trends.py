"""Trend calculation utility for timeline data.

Compares the average of the most recent 3 data points against the average
of the oldest 4 data points. If the recent average exceeds the older average
by more than the threshold (default 15%), the trend is classified as
increasing; if it falls below by the same margin, decreasing; otherwise stable.
"""

from typing import Tuple


def calculate_trend(
    timeline: list,
    key: str,
    threshold: float = 0.15,
    labels: Tuple[str, str, str] = ("increasing", "decreasing", "stable"),
) -> str:
    """Calculate trend direction from a timeline of data points.

    Compares the average of the last 3 entries against the average of
    the first 4 entries. Returns one of the provided label strings
    based on whether the change exceeds the threshold.

    Args:
        timeline: List of dicts, each containing at least ``key``.
        key: Dictionary key to extract numeric values from.
        threshold: Fractional change threshold (default 0.15 = 15%).
        labels: Tuple of (increasing_label, decreasing_label, stable_label).

    Returns:
        One of the three label strings.
    """
    increasing_label, decreasing_label, stable_label = labels

    if len(timeline) < 4:
        return stable_label

    recent_avg = sum(t[key] for t in timeline[-3:]) / 3
    older_avg = sum(t[key] for t in timeline[:4]) / 4

    if older_avg == 0:
        return stable_label

    if recent_avg > older_avg * (1 + threshold):
        return increasing_label
    elif recent_avg < older_avg * (1 - threshold):
        return decreasing_label
    else:
        return stable_label
