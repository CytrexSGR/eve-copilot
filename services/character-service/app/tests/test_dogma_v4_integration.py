"""Integration tests for Dogma Engine v4 features.
Verifies all 5 new features work together without conflicts.
"""
import pytest


class TestV4ModelIntegration:
    """Verify all v4 request/response models work together."""

    def test_all_new_request_fields_accepted(self):
        """FittingStatsRequest should accept all v4 fields simultaneously."""
        from app.services.fitting_stats.models import (
            FittingStatsRequest, FighterInput, FleetBoostInput, ProjectedEffectInput
        )
        req = FittingStatsRequest(
            ship_type_id=34317,  # Confessor
            items=[{"type_id": 3170, "flag": 11, "quantity": 1}],
            mode_type_id=34319,  # Defense Mode
            fighters=[FighterInput(type_id=23057, quantity=1)],
            fleet_boosts=[FleetBoostInput(buff_id=10, value=25.0)],
            projected_effects=[ProjectedEffectInput(effect_type="web", strength=60.0)],
            target_projected=[ProjectedEffectInput(effect_type="paint", strength=30.0)],
        )
        assert req.mode_type_id == 34319
        assert len(req.fighters) == 1
        assert len(req.fleet_boosts) == 1
        assert len(req.projected_effects) == 1
        assert len(req.target_projected) == 1

    def test_response_has_all_v4_fields(self):
        from app.services.fitting_stats.models import FittingStatsResponse
        fields = set(FittingStatsResponse.model_fields.keys())
        assert "mode" in fields
        assert "active_boosts" in fields
        assert "projected_effects_summary" in fields

    def test_offense_has_all_v4_fields(self):
        from app.services.fitting_stats.models import OffenseStats
        fields = set(OffenseStats.model_fields.keys())
        assert "fighter_dps" in fields
        assert "fighter_details" in fields
        assert "spool" in fields

    def test_applied_dps_has_spool(self):
        from app.services.fitting_stats.models import AppliedDPS
        fields = set(AppliedDPS.model_fields.keys())
        assert "spool_applied" in fields


class TestCrossFeatureInteraction:
    """Test interactions between features."""

    def test_fleet_boost_then_projected_web(self):
        """Fleet speed boost applied first, then web reduces boosted speed."""
        from app.services.fitting_stats.fleet_boosts import apply_fleet_boosts
        from app.services.fitting_stats.projected import apply_projected_effects

        base = {37: 1000.0}
        boosted = apply_fleet_boosts(base, [{"buff_id": 35, "value": 25.0}])
        assert abs(boosted[37] - 1250.0) < 0.1

        result = apply_projected_effects(boosted, [{"effect_type": "web", "strength": 60.0, "count": 1}])
        assert abs(result["modified_attrs"][37] - 500.0) < 0.1  # 1250 * 0.4

    def test_fleet_shield_boost_then_projected_neut(self):
        """Shield boost doesn't interact with neut drain."""
        from app.services.fitting_stats.fleet_boosts import apply_fleet_boosts
        from app.services.fitting_stats.projected import apply_projected_effects

        base = {263: 10000.0, 482: 5000.0}
        boosted = apply_fleet_boosts(base, [{"buff_id": 10, "value": 25.0}])
        assert boosted[263] > 12000

        result = apply_projected_effects(boosted, [{"effect_type": "neut", "strength": 600.0, "count": 1}])
        assert result["cap_drain_per_s"] > 0
        assert result["modified_attrs"][263] == boosted[263]  # Shield HP unchanged by neut

    def test_spool_with_fleet_damage_boost(self):
        """Spool-up on boosted base DPS."""
        from app.services.fitting_stats.spool import calculate_spool_dps
        boosted_base = 100.0 * 1.25  # Fleet boost +25%
        result = calculate_spool_dps(boosted_base, 0.05, 1.5)
        assert result["min_dps"] == 125.0
        assert result["max_dps"] == 312.5

    def test_fighter_dps_independent_of_projected(self):
        """Fighter DPS is not affected by projected effects on the carrier."""
        from app.services.fitting_stats.fighters import calculate_fighter_dps
        from app.services.fitting_stats.projected import apply_projected_effects

        fighter_attrs = {2215: 9, 51: 4000.0, 64: 1.0, 114: 10.0, 116: 0.0, 117: 10.0, 118: 0.0}
        fighter_result = calculate_fighter_dps(fighter_attrs, squadrons=2)

        ship_attrs = {37: 100.0}
        apply_projected_effects(ship_attrs, [{"effect_type": "web", "strength": 60.0, "count": 1}])

        # Fighter DPS unchanged
        fighter_result_after = calculate_fighter_dps(fighter_attrs, squadrons=2)
        assert fighter_result["total_dps"] == fighter_result_after["total_dps"]


class TestAllPresetsValid:
    """Verify all presets reference valid definitions."""

    def test_all_fleet_presets_reference_valid_buffs(self):
        from app.services.fitting_stats.fleet_boosts import BOOST_PRESETS, BUFF_DEFINITIONS
        for name, boosts in BOOST_PRESETS.items():
            for b in boosts:
                assert b["buff_id"] in BUFF_DEFINITIONS, f"Preset {name}: unknown buff_id {b['buff_id']}"

    def test_all_projected_presets_reference_valid_types(self):
        from app.services.fitting_stats.projected import PROJECTED_PRESETS, PROJECTED_DEFINITIONS
        for name, effects in PROJECTED_PRESETS.items():
            for e in effects:
                assert e["effect_type"] in PROJECTED_DEFINITIONS, f"Preset {name}: unknown type {e['effect_type']}"
