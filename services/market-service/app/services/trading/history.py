# app/services/trading/history.py
"""Trading History and Pattern Analysis Service.

Migrated from monolith to market-service.
Uses cached transaction data from database instead of ESI.
"""

import logging
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from typing import Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class TradeEntry(BaseModel):
    """Single trade journal entry."""
    transaction_id: int
    date: datetime
    type_id: int
    type_name: str
    quantity: int
    unit_price: float
    total_value: float
    is_buy: bool
    location_name: str
    client_id: Optional[int]


class DailyStats(BaseModel):
    """Daily trading statistics."""
    date: str
    buy_count: int
    sell_count: int
    buy_volume: int
    sell_volume: int
    buy_value: float
    sell_value: float
    profit_estimate: float
    unique_items: int


class HourlyPattern(BaseModel):
    """Hourly trading pattern."""
    hour: int
    trade_count: int
    avg_value: float
    buy_percentage: float


class DayOfWeekPattern(BaseModel):
    """Day of week trading pattern."""
    day: int  # 0=Monday, 6=Sunday
    day_name: str
    trade_count: int
    avg_value: float
    profit_estimate: float


class ItemPerformance(BaseModel):
    """Performance metrics for a single item."""
    type_id: int
    type_name: str
    buy_count: int
    sell_count: int
    total_bought: int
    total_sold: int
    avg_buy_price: float
    avg_sell_price: float
    margin_percent: float
    total_profit: float
    trade_frequency: float  # trades per day


class TradingHistory(BaseModel):
    """Complete trading history and analysis."""
    character_id: int
    period_days: int
    total_trades: int
    total_buy_value: float
    total_sell_value: float
    estimated_profit: float

    # Recent trades
    recent_trades: list[TradeEntry]

    # Daily breakdown
    daily_stats: list[DailyStats]

    # Patterns
    hourly_patterns: list[HourlyPattern]
    day_of_week_patterns: list[DayOfWeekPattern]

    # Top performers
    top_items: list[ItemPerformance]

    # Insights
    best_trading_hours: list[int]
    best_trading_days: list[str]
    insights: list[str]


class TradingHistoryService:
    """Service for analyzing trading history and patterns.

    Adapted for market-service to use cached transaction data from database.
    """

    def __init__(self, db_pool):
        """Initialize with database pool.

        Args:
            db_pool: Database connection pool (eve_shared)
        """
        self.db = db_pool
        self.day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

    def get_trading_history(
        self,
        character_id: int,
        days: int = 30,
        include_corp: bool = True
    ) -> TradingHistory:
        """Get comprehensive trading history with pattern analysis.

        Args:
            character_id: Character ID
            days: Number of days to analyze
            include_corp: Include corporation transactions

        Returns:
            TradingHistory with full analysis
        """
        # Fetch transactions from database
        transactions = self._fetch_transactions(character_id, days, include_corp)

        if not transactions:
            return TradingHistory(
                character_id=character_id,
                period_days=days,
                total_trades=0,
                total_buy_value=0,
                total_sell_value=0,
                estimated_profit=0,
                recent_trades=[],
                daily_stats=[],
                hourly_patterns=[],
                day_of_week_patterns=[],
                top_items=[],
                best_trading_hours=[],
                best_trading_days=[],
                insights=["No trading activity in the selected period."]
            )

        # Build recent trades list
        recent_trades = self._build_trade_entries(transactions[:100])  # Last 100 trades

        # Calculate daily stats
        daily_stats = self._calculate_daily_stats(transactions)

        # Analyze patterns
        hourly_patterns = self._analyze_hourly_patterns(transactions)
        dow_patterns = self._analyze_day_of_week_patterns(transactions)

        # Calculate item performance
        top_items = self._calculate_item_performance(transactions)

        # Calculate totals
        total_buy_value = sum(t['unit_price'] * t['quantity'] for t in transactions if t['is_buy'])
        total_sell_value = sum(t['unit_price'] * t['quantity'] for t in transactions if not t['is_buy'])
        estimated_profit = total_sell_value - total_buy_value

        # Generate insights
        best_hours = [p.hour for p in sorted(hourly_patterns, key=lambda x: x.avg_value, reverse=True)[:3]]
        best_days = [p.day_name for p in sorted(dow_patterns, key=lambda x: x.profit_estimate, reverse=True)[:3]]
        insights = self._generate_insights(transactions, hourly_patterns, dow_patterns, top_items)

        return TradingHistory(
            character_id=character_id,
            period_days=days,
            total_trades=len(transactions),
            total_buy_value=total_buy_value,
            total_sell_value=total_sell_value,
            estimated_profit=estimated_profit,
            recent_trades=recent_trades,
            daily_stats=daily_stats,
            hourly_patterns=hourly_patterns,
            day_of_week_patterns=dow_patterns,
            top_items=top_items[:10],  # Top 10 items
            best_trading_hours=best_hours,
            best_trading_days=best_days,
            insights=insights
        )

    def _fetch_transactions(self, character_id: int, days: int, include_corp: bool) -> list[dict]:
        """Fetch transactions from cached database table.

        Args:
            character_id: Character ID
            days: Number of days to look back
            include_corp: Include corporation transactions

        Returns:
            List of transaction dicts
        """
        transactions = []
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        try:
            with self.db.cursor() as cur:
                # Fetch from cached transactions table
                cur.execute('''
                    SELECT transaction_id, transaction_date, type_id, type_name,
                           quantity, unit_price, is_buy, location_id, client_id
                    FROM character_wallet_transactions
                    WHERE character_id = %s AND transaction_date >= %s
                    ORDER BY transaction_date DESC
                ''', (character_id, cutoff))

                for row in cur.fetchall():
                    txn_date = row['transaction_date']
                    if isinstance(txn_date, str):
                        txn_date = datetime.fromisoformat(txn_date.replace('Z', '+00:00'))
                    elif txn_date and txn_date.tzinfo is None:
                        txn_date = txn_date.replace(tzinfo=timezone.utc)

                    transactions.append({
                        'transaction_id': row['transaction_id'] or 0,
                        'date': txn_date,
                        'type_id': row['type_id'],
                        'type_name': row['type_name'] or f"Type {row['type_id']}",
                        'quantity': abs(row['quantity']) if row['quantity'] else 0,
                        'unit_price': float(row['unit_price']) if row['unit_price'] else 0,
                        'is_buy': row['is_buy'],
                        'location_id': row['location_id'],
                        'location_name': f"Location {row['location_id']}" if row['location_id'] else "Unknown",
                        'client_id': row['client_id'],
                        'is_personal': True
                    })

        except Exception as e:
            logger.warning(f"Could not fetch transactions for {character_id}: {e}")

        # Sort by date descending
        transactions.sort(key=lambda x: x['date'] if x['date'] else datetime.min.replace(tzinfo=timezone.utc), reverse=True)

        return transactions

    def _build_trade_entries(self, transactions: list[dict]) -> list[TradeEntry]:
        """Build trade entry objects from raw transactions."""
        entries = []
        for txn in transactions:
            entries.append(TradeEntry(
                transaction_id=txn['transaction_id'],
                date=txn['date'] or datetime.now(timezone.utc),
                type_id=txn['type_id'],
                type_name=txn.get('type_name', f"Type {txn['type_id']}"),
                quantity=txn['quantity'],
                unit_price=float(txn['unit_price']),
                total_value=float(txn['unit_price']) * txn['quantity'],
                is_buy=txn['is_buy'],
                location_name=str(txn.get('location_name', 'Unknown')),
                client_id=txn.get('client_id')
            ))
        return entries

    def _calculate_daily_stats(self, transactions: list[dict]) -> list[DailyStats]:
        """Calculate daily trading statistics."""
        daily = defaultdict(lambda: {
            'buy_count': 0, 'sell_count': 0,
            'buy_volume': 0, 'sell_volume': 0,
            'buy_value': 0, 'sell_value': 0,
            'items': set()
        })

        for txn in transactions:
            if not txn['date']:
                continue
            date_key = txn['date'].strftime('%Y-%m-%d')
            if txn['is_buy']:
                daily[date_key]['buy_count'] += 1
                daily[date_key]['buy_volume'] += txn['quantity']
                daily[date_key]['buy_value'] += txn['unit_price'] * txn['quantity']
            else:
                daily[date_key]['sell_count'] += 1
                daily[date_key]['sell_volume'] += txn['quantity']
                daily[date_key]['sell_value'] += txn['unit_price'] * txn['quantity']
            daily[date_key]['items'].add(txn['type_id'])

        stats = []
        for date_key in sorted(daily.keys()):
            d = daily[date_key]
            stats.append(DailyStats(
                date=date_key,
                buy_count=d['buy_count'],
                sell_count=d['sell_count'],
                buy_volume=d['buy_volume'],
                sell_volume=d['sell_volume'],
                buy_value=d['buy_value'],
                sell_value=d['sell_value'],
                profit_estimate=d['sell_value'] - d['buy_value'],
                unique_items=len(d['items'])
            ))

        return stats

    def _analyze_hourly_patterns(self, transactions: list[dict]) -> list[HourlyPattern]:
        """Analyze trading patterns by hour of day."""
        hourly = defaultdict(lambda: {'count': 0, 'total_value': 0, 'buy_count': 0})

        for txn in transactions:
            if not txn['date']:
                continue
            hour = txn['date'].hour
            value = txn['unit_price'] * txn['quantity']
            hourly[hour]['count'] += 1
            hourly[hour]['total_value'] += value
            if txn['is_buy']:
                hourly[hour]['buy_count'] += 1

        patterns = []
        for hour in range(24):
            data = hourly.get(hour, {'count': 0, 'total_value': 0, 'buy_count': 0})
            count = data['count']
            patterns.append(HourlyPattern(
                hour=hour,
                trade_count=count,
                avg_value=data['total_value'] / count if count > 0 else 0,
                buy_percentage=(data['buy_count'] / count * 100) if count > 0 else 0
            ))

        return patterns

    def _analyze_day_of_week_patterns(self, transactions: list[dict]) -> list[DayOfWeekPattern]:
        """Analyze trading patterns by day of week."""
        daily = defaultdict(lambda: {'count': 0, 'total_value': 0, 'buy_value': 0, 'sell_value': 0})

        for txn in transactions:
            if not txn['date']:
                continue
            dow = txn['date'].weekday()
            value = txn['unit_price'] * txn['quantity']
            daily[dow]['count'] += 1
            daily[dow]['total_value'] += value
            if txn['is_buy']:
                daily[dow]['buy_value'] += value
            else:
                daily[dow]['sell_value'] += value

        patterns = []
        for day in range(7):
            data = daily.get(day, {'count': 0, 'total_value': 0, 'buy_value': 0, 'sell_value': 0})
            count = data['count']
            patterns.append(DayOfWeekPattern(
                day=day,
                day_name=self.day_names[day],
                trade_count=count,
                avg_value=data['total_value'] / count if count > 0 else 0,
                profit_estimate=data['sell_value'] - data['buy_value']
            ))

        return patterns

    def _calculate_item_performance(self, transactions: list[dict]) -> list[ItemPerformance]:
        """Calculate performance metrics per item."""
        items = defaultdict(lambda: {
            'type_name': '', 'buy_count': 0, 'sell_count': 0,
            'total_bought': 0, 'total_sold': 0,
            'buy_value': 0, 'sell_value': 0,
            'first_trade': None, 'last_trade': None
        })

        for txn in transactions:
            type_id = txn['type_id']
            items[type_id]['type_name'] = txn.get('type_name', f"Type {type_id}")

            if txn['is_buy']:
                items[type_id]['buy_count'] += 1
                items[type_id]['total_bought'] += txn['quantity']
                items[type_id]['buy_value'] += txn['unit_price'] * txn['quantity']
            else:
                items[type_id]['sell_count'] += 1
                items[type_id]['total_sold'] += txn['quantity']
                items[type_id]['sell_value'] += txn['unit_price'] * txn['quantity']

            if txn['date']:
                if items[type_id]['first_trade'] is None or txn['date'] < items[type_id]['first_trade']:
                    items[type_id]['first_trade'] = txn['date']
                if items[type_id]['last_trade'] is None or txn['date'] > items[type_id]['last_trade']:
                    items[type_id]['last_trade'] = txn['date']

        performance = []
        for type_id, data in items.items():
            avg_buy = data['buy_value'] / data['total_bought'] if data['total_bought'] > 0 else 0
            avg_sell = data['sell_value'] / data['total_sold'] if data['total_sold'] > 0 else 0
            margin = ((avg_sell - avg_buy) / avg_buy * 100) if avg_buy > 0 else 0
            profit = data['sell_value'] - data['buy_value']

            # Calculate trade frequency
            total_trades = data['buy_count'] + data['sell_count']
            if data['first_trade'] and data['last_trade'] and data['first_trade'] != data['last_trade']:
                days = (data['last_trade'] - data['first_trade']).days or 1
                frequency = total_trades / days
            else:
                frequency = total_trades

            performance.append(ItemPerformance(
                type_id=type_id,
                type_name=data['type_name'],
                buy_count=data['buy_count'],
                sell_count=data['sell_count'],
                total_bought=data['total_bought'],
                total_sold=data['total_sold'],
                avg_buy_price=avg_buy,
                avg_sell_price=avg_sell,
                margin_percent=margin,
                total_profit=profit,
                trade_frequency=frequency
            ))

        # Sort by total profit
        performance.sort(key=lambda x: x.total_profit, reverse=True)
        return performance

    def _generate_insights(
        self,
        transactions: list[dict],
        hourly: list[HourlyPattern],
        dow: list[DayOfWeekPattern],
        items: list[ItemPerformance]
    ) -> list[str]:
        """Generate actionable insights from trading patterns."""
        insights = []

        # Best trading hours
        best_hours = sorted(hourly, key=lambda x: x.trade_count, reverse=True)[:3]
        if best_hours and best_hours[0].trade_count > 0:
            hours_str = ', '.join(f"{h.hour:02d}:00" for h in best_hours)
            insights.append(f"Most active trading hours: {hours_str} UTC")

        # Best trading days
        best_days = sorted(dow, key=lambda x: x.profit_estimate, reverse=True)[:2]
        if best_days and best_days[0].profit_estimate > 0:
            days_str = ' and '.join(d.day_name for d in best_days)
            insights.append(f"Most profitable days: {days_str}")

        # Top performing items
        profitable_items = [i for i in items if i.total_profit > 0][:3]
        if profitable_items:
            items_str = ', '.join(i.type_name for i in profitable_items)
            insights.append(f"Top profit items: {items_str}")

        # Items with negative performance
        losing_items = [i for i in items if i.total_profit < 0]
        if losing_items:
            worst = sorted(losing_items, key=lambda x: x.total_profit)[:3]
            items_str = ', '.join(i.type_name for i in worst)
            insights.append(f"Items losing ISK: {items_str} - consider adjusting strategy")

        # High margin items
        high_margin = [i for i in items if i.margin_percent > 20 and i.sell_count > 0]
        if high_margin:
            margin_str = ', '.join(f"{i.type_name} ({i.margin_percent:.1f}%)" for i in high_margin[:3])
            insights.append(f"High margin items: {margin_str}")

        # Weekend vs weekday
        weekday_profit = sum(d.profit_estimate for d in dow if d.day < 5)
        weekend_profit = sum(d.profit_estimate for d in dow if d.day >= 5)
        if weekday_profit > weekend_profit * 2:
            insights.append("Weekdays significantly more profitable than weekends")
        elif weekend_profit > weekday_profit * 2:
            insights.append("Weekends significantly more profitable than weekdays")

        if not insights:
            insights.append("Consistent trading pattern detected. Keep monitoring for trends.")

        return insights
