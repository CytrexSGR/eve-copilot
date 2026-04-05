"""Trading analytics service for market-service.

This is a simplified version that works with database directly,
adapted from the monolith's TradingAnalyticsService.
"""

import logging
from datetime import datetime, date, timedelta, timezone
from typing import List, Dict

from app.services.trading.models import (
    ItemPnL,
    TradingPnLReport,
    ItemVelocity,
    VelocityReport,
    MarginAlert,
    CompetitorInfo,
    CompetitionReport,
    TradingSummary,
)
from eve_shared.constants import JITA_REGION_ID

logger = logging.getLogger(__name__)


class TradingAnalyticsService:
    """Service for trading analytics and P&L calculations.

    Simplified version that works with cached transaction data from database.
    """

    def __init__(self, db_pool):
        """Initialize with database pool.

        Args:
            db_pool: Database connection pool (eve_shared)
        """
        self.db = db_pool

    def _get_transactions(self, character_id: int, days: int = 30) -> List[Dict]:
        """Get cached transactions from database.

        Args:
            character_id: Character ID
            days: Lookback period

        Returns:
            List of transaction dicts
        """
        transactions = []
        start_date = datetime.now(timezone.utc) - timedelta(days=days)

        try:
            with self.db.cursor() as cur:
                # Try to get from cached transactions table
                cur.execute('''
                    SELECT type_id, type_name, quantity, unit_price, is_buy, transaction_date
                    FROM character_wallet_transactions
                    WHERE character_id = %s AND transaction_date >= %s
                    ORDER BY transaction_date DESC
                ''', (character_id, start_date))

                for row in cur.fetchall():
                    transactions.append({
                        'type_id': row['type_id'],
                        'type_name': row['type_name'] or 'Unknown',
                        'quantity': row['quantity'],
                        'unit_price': float(row['unit_price']) if row['unit_price'] else 0,
                        'is_buy': row['is_buy'],
                        'date': row['transaction_date'],
                    })

        except Exception as e:
            logger.warning(f"Could not fetch transactions for {character_id}: {e}")
            # Return empty list if table doesn't exist

        return transactions

    def calculate_pnl(
        self,
        character_id: int,
        include_corp: bool = True,
        days: int = 30
    ) -> TradingPnLReport:
        """Calculate P&L from transactions.

        Uses simple average cost basis calculation.

        Args:
            character_id: Character ID
            include_corp: Include corp transactions (not yet implemented)
            days: Lookback period in days

        Returns:
            TradingPnLReport with item-level P&L
        """
        all_txns = self._get_transactions(character_id, days)

        # Group by item
        by_item: Dict[int, Dict] = {}

        for txn in all_txns:
            type_id = txn['type_id']

            if type_id not in by_item:
                by_item[type_id] = {
                    'type_id': type_id,
                    'type_name': txn['type_name'],
                    'buys': [],
                    'sells': [],
                    'total_bought': 0,
                    'total_sold': 0,
                    'total_buy_value': 0,
                    'total_sell_value': 0,
                    'first_trade': txn['date'],
                    'last_trade': txn['date'],
                }

            item = by_item[type_id]

            if txn['is_buy']:
                item['buys'].append({
                    'qty': abs(txn['quantity']),
                    'price': txn['unit_price']
                })
                item['total_bought'] += abs(txn['quantity'])
                item['total_buy_value'] += abs(txn['quantity']) * txn['unit_price']
            else:
                item['sells'].append({
                    'qty': abs(txn['quantity']),
                    'price': txn['unit_price']
                })
                item['total_sold'] += abs(txn['quantity'])
                item['total_sell_value'] += abs(txn['quantity']) * txn['unit_price']

            if txn['date'] and txn['date'] < item['first_trade']:
                item['first_trade'] = txn['date']
            if txn['date'] and txn['date'] > item['last_trade']:
                item['last_trade'] = txn['date']

        # Calculate P&L per item
        items = []
        total_realized = 0
        total_unrealized = 0

        for type_id, data in by_item.items():
            # Calculate averages
            avg_buy = data['total_buy_value'] / data['total_bought'] if data['total_bought'] > 0 else 0
            avg_sell = data['total_sell_value'] / data['total_sold'] if data['total_sold'] > 0 else 0

            # Inventory
            inventory = data['total_bought'] - data['total_sold']

            # Realized P&L (sold items)
            realized_pnl = data['total_sell_value'] - (data['total_sold'] * avg_buy) if data['total_sold'] > 0 else 0

            # For unrealized P&L, use average sell price as proxy for market
            current_price = avg_sell if avg_sell > 0 else avg_buy
            unrealized_pnl = (inventory * current_price) - (inventory * avg_buy) if inventory > 0 else 0

            # Margin
            margin_pct = ((avg_sell - avg_buy) / avg_buy * 100) if avg_buy > 0 and avg_sell > 0 else 0

            # ROI
            roi_pct = (realized_pnl / data['total_buy_value'] * 100) if data['total_buy_value'] > 0 else 0

            item_pnl = ItemPnL(
                type_id=type_id,
                type_name=data['type_name'],
                total_bought=data['total_bought'],
                total_sold=data['total_sold'],
                current_inventory=inventory,
                total_buy_value=data['total_buy_value'],
                total_sell_value=data['total_sell_value'],
                realized_pnl=round(realized_pnl, 2),
                unrealized_pnl=round(unrealized_pnl, 2),
                avg_buy_price=round(avg_buy, 2),
                avg_sell_price=round(avg_sell, 2),
                current_market_price=round(current_price, 2),
                margin_percent=round(margin_pct, 2),
                roi_percent=round(roi_pct, 2),
                first_trade_at=data['first_trade'],
                last_trade_at=data['last_trade'],
            )

            items.append(item_pnl)
            total_realized += realized_pnl
            total_unrealized += unrealized_pnl

        # Sort by realized P&L
        items.sort(key=lambda x: x.realized_pnl, reverse=True)

        # Top winners/losers
        top_winners = [i for i in items if i.realized_pnl > 0][:10]
        top_losers = sorted([i for i in items if i.realized_pnl < 0], key=lambda x: x.realized_pnl)[:10]

        return TradingPnLReport(
            character_id=character_id,
            corporation_id=None,
            include_corp=include_corp,
            total_realized_pnl=round(total_realized, 2),
            total_unrealized_pnl=round(total_unrealized, 2),
            total_pnl=round(total_realized + total_unrealized, 2),
            items=items,
            top_winners=top_winners,
            top_losers=top_losers,
            period_start=date.today() - timedelta(days=days),
            period_end=date.today(),
        )

    def get_margin_alerts(
        self,
        character_id: int,
        threshold_percent: float = 10.0
    ) -> List[MarginAlert]:
        """Get items with low or negative margins.

        Args:
            character_id: Character ID
            threshold_percent: Alert when margin below this

        Returns:
            List of MarginAlert for items needing attention
        """
        alerts = []

        try:
            with self.db.cursor() as cur:
                # Get active orders with market prices
                cur.execute('''
                    SELECT o.type_id, t."typeName", o.price, o.is_buy_order, mp.lowest_sell
                    FROM character_market_orders o
                    LEFT JOIN "invTypes" t ON o.type_id = t."typeID"
                    LEFT JOIN market_prices mp ON o.type_id = mp.type_id AND mp.region_id = %s
                    WHERE o.character_id = %s AND o.state = 'open'
                ''', (JITA_REGION_ID, character_id))

                for row in cur.fetchall():
                    type_id = row['type_id']
                    type_name = row['typeName'] or f'Type {type_id}'
                    your_price = float(row['price']) if row['price'] else 0
                    is_buy = row['is_buy_order']
                    market_price = float(row['lowest_sell']) if row['lowest_sell'] else 0

                    if not is_buy and market_price > 0:  # Sell orders
                        margin = ((your_price - market_price) / market_price * 100)

                        if margin < 0:
                            alerts.append(MarginAlert(
                                type_id=type_id,
                                type_name=type_name,
                                your_price=your_price,
                                market_price=market_price,
                                margin_percent=round(margin, 2),
                                alert_type='margin_negative',
                                severity='critical'
                            ))
                        elif margin < threshold_percent:
                            alerts.append(MarginAlert(
                                type_id=type_id,
                                type_name=type_name,
                                your_price=your_price,
                                market_price=market_price,
                                margin_percent=round(margin, 2),
                                alert_type='margin_low',
                                severity='warning'
                            ))

        except Exception as e:
            logger.warning(f"Could not fetch margin alerts for {character_id}: {e}")

        return alerts

    def get_trading_summary(
        self,
        character_id: int,
        include_corp: bool = True
    ) -> TradingSummary:
        """Get quick trading summary for dashboard.

        Args:
            character_id: Character ID
            include_corp: Include corp data

        Returns:
            TradingSummary with key metrics
        """
        pnl = self.calculate_pnl(character_id, include_corp, days=30)
        alerts = self.get_margin_alerts(character_id, threshold_percent=10.0)

        return TradingSummary(
            character_id=character_id,
            total_realized_pnl=pnl.total_realized_pnl,
            total_unrealized_pnl=pnl.total_unrealized_pnl,
            total_pnl=pnl.total_pnl,
            items_traded=len(pnl.items),
            profitable_items=len([i for i in pnl.items if i.realized_pnl > 0]),
            losing_items=len([i for i in pnl.items if i.realized_pnl < 0]),
            margin_alerts=len(alerts),
            critical_alerts=len([a for a in alerts if a.severity == 'critical']),
            top_winner=pnl.top_winners[0] if pnl.top_winners else None,
            top_loser=pnl.top_losers[0] if pnl.top_losers else None,
        )

    def get_velocity_report(
        self,
        character_id: int,
        include_corp: bool = True
    ) -> VelocityReport:
        """Calculate velocity metrics for all traded items.

        Args:
            character_id: Character ID
            include_corp: Include corp transactions

        Returns:
            VelocityReport with items classified by velocity
        """
        all_txns = self._get_transactions(character_id, days=30)

        now = datetime.now(timezone.utc)
        seven_days_ago = now - timedelta(days=7)
        thirty_days_ago = now - timedelta(days=30)

        # Group by item with time-based volumes
        by_item: Dict[int, Dict] = {}

        for txn in all_txns:
            type_id = txn['type_id']

            if type_id not in by_item:
                by_item[type_id] = {
                    'type_id': type_id,
                    'type_name': txn['type_name'],
                    'bought_7d': 0,
                    'sold_7d': 0,
                    'bought_30d': 0,
                    'sold_30d': 0,
                    'total_bought': 0,
                    'total_sold': 0,
                    'first_trade': txn['date'],
                    'last_trade': txn['date'],
                }

            item = by_item[type_id]
            qty = abs(txn['quantity'])
            txn_date = txn['date']

            if txn['is_buy']:
                item['total_bought'] += qty
                if txn_date and txn_date >= thirty_days_ago:
                    item['bought_30d'] += qty
                if txn_date and txn_date >= seven_days_ago:
                    item['bought_7d'] += qty
            else:
                item['total_sold'] += qty
                if txn_date and txn_date >= thirty_days_ago:
                    item['sold_30d'] += qty
                if txn_date and txn_date >= seven_days_ago:
                    item['sold_7d'] += qty

            if txn_date and item['first_trade'] and txn_date < item['first_trade']:
                item['first_trade'] = txn_date
            if txn_date and item['last_trade'] and txn_date > item['last_trade']:
                item['last_trade'] = txn_date

        # Calculate velocity metrics for each item
        items: List[ItemVelocity] = []

        for type_id, data in by_item.items():
            # Current inventory
            inventory = data['total_bought'] - data['total_sold']

            # Average daily sales (30 day basis)
            avg_daily_sales = data['sold_30d'] / 30.0 if data['sold_30d'] > 0 else 0

            # Days to sell current inventory
            days_to_sell = None
            if inventory > 0 and avg_daily_sales > 0:
                days_to_sell = round(inventory / avg_daily_sales, 1)

            # Annualized turnover rate
            avg_inventory = (data['total_bought'] + inventory) / 2 if data['total_bought'] > 0 else 0
            turnover = 0.0
            if avg_inventory > 0:
                turnover = (data['sold_30d'] / avg_inventory) * 12  # Annualized from 30d

            # Classify velocity
            if avg_daily_sales >= 10:
                velocity_class = 'fast'
            elif avg_daily_sales >= 1:
                velocity_class = 'medium'
            elif data['sold_30d'] > 0:
                velocity_class = 'slow'
            elif inventory > 0:
                velocity_class = 'dead'
            else:
                velocity_class = 'sold_out'

            vel = ItemVelocity(
                type_id=type_id,
                type_name=data['type_name'],
                volume_bought_7d=data['bought_7d'],
                volume_sold_7d=data['sold_7d'],
                volume_bought_30d=data['bought_30d'],
                volume_sold_30d=data['sold_30d'],
                avg_daily_volume=round(avg_daily_sales, 2),
                days_to_sell=days_to_sell,
                turnover_rate=round(turnover, 2),
                velocity_class=velocity_class,
            )
            items.append(vel)

        # Classify into buckets
        fast_movers = sorted(
            [i for i in items if i.velocity_class == 'fast'],
            key=lambda x: x.avg_daily_volume,
            reverse=True
        )
        slow_movers = sorted(
            [i for i in items if i.velocity_class in ('medium', 'slow')],
            key=lambda x: x.days_to_sell or float('inf')
        )
        dead_stock = [i for i in items if i.velocity_class == 'dead']

        return VelocityReport(
            character_id=character_id,
            fast_movers=fast_movers[:20],
            slow_movers=slow_movers[:20],
            dead_stock=dead_stock,
        )

    def _get_auth_client(self):
        """Get auth service client for token retrieval."""
        import httpx
        from app.config import settings
        return httpx.Client(base_url=settings.auth_service_url, timeout=10.0)

    def _get_all_characters(self) -> List[Dict]:
        """Get all registered characters from auth service.

        Returns:
            List of dicts with character_id and character_name
        """
        try:
            with self._get_auth_client() as client:
                response = client.get("/api/auth/characters")
                if response.status_code == 200:
                    data = response.json()
                    return data.get("characters", [])
                return []
        except Exception as e:
            logger.warning(f"Failed to get characters: {e}")
            return []

    def _get_character_token(self, character_id: int) -> str:
        """Get valid access token for character from auth service."""
        try:
            with self._get_auth_client() as client:
                response = client.get(f"/api/auth/token/{character_id}")
                if response.status_code == 200:
                    data = response.json()
                    return data.get("access_token")
                return None
        except Exception as e:
            logger.warning(f"Failed to get token for {character_id}: {e}")
            return None

    def _get_character_orders_from_esi(self, character_id: int, token: str) -> List[dict]:
        """Get market orders for a character via ESI."""
        import httpx
        from app.config import settings

        try:
            with httpx.Client(timeout=settings.esi_timeout) as client:
                response = client.get(
                    f"{settings.esi_base_url}/characters/{character_id}/orders/",
                    headers={"Authorization": f"Bearer {token}"},
                    params={"datasource": "tranquility"}
                )
                if response.status_code == 200:
                    return response.json()
                return []
        except Exception as e:
            logger.warning(f"Failed to get ESI orders for {character_id}: {e}")
            return []

    def _get_type_name(self, type_id: int) -> str:
        """Get item name from database."""
        try:
            with self.db.cursor() as cur:
                cur.execute(
                    'SELECT "typeName" FROM "invTypes" WHERE "typeID" = %s',
                    (type_id,)
                )
                row = cur.fetchone()
                if row:
                    return row["typeName"]
        except Exception:
            pass
        return f"Type {type_id}"

    def _get_station_name(self, location_id: int) -> str:
        """Get station name from database."""
        try:
            with self.db.cursor() as cur:
                cur.execute(
                    'SELECT "stationName" FROM "staStations" WHERE "stationID" = %s',
                    (location_id,)
                )
                row = cur.fetchone()
                if row:
                    return row["stationName"]
        except Exception:
            pass
        return f"Station {location_id}"

    def _get_market_prices(self, type_id: int, region_id: int) -> dict:
        """Get market prices from cache."""
        try:
            with self.db.cursor() as cur:
                cur.execute(
                    '''SELECT lowest_sell, highest_buy FROM market_prices
                       WHERE type_id = %s AND region_id = %s''',
                    (type_id, region_id)
                )
                row = cur.fetchone()
                if row:
                    return {
                        'lowest_sell': float(row['lowest_sell']) if row['lowest_sell'] else 0,
                        'highest_buy': float(row['highest_buy']) if row['highest_buy'] else 0
                    }
        except Exception:
            pass
        return {'lowest_sell': 0, 'highest_buy': 0}

    def get_competition_report(
        self,
        character_id: int,
        include_corp: bool = True
    ) -> CompetitionReport:
        """Analyze competitive position for all active orders.

        Fetches orders directly from ESI and compares with cached market prices.

        Args:
            character_id: Character ID
            include_corp: If True, aggregate orders from ALL registered characters

        Returns:
            CompetitionReport with competitive position analysis
        """
        sell_orders: List[CompetitorInfo] = []
        buy_orders: List[CompetitorInfo] = []

        undercut_count = 0
        outbid_count = 0
        competitive_count = 0
        total_orders = 0

        # Determine which characters to fetch orders for
        if include_corp:
            # Fetch from all registered characters
            all_chars = self._get_all_characters()
            characters_to_fetch = [
                (c['character_id'], c['character_name'])
                for c in all_chars
                if c.get('is_valid', True)
            ]
            if not characters_to_fetch:
                # Fallback to single character if no characters found
                characters_to_fetch = [(character_id, None)]
        else:
            # Just the selected character
            characters_to_fetch = [(character_id, None)]

        # Process orders for each character
        for char_id, char_name in characters_to_fetch:
            token = self._get_character_token(char_id)
            if not token:
                logger.warning(f"No token available for character {char_id}")
                continue

            # Fetch orders from ESI
            esi_orders = self._get_character_orders_from_esi(char_id, token)

            for order in esi_orders:
                type_id = order.get('type_id')
                your_price = float(order.get('price', 0))
                is_buy = order.get('is_buy_order', False)
                volume_remain = order.get('volume_remain', 0)
                location_id = order.get('location_id', 0)
                region_id = order.get('region_id', JITA_REGION_ID)  # Default to The Forge

                # Get type name and location name
                type_name = self._get_type_name(type_id)
                location_name = self._get_station_name(location_id)

                # Get market prices for comparison
                prices = self._get_market_prices(type_id, region_id)
                market_price = prices['highest_buy'] if is_buy else prices['lowest_sell']

                total_orders += 1

                # Determine position and status
                if is_buy:
                    if market_price > 0 and your_price < market_price:
                        position = 2
                        status = 'outbid'
                        outbid_count += 1
                    else:
                        position = 1
                        status = 'ok'
                        competitive_count += 1
                else:
                    if market_price > 0 and your_price > market_price:
                        position = 2
                        status = 'undercut'
                        undercut_count += 1
                    else:
                        position = 1
                        status = 'ok'
                        competitive_count += 1

                # Calculate price gap
                price_gap = abs(your_price - market_price) if market_price > 0 else 0
                price_gap_pct = (price_gap / market_price * 100) if market_price > 0 else 0

                info = CompetitorInfo(
                    type_id=type_id,
                    type_name=type_name,
                    region_id=region_id,
                    location_name=location_name,
                    character_id=char_id,
                    character_name=char_name,
                    our_position=position,
                    total_competitors=1,
                    best_price=market_price,
                    our_price=your_price,
                    price_gap=round(price_gap, 2),
                    price_gap_percent=round(price_gap_pct, 2),
                    is_buy_order=is_buy,
                    volume_remain=volume_remain,
                    status=status,
                )

                if is_buy:
                    buy_orders.append(info)
                else:
                    sell_orders.append(info)

        # Sort: undercut/outbid first, then by price gap
        sell_orders.sort(key=lambda x: (0 if x.status == 'undercut' else 1, -x.price_gap_percent))
        buy_orders.sort(key=lambda x: (0 if x.status == 'outbid' else 1, -x.price_gap_percent))

        return CompetitionReport(
            character_id=character_id,
            total_orders=total_orders,
            competitive_orders=competitive_count,
            undercut_orders=undercut_count,
            outbid_orders=outbid_count,
            sell_orders=sell_orders,
            buy_orders=buy_orders,
        )
