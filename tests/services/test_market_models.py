# tests/services/test_market_models.py
"""Tests for Market models."""
import pytest
from datetime import datetime, timedelta
from src.services.market.models import MarketPrice, PriceSource, JITA_REGION_ID


class TestMarketPrice:
    """Test MarketPrice model."""

    def test_market_price_creation(self):
        """Test basic MarketPrice creation."""
        fixed_time = datetime(2026, 1, 18, 12, 0, 0)  # Fixed timestamp
        price = MarketPrice(
            type_id=34,
            sell_price=5.50,
            buy_price=5.00,
            adjusted_price=5.25,
            average_price=5.30,
            region_id=JITA_REGION_ID,
            source=PriceSource.CACHE,
            last_updated=fixed_time
        )
        assert price.type_id == 34
        assert price.sell_price == 5.50
        assert price.source == PriceSource.CACHE

    def test_market_price_is_stale(self):
        """Test staleness detection."""
        # Use datetime.utcnow() to match the model's is_stale() method
        old_time = datetime.utcnow() - timedelta(hours=2)
        price = MarketPrice(
            type_id=34,
            sell_price=5.50,
            buy_price=5.00,
            region_id=JITA_REGION_ID,
            source=PriceSource.CACHE,
            last_updated=old_time
        )
        assert price.is_stale(max_age_seconds=3600) is True

    def test_market_price_not_stale(self):
        """Test fresh price detection."""
        # Use datetime.utcnow() to match the model's is_stale() method
        recent_time = datetime.utcnow() - timedelta(minutes=30)
        price = MarketPrice(
            type_id=34,
            sell_price=5.50,
            buy_price=5.00,
            region_id=JITA_REGION_ID,
            source=PriceSource.ESI,
            last_updated=recent_time
        )
        assert price.is_stale(max_age_seconds=3600) is False
