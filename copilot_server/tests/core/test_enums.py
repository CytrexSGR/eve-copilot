# copilot_server/tests/core/test_enums.py
"""
Tests for shared enums in copilot_server.core.enums
"""

import pytest
from copilot_server.core.enums import RiskLevel, AutonomyLevel


class TestRiskLevel:
    """Tests for RiskLevel enum."""

    def test_risk_level_values(self):
        """Test RiskLevel enum values."""
        assert RiskLevel.READ_ONLY.value == "READ_ONLY"
        assert RiskLevel.WRITE_LOW_RISK.value == "WRITE_LOW_RISK"
        assert RiskLevel.WRITE_HIGH_RISK.value == "WRITE_HIGH_RISK"
        assert RiskLevel.CRITICAL.value == "CRITICAL"

    def test_risk_level_is_str_enum(self):
        """RiskLevel should be a str enum for JSON serialization."""
        assert isinstance(RiskLevel.READ_ONLY, str)
        assert RiskLevel.READ_ONLY == "READ_ONLY"

    def test_risk_level_from_string(self):
        """Should be able to create RiskLevel from string."""
        assert RiskLevel("READ_ONLY") == RiskLevel.READ_ONLY
        assert RiskLevel("CRITICAL") == RiskLevel.CRITICAL

    def test_risk_level_count(self):
        """Should have exactly 4 risk levels."""
        assert len(RiskLevel) == 4


class TestAutonomyLevel:
    """Tests for AutonomyLevel enum."""

    def test_autonomy_level_values(self):
        """Test AutonomyLevel enum values."""
        assert AutonomyLevel.READ_ONLY.value == 0
        assert AutonomyLevel.RECOMMENDATIONS.value == 1
        assert AutonomyLevel.ASSISTED.value == 2
        assert AutonomyLevel.SUPERVISED.value == 3

    def test_autonomy_level_ordering(self):
        """Autonomy levels should be ordered by increasing autonomy."""
        assert AutonomyLevel.READ_ONLY.value < AutonomyLevel.RECOMMENDATIONS.value
        assert AutonomyLevel.RECOMMENDATIONS.value < AutonomyLevel.ASSISTED.value
        assert AutonomyLevel.ASSISTED.value < AutonomyLevel.SUPERVISED.value

    def test_autonomy_level_count(self):
        """Should have exactly 4 autonomy levels."""
        assert len(AutonomyLevel) == 4


class TestBackwardCompatibility:
    """Tests for backward compatibility of imports."""

    def test_import_from_core(self):
        """Should be able to import from core module."""
        from copilot_server.core import RiskLevel, AutonomyLevel
        assert RiskLevel.READ_ONLY.value == "READ_ONLY"
        assert AutonomyLevel.RECOMMENDATIONS.value == 1

    def test_import_from_user_settings(self):
        """Should be able to import from user_settings (backward compat)."""
        from copilot_server.models.user_settings import RiskLevel, AutonomyLevel
        assert RiskLevel.READ_ONLY.value == "READ_ONLY"
        assert AutonomyLevel.RECOMMENDATIONS.value == 1

    def test_import_from_tool_classification(self):
        """Should be able to import from tool_classification."""
        from copilot_server.governance.tool_classification import RiskLevel
        assert RiskLevel.READ_ONLY.value == "READ_ONLY"

    def test_enums_are_same_class(self):
        """Enums from different imports should be the same class."""
        from copilot_server.core.enums import RiskLevel as CoreRiskLevel
        from copilot_server.models.user_settings import RiskLevel as SettingsRiskLevel
        from copilot_server.governance.tool_classification import RiskLevel as ClassificationRiskLevel

        # They should all be the same class
        assert CoreRiskLevel is SettingsRiskLevel
        assert CoreRiskLevel is ClassificationRiskLevel

        # Values should be equal
        assert CoreRiskLevel.READ_ONLY == SettingsRiskLevel.READ_ONLY
        assert CoreRiskLevel.CRITICAL == ClassificationRiskLevel.CRITICAL
