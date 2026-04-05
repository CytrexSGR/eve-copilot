"""Tests for calculate_trend() utility."""

import pytest

from app.utils.trends import calculate_trend


class TestCalculateTrendBasic:
    """Basic trend calculation tests."""

    def test_increasing_trend(self):
        """Recent values significantly higher than older values."""
        timeline = [
            {"kills": 10}, {"kills": 10}, {"kills": 10}, {"kills": 10},
            {"kills": 20}, {"kills": 20}, {"kills": 20},
        ]
        assert calculate_trend(timeline, "kills") == "increasing"

    def test_decreasing_trend(self):
        """Recent values significantly lower than older values."""
        timeline = [
            {"kills": 20}, {"kills": 20}, {"kills": 20}, {"kills": 20},
            {"kills": 5}, {"kills": 5}, {"kills": 5},
        ]
        assert calculate_trend(timeline, "kills") == "decreasing"

    def test_stable_trend(self):
        """Values roughly the same across the timeline."""
        timeline = [
            {"kills": 10}, {"kills": 10}, {"kills": 10}, {"kills": 10},
            {"kills": 11}, {"kills": 10}, {"kills": 10},
        ]
        assert calculate_trend(timeline, "kills") == "stable"


class TestCalculateTrendShortTimeline:
    """Short timeline guard tests."""

    def test_empty_timeline(self):
        assert calculate_trend([], "kills") == "stable"

    def test_one_entry(self):
        assert calculate_trend([{"kills": 5}], "kills") == "stable"

    def test_three_entries(self):
        """Exactly 3 entries = below threshold of 4."""
        timeline = [{"kills": 10}, {"kills": 10}, {"kills": 10}]
        assert calculate_trend(timeline, "kills") == "stable"

    def test_four_entries_minimum(self):
        """Exactly 4 entries = at threshold, should calculate."""
        # older_avg = timeline[:4] / 4 = 10, recent_avg = timeline[-3:] / 3 = 10
        timeline = [{"kills": 10}, {"kills": 10}, {"kills": 10}, {"kills": 10}]
        assert calculate_trend(timeline, "kills") == "stable"

    def test_short_timeline_returns_custom_stable_label(self):
        """Short timeline should return the stable label from custom labels."""
        assert calculate_trend([], "kills", labels=("up", "down", "flat")) == "flat"


class TestCalculateTrendCustomLabels:
    """Custom label tuple tests."""

    def test_geography_labels(self):
        """Geography uses expanding/contracting/stable."""
        timeline = [
            {"regions": 5}, {"regions": 5}, {"regions": 5}, {"regions": 5},
            {"regions": 15}, {"regions": 15}, {"regions": 15},
        ]
        result = calculate_trend(
            timeline, "regions",
            labels=("expanding", "contracting", "stable")
        )
        assert result == "expanding"

    def test_geography_contracting(self):
        timeline = [
            {"regions": 15}, {"regions": 15}, {"regions": 15}, {"regions": 15},
            {"regions": 3}, {"regions": 3}, {"regions": 3},
        ]
        result = calculate_trend(
            timeline, "regions",
            labels=("expanding", "contracting", "stable")
        )
        assert result == "contracting"

    def test_hunting_labels(self):
        """Hunting uses escalating/declining/steady."""
        timeline = [
            {"kills": 5}, {"kills": 5}, {"kills": 5}, {"kills": 5},
            {"kills": 20}, {"kills": 20}, {"kills": 20},
        ]
        result = calculate_trend(
            timeline, "kills",
            labels=("escalating", "declining", "steady")
        )
        assert result == "escalating"

    def test_hunting_declining(self):
        timeline = [
            {"kills": 20}, {"kills": 20}, {"kills": 20}, {"kills": 20},
            {"kills": 3}, {"kills": 3}, {"kills": 3},
        ]
        result = calculate_trend(
            timeline, "kills",
            labels=("escalating", "declining", "steady")
        )
        assert result == "declining"

    def test_hunting_steady(self):
        timeline = [
            {"kills": 10}, {"kills": 10}, {"kills": 10}, {"kills": 10},
            {"kills": 10}, {"kills": 10}, {"kills": 10},
        ]
        result = calculate_trend(
            timeline, "kills",
            labels=("escalating", "declining", "steady")
        )
        assert result == "steady"


class TestCalculateTrendThreshold:
    """Threshold behavior tests."""

    def test_exactly_at_15_percent_increase_is_increasing(self):
        """Boundary: due to floating point, 115/100 passes the > 1.15 check."""
        # 100.0 * 1.15 = 114.99999999999999 (float), so 115.0 > 114.99... = True
        timeline = [
            {"v": 100}, {"v": 100}, {"v": 100}, {"v": 100},
            {"v": 115}, {"v": 115}, {"v": 115},
        ]
        assert calculate_trend(timeline, "v") == "increasing"

    def test_just_above_15_percent_increase(self):
        """Just above 15% increase triggers increasing."""
        timeline = [
            {"v": 100}, {"v": 100}, {"v": 100}, {"v": 100},
            {"v": 116}, {"v": 116}, {"v": 116},
        ]
        assert calculate_trend(timeline, "v") == "increasing"

    def test_exactly_at_15_percent_decrease_is_stable(self):
        """Boundary: exactly 15% decrease should NOT trigger decreasing."""
        # older_avg = 100, recent needs to be < 100 * 0.85 = 85
        # recent_avg = 85 means NOT < 85 → stable
        timeline = [
            {"v": 100}, {"v": 100}, {"v": 100}, {"v": 100},
            {"v": 85}, {"v": 85}, {"v": 85},
        ]
        assert calculate_trend(timeline, "v") == "stable"

    def test_just_below_15_percent_decrease(self):
        """Just below 15% decrease triggers decreasing."""
        timeline = [
            {"v": 100}, {"v": 100}, {"v": 100}, {"v": 100},
            {"v": 84}, {"v": 84}, {"v": 84},
        ]
        assert calculate_trend(timeline, "v") == "decreasing"

    def test_custom_threshold(self):
        """Custom threshold value."""
        timeline = [
            {"v": 100}, {"v": 100}, {"v": 100}, {"v": 100},
            {"v": 106}, {"v": 106}, {"v": 106},
        ]
        # Default threshold 0.15: 106 < 115 → stable
        assert calculate_trend(timeline, "v") == "stable"
        # Custom threshold 0.05: 106 > 105 → increasing
        assert calculate_trend(timeline, "v", threshold=0.05) == "increasing"


class TestCalculateTrendEdgeCases:
    """Edge case tests."""

    def test_zero_older_avg_returns_stable(self):
        """Division by zero guard when older values are all zero."""
        timeline = [
            {"v": 0}, {"v": 0}, {"v": 0}, {"v": 0},
            {"v": 10}, {"v": 10}, {"v": 10},
        ]
        assert calculate_trend(timeline, "v") == "stable"

    def test_all_zeros_returns_stable(self):
        """All zeros should return stable."""
        timeline = [
            {"v": 0}, {"v": 0}, {"v": 0}, {"v": 0},
            {"v": 0}, {"v": 0}, {"v": 0},
        ]
        assert calculate_trend(timeline, "v") == "stable"

    def test_different_keys(self):
        """Works with various dictionary keys."""
        timeline = [
            {"deaths": 5}, {"deaths": 5}, {"deaths": 5}, {"deaths": 5},
            {"deaths": 20}, {"deaths": 20}, {"deaths": 20},
        ]
        assert calculate_trend(timeline, "deaths") == "increasing"

    def test_active_pilots_key(self):
        """Works with active_pilots key."""
        timeline = [
            {"active_pilots": 50}, {"active_pilots": 50},
            {"active_pilots": 50}, {"active_pilots": 50},
            {"active_pilots": 10}, {"active_pilots": 10}, {"active_pilots": 10},
        ]
        assert calculate_trend(timeline, "active_pilots") == "decreasing"

    def test_large_timeline(self):
        """Works with long timelines (only uses first 4 and last 3)."""
        timeline = [{"v": 10}] * 4 + [{"v": 50}] * 20 + [{"v": 100}] * 3
        # older = first 4 → avg 10, recent = last 3 → avg 100
        assert calculate_trend(timeline, "v") == "increasing"

    def test_exactly_four_entries_overlap(self):
        """With 4 entries, first 4 and last 3 overlap."""
        # timeline[:4] = [10, 10, 10, 20], avg = 12.5
        # timeline[-3:] = [10, 10, 20], avg = 13.33
        # 13.33 < 12.5 * 1.15 = 14.375 → stable
        timeline = [{"v": 10}, {"v": 10}, {"v": 10}, {"v": 20}]
        assert calculate_trend(timeline, "v") == "stable"
