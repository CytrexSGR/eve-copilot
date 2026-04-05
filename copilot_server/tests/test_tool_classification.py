# copilot_server/tests/test_tool_classification.py

import pytest
from copilot_server.core.enums import RiskLevel
from copilot_server.governance.tool_classification import (
    ToolRiskRegistry,
    get_tool_risk_level,
    classify_all_tools,
    get_tools_by_risk_level,
)


@pytest.fixture(autouse=True)
def reset_registry():
    """Reset singleton between tests."""
    ToolRiskRegistry.reset_instance()
    yield
    ToolRiskRegistry.reset_instance()


def test_read_only_tools_are_green():
    """Read-only tools should be classified as READ_ONLY."""
    assert get_tool_risk_level("search_item") == RiskLevel.READ_ONLY
    assert get_tool_risk_level("get_market_stats") == RiskLevel.READ_ONLY
    assert get_tool_risk_level("get_war_summary") == RiskLevel.READ_ONLY


def test_write_low_risk_tools_are_yellow():
    """Low-risk write tools should be classified as WRITE_LOW_RISK."""
    assert get_tool_risk_level("create_shopping_list") == RiskLevel.WRITE_LOW_RISK
    assert get_tool_risk_level("create_bookmark") == RiskLevel.WRITE_LOW_RISK
    assert get_tool_risk_level("mark_item_purchased") == RiskLevel.WRITE_LOW_RISK


def test_write_high_risk_tools_are_orange():
    """High-risk write tools should be classified as WRITE_HIGH_RISK."""
    assert get_tool_risk_level("delete_shopping_list") == RiskLevel.WRITE_HIGH_RISK
    assert get_tool_risk_level("delete_bookmark") == RiskLevel.WRITE_HIGH_RISK


def test_all_tools_classified():
    """All MCP tools must have risk classification (loaded from JSON)."""
    classification = classify_all_tools()
    # JSON config has 258 tools across all categories
    assert len(classification) >= 250, f"Expected at least 250 tools, got {len(classification)}"

    # Verify all tools are classified with valid RiskLevel
    for tool_name, risk_level in classification.items():
        assert isinstance(risk_level, RiskLevel), f"Invalid risk level for {tool_name}"


def test_no_critical_tools_in_config():
    """CRITICAL tools should not be in config (only unknown tools get CRITICAL)."""
    classification = classify_all_tools()
    critical_tools = [
        name for name, level in classification.items()
        if level == RiskLevel.CRITICAL
    ]
    assert len(critical_tools) == 0, f"Found CRITICAL tools in config: {critical_tools}"


def test_unknown_tool_returns_critical():
    """Unknown tools should return CRITICAL risk level."""
    risk = get_tool_risk_level("unknown_tool_xyz_123")
    assert risk == RiskLevel.CRITICAL


def test_get_tools_by_risk_level():
    """Should return all tools at a specific risk level."""
    read_only_tools = get_tools_by_risk_level(RiskLevel.READ_ONLY)
    assert "search_item" in read_only_tools
    assert "get_market_stats" in read_only_tools

    write_low_tools = get_tools_by_risk_level(RiskLevel.WRITE_LOW_RISK)
    assert "create_shopping_list" in write_low_tools
    assert "create_bookmark" in write_low_tools


def test_registry_singleton():
    """ToolRiskRegistry should be a singleton."""
    instance1 = ToolRiskRegistry.get_instance()
    instance2 = ToolRiskRegistry.get_instance()
    assert instance1 is instance2


def test_registry_reset():
    """Resetting singleton should create new instance."""
    instance1 = ToolRiskRegistry.get_instance()
    ToolRiskRegistry.reset_instance()
    instance2 = ToolRiskRegistry.get_instance()
    assert instance1 is not instance2


def test_backward_compatibility():
    """Convenience functions should work for backward compatibility."""
    # These are the functions used in existing code
    risk = get_tool_risk_level("search_item")
    assert risk == RiskLevel.READ_ONLY

    all_tools = classify_all_tools()
    assert isinstance(all_tools, dict)

    read_only = get_tools_by_risk_level(RiskLevel.READ_ONLY)
    assert isinstance(read_only, list)
