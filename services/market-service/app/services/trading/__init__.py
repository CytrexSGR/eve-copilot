"""Trading analytics module for market-service."""

from app.services.trading.models import (
    ItemPnL,
    TradingPnLReport,
    ItemVelocity,
    VelocityReport,
    MarginAlert,
    CompetitorInfo,
    CompetitionReport,
    TradingGoal,
    TradingSummary,
)
from app.services.trading.service import TradingAnalyticsService
from app.services.trading.goals import (
    TradingGoalsService,
    TradingGoal as GoalModel,
    GoalProgress,
    GoalsResponse,
)
from app.services.trading.history import (
    TradingHistoryService,
    TradingHistory,
    TradeEntry,
    DailyStats,
    HourlyPattern,
    DayOfWeekPattern,
    ItemPerformance,
)

__all__ = [
    # Analytics
    "ItemPnL",
    "TradingPnLReport",
    "ItemVelocity",
    "VelocityReport",
    "MarginAlert",
    "CompetitorInfo",
    "CompetitionReport",
    "TradingGoal",
    "TradingSummary",
    "TradingAnalyticsService",
    # Goals
    "TradingGoalsService",
    "GoalModel",
    "GoalProgress",
    "GoalsResponse",
    # History
    "TradingHistoryService",
    "TradingHistory",
    "TradeEntry",
    "DailyStats",
    "HourlyPattern",
    "DayOfWeekPattern",
    "ItemPerformance",
]
