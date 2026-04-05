"""
Tool Risk Classification
Loads tool risk levels from configuration file.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional

from ..core.enums import RiskLevel

logger = logging.getLogger(__name__)

# Default config path
CONFIG_PATH = Path(__file__).parent.parent / "config" / "tool_risks.json"


class ToolRiskRegistry:
    """
    Registry for tool risk levels.
    Loads from JSON config with fallback to hardcoded defaults.
    """

    _instance: Optional["ToolRiskRegistry"] = None

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or CONFIG_PATH
        self._risks: Dict[str, RiskLevel] = {}
        self._load_config()

    @classmethod
    def get_instance(cls) -> "ToolRiskRegistry":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton (for testing)."""
        cls._instance = None

    def _load_config(self) -> None:
        """Load risk levels from JSON config."""
        try:
            if self.config_path.exists():
                with open(self.config_path) as f:
                    data = json.load(f)

                # Flatten nested categories
                for category, tools in data.items():
                    if category.startswith("_"):
                        continue  # Skip metadata
                    if isinstance(tools, dict):
                        for tool_name, risk_str in tools.items():
                            try:
                                self._risks[tool_name] = RiskLevel(risk_str)
                            except ValueError:
                                logger.error(f"Invalid risk level '{risk_str}' for tool '{tool_name}'")

                logger.info(f"Loaded {len(self._risks)} tool risk levels from {self.config_path}")
            else:
                logger.warning(f"Config not found at {self.config_path}, using defaults")
                self._load_defaults()
        except Exception as e:
            logger.error(f"Failed to load config: {e}, using defaults")
            self._load_defaults()

    def _load_defaults(self) -> None:
        """Load hardcoded defaults as fallback."""
        # Minimal defaults for critical tools
        self._risks = {
            "eve_copilot_context": RiskLevel.READ_ONLY,
            "get_available_tools": RiskLevel.READ_ONLY,
        }

    def get_risk_level(self, tool_name: str) -> RiskLevel:
        """
        Get risk level for tool.

        Args:
            tool_name: Tool name

        Returns:
            RiskLevel (CRITICAL if unknown)
        """
        if tool_name not in self._risks:
            logger.warning(f"Unknown tool '{tool_name}', defaulting to CRITICAL")
            return RiskLevel.CRITICAL
        return self._risks[tool_name]

    def get_all_tools(self) -> Dict[str, RiskLevel]:
        """Get all registered tools."""
        return self._risks.copy()

    def get_tools_by_risk(self, risk_level: RiskLevel) -> list:
        """Get all tools at specific risk level."""
        return [name for name, level in self._risks.items() if level == risk_level]


# Convenience functions (backward compatible)
def get_tool_risk_level(tool_name: str) -> RiskLevel:
    """Get risk level for tool."""
    return ToolRiskRegistry.get_instance().get_risk_level(tool_name)


def classify_all_tools() -> Dict[str, RiskLevel]:
    """Get all tool classifications."""
    return ToolRiskRegistry.get_instance().get_all_tools()


def get_tools_by_risk_level(risk_level: RiskLevel) -> list:
    """Get tools at specific risk level."""
    return ToolRiskRegistry.get_instance().get_tools_by_risk(risk_level)
