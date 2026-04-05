"""Trading analytics models for market-service."""

from datetime import datetime, date
from typing import List, Optional
from pydantic import BaseModel, Field


class ItemPnL(BaseModel):
    """P&L for a single item."""

    type_id: int = Field(..., gt=0)
    type_name: str = Field(default="Unknown")

    # Quantities
    total_bought: int = Field(default=0, ge=0)
    total_sold: int = Field(default=0, ge=0)
    current_inventory: int = Field(default=0)

    # Values
    total_buy_value: float = Field(default=0)
    total_sell_value: float = Field(default=0)
    realized_pnl: float = Field(default=0)
    unrealized_pnl: float = Field(default=0)  # Based on current market price

    # Averages
    avg_buy_price: float = Field(default=0)
    avg_sell_price: float = Field(default=0)
    current_market_price: float = Field(default=0)

    # Metrics
    margin_percent: float = Field(default=0)
    roi_percent: float = Field(default=0)

    # Timestamps
    first_trade_at: Optional[datetime] = None
    last_trade_at: Optional[datetime] = None


class TradingPnLReport(BaseModel):
    """Complete P&L report."""

    character_id: int = Field(..., gt=0)
    corporation_id: Optional[int] = None
    include_corp: bool = Field(default=True)

    # Aggregates
    total_realized_pnl: float = Field(default=0)
    total_unrealized_pnl: float = Field(default=0)
    total_pnl: float = Field(default=0)

    # Items
    items: List[ItemPnL] = Field(default_factory=list)
    top_winners: List[ItemPnL] = Field(default_factory=list)
    top_losers: List[ItemPnL] = Field(default_factory=list)

    # Period
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    generated_at: datetime = Field(default_factory=datetime.now)


class ItemVelocity(BaseModel):
    """Velocity metrics for an item."""

    type_id: int = Field(..., gt=0)
    type_name: str = Field(default="Unknown")

    # Volume
    volume_bought_7d: int = Field(default=0)
    volume_sold_7d: int = Field(default=0)
    volume_bought_30d: int = Field(default=0)
    volume_sold_30d: int = Field(default=0)

    # Turnover
    avg_daily_volume: float = Field(default=0)
    days_to_sell: Optional[float] = None  # Based on current inventory
    turnover_rate: float = Field(default=0)  # Annualized

    # Classification
    velocity_class: str = Field(default="unknown")  # fast, medium, slow, dead


class VelocityReport(BaseModel):
    """Velocity report for all traded items."""

    character_id: int = Field(..., gt=0)

    fast_movers: List[ItemVelocity] = Field(default_factory=list)
    slow_movers: List[ItemVelocity] = Field(default_factory=list)
    dead_stock: List[ItemVelocity] = Field(default_factory=list)

    generated_at: datetime = Field(default_factory=datetime.now)


class MarginAlert(BaseModel):
    """Margin alert for an item."""

    type_id: int = Field(..., gt=0)
    type_name: str = Field(default="Unknown")

    your_price: float
    market_price: float
    margin_percent: float

    alert_type: str  # 'margin_low', 'margin_negative', 'spread_collapsed'
    severity: str  # 'warning', 'critical'


class CompetitorInfo(BaseModel):
    """Competition info for an item."""

    type_id: int = Field(..., gt=0)
    type_name: str = Field(default="Unknown")
    region_id: int
    location_name: str = Field(default="Unknown")

    # Character info (for multi-account aggregation)
    character_id: Optional[int] = None
    character_name: Optional[str] = None

    our_position: int  # 1 = best price
    total_competitors: int

    best_price: float
    our_price: float
    price_gap: float
    price_gap_percent: float

    is_buy_order: bool = False
    volume_remain: int = Field(default=0)
    status: str = Field(default="ok")  # ok, undercut, outbid


class CompetitionReport(BaseModel):
    """Competition report for all active orders."""

    character_id: int = Field(..., gt=0)

    total_orders: int = Field(default=0)
    competitive_orders: int = Field(default=0)  # At position 1
    undercut_orders: int = Field(default=0)
    outbid_orders: int = Field(default=0)

    sell_orders: List[CompetitorInfo] = Field(default_factory=list)
    buy_orders: List[CompetitorInfo] = Field(default_factory=list)

    generated_at: datetime = Field(default_factory=datetime.now)


class TradingGoal(BaseModel):
    """Trading goal with progress."""

    goal_type: str  # daily, weekly, monthly
    target_value: float
    current_value: float
    progress_percent: float

    period_start: date
    period_end: date
    days_remaining: int

    is_achieved: bool
    on_track: bool  # Projected to achieve?


class TradingSummary(BaseModel):
    """Quick trading summary for dashboard."""

    character_id: int = Field(..., gt=0)
    total_realized_pnl: float = Field(default=0)
    total_unrealized_pnl: float = Field(default=0)
    total_pnl: float = Field(default=0)

    items_traded: int = Field(default=0)
    profitable_items: int = Field(default=0)
    losing_items: int = Field(default=0)

    margin_alerts: int = Field(default=0)
    critical_alerts: int = Field(default=0)

    top_winner: Optional[ItemPnL] = None
    top_loser: Optional[ItemPnL] = None
