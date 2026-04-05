import pytest
from app.services.dogma.constraints import (
    FittingViolation,
    validate_resource_limits,
    validate_max_group_fitted,
    validate_max_type_fitted,
    validate_hardcoded_rules,
)

class TestResourceLimits:
    def test_within_cpu_limit(self):
        violations = validate_resource_limits(
            ship_cpu=400, used_cpu=350,
            ship_pg=1200, used_pg=1000,
            ship_cal=400, used_cal=200,
        )
        assert violations == []

    def test_cpu_exceeded(self):
        violations = validate_resource_limits(
            ship_cpu=400, used_cpu=450,
            ship_pg=1200, used_pg=1000,
            ship_cal=400, used_cal=200,
        )
        assert len(violations) == 1
        assert violations[0].resource == "cpu"
        assert violations[0].used == 450
        assert violations[0].total == 400

    def test_all_exceeded(self):
        violations = validate_resource_limits(
            ship_cpu=400, used_cpu=500,
            ship_pg=1200, used_pg=1500,
            ship_cal=400, used_cal=500,
        )
        assert len(violations) == 3

    def test_exact_limit_is_valid(self):
        violations = validate_resource_limits(
            ship_cpu=400, used_cpu=400,
            ship_pg=1200, used_pg=1200,
            ship_cal=400, used_cal=400,
        )
        assert violations == []


class TestMaxGroupFitted:
    def test_single_damage_control_allowed(self):
        """One Damage Control II (group 60, maxGroupFitted=1)."""
        violations = validate_max_group_fitted(
            module_type_ids=[2048],
            module_groups={2048: 60},
            max_group_fitted={2048: 1},
        )
        assert violations == []

    def test_two_damage_controls_violated(self):
        violations = validate_max_group_fitted(
            module_type_ids=[2048, 2048],
            module_groups={2048: 60},
            max_group_fitted={2048: 1},
        )
        assert len(violations) == 1
        assert violations[0].resource == "maxGroupFitted"
        assert violations[0].used == 2
        assert violations[0].total == 1

    def test_no_restrictions_passes(self):
        violations = validate_max_group_fitted(
            module_type_ids=[3831, 3831, 3831],
            module_groups={3831: 38},
            max_group_fitted={},
        )
        assert violations == []


class TestMaxTypeFitted:
    def test_two_of_limited_type_violated(self):
        violations = validate_max_type_fitted(
            module_type_ids=[12345, 12345],
            max_type_fitted={12345: 1},
        )
        assert len(violations) == 1

    def test_within_type_limit(self):
        violations = validate_max_type_fitted(
            module_type_ids=[12345],
            max_type_fitted={12345: 1},
        )
        assert violations == []


class TestHardcodedRules:
    def test_two_cloaks_violated(self):
        violations = validate_hardcoded_rules(
            module_type_ids=[11370, 11370],  # two Covert Ops Cloaks
            module_groups={11370: 330},
        )
        assert len(violations) == 1
        assert violations[0].resource == "maxGroupFitted"
        assert violations[0].used == 2
        assert violations[0].total == 1

    def test_single_cloak_allowed(self):
        violations = validate_hardcoded_rules(
            module_type_ids=[11370],
            module_groups={11370: 330},
        )
        assert violations == []

    def test_mixed_cloak_types_violated(self):
        """Two different cloak types (same group 330) should violate."""
        violations = validate_hardcoded_rules(
            module_type_ids=[11370, 11578],  # Covert Ops + Improved
            module_groups={11370: 330, 11578: 330},
        )
        assert len(violations) == 1

    def test_no_cloaks_no_violation(self):
        violations = validate_hardcoded_rules(
            module_type_ids=[3831, 3831],
            module_groups={3831: 38},
        )
        assert violations == []
