"""Tests for structure bonus calculation logic.

Tests the formulas in app/services/structure_bonus.py:
  - material_modifier = (1 - structure_me/100) * (1 - rig_me * sec_mult / 100)
  - time_modifier = (1 - structure_te/100) * (1 - rig_te * sec_mult / 100)
  - cost_modifier = 1 - (cost_bonus / 100)
  - Security scaling: high=1.0, low=1.9, null=2.1, wh=2.1
  - quantity = max(1, ceil(base_qty * me_factor * structure_modifier))
"""

import math
from decimal import Decimal

import pytest

from app.services.structure_bonus import StructureBonusCalculator, SECURITY_SCALING
from app.tests.conftest import MockCursor, MockDB


# ── SECURITY_SCALING constant tests ─────────────────────────────


class TestSecurityScaling:
    """Verify security scaling constants."""

    def test_highsec_scaling(self):
        assert SECURITY_SCALING["high"] == Decimal("1.0")

    def test_lowsec_scaling(self):
        assert SECURITY_SCALING["low"] == Decimal("1.9")

    def test_nullsec_scaling(self):
        assert SECURITY_SCALING["null"] == Decimal("2.1")

    def test_wormhole_scaling(self):
        assert SECURITY_SCALING["wh"] == Decimal("2.1")

    def test_null_equals_wh(self):
        """Nullsec and wormhole have identical scaling."""
        assert SECURITY_SCALING["null"] == SECURITY_SCALING["wh"]


# ── Material modifier formula tests ─────────────────────────────


class TestMaterialModifier:
    """Test combined structure + rig material modifier calculation.

    Formula: (1 - structure_me/100) * (1 - rig_me * sec_mult / 100)
    """

    def test_no_bonus(self):
        """No structure or rig bonus: modifier = 1.0."""
        structure_me = Decimal("0")
        rig_me = Decimal("0")
        sec_mult = Decimal("1.0")

        structure_mod = Decimal("1") - (structure_me / Decimal("100"))
        rig_mod = Decimal("1") - (rig_me * sec_mult / Decimal("100"))
        combined = float(structure_mod * rig_mod)

        assert combined == 1.0

    def test_structure_only_1pct(self):
        """1% structure ME bonus, no rig: 0.99."""
        structure_me = Decimal("1")
        rig_me = Decimal("0")
        sec_mult = Decimal("1.0")

        structure_mod = Decimal("1") - (structure_me / Decimal("100"))
        rig_mod = Decimal("1") - (rig_me * sec_mult / Decimal("100"))
        combined = float(structure_mod * rig_mod)

        assert combined == pytest.approx(0.99)

    def test_rig_highsec(self):
        """4.2% rig ME in highsec (scaling 1.0): 0.958 rig modifier."""
        structure_me = Decimal("1")
        rig_me = Decimal("4.2")
        sec_mult = SECURITY_SCALING["high"]

        structure_mod = Decimal("1") - (structure_me / Decimal("100"))
        rig_mod = Decimal("1") - (rig_me * sec_mult / Decimal("100"))
        combined = float(structure_mod * rig_mod)

        # 0.99 * 0.958 = 0.94842
        assert combined == pytest.approx(0.94842, rel=1e-4)

    def test_rig_lowsec(self):
        """4.2% rig ME in lowsec (scaling 1.9): 4.2*1.9 = 7.98%."""
        structure_me = Decimal("1")
        rig_me = Decimal("4.2")
        sec_mult = SECURITY_SCALING["low"]

        structure_mod = Decimal("1") - (structure_me / Decimal("100"))
        rig_mod = Decimal("1") - (rig_me * sec_mult / Decimal("100"))
        combined = float(structure_mod * rig_mod)

        # 0.99 * (1 - 7.98/100) = 0.99 * 0.9202 = 0.910998
        assert combined == pytest.approx(0.910998, rel=1e-4)

    def test_rig_nullsec(self):
        """4.2% rig ME in nullsec (scaling 2.1): 4.2*2.1 = 8.82%."""
        structure_me = Decimal("1")
        rig_me = Decimal("4.2")
        sec_mult = SECURITY_SCALING["null"]

        structure_mod = Decimal("1") - (structure_me / Decimal("100"))
        rig_mod = Decimal("1") - (rig_me * sec_mult / Decimal("100"))
        combined = float(structure_mod * rig_mod)

        # 0.99 * (1 - 8.82/100) = 0.99 * 0.9118 = 0.902682
        assert combined == pytest.approx(0.902682, rel=1e-4)

    def test_large_bonus_clamped_positive(self):
        """Combined modifier should not go below 0.0."""
        # Simulating an extreme (unrealistic) rig bonus
        structure_me = Decimal("50")
        rig_me = Decimal("60")
        sec_mult = Decimal("2.1")

        structure_mod = Decimal("1") - (structure_me / Decimal("100"))
        rig_mod = Decimal("1") - (rig_me * sec_mult / Decimal("100"))
        combined = max(0.0, float(structure_mod * rig_mod))

        # 0.5 * (1 - 126/100) = 0.5 * -0.26 = -0.13 -> clamped to 0.0
        assert combined == 0.0


# ── Time modifier tests ─────────────────────────────────────────


class TestTimeModifier:
    """Test time modifier follows the same pattern as material modifier."""

    def test_no_te_bonus(self):
        """No TE bonus: time modifier = 1.0."""
        structure_te = Decimal("0")
        rig_te = Decimal("0")
        sec_mult = Decimal("1.0")

        structure_mod = Decimal("1") - (structure_te / Decimal("100"))
        rig_mod = Decimal("1") - (rig_te * sec_mult / Decimal("100"))
        combined = float(structure_mod * rig_mod)

        assert combined == 1.0

    def test_te_with_rig_nullsec(self):
        """25% TE structure + 20% TE rig in null (2.1x)."""
        structure_te = Decimal("25")
        rig_te = Decimal("20")
        sec_mult = SECURITY_SCALING["null"]

        structure_mod = Decimal("1") - (structure_te / Decimal("100"))
        rig_mod = Decimal("1") - (rig_te * sec_mult / Decimal("100"))
        combined = float(structure_mod * rig_mod)

        # 0.75 * (1 - 42/100) = 0.75 * 0.58 = 0.435
        assert combined == pytest.approx(0.435, rel=1e-3)


# ── Quantity calculation with structure bonus ────────────────────


class TestQuantityWithStructureBonus:
    """Test full quantity formula: max(1, ceil(base * me_factor * struct_mod))."""

    def test_standard_production(self):
        """ME10 in nullsec Raitaru: typical quantity reduction."""
        base_qty = 1000
        me = 10
        me_factor = 1 - (me / 100)  # 0.9
        struct_mod = 0.902682  # from nullsec test above

        qty = max(1, math.ceil(base_qty * me_factor * struct_mod))
        # 1000 * 0.9 * 0.902682 = 812.4138 -> ceil = 813
        assert qty == 813

    def test_no_bonuses(self):
        """ME0, no structure bonus: full material cost."""
        base_qty = 1000
        me_factor = 1.0
        struct_mod = 1.0

        qty = max(1, math.ceil(base_qty * me_factor * struct_mod))
        assert qty == 1000

    def test_minimum_one(self):
        """Even with max bonuses, minimum is 1."""
        base_qty = 1
        me_factor = 0.9
        struct_mod = 0.9

        qty = max(1, math.ceil(base_qty * me_factor * struct_mod))
        # 1 * 0.9 * 0.9 = 0.81 -> ceil = 1 -> max(1,1) = 1
        assert qty == 1

    def test_fractional_rounding(self):
        """Verify ceil always rounds up fractional results."""
        base_qty = 101
        me_factor = 0.95  # ME 5
        struct_mod = 0.99  # 1% structure bonus

        qty = max(1, math.ceil(base_qty * me_factor * struct_mod))
        # 101 * 0.95 * 0.99 = 94.9905 -> ceil = 95
        assert qty == 95


# ── Integration test with mock DB ────────────────────────────────


class TestStructureBonusWithMockDB:
    """Test StructureBonusCalculator with mocked database."""

    def test_get_material_modifier_highsec(self, mock_db):
        """Full integration: highsec facility with 1% ME and 4.2% rig."""
        facility_data = {
            "me_bonus": 1,
            "rig_me_bonus": 4.2,
            "security": "high",
        }
        cur = MockCursor([facility_data])
        db = mock_db(cur)
        calc = StructureBonusCalculator(db)
        mod = calc.get_material_modifier(1)

        assert mod == pytest.approx(0.94842, rel=1e-4)

    def test_get_material_modifier_no_facility(self, mock_db):
        """Unknown facility returns 1.0 (no bonus)."""
        cur = MockCursor([])  # No rows = facility not found
        db = mock_db(cur)
        calc = StructureBonusCalculator(db)
        mod = calc.get_material_modifier(999)

        assert mod == 1.0

    def test_get_cost_modifier(self, mock_db):
        """Cost modifier: 5% cost bonus -> 0.95."""
        facility_data = {"cost_bonus": 5}
        cur = MockCursor([facility_data])
        db = mock_db(cur)
        calc = StructureBonusCalculator(db)
        mod = calc.get_cost_modifier(1)

        assert mod == pytest.approx(0.95)

    def test_get_facility_tax_default(self, mock_db):
        """No facility found returns NPC default 10%."""
        cur = MockCursor([])
        db = mock_db(cur)
        calc = StructureBonusCalculator(db)
        tax = calc.get_facility_tax(999)

        assert tax == pytest.approx(0.10)

    def test_get_facility_tax_custom(self, mock_db):
        """Custom facility tax rate of 3.5%."""
        facility_data = {"facility_tax": 3.5}
        cur = MockCursor([facility_data])
        db = mock_db(cur)
        calc = StructureBonusCalculator(db)
        tax = calc.get_facility_tax(1)

        assert tax == pytest.approx(0.035)
