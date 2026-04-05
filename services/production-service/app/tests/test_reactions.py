"""Tests for reaction formulas and profitability calculations.

Tests the helper functions in app/routers/reactions.py:
  - _get_all_reactions: fetch all reaction formulas from DB
  - _get_reaction: fetch a single reaction by type_id
  - _get_prices: fetch market prices for type_ids
  - _calculate_profitability: compute profit per run/hour, ROI
  - ReactionFormula.runs_per_hour property
"""

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from app.routers.reactions import (
    FacilityBonus,
    ReactionFormula,
    ReactionInput,
    ReactionProfitability,
    _calculate_profitability,
    _get_all_reactions,
    _get_prices,
    _get_reaction,
)


# =============================================================================
# Helpers
# =============================================================================


def _make_dict_cursor(result_sets):
    """Create a mock cursor that returns dict-like rows (RealDictCursor style).

    Each call to execute() advances to the next result set.
    """
    cursor = MagicMock()
    call_index = {"i": 0}
    rows_store = {"rows": []}

    def _execute(sql, params=None):
        idx = call_index["i"]
        if idx < len(result_sets):
            rows_store["rows"] = result_sets[idx]
        else:
            rows_store["rows"] = []
        call_index["i"] += 1

    cursor.execute = _execute
    cursor.fetchall = lambda: rows_store["rows"]
    cursor.fetchone = lambda: rows_store["rows"][0] if rows_store["rows"] else None
    cursor.__enter__ = lambda s: cursor
    cursor.__exit__ = MagicMock(return_value=False)
    return cursor


def _make_db(result_sets):
    """Create a mock DB with cursor() context manager returning dict rows."""
    cursor = _make_dict_cursor(result_sets)
    db = MagicMock()
    db.cursor.return_value = cursor
    return db


# =============================================================================
# Sample data
# =============================================================================

SAMPLE_REACTION = {
    "reaction_type_id": 46166,
    "reaction_name": "Fullerite-C320 Reaction",
    "product_type_id": 30305,
    "product_name": "PPD Fullerene Fibers",
    "product_quantity": 100,
    "reaction_time": 3600,
    "reaction_category": "composite",
}

SAMPLE_INPUTS = [
    {
        "reaction_type_id": 46166,
        "input_type_id": 30370,
        "input_name": "Fullerite-C320",
        "quantity": 100,
    },
    {
        "reaction_type_id": 46166,
        "input_type_id": 16634,
        "input_name": "Fernite Carbide",
        "quantity": 50,
    },
]


# =============================================================================
# ReactionFormula model tests
# =============================================================================


class TestReactionFormulaModel:
    """Test ReactionFormula Pydantic model and properties."""

    def test_runs_per_hour_standard(self):
        """3600s reaction = 1 run/hour."""
        formula = ReactionFormula(
            reaction_type_id=1,
            reaction_name="Test",
            product_type_id=2,
            product_name="Product",
            product_quantity=100,
            reaction_time=3600,
            inputs=[],
        )
        assert formula.runs_per_hour == pytest.approx(1.0)

    def test_runs_per_hour_fast(self):
        """900s reaction = 4 runs/hour."""
        formula = ReactionFormula(
            reaction_type_id=1,
            reaction_name="Fast",
            product_type_id=2,
            product_name="Product",
            product_quantity=100,
            reaction_time=900,
            inputs=[],
        )
        assert formula.runs_per_hour == pytest.approx(4.0)

    def test_runs_per_hour_zero_time(self):
        """Zero reaction time returns 0 (guard)."""
        formula = ReactionFormula(
            reaction_type_id=1,
            reaction_name="Broken",
            product_type_id=2,
            product_name="Product",
            product_quantity=100,
            reaction_time=1,  # minimum allowed by gt=0
            inputs=[],
        )
        # With reaction_time=1: 3600/1 = 3600
        assert formula.runs_per_hour == pytest.approx(3600.0)

    def test_with_inputs(self):
        """Model accepts a list of ReactionInput."""
        inp = ReactionInput(input_type_id=100, input_name="Stuff", quantity=50)
        formula = ReactionFormula(
            reaction_type_id=1,
            reaction_name="Test",
            product_type_id=2,
            product_name="Product",
            product_quantity=10,
            reaction_time=1800,
            inputs=[inp],
        )
        assert len(formula.inputs) == 1
        assert formula.inputs[0].input_name == "Stuff"


# =============================================================================
# FacilityBonus model tests
# =============================================================================


class TestFacilityBonus:
    """Test FacilityBonus defaults and validation."""

    def test_defaults(self):
        bonus = FacilityBonus()
        assert bonus.time_multiplier == 1.0
        assert bonus.material_multiplier == 1.0

    def test_custom_values(self):
        bonus = FacilityBonus(time_multiplier=0.75, material_multiplier=0.98)
        assert bonus.time_multiplier == 0.75
        assert bonus.material_multiplier == 0.98


# =============================================================================
# _get_prices tests
# =============================================================================


class TestGetPrices:
    """Test price fetching from database."""

    def test_empty_type_ids(self):
        """No type_ids -> empty dict."""
        db = MagicMock()
        result = _get_prices(db, [])
        assert result == {}

    def test_jita_prices_from_moon_table(self):
        """Prices found in moon_material_prices (Jita)."""
        moon_rows = [
            {
                "type_id": 100,
                "jita_sell": 500.0,
                "jita_buy": 480.0,
                "amarr_sell": 510.0,
                "amarr_buy": 490.0,
            }
        ]
        db = _make_db([moon_rows, []])  # moon prices, then market_prices (for missing)
        result = _get_prices(db, [100])

        assert result[100]["sell"] == Decimal("500.0")
        assert result[100]["buy"] == Decimal("480.0")

    def test_amarr_prices(self):
        """When region_id is Domain (10000043), use Amarr prices."""
        moon_rows = [
            {
                "type_id": 100,
                "jita_sell": 500.0,
                "jita_buy": 480.0,
                "amarr_sell": 510.0,
                "amarr_buy": 490.0,
            }
        ]
        db = _make_db([moon_rows, []])
        result = _get_prices(db, [100], region_id=10000043)

        assert result[100]["sell"] == Decimal("510.0")
        assert result[100]["buy"] == Decimal("490.0")

    def test_fallback_to_market_prices(self):
        """Missing from moon table -> falls back to market_prices."""
        moon_rows = []  # nothing in moon table
        market_rows = [
            {"type_id": 200, "lowest_sell": 1000.0, "highest_buy": 950.0}
        ]
        db = _make_db([moon_rows, market_rows])
        result = _get_prices(db, [200])

        assert result[200]["sell"] == Decimal("1000.0")
        assert result[200]["buy"] == Decimal("950.0")

    def test_no_prices_found(self):
        """No prices in any table -> sell/buy remain None."""
        db = _make_db([[], []])
        result = _get_prices(db, [999])

        assert result[999]["sell"] is None
        assert result[999]["buy"] is None


# =============================================================================
# _get_all_reactions tests
# =============================================================================


class TestGetAllReactions:
    """Test fetching all reactions."""

    def test_returns_list(self):
        """Returns a list of ReactionFormula objects."""
        reactions_rows = [SAMPLE_REACTION]
        inputs_rows = SAMPLE_INPUTS

        db = _make_db([reactions_rows, inputs_rows])
        result = _get_all_reactions(db)

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], ReactionFormula)

    def test_empty_database(self):
        """No reactions in DB -> empty list."""
        db = _make_db([[], []])
        result = _get_all_reactions(db)
        assert result == []

    def test_reaction_fields(self):
        """Returned formula has correct field values."""
        db = _make_db([[SAMPLE_REACTION], SAMPLE_INPUTS])
        result = _get_all_reactions(db)

        r = result[0]
        assert r.reaction_type_id == 46166
        assert r.reaction_name == "Fullerite-C320 Reaction"
        assert r.product_type_id == 30305
        assert r.product_name == "PPD Fullerene Fibers"
        assert r.product_quantity == 100
        assert r.reaction_time == 3600
        assert r.reaction_category == "composite"

    def test_inputs_attached(self):
        """Inputs are correctly attached to their reactions."""
        db = _make_db([[SAMPLE_REACTION], SAMPLE_INPUTS])
        result = _get_all_reactions(db)

        assert len(result[0].inputs) == 2
        names = {i.input_name for i in result[0].inputs}
        assert "Fullerite-C320" in names
        assert "Fernite Carbide" in names

    def test_reaction_without_inputs(self):
        """Reaction with no inputs in formula_inputs table."""
        db = _make_db([[SAMPLE_REACTION], []])
        result = _get_all_reactions(db)

        assert len(result) == 1
        assert result[0].inputs == []


# =============================================================================
# _get_reaction tests
# =============================================================================


class TestGetReaction:
    """Test fetching a single reaction."""

    def test_found(self):
        """Existing reaction returns ReactionFormula."""
        db = _make_db([[SAMPLE_REACTION], SAMPLE_INPUTS])
        result = _get_reaction(db, 46166)

        assert result is not None
        assert isinstance(result, ReactionFormula)
        assert result.reaction_type_id == 46166

    def test_not_found(self):
        """Non-existent reaction returns None."""
        db = _make_db([[], []])
        result = _get_reaction(db, 99999)
        assert result is None

    def test_inputs_included(self):
        """Single reaction also includes its inputs."""
        db = _make_db([[SAMPLE_REACTION], SAMPLE_INPUTS])
        result = _get_reaction(db, 46166)

        assert len(result.inputs) == 2


# =============================================================================
# _calculate_profitability tests
# =============================================================================


class TestCalculateProfitability:
    """Test profitability calculations."""

    def _make_reaction(self):
        return ReactionFormula(
            reaction_type_id=46166,
            reaction_name="Test Reaction",
            product_type_id=30305,
            product_name="Test Product",
            product_quantity=100,
            reaction_time=3600,
            inputs=[
                ReactionInput(input_type_id=100, input_name="Input A", quantity=50),
                ReactionInput(input_type_id=200, input_name="Input B", quantity=25),
            ],
        )

    def test_profitable_reaction(self):
        """Reaction with positive profit."""
        reaction = self._make_reaction()

        # Prices: input A sell=10, input B sell=20, product sell=100
        moon_rows = [
            {"type_id": 100, "jita_sell": 10.0, "jita_buy": 9.0,
             "amarr_sell": None, "amarr_buy": None},
            {"type_id": 200, "jita_sell": 20.0, "jita_buy": 18.0,
             "amarr_sell": None, "amarr_buy": None},
            {"type_id": 30305, "jita_sell": 100.0, "jita_buy": 95.0,
             "amarr_sell": None, "amarr_buy": None},
        ]
        db = _make_db([moon_rows, []])

        result = _calculate_profitability(db, reaction)

        assert isinstance(result, ReactionProfitability)
        # input_cost = 50*10 + 25*20 = 500 + 500 = 1000
        assert result.input_cost == Decimal("1000")
        # output_value = 100 * 100 = 10000
        assert result.output_value == Decimal("10000")
        # profit = 10000 - 1000 = 9000
        assert result.profit_per_run == Decimal("9000")
        # 1 run/hour -> profit_per_hour = 9000
        assert float(result.profit_per_hour) == pytest.approx(9000.0)
        # ROI = 9000/1000 * 100 = 900%
        assert result.roi_percent == pytest.approx(900.0)

    def test_loss_reaction(self):
        """Reaction with negative profit."""
        reaction = self._make_reaction()

        moon_rows = [
            {"type_id": 100, "jita_sell": 100.0, "jita_buy": 90.0,
             "amarr_sell": None, "amarr_buy": None},
            {"type_id": 200, "jita_sell": 200.0, "jita_buy": 180.0,
             "amarr_sell": None, "amarr_buy": None},
            {"type_id": 30305, "jita_sell": 1.0, "jita_buy": 0.5,
             "amarr_sell": None, "amarr_buy": None},
        ]
        db = _make_db([moon_rows, []])

        result = _calculate_profitability(db, reaction)

        # input_cost = 50*100 + 25*200 = 5000 + 5000 = 10000
        # output_value = 100 * 1 = 100
        assert result.profit_per_run < 0
        assert result.roi_percent < 0

    def test_facility_bonus_time(self):
        """Facility time bonus reduces reaction time."""
        reaction = self._make_reaction()

        moon_rows = [
            {"type_id": 100, "jita_sell": 10.0, "jita_buy": 9.0,
             "amarr_sell": None, "amarr_buy": None},
            {"type_id": 200, "jita_sell": 20.0, "jita_buy": 18.0,
             "amarr_sell": None, "amarr_buy": None},
            {"type_id": 30305, "jita_sell": 100.0, "jita_buy": 95.0,
             "amarr_sell": None, "amarr_buy": None},
        ]
        db = _make_db([moon_rows, []])

        bonus = FacilityBonus(time_multiplier=0.75, material_multiplier=1.0)
        result = _calculate_profitability(db, reaction, facility_bonus=bonus)

        # Adjusted time = 3600 * 0.75 = 2700
        assert result.reaction_time == 2700
        # runs_per_hour = 3600/2700 = 1.333...
        assert result.runs_per_hour == pytest.approx(1.33, rel=1e-2)

    def test_facility_bonus_materials(self):
        """Facility material bonus reduces input quantities."""
        reaction = self._make_reaction()

        moon_rows = [
            {"type_id": 100, "jita_sell": 10.0, "jita_buy": 9.0,
             "amarr_sell": None, "amarr_buy": None},
            {"type_id": 200, "jita_sell": 20.0, "jita_buy": 18.0,
             "amarr_sell": None, "amarr_buy": None},
            {"type_id": 30305, "jita_sell": 100.0, "jita_buy": 95.0,
             "amarr_sell": None, "amarr_buy": None},
        ]
        db = _make_db([moon_rows, []])

        bonus = FacilityBonus(time_multiplier=1.0, material_multiplier=0.98)
        result = _calculate_profitability(db, reaction, facility_bonus=bonus)

        # adjusted qty A = int(50 * 0.98) = 49, B = int(25 * 0.98) = 24
        # input_cost = 49*10 + 24*20 = 490 + 480 = 970
        assert result.input_cost == Decimal("970")

    def test_zero_input_cost_roi(self):
        """When input cost is 0, ROI is 0 or inf depending on profit."""
        reaction = ReactionFormula(
            reaction_type_id=1,
            reaction_name="Free Reaction",
            product_type_id=30305,
            product_name="Product",
            product_quantity=1,
            reaction_time=3600,
            inputs=[],  # no inputs
        )

        moon_rows = [
            {"type_id": 30305, "jita_sell": 100.0, "jita_buy": 95.0,
             "amarr_sell": None, "amarr_buy": None},
        ]
        db = _make_db([moon_rows, []])

        result = _calculate_profitability(db, reaction)

        assert result.input_cost == Decimal("0")
        assert result.output_value == Decimal("100")

    def test_no_prices_available(self):
        """Missing prices treated as 0."""
        reaction = self._make_reaction()
        db = _make_db([[], []])

        result = _calculate_profitability(db, reaction)

        assert result.input_cost == Decimal("0")
        assert result.output_value == Decimal("0")
        assert result.profit_per_run == Decimal("0")
