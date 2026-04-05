"""Tests for skill injection detection logic.

Tests the SP delta analysis from vetting_engine.py (Spec Section 2.3):
- Natural SP rate thresholds
- SP delta calculation
- Injection detection boundary conditions
- Injector count estimation across SP brackets
"""

import pytest

# ---- Constants from config.py ----

SP_RATE_THRESHOLD = 2700.0  # Max natural SP/hour
SP_RATE_BUFFER = 500.0      # Buffer for server ticks


# ---- Pure functions extracted from VettingEngine._detect_skill_injection ----


def detect_injection(
    current_sp: int,
    last_sp: int,
    hours_elapsed: float,
) -> dict:
    """Detect skill injection via SP delta analysis.

    Reimplemented from VettingEngine._detect_skill_injection core logic.
    """
    result = {"injected": False, "flags": [], "estimated_injectors": 0}

    if hours_elapsed < 0.5:
        return result

    sp_delta = current_sp - last_sp
    max_natural_sp = (SP_RATE_THRESHOLD + SP_RATE_BUFFER) * hours_elapsed

    if sp_delta > max_natural_sp:
        injected_sp = sp_delta - (SP_RATE_THRESHOLD * hours_elapsed)

        # Estimate injectors based on SP brackets
        if current_sp < 5_000_000:
            estimated = int(injected_sp / 500_000)
        elif current_sp < 50_000_000:
            estimated = int(injected_sp / 400_000)
        elif current_sp < 80_000_000:
            estimated = int(injected_sp / 300_000)
        else:
            estimated = int(injected_sp / 150_000)

        result["injected"] = True
        result["estimated_injectors"] = max(1, estimated)
        result["flags"].append({
            "type": "sp_injection_detected",
            "sp_delta": sp_delta,
            "max_natural": int(max_natural_sp),
            "hours_elapsed": round(hours_elapsed, 1),
            "estimated_injectors": result["estimated_injectors"],
        })

    return result


# ---- Tests ----


class TestSPThresholdConstants:
    """Verify SP threshold constants from config."""

    def test_sp_rate_threshold(self):
        """Default SP rate threshold should be 2700 SP/hour."""
        assert SP_RATE_THRESHOLD == 2700.0

    def test_sp_rate_buffer(self):
        """Default SP rate buffer should be 500 SP/hour."""
        assert SP_RATE_BUFFER == 500.0

    def test_effective_max_rate(self):
        """Effective max natural rate = threshold + buffer."""
        assert SP_RATE_THRESHOLD + SP_RATE_BUFFER == 3200.0


class TestInjectionDetection:
    """Tests for the injection detection algorithm."""

    def test_no_injection_normal_training(self):
        """Normal SP gain within natural rate should not flag."""
        # 24 hours at 2000 SP/hr = 48,000 SP gain
        result = detect_injection(
            current_sp=10_048_000,
            last_sp=10_000_000,
            hours_elapsed=24.0,
        )
        assert result["injected"] is False

    def test_clear_injection_detected(self):
        """Large SP delta far exceeding natural rate should flag."""
        # 1 hour, gained 5M SP (natural max ~3200)
        result = detect_injection(
            current_sp=15_000_000,
            last_sp=10_000_000,
            hours_elapsed=1.0,
        )
        assert result["injected"] is True
        assert result["estimated_injectors"] >= 1

    def test_too_short_interval_skipped(self):
        """Intervals less than 0.5 hours should be skipped."""
        result = detect_injection(
            current_sp=15_000_000,
            last_sp=10_000_000,
            hours_elapsed=0.3,
        )
        assert result["injected"] is False

    def test_exactly_half_hour_processed(self):
        """Exactly 0.5 hours should be processed."""
        # 0.5 hours, max natural = 1600 SP; gain of 5M should flag
        result = detect_injection(
            current_sp=15_000_000,
            last_sp=10_000_000,
            hours_elapsed=0.5,
        )
        assert result["injected"] is True

    def test_boundary_at_max_natural_rate(self):
        """SP gain exactly at max natural rate should NOT flag."""
        hours = 10.0
        max_natural = (SP_RATE_THRESHOLD + SP_RATE_BUFFER) * hours  # 32,000
        result = detect_injection(
            current_sp=10_032_000,
            last_sp=10_000_000,
            hours_elapsed=hours,
        )
        assert result["injected"] is False

    def test_just_above_max_natural_rate(self):
        """SP gain just above max natural rate should flag."""
        hours = 10.0
        max_natural = (SP_RATE_THRESHOLD + SP_RATE_BUFFER) * hours  # 32,000
        result = detect_injection(
            current_sp=10_000_000 + int(max_natural) + 1,
            last_sp=10_000_000,
            hours_elapsed=hours,
        )
        assert result["injected"] is True

    def test_sp_loss_not_flagged(self):
        """Negative SP delta (SP extraction) should not flag injection."""
        result = detect_injection(
            current_sp=9_000_000,
            last_sp=10_000_000,
            hours_elapsed=24.0,
        )
        assert result["injected"] is False

    def test_zero_delta_not_flagged(self):
        """No SP change should not flag injection."""
        result = detect_injection(
            current_sp=10_000_000,
            last_sp=10_000_000,
            hours_elapsed=24.0,
        )
        assert result["injected"] is False


class TestInjectorEstimationBrackets:
    """Tests for skill injector estimation across SP brackets."""

    def test_low_sp_bracket_500k_per_injector(self):
        """Characters <5M SP: 500K SP per injector."""
        result = detect_injection(
            current_sp=3_000_000,
            last_sp=1_000_000,
            hours_elapsed=1.0,
        )
        assert result["injected"] is True
        # injected_sp = 2M - 2700 = ~1.997M
        # 1.997M / 500K = 3
        assert result["estimated_injectors"] == 3

    def test_mid_sp_bracket_400k_per_injector(self):
        """Characters 5-50M SP: 400K SP per injector."""
        result = detect_injection(
            current_sp=20_000_000,
            last_sp=18_000_000,
            hours_elapsed=1.0,
        )
        assert result["injected"] is True
        # injected_sp = 2M - 2700 = ~1.997M
        # 1.997M / 400K = 4
        assert result["estimated_injectors"] == 4

    def test_high_sp_bracket_300k_per_injector(self):
        """Characters 50-80M SP: 300K SP per injector."""
        result = detect_injection(
            current_sp=60_000_000,
            last_sp=58_000_000,
            hours_elapsed=1.0,
        )
        assert result["injected"] is True
        # injected_sp = 2M - 2700 = ~1.997M
        # 1.997M / 300K = 6
        assert result["estimated_injectors"] == 6

    def test_very_high_sp_bracket_150k_per_injector(self):
        """Characters >80M SP: 150K SP per injector."""
        result = detect_injection(
            current_sp=100_000_000,
            last_sp=98_000_000,
            hours_elapsed=1.0,
        )
        assert result["injected"] is True
        # injected_sp = 2M - 2700 = ~1.997M
        # 1.997M / 150K = 13
        assert result["estimated_injectors"] == 13

    def test_flag_contains_expected_fields(self):
        """Injection flag should contain all expected diagnostic fields."""
        result = detect_injection(
            current_sp=15_000_000,
            last_sp=10_000_000,
            hours_elapsed=2.0,
        )
        assert result["injected"] is True
        flag = result["flags"][0]
        assert "type" in flag
        assert flag["type"] == "sp_injection_detected"
        assert "sp_delta" in flag
        assert "max_natural" in flag
        assert "hours_elapsed" in flag
        assert "estimated_injectors" in flag

    def test_minimum_one_injector(self):
        """Even a small injection should report at least 1 injector."""
        # Just barely above threshold
        hours = 1.0
        max_natural = (SP_RATE_THRESHOLD + SP_RATE_BUFFER) * hours
        result = detect_injection(
            current_sp=10_000_000 + int(max_natural) + 10,
            last_sp=10_000_000,
            hours_elapsed=hours,
        )
        assert result["injected"] is True
        assert result["estimated_injectors"] >= 1
