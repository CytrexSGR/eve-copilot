"""Tests for market price analysis, trading recommendations, risk factors, and strategies."""

from datetime import datetime, timedelta

import pytest

from app.models.price import MarketPrice, PriceSource, CacheStats
from app.models.thera import TheraConnection, ShipSize, SecurityClass, HubType
from app.routers.trading_opportunities import TradingOpportunitiesService
from app.routers.trading_opportunities_v2 import (
    REGION_NAMES,
    calculate_risk_factors,
    calculate_recommendation,
    calculate_strategy,
)


# ---------------------------------------------------------------------------
# MarketPrice.is_stale
# ---------------------------------------------------------------------------


class TestMarketPriceIsStale:
    """Test MarketPrice staleness detection."""

    def test_fresh_price_not_stale(self):
        """Price updated just now is not stale."""
        mp = MarketPrice(
            type_id=34,
            sell_price=5.0,
            buy_price=4.0,
            last_updated=datetime.utcnow(),
        )
        assert mp.is_stale(max_age_seconds=3600) is False

    def test_old_price_is_stale(self):
        """Price older than max_age is stale."""
        mp = MarketPrice(
            type_id=34,
            sell_price=5.0,
            buy_price=4.0,
            last_updated=datetime.utcnow() - timedelta(hours=2),
        )
        assert mp.is_stale(max_age_seconds=3600) is True

    def test_custom_max_age(self):
        """Custom max_age_seconds threshold works."""
        mp = MarketPrice(
            type_id=34,
            sell_price=5.0,
            buy_price=4.0,
            last_updated=datetime.utcnow() - timedelta(seconds=30),
        )
        assert mp.is_stale(max_age_seconds=60) is False
        assert mp.is_stale(max_age_seconds=10) is True

    def test_exactly_at_boundary(self):
        """Price exactly at the boundary is not stale (> not >=)."""
        mp = MarketPrice(
            type_id=34,
            sell_price=5.0,
            buy_price=4.0,
            last_updated=datetime.utcnow() - timedelta(seconds=3600),
        )
        # At exactly 3600 seconds, total_seconds() should be ~3600
        # Due to execution time, this should be stale
        assert mp.is_stale(max_age_seconds=3600) is True


# ---------------------------------------------------------------------------
# MarketPrice defaults and fields
# ---------------------------------------------------------------------------


class TestMarketPriceDefaults:
    """Test MarketPrice Pydantic model defaults and validation."""

    def test_default_region_is_jita(self):
        """Default region should be Jita (10000002)."""
        mp = MarketPrice(type_id=34)
        assert mp.region_id == 10000002

    def test_default_source_unknown(self):
        """Default source should be 'unknown'."""
        mp = MarketPrice(type_id=34)
        assert mp.source == "unknown"

    def test_default_prices_zero(self):
        """Default prices should be 0.0."""
        mp = MarketPrice(type_id=34)
        assert mp.sell_price == 0.0
        assert mp.buy_price == 0.0
        assert mp.adjusted_price == 0.0
        assert mp.average_price == 0.0

    def test_source_enum_values(self):
        """PriceSource enum values match expected strings."""
        assert PriceSource.REDIS == "redis"
        assert PriceSource.CACHE == "cache"
        assert PriceSource.ESI == "esi"
        assert PriceSource.UNKNOWN == "unknown"


# ---------------------------------------------------------------------------
# CacheStats model
# ---------------------------------------------------------------------------


class TestCacheStats:
    """Test CacheStats model."""

    def test_empty_cache_is_stale(self):
        """Empty cache should be stale."""
        stats = CacheStats(total_items=0, is_stale=True)
        assert stats.is_stale is True
        assert stats.total_items == 0

    def test_populated_cache(self):
        """Populated cache with recent data."""
        now = datetime.utcnow()
        stats = CacheStats(
            total_items=5000,
            oldest_entry=now - timedelta(minutes=50),
            newest_entry=now - timedelta(minutes=5),
            cache_age_seconds=300,
            is_stale=False,
        )
        assert stats.total_items == 5000
        assert stats.is_stale is False


# ---------------------------------------------------------------------------
# TheraConnection.supports_ship_size
# ---------------------------------------------------------------------------


class TestTheraConnectionSupportsShipSize:
    """Test wormhole ship size compatibility check."""

    @pytest.fixture
    def connection(self):
        """Create a test Thera connection with 'large' max ship size."""
        return TheraConnection(
            id="test-1",
            wh_type="H296",
            max_ship_size="large",
            remaining_hours=12,
            expires_at=datetime.utcnow() + timedelta(hours=12),
            out_system_id=31000005,
            out_system_name="Thera",
            out_signature="ABC-123",
            in_system_id=30000142,
            in_system_name="Jita",
            in_system_class="hs",
            in_region_id=10000002,
            in_region_name="The Forge",
        )

    def test_medium_fits_large(self, connection):
        """Medium ships fit through large wormholes."""
        assert connection.supports_ship_size("medium") is True

    def test_large_fits_large(self, connection):
        """Large ships fit through large wormholes."""
        assert connection.supports_ship_size("large") is True

    def test_xlarge_doesnt_fit_large(self, connection):
        """XLarge ships don't fit through large wormholes."""
        assert connection.supports_ship_size("xlarge") is False

    def test_capital_doesnt_fit_large(self, connection):
        """Capitals don't fit through large wormholes."""
        assert connection.supports_ship_size("capital") is False

    def test_invalid_size_returns_false(self, connection):
        """Invalid ship size returns False."""
        assert connection.supports_ship_size("battlestar") is False

    @pytest.mark.parametrize(
        "wh_size,ship_size,expected",
        [
            ("medium", "medium", True),
            ("medium", "large", False),
            ("xlarge", "medium", True),
            ("xlarge", "large", True),
            ("xlarge", "xlarge", True),
            ("xlarge", "capital", False),
            ("capital", "medium", True),
            ("capital", "capital", True),
        ],
    )
    def test_size_matrix(self, ship_size, wh_size, expected):
        """Parametrized ship size compatibility matrix."""
        conn = TheraConnection(
            id="test-matrix",
            wh_type="X",
            max_ship_size=wh_size,
            remaining_hours=1,
            expires_at=datetime.utcnow() + timedelta(hours=1),
            out_system_id=31000005,
            out_system_name="Thera",
            out_signature="A",
            in_system_id=30000142,
            in_system_name="Jita",
            in_system_class="hs",
            in_region_id=10000002,
            in_region_name="The Forge",
        )
        assert conn.supports_ship_size(ship_size) is expected


# ---------------------------------------------------------------------------
# Thera model enums
# ---------------------------------------------------------------------------


class TestTheraEnums:
    """Test Thera model enumerations."""

    def test_ship_sizes(self):
        """ShipSize enum has correct values."""
        assert ShipSize.MEDIUM == "medium"
        assert ShipSize.LARGE == "large"
        assert ShipSize.XLARGE == "xlarge"
        assert ShipSize.CAPITAL == "capital"

    def test_security_classes(self):
        """SecurityClass enum has correct values."""
        assert SecurityClass.HIGHSEC == "hs"
        assert SecurityClass.LOWSEC == "ls"
        assert SecurityClass.NULLSEC == "ns"
        assert SecurityClass.WORMHOLE == "wh"

    def test_hub_types(self):
        """HubType enum has correct values."""
        assert HubType.THERA == "thera"
        assert HubType.TURNUR == "turnur"
        assert HubType.ALL == "all"


# ---------------------------------------------------------------------------
# calculate_recommendation (V1 - TradingOpportunitiesService)
# ---------------------------------------------------------------------------


class TestCalculateRecommendationV1:
    """Test V1 recommendation scoring from TradingOpportunitiesService."""

    def _calc(self, margin, volume, competition):
        svc = TradingOpportunitiesService.__new__(TradingOpportunitiesService)
        return svc.calculate_recommendation(margin, volume, competition)

    def test_excellent_high_margin_high_volume_low_comp(self):
        """High margin + high volume + low comp -> excellent."""
        rec, reason = self._calc(margin=20.0, volume=1500, competition="low")
        assert rec == "excellent"
        assert "High margin" in reason

    def test_good_good_margin_decent_volume(self):
        """Good margin + decent volume -> good."""
        rec, reason = self._calc(margin=12.0, volume=600, competition="medium")
        assert rec == "good"

    def test_moderate_low_score(self):
        """Moderate margin + low volume -> moderate or risky."""
        rec, reason = self._calc(margin=6.0, volume=200, competition="medium")
        assert rec == "moderate"

    def test_risky_all_bad(self):
        """Low margin + very low volume + high comp -> risky."""
        rec, reason = self._calc(margin=2.0, volume=50, competition="high")
        assert rec == "risky"

    def test_reason_contains_all_factors(self):
        """Reason string includes all contributing factors."""
        _, reason = self._calc(margin=15.0, volume=1000, competition="low")
        assert "High margin" in reason
        assert "high volume" in reason
        assert "low competition" in reason


# ---------------------------------------------------------------------------
# calculate_risk_factors (V2)
# ---------------------------------------------------------------------------


class TestCalculateRiskFactors:
    """Test V2 risk factor generation."""

    def test_stable_market(self):
        """No risk factors -> 'stable market'."""
        factors = calculate_risk_factors({
            "price_volatility": 2.0,
            "avg_daily_volume": 500,
            "trend_7d": 3.0,
            "days_to_sell_100": 5.0,
        })
        assert factors == ["stable market"]

    def test_high_volatility(self):
        """Volatility > 10 -> 'high volatility'."""
        factors = calculate_risk_factors({"price_volatility": 15.0})
        assert "high volatility" in factors

    def test_moderate_volatility(self):
        """Volatility 5-10 -> 'moderate volatility'."""
        factors = calculate_risk_factors({"price_volatility": 7.0})
        assert "moderate volatility" in factors

    def test_no_volume_data(self):
        """Missing volume -> 'no volume data'."""
        factors = calculate_risk_factors({"avg_daily_volume": None})
        assert "no volume data" in factors

    def test_very_low_volume(self):
        """Volume < 50 -> 'very low volume'."""
        factors = calculate_risk_factors({"avg_daily_volume": 30})
        assert "very low volume" in factors

    def test_low_volume(self):
        """Volume 50-200 -> 'low volume'."""
        factors = calculate_risk_factors({"avg_daily_volume": 100})
        assert "low volume" in factors

    def test_price_dropping(self):
        """Trend < -10 -> 'price dropping'."""
        factors = calculate_risk_factors({"trend_7d": -15.0})
        assert "price dropping" in factors

    def test_price_spiking(self):
        """Trend > 20 -> 'price spiking'."""
        factors = calculate_risk_factors({"trend_7d": 25.0})
        assert "price spiking" in factors

    def test_slow_turnover(self):
        """Days to sell > 30 -> 'slow turnover'."""
        factors = calculate_risk_factors({"days_to_sell_100": 45.0})
        assert "slow turnover" in factors

    def test_multiple_risk_factors(self):
        """Multiple risks combine."""
        factors = calculate_risk_factors({
            "price_volatility": 12.0,
            "avg_daily_volume": 30,
            "trend_7d": -20.0,
            "days_to_sell_100": 60.0,
        })
        assert "high volatility" in factors
        assert "very low volume" in factors
        assert "price dropping" in factors
        assert "slow turnover" in factors
        assert len(factors) == 4


# ---------------------------------------------------------------------------
# calculate_recommendation (V2)
# ---------------------------------------------------------------------------


class TestCalculateRecommendationV2:
    """Test V2 recommendation scoring with risk integration."""

    def test_excellent_all_positive(self):
        """High margin + high volume + low risk -> excellent."""
        rec, reason = calculate_recommendation(margin=20.0, volume=1200, risk_score=10)
        assert rec == "excellent"

    def test_good_decent_metrics(self):
        """Good margin + decent volume + moderate risk -> good."""
        rec, reason = calculate_recommendation(margin=12.0, volume=600, risk_score=30)
        assert rec == "good"

    def test_moderate_mixed(self):
        """Moderate margin + low volume + moderate risk."""
        rec, reason = calculate_recommendation(margin=7.0, volume=200, risk_score=35)
        assert rec == "moderate"

    def test_risky_all_bad(self):
        """Low margin + no volume + high risk -> risky."""
        rec, reason = calculate_recommendation(margin=3.0, volume=50, risk_score=60)
        assert rec == "risky"

    def test_none_volume(self):
        """None volume is handled gracefully."""
        rec, reason = calculate_recommendation(margin=10.0, volume=None, risk_score=20)
        assert "no volume data" in reason
        assert rec in ("good", "moderate")

    def test_high_risk_penalty(self):
        """High risk score > 40 adds 'high risk' to reasons."""
        _, reason = calculate_recommendation(margin=15.0, volume=1000, risk_score=50)
        assert "high risk" in reason

    def test_low_risk_bonus(self):
        """Low risk score <= 20 adds 'low risk' to reasons."""
        _, reason = calculate_recommendation(margin=15.0, volume=1000, risk_score=15)
        assert "low risk" in reason


# ---------------------------------------------------------------------------
# calculate_strategy
# ---------------------------------------------------------------------------


class TestCalculateStrategy:
    """Test trading strategy calculation."""

    def test_instant_turnover(self):
        """Days to sell <= 0.1 -> instant turnover."""
        s = calculate_strategy(days_to_sell=0.05, total_orders=50, volume=5000)
        assert s.turnover == "instant"

    def test_fast_turnover(self):
        """Days to sell <= 1 -> fast turnover."""
        s = calculate_strategy(days_to_sell=0.5, total_orders=50, volume=500)
        assert s.turnover == "fast"

    def test_moderate_turnover(self):
        """Days to sell <= 7 -> moderate turnover."""
        s = calculate_strategy(days_to_sell=4.0, total_orders=50, volume=200)
        assert s.turnover == "moderate"

    def test_slow_turnover(self):
        """Days to sell > 7 -> slow turnover."""
        s = calculate_strategy(days_to_sell=15.0, total_orders=50, volume=50)
        assert s.turnover == "slow"

    def test_unknown_turnover_none_days(self):
        """None days_to_sell -> unknown turnover."""
        s = calculate_strategy(days_to_sell=None, total_orders=50, volume=100)
        assert s.turnover == "unknown"

    def test_unknown_turnover_none_volume(self):
        """None volume -> unknown turnover."""
        s = calculate_strategy(days_to_sell=1.0, total_orders=50, volume=None)
        assert s.turnover == "unknown"

    def test_extreme_competition(self):
        """2000+ orders -> extreme competition."""
        s = calculate_strategy(days_to_sell=0.5, total_orders=2500, volume=5000)
        assert s.competition == "extreme"
        assert s.style == "active"
        assert s.update_frequency == "Every 15-30 min"
        assert s.order_duration == "1 day"

    def test_high_competition(self):
        """500-2000 orders -> high competition."""
        s = calculate_strategy(days_to_sell=0.5, total_orders=800, volume=1000)
        assert s.competition == "high"
        assert s.style == "active"

    def test_medium_competition(self):
        """100-500 orders -> medium competition."""
        s = calculate_strategy(days_to_sell=1.0, total_orders=200, volume=500)
        assert s.competition == "medium"
        assert s.style == "semi-active"
        assert s.update_frequency == "2-3x per day"
        assert s.order_duration == "3 days"

    def test_low_competition(self):
        """< 100 orders -> low competition."""
        s = calculate_strategy(days_to_sell=5.0, total_orders=30, volume=50)
        assert s.competition == "low"
        assert s.style == "passive"
        assert s.update_frequency == "Once daily"
        assert s.order_duration == "1 week"

    def test_tips_high_volume(self):
        """Very high volume generates appropriate tip."""
        s = calculate_strategy(days_to_sell=0.5, total_orders=50, volume=15000)
        tip_text = " ".join(s.tips)
        assert "high volume" in tip_text.lower() or "larger orders" in tip_text.lower()

    def test_tips_low_volume(self):
        """Low volume generates appropriate tip."""
        s = calculate_strategy(days_to_sell=5.0, total_orders=50, volume=30)
        tip_text = " ".join(s.tips)
        assert "low volume" in tip_text.lower() or "small" in tip_text.lower()

    def test_tips_not_empty(self):
        """Strategy always has at least one tip."""
        s = calculate_strategy(days_to_sell=1.0, total_orders=200, volume=500)
        assert len(s.tips) >= 1
