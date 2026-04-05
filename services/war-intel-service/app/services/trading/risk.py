# app/services/trading/risk.py
"""Risk Management Service for trading portfolio analysis.

Uses eve_shared pattern for database access.
"""

from pydantic import BaseModel
from app.database import db_cursor


class ConcentrationRisk(BaseModel):
    """Single item concentration risk."""
    type_id: int
    type_name: str
    value: float
    percent_of_portfolio: float
    order_count: int
    is_concentrated: bool  # >10% of portfolio
    risk_level: str  # 'low', 'medium', 'high', 'critical'


class LiquidityRisk(BaseModel):
    """Single item liquidity risk."""
    type_id: int
    type_name: str
    your_volume: int
    market_daily_volume: float
    days_to_sell: float | None
    liquidity_score: float  # 0-100, higher is more liquid
    risk_level: str  # 'low', 'medium', 'high', 'critical'


class ExposureRisk(BaseModel):
    """Value at risk from price movements."""
    type_id: int
    type_name: str
    position_value: float
    price_volatility_7d: float  # % change over 7 days
    value_at_risk_5pct: float  # Estimated loss at 5% price drop
    risk_level: str


class RiskSummary(BaseModel):
    """Overall risk summary."""
    total_portfolio_value: float
    total_orders: int
    concentration_score: float  # 0-100, lower is better
    liquidity_score: float  # 0-100, higher is better
    overall_risk_level: str  # 'low', 'medium', 'high', 'critical'
    top_concentration_risks: list[ConcentrationRisk]
    top_liquidity_risks: list[LiquidityRisk]
    recommendations: list[str]


class RiskManagementService:
    """Service for analyzing trading portfolio risks."""

    def get_risk_summary(
        self,
        character_id: int,
        include_corp: bool = True,
        concentration_threshold: float = 10.0,
        liquidity_threshold: float = 7.0  # Days to sell
    ) -> RiskSummary:
        """Get comprehensive risk summary for trading portfolio."""

        # Get concentration risks
        concentration_risks = self._analyze_concentration(
            character_id, include_corp, concentration_threshold
        )

        # Get liquidity risks
        liquidity_risks = self._analyze_liquidity(
            character_id, include_corp, liquidity_threshold
        )

        # Calculate overall scores
        total_value = sum(c.value for c in concentration_risks) if concentration_risks else 0
        total_orders = sum(c.order_count for c in concentration_risks) if concentration_risks else 0

        # Concentration score (lower = better diversified)
        if concentration_risks:
            max_concentration = max(c.percent_of_portfolio for c in concentration_risks)
            # Herfindahl-like index (simplified)
            hhi = sum((c.percent_of_portfolio / 100) ** 2 for c in concentration_risks) * 10000
            concentration_score = min(100, hhi / 100)  # Normalize to 0-100
        else:
            max_concentration = 0
            concentration_score = 0

        # Liquidity score (higher = more liquid)
        if liquidity_risks:
            avg_liquidity = sum(l.liquidity_score for l in liquidity_risks) / len(liquidity_risks)
            liquidity_score = avg_liquidity
        else:
            liquidity_score = 100

        # Overall risk level
        critical_concentration = len([c for c in concentration_risks if c.risk_level == 'critical'])
        high_concentration = len([c for c in concentration_risks if c.risk_level == 'high'])
        critical_liquidity = len([l for l in liquidity_risks if l.risk_level == 'critical'])
        high_liquidity = len([l for l in liquidity_risks if l.risk_level == 'high'])

        if critical_concentration > 0 or critical_liquidity > 2:
            overall_risk = 'critical'
        elif high_concentration > 0 or critical_liquidity > 0 or high_liquidity > 3:
            overall_risk = 'high'
        elif high_liquidity > 0 or concentration_score > 50:
            overall_risk = 'medium'
        else:
            overall_risk = 'low'

        # Generate recommendations
        recommendations = self._generate_recommendations(
            concentration_risks, liquidity_risks, concentration_score, liquidity_score
        )

        return RiskSummary(
            total_portfolio_value=total_value,
            total_orders=total_orders,
            concentration_score=round(concentration_score, 1),
            liquidity_score=round(liquidity_score, 1),
            overall_risk_level=overall_risk,
            top_concentration_risks=sorted(
                [c for c in concentration_risks if c.is_concentrated],
                key=lambda x: x.percent_of_portfolio,
                reverse=True
            )[:10],
            top_liquidity_risks=sorted(
                [l for l in liquidity_risks if l.risk_level in ('critical', 'high', 'medium')],
                key=lambda x: x.days_to_sell if x.days_to_sell else 999,
                reverse=True
            )[:10],
            recommendations=recommendations
        )

    def _analyze_concentration(
        self,
        character_id: int,
        include_corp: bool,
        threshold: float
    ) -> list[ConcentrationRisk]:
        """Analyze portfolio concentration by item type."""

        with db_cursor() as cur:
            # Get all active sell orders with values
            query = """
            WITH order_values AS (
                SELECT
                    o.type_id,
                    t."typeName" as type_name,
                    SUM(o.price * o.volume_remain) as total_value,
                    COUNT(*) as order_count
                FROM character_orders o
                JOIN "invTypes" t ON o.type_id = t."typeID"
                WHERE o.character_id = %s
                  AND o.is_buy_order = false
                  AND o.state = 'active'
                GROUP BY o.type_id, t."typeName"
            )
            SELECT
                type_id,
                type_name,
                total_value,
                order_count,
                total_value * 100.0 / NULLIF(SUM(total_value) OVER (), 0) as percent_of_total
            FROM order_values
            ORDER BY total_value DESC
            """
            cur.execute(query, (character_id,))
            rows = cur.fetchall()

        if not rows:
            return []

        results = []
        for row in rows:
            type_id = row['type_id']
            type_name = row['type_name']
            value = row['total_value']
            order_count = row['order_count']
            pct = row['percent_of_total'] or 0

            # Determine risk level based on concentration
            if pct >= 25:
                risk_level = 'critical'
            elif pct >= 15:
                risk_level = 'high'
            elif pct >= threshold:
                risk_level = 'medium'
            else:
                risk_level = 'low'

            results.append(ConcentrationRisk(
                type_id=type_id,
                type_name=type_name or f"Type {type_id}",
                value=value or 0,
                percent_of_portfolio=round(pct, 2),
                order_count=order_count,
                is_concentrated=pct >= threshold,
                risk_level=risk_level
            ))

        return results

    def _analyze_liquidity(
        self,
        character_id: int,
        include_corp: bool,
        threshold_days: float
    ) -> list[LiquidityRisk]:
        """Analyze liquidity risk based on market volume vs position size."""

        with db_cursor() as cur:
            # Get sell orders with market volume data from market_prices
            # Using Jita (region 10000002) as reference for volume
            query = """
            WITH my_orders AS (
                SELECT
                    o.type_id,
                    t."typeName" as type_name,
                    SUM(o.volume_remain) as my_volume
                FROM character_orders o
                JOIN "invTypes" t ON o.type_id = t."typeID"
                WHERE o.character_id = %s
                  AND o.is_buy_order = false
                  AND o.state = 'active'
                GROUP BY o.type_id, t."typeName"
            )
            SELECT
                m.type_id,
                m.type_name,
                m.my_volume,
                COALESCE(mp.sell_volume, 100) / 7.0 as market_daily_volume
            FROM my_orders m
            LEFT JOIN market_prices mp ON m.type_id = mp.type_id AND mp.region_id = 10000002
            ORDER BY m.my_volume DESC
            """
            cur.execute(query, (character_id,))
            rows = cur.fetchall()

        if not rows:
            return []

        results = []
        for row in rows:
            type_id = row['type_id']
            type_name = row['type_name']
            my_volume = row['my_volume']
            market_volume = row['market_daily_volume']

            # Calculate days to sell
            if market_volume and market_volume > 0:
                days_to_sell = my_volume / market_volume
            else:
                days_to_sell = None  # Unknown/very low market volume

            # Calculate liquidity score (0-100)
            if days_to_sell is None:
                liquidity_score = 10  # Very illiquid
            elif days_to_sell <= 1:
                liquidity_score = 100
            elif days_to_sell <= 3:
                liquidity_score = 80
            elif days_to_sell <= 7:
                liquidity_score = 60
            elif days_to_sell <= 14:
                liquidity_score = 40
            elif days_to_sell <= 30:
                liquidity_score = 20
            else:
                liquidity_score = 10

            # Determine risk level
            if days_to_sell is None or days_to_sell > 30:
                risk_level = 'critical'
            elif days_to_sell > 14:
                risk_level = 'high'
            elif days_to_sell > threshold_days:
                risk_level = 'medium'
            else:
                risk_level = 'low'

            results.append(LiquidityRisk(
                type_id=type_id,
                type_name=type_name or f"Type {type_id}",
                your_volume=my_volume,
                market_daily_volume=round(market_volume or 0, 1),
                days_to_sell=round(days_to_sell, 1) if days_to_sell else None,
                liquidity_score=liquidity_score,
                risk_level=risk_level
            ))

        return results

    def _generate_recommendations(
        self,
        concentration_risks: list[ConcentrationRisk],
        liquidity_risks: list[LiquidityRisk],
        concentration_score: float,
        liquidity_score: float
    ) -> list[str]:
        """Generate actionable recommendations based on risks."""

        recommendations = []

        # Concentration recommendations
        critical_concentration = [c for c in concentration_risks if c.risk_level == 'critical']
        if critical_concentration:
            items = ', '.join(c.type_name for c in critical_concentration[:3])
            recommendations.append(
                f"Critical concentration: {items} represent over 25% each. "
                "Consider diversifying to reduce single-item risk."
            )

        high_concentration = [c for c in concentration_risks if c.risk_level == 'high']
        if high_concentration and not critical_concentration:
            recommendations.append(
                f"{len(high_concentration)} items have high concentration (15-25%). "
                "Monitor these positions closely."
            )

        if concentration_score > 70:
            recommendations.append(
                "Portfolio is highly concentrated. Consider spreading across more items "
                "to reduce risk from price swings on any single item."
            )

        # Liquidity recommendations
        critical_liquidity = [l for l in liquidity_risks if l.risk_level == 'critical']
        if critical_liquidity:
            items = ', '.join(l.type_name for l in critical_liquidity[:3])
            recommendations.append(
                f"Dead stock warning: {items} may take 30+ days to sell. "
                "Consider repricing or liquidating these positions."
            )

        high_liquidity = [l for l in liquidity_risks if l.risk_level == 'high']
        if high_liquidity and not critical_liquidity:
            recommendations.append(
                f"{len(high_liquidity)} items have low liquidity (14-30 days to sell). "
                "These positions tie up capital for extended periods."
            )

        if liquidity_score < 50:
            recommendations.append(
                "Low overall liquidity score. Many positions may be difficult to exit quickly. "
                "Consider moving to faster-selling items."
            )

        # Positive recommendations
        if concentration_score < 30 and liquidity_score > 70:
            recommendations.append(
                "Portfolio is well-diversified with good liquidity. "
                "Current risk profile is healthy."
            )

        if not recommendations:
            recommendations.append(
                "No significant risks detected. Continue monitoring your positions."
            )

        return recommendations

    def get_concentration_details(
        self,
        character_id: int,
        include_corp: bool = True
    ) -> list[ConcentrationRisk]:
        """Get detailed concentration analysis for all items."""
        return self._analyze_concentration(character_id, include_corp, 0)

    def get_liquidity_details(
        self,
        character_id: int,
        include_corp: bool = True
    ) -> list[LiquidityRisk]:
        """Get detailed liquidity analysis for all items."""
        return self._analyze_liquidity(character_id, include_corp, 0)
