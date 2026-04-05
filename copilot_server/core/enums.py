"""
Shared enums used across copilot_server modules.
Extracted to prevent circular imports between models and governance.
"""

from enum import Enum


class RiskLevel(str, Enum):
    """
    Risk level for MCP tools.

    Levels:
        READ_ONLY: Analytics, market data, no state changes
        WRITE_LOW_RISK: Shopping lists, bookmarks, non-critical writes
        WRITE_HIGH_RISK: Market orders, contract creation
        CRITICAL: Unknown tools, requires explicit approval
    """
    READ_ONLY = "READ_ONLY"
    WRITE_LOW_RISK = "WRITE_LOW_RISK"
    WRITE_HIGH_RISK = "WRITE_HIGH_RISK"
    CRITICAL = "CRITICAL"


class AutonomyLevel(Enum):
    """
    User's preferred autonomy level for AI agent.

    Levels:
        READ_ONLY (0): Only analytics, no writes
        RECOMMENDATIONS (1): Suggest actions, user decides (DEFAULT)
        ASSISTED (2): Prepare actions, ask confirmation
        SUPERVISED (3): Auto-execute within limits (future)
    """
    READ_ONLY = 0
    RECOMMENDATIONS = 1
    ASSISTED = 2
    SUPERVISED = 3
