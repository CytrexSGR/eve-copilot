"""Tests for combat booster support."""
import pytest

from app.services.fitting_stats.boosters import (
    parse_booster_effects,
    ATTR_BOOSTERNESS,
    SIDE_EFFECT_CHANCE_ATTRS,
    SIDE_EFFECT_PENALTY_ATTRS,
    SIDE_EFFECT_MAGNITUDE_ATTRS,
)
from app.services.fitting_stats.models import (
    BoosterInput,
    FittingStatsRequest,
)
from app.services.fitting_service import FittingItem


class TestBoosterConstants:
    """Verify booster constants exist and have correct values."""

    def test_attr_boosterness(self):
        assert ATTR_BOOSTERNESS == 1087

    def test_side_effect_chance_attrs_count(self):
        assert len(SIDE_EFFECT_CHANCE_ATTRS) == 5

    def test_side_effect_chance_attrs_values(self):
        assert SIDE_EFFECT_CHANCE_ATTRS == [1089, 1090, 1091, 1092, 1093]

    def test_side_effect_penalty_attrs_count(self):
        assert len(SIDE_EFFECT_PENALTY_ATTRS) == 5

    def test_side_effect_penalty_attrs_values(self):
        assert SIDE_EFFECT_PENALTY_ATTRS == [1099, 1100, 1101, 1102, 1103]

    def test_side_effect_magnitude_attrs_count(self):
        assert len(SIDE_EFFECT_MAGNITUDE_ATTRS) == 11

    def test_side_effect_magnitude_attrs_range(self):
        assert SIDE_EFFECT_MAGNITUDE_ATTRS[0] == 1141
        assert SIDE_EFFECT_MAGNITUDE_ATTRS[-1] == 1151


class TestBoosterParsing:
    """Tests for parse_booster_effects function."""

    def test_parse_booster_slot(self):
        attrs = {ATTR_BOOSTERNESS: 1.0}
        slot = int(attrs.get(ATTR_BOOSTERNESS, 0))
        assert slot == 1

    def test_primary_bonus_extracted(self):
        result = parse_booster_effects(
            booster_type_id=28672,
            booster_attrs={1087: 1.0, 330: 20.0},
            side_effects_enabled=[],
        )
        assert len(result["primary_bonuses"]) == 1
        assert result["primary_bonuses"][0]["value"] == 20.0
        assert result["primary_bonuses"][0]["source_attr"] == 330

    def test_no_primary_bonus_when_attr_missing(self):
        result = parse_booster_effects(
            booster_type_id=28672,
            booster_attrs={1087: 1.0},
            side_effects_enabled=[],
        )
        assert len(result["primary_bonuses"]) == 0

    def test_no_primary_bonus_when_zero(self):
        result = parse_booster_effects(
            booster_type_id=28672,
            booster_attrs={1087: 1.0, 330: 0},
            side_effects_enabled=[],
        )
        assert len(result["primary_bonuses"]) == 0

    def test_no_side_effects_when_disabled(self):
        result = parse_booster_effects(
            booster_type_id=28672,
            booster_attrs={1087: 1.0, 330: 20.0, 1089: 20.0, 1099: 116},
            side_effects_enabled=[],
        )
        assert len(result["side_effects"]) == 0

    def test_side_effect_included_when_enabled(self):
        result = parse_booster_effects(
            booster_type_id=28672,
            booster_attrs={1087: 1.0, 330: 20.0, 1089: 20.0, 1099: 116, 1141: -5.0},
            side_effects_enabled=[0],  # Enable first side effect
        )
        assert len(result["side_effects"]) == 1
        assert result["side_effects"][0]["target_attr"] == 116
        assert result["side_effects"][0]["magnitude"] == -5.0
        assert result["side_effects"][0]["chance"] == 20.0

    def test_multiple_side_effects_enabled(self):
        result = parse_booster_effects(
            booster_type_id=28672,
            booster_attrs={
                1087: 1.0, 330: 20.0,
                1089: 20.0, 1099: 116, 1141: -5.0,
                1090: 20.0, 1100: 68,
            },
            side_effects_enabled=[0, 1],
        )
        assert len(result["side_effects"]) == 2
        assert result["side_effects"][0]["target_attr"] == 116
        assert result["side_effects"][1]["target_attr"] == 68

    def test_side_effect_not_included_when_wrong_index(self):
        result = parse_booster_effects(
            booster_type_id=28672,
            booster_attrs={1087: 1.0, 330: 20.0, 1089: 20.0, 1099: 116, 1141: -5.0},
            side_effects_enabled=[1],  # Enable second, but only first has data
        )
        assert len(result["side_effects"]) == 0

    def test_side_effect_zero_chance_ignored(self):
        result = parse_booster_effects(
            booster_type_id=28672,
            booster_attrs={1087: 1.0, 330: 20.0, 1089: 0, 1099: 116, 1141: -5.0},
            side_effects_enabled=[0],
        )
        assert len(result["side_effects"]) == 0

    def test_side_effect_zero_target_attr_ignored(self):
        result = parse_booster_effects(
            booster_type_id=28672,
            booster_attrs={1087: 1.0, 330: 20.0, 1089: 20.0, 1099: 0, 1141: -5.0},
            side_effects_enabled=[0],
        )
        assert len(result["side_effects"]) == 0

    def test_empty_attrs_returns_empty(self):
        result = parse_booster_effects(
            booster_type_id=28672,
            booster_attrs={},
            side_effects_enabled=[],
        )
        assert result["primary_bonuses"] == []
        assert result["side_effects"] == []

    def test_return_structure(self):
        result = parse_booster_effects(
            booster_type_id=28672,
            booster_attrs={330: 10.0},
            side_effects_enabled=[],
        )
        assert "primary_bonuses" in result
        assert "side_effects" in result
        assert isinstance(result["primary_bonuses"], list)
        assert isinstance(result["side_effects"], list)


class TestBoosterInputModel:
    """Tests for BoosterInput pydantic model."""

    def test_creation(self):
        booster = BoosterInput(type_id=28672)
        assert booster.type_id == 28672
        assert booster.side_effects_enabled == []

    def test_with_side_effects(self):
        booster = BoosterInput(type_id=28672, side_effects_enabled=[0, 2, 4])
        assert booster.type_id == 28672
        assert booster.side_effects_enabled == [0, 2, 4]

    def test_defaults(self):
        booster = BoosterInput(type_id=12345)
        assert booster.side_effects_enabled == []


class TestFittingStatsRequestBoosters:
    """Tests for boosters field on FittingStatsRequest."""

    def test_boosters_defaults_to_none(self):
        req = FittingStatsRequest(
            ship_type_id=24698,
            items=[FittingItem(type_id=3841, flag=19, quantity=1)],
        )
        assert req.boosters is None

    def test_boosters_accepts_list(self):
        req = FittingStatsRequest(
            ship_type_id=24698,
            items=[FittingItem(type_id=3841, flag=19, quantity=1)],
            boosters=[
                BoosterInput(type_id=28672),
                BoosterInput(type_id=28674, side_effects_enabled=[0, 1]),
            ],
        )
        assert req.boosters is not None
        assert len(req.boosters) == 2
        assert req.boosters[0].type_id == 28672
        assert req.boosters[1].side_effects_enabled == [0, 1]

    def test_boosters_empty_list(self):
        req = FittingStatsRequest(
            ship_type_id=24698,
            items=[FittingItem(type_id=3841, flag=19, quantity=1)],
            boosters=[],
        )
        assert req.boosters == []
