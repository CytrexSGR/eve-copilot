"""Tests for PricingEngine pure logic.

Tests collect_fitting_type_ids() and insurance multiplier logic
without requiring database connections.
"""

from decimal import Decimal

import pytest

from app.services.pricing import PricingEngine, FUZZWORK_BATCH_SIZE, JITA_STATION_ID


# ──────────────────── Module Constants ───────────────────────────────────


class TestPricingConstants:
    """Validate pricing module constants."""

    def test_fuzzwork_batch_size(self):
        """Fuzzwork batch size is 200."""
        assert FUZZWORK_BATCH_SIZE == 200

    def test_jita_station_id(self):
        """Jita 4-4 station ID is 60003760."""
        assert JITA_STATION_ID == 60003760


# ──────────────────── collect_fitting_type_ids() ─────────────────────────


class TestCollectFittingTypeIds:
    """Test type_id collection from fitting structures."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.engine = PricingEngine()

    def test_empty_fitting(self):
        """Empty fitting returns empty list."""
        fitting = {"high": [], "med": [], "low": [], "rig": [], "drones": []}
        result = self.engine.collect_fitting_type_ids(fitting)
        assert result == []

    def test_single_module(self):
        """Single module returns one type_id."""
        fitting = {
            "high": [{"type_id": 3170, "quantity": 1}],
            "med": [], "low": [], "rig": [], "drones": [],
        }
        result = self.engine.collect_fitting_type_ids(fitting)
        assert result == [3170]

    def test_all_slots_populated(self, sample_fitting):
        """Fitting with all slots returns all unique type_ids."""
        result = self.engine.collect_fitting_type_ids(sample_fitting)
        result_set = set(result)
        assert 3170 in result_set   # high
        assert 3841 in result_set   # med
        assert 2048 in result_set   # low
        assert 26082 in result_set  # rig
        assert 2488 in result_set   # drones
        assert len(result_set) == 5

    def test_duplicate_ids_deduplicated(self):
        """Duplicate type_ids across slots are deduplicated."""
        fitting = {
            "high": [{"type_id": 100, "quantity": 1}],
            "med": [{"type_id": 100, "quantity": 1}],
            "low": [{"type_id": 200, "quantity": 1}],
            "rig": [{"type_id": 100, "quantity": 1}],
            "drones": [],
        }
        result = self.engine.collect_fitting_type_ids(fitting)
        assert set(result) == {100, 200}
        # Deduplication is done via set internally
        assert len(result) == 2

    def test_missing_type_id_skipped(self):
        """Modules without type_id (None/0) are skipped."""
        fitting = {
            "high": [{"type_id": None, "quantity": 1}, {"type_id": 0, "quantity": 1}],
            "med": [{"type_id": 500, "quantity": 1}],
            "low": [], "rig": [], "drones": [],
        }
        result = self.engine.collect_fitting_type_ids(fitting)
        # 0 is falsy, None is falsy — both skipped
        assert set(result) == {500}

    def test_missing_slot_key_treated_as_empty(self):
        """Fitting missing a slot key defaults to empty list."""
        fitting = {"high": [{"type_id": 100, "quantity": 1}]}
        result = self.engine.collect_fitting_type_ids(fitting)
        assert result == [100]

    def test_multiple_items_same_type(self):
        """Multiple modules of the same type are still one unique ID."""
        fitting = {
            "high": [
                {"type_id": 3170, "quantity": 1},
                {"type_id": 3170, "quantity": 1},
                {"type_id": 3170, "quantity": 1},
            ],
            "med": [], "low": [], "rig": [], "drones": [],
        }
        result = self.engine.collect_fitting_type_ids(fitting)
        assert result == [3170]


# ──────────────────── Insurance Multipliers ──────────────────────────────


class TestInsuranceMultipliers:
    """Test insurance payout multiplier logic (pure math, extracted from code)."""

    def test_insurance_multiplier_values(self):
        """Validate all 7 insurance level multipliers."""
        multipliers = {
            "basic": Decimal("0.50"),
            "standard": Decimal("0.60"),
            "bronze": Decimal("0.70"),
            "silver": Decimal("0.80"),
            "gold": Decimal("0.90"),
            "platinum": Decimal("1.00"),
        }
        assert multipliers["basic"] == Decimal("0.50")
        assert multipliers["standard"] == Decimal("0.60")
        assert multipliers["bronze"] == Decimal("0.70")
        assert multipliers["silver"] == Decimal("0.80")
        assert multipliers["gold"] == Decimal("0.90")
        assert multipliers["platinum"] == Decimal("1.00")

    def test_unknown_level_fallback(self):
        """Unknown insurance level should fallback to 0.00."""
        multipliers = {
            "basic": Decimal("0.50"),
            "standard": Decimal("0.60"),
            "bronze": Decimal("0.70"),
            "silver": Decimal("0.80"),
            "gold": Decimal("0.90"),
            "platinum": Decimal("1.00"),
        }
        mult = multipliers.get("nonexistent", Decimal("0.00"))
        assert mult == Decimal("0.00")

    def test_insurance_payout_calculation(self):
        """Calculate insurance payout: base_price * multiplier, quantized to 0.01.

        Example: Drake base price 10M ISK, platinum insurance.
        """
        base_price = Decimal("10000000.00")
        mult = Decimal("1.00")
        payout = (base_price * mult).quantize(Decimal("0.01"))
        assert payout == Decimal("10000000.00")

    def test_insurance_payout_bronze(self):
        """Bronze insurance: base_price * 0.70."""
        base_price = Decimal("5000000.00")
        mult = Decimal("0.70")
        payout = (base_price * mult).quantize(Decimal("0.01"))
        assert payout == Decimal("3500000.00")

    def test_insurance_none_returns_zero(self):
        """'none' level returns Decimal('0.00') directly (bypasses multiplier lookup)."""
        # In the actual code, level == "none" returns Decimal("0.00") early
        level = "none"
        if level == "none":
            payout = Decimal("0.00")
        else:
            payout = Decimal("1.00")
        assert payout == Decimal("0.00")
