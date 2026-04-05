"""Tests for Hot Items configuration."""
import pytest
from src.services.market.hot_items import HotItemsConfig, get_hot_items


class TestHotItemsConfig:
    """Test Hot Items configuration."""

    def test_fuel_items_included(self):
        """Test that fuel isotopes are in hot items."""
        hot_items = get_hot_items()
        # Nitrogen Isotopes
        assert 17888 in hot_items
        # Hydrogen Isotopes
        assert 17889 in hot_items

    def test_mineral_items_included(self):
        """Test that minerals are in hot items."""
        hot_items = get_hot_items()
        # Tritanium
        assert 34 in hot_items
        # Pyerite
        assert 35 in hot_items
        # Mexallon
        assert 36 in hot_items

    def test_hot_items_minimum_count(self):
        """Test we have enough hot items for production."""
        hot_items = get_hot_items()
        # Should have at least 50 items (minerals, fuel, common mats)
        assert len(hot_items) >= 50

    def test_config_cache_settings(self):
        """Test cache configuration."""
        config = HotItemsConfig()
        assert config.redis_ttl_seconds == 300  # 5 minutes
        assert config.refresh_interval_seconds == 240  # 4 minutes (before expiry)
