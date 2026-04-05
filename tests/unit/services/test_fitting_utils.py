# tests/unit/services/test_fitting_utils.py
"""Unit tests for fitting utility functions."""

import pytest
import math
from src.services.fitting.utils import (
    stacking_penalty,
    apply_stacking_penalty,
)


class TestStackingPenalty:
    """Test EVE Online stacking penalty formula."""

    def test_first_module_no_penalty(self):
        """First module has no penalty (100% effective)."""
        penalty = stacking_penalty(0)
        assert penalty == pytest.approx(1.0, abs=0.001)

    def test_second_module_penalty(self):
        """Second module ~87% effective."""
        penalty = stacking_penalty(1)
        assert penalty == pytest.approx(0.869, abs=0.01)

    def test_third_module_penalty(self):
        """Third module ~57% effective."""
        penalty = stacking_penalty(2)
        assert penalty == pytest.approx(0.571, abs=0.01)

    def test_fourth_module_penalty(self):
        """Fourth module ~28% effective."""
        penalty = stacking_penalty(3)
        assert penalty == pytest.approx(0.283, abs=0.01)

    def test_fifth_module_penalty(self):
        """Fifth module ~10% effective."""
        penalty = stacking_penalty(4)
        assert penalty == pytest.approx(0.106, abs=0.01)


class TestApplyStackingPenalty:
    """Test applying stacking penalty to damage multipliers."""

    def test_single_module(self):
        """Single module, no stacking."""
        # 1.10 = +10% damage
        result = apply_stacking_penalty([1.10])
        assert result == pytest.approx(1.10, abs=0.001)

    def test_two_identical_modules(self):
        """Two identical BCUs with stacking."""
        # First: +10%, Second: +10% * 0.87 = +8.7%
        # Total: 1.10 * 1.087 = 1.1957
        result = apply_stacking_penalty([1.10, 1.10])
        assert result == pytest.approx(1.1957, abs=0.01)

    def test_three_cn_bcus(self):
        """Three Caldari Navy BCUs (realistic scenario)."""
        # CN BCU: +10% damage
        # 1st: +10%, 2nd: +8.69%, 3rd: +5.71%
        # Total: 1.10 * 1.0869 * 1.0571 ≈ 1.264
        result = apply_stacking_penalty([1.10, 1.10, 1.10])
        assert result == pytest.approx(1.264, abs=0.01)

    def test_modules_sorted_by_effectiveness(self):
        """Modules should be sorted by effectiveness (highest first)."""
        # +10% and +8% - better one applied first
        result_sorted = apply_stacking_penalty([1.10, 1.08])
        result_unsorted = apply_stacking_penalty([1.08, 1.10])
        # Should be equal because sorting happens internally
        assert result_sorted == pytest.approx(result_unsorted, abs=0.001)

    def test_empty_list(self):
        """Empty list returns 1.0 (no modification)."""
        result = apply_stacking_penalty([])
        assert result == 1.0

    def test_rof_multipliers(self):
        """RoF multipliers (< 1.0 means faster fire rate)."""
        # 0.895 = -10.5% RoF = fires 1/0.895 = 1.117x faster
        # For DPS calculation, we want to convert to DPS multiplier
        result = apply_stacking_penalty([0.895, 0.895, 0.895])
        # Stacking applies to the bonus (0.105), not the full value
        # Expected: ~0.77 (combined RoF multiplier)
        assert result < 0.895  # Should stack down
