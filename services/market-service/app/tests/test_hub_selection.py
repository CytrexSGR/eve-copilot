"""Tests for trade hub constants, hot items, region naming, and Thera system IDs."""

import pytest

from eve_shared.constants import (
    JITA_REGION_ID,
    JITA_STATION_ID,
    REGION_NAMES,
    TRADE_HUB_REGIONS,
    TRADE_HUB_STATIONS,
    TRADE_HUB_SYSTEMS,
)
from app.services.hot_items import (
    MINERALS,
    ISOTOPES,
    FUEL_BLOCKS,
    MOON_MATERIALS,
    PRODUCTION_MATERIALS,
    HotItemsConfig,
    get_hot_items,
    get_hot_items_by_category,
)
from app.services.thera_client import THERA_SYSTEM_ID, TURNUR_SYSTEM_ID
from app.routers.trading_opportunities_v2 import REGION_NAMES as V2_REGION_NAMES


# ---------------------------------------------------------------------------
# Trade hub constants
# ---------------------------------------------------------------------------


class TestTradeHubConstants:
    """Test trade hub region, station, and system ID constants."""

    def test_jita_region_id(self):
        """Jita region (The Forge) is 10000002."""
        assert JITA_REGION_ID == 10000002

    def test_jita_station_id(self):
        """Jita 4-4 station is 60003760."""
        assert JITA_STATION_ID == 60003760

    def test_five_trade_hub_regions(self):
        """There are exactly 5 trade hub regions."""
        assert len(TRADE_HUB_REGIONS) == 5

    def test_five_trade_hub_stations(self):
        """There are exactly 5 trade hub stations."""
        assert len(TRADE_HUB_STATIONS) == 5

    def test_five_trade_hub_systems(self):
        """There are exactly 5 trade hub systems."""
        assert len(TRADE_HUB_SYSTEMS) == 5

    @pytest.mark.parametrize(
        "region_key,region_id",
        [
            ("the_forge", 10000002),
            ("domain", 10000043),
            ("heimatar", 10000030),
            ("sinq_laison", 10000032),
            ("metropolis", 10000042),
        ],
    )
    def test_region_name_to_id_mapping(self, region_key, region_id):
        """Each trade hub region maps to correct ID."""
        assert TRADE_HUB_REGIONS[region_key] == region_id

    @pytest.mark.parametrize(
        "region_id,station_id",
        [
            (10000002, 60003760),   # Jita
            (10000043, 60008494),   # Amarr
            (10000030, 60004588),   # Rens
            (10000032, 60011866),   # Dodixie
            (10000042, 60005686),   # Hek
        ],
    )
    def test_region_to_station_mapping(self, region_id, station_id):
        """Each region maps to its trade hub station."""
        assert TRADE_HUB_STATIONS[region_id] == station_id

    @pytest.mark.parametrize(
        "system_name,system_id",
        [
            ("jita", 30000142),
            ("amarr", 30002187),
            ("rens", 30002510),
            ("dodixie", 30002659),
            ("hek", 30002053),
        ],
    )
    def test_system_name_to_id(self, system_name, system_id):
        """Each trade hub system name maps to correct solar system ID."""
        assert TRADE_HUB_SYSTEMS[system_name] == system_id

    def test_all_hub_regions_have_stations(self):
        """Every trade hub region has a corresponding station."""
        for region_id in TRADE_HUB_REGIONS.values():
            assert region_id in TRADE_HUB_STATIONS

    def test_jita_station_in_jita_region(self):
        """Jita station is associated with The Forge region."""
        assert TRADE_HUB_STATIONS[JITA_REGION_ID] == JITA_STATION_ID


# ---------------------------------------------------------------------------
# Region names
# ---------------------------------------------------------------------------


class TestRegionNames:
    """Test region display name mappings."""

    @pytest.mark.parametrize(
        "region_id,display_name",
        [
            (10000002, "The Forge"),
            (10000043, "Domain"),
            (10000030, "Heimatar"),
            (10000032, "Sinq Laison"),
            (10000042, "Metropolis"),
        ],
    )
    def test_shared_region_names(self, region_id, display_name):
        """Shared constants REGION_NAMES has correct display names."""
        assert REGION_NAMES[region_id] == display_name

    @pytest.mark.parametrize(
        "region_id,display_name",
        [
            (10000002, "The Forge"),
            (10000043, "Domain"),
            (10000030, "Heimatar"),
            (10000032, "Sinq Laison"),
            (10000042, "Metropolis"),
        ],
    )
    def test_v2_region_names_match_shared(self, region_id, display_name):
        """V2 router REGION_NAMES matches shared constants."""
        assert V2_REGION_NAMES[region_id] == display_name

    def test_all_hub_regions_have_names(self):
        """Every trade hub region has a display name."""
        for region_id in TRADE_HUB_REGIONS.values():
            assert region_id in REGION_NAMES


# ---------------------------------------------------------------------------
# Thera system IDs
# ---------------------------------------------------------------------------


class TestTheraSystemIDs:
    """Test Thera and Turnur system ID constants."""

    def test_thera_system_id(self):
        """Thera system ID is 31000005 (J-space)."""
        assert THERA_SYSTEM_ID == 31000005

    def test_turnur_system_id(self):
        """Turnur system ID is 30002086 (Metropolis)."""
        assert TURNUR_SYSTEM_ID == 30002086

    def test_thera_is_wormhole_space(self):
        """Thera system ID > 31000000 confirms wormhole space."""
        assert THERA_SYSTEM_ID > 31000000

    def test_turnur_is_k_space(self):
        """Turnur system ID < 31000000 confirms K-space."""
        assert TURNUR_SYSTEM_ID < 31000000


# ---------------------------------------------------------------------------
# Hot items configuration
# ---------------------------------------------------------------------------


class TestHotItems:
    """Test hot items categories and configuration."""

    def test_minerals_count(self):
        """There are 8 mineral type IDs."""
        assert len(MINERALS) == 8

    def test_isotopes_count(self):
        """There are 4 isotope type IDs."""
        assert len(ISOTOPES) == 4

    def test_fuel_blocks_count(self):
        """There are 4 fuel block type IDs."""
        assert len(FUEL_BLOCKS) == 4

    def test_moon_materials_count(self):
        """There are 20 moon material type IDs."""
        assert len(MOON_MATERIALS) == 20

    def test_tritanium_in_minerals(self):
        """Tritanium (34) is in minerals."""
        assert 34 in MINERALS

    def test_morphite_in_minerals(self):
        """Morphite (11399) is in minerals."""
        assert 11399 in MINERALS

    def test_get_hot_items_returns_union(self):
        """get_hot_items() returns the union of all categories."""
        all_items = get_hot_items()
        expected_count = (
            len(MINERALS)
            + len(ISOTOPES)
            + len(FUEL_BLOCKS)
            + len(MOON_MATERIALS)
            + len(PRODUCTION_MATERIALS)
        )
        assert len(all_items) == expected_count

    def test_get_hot_items_contains_tritanium(self):
        """Hot items includes Tritanium."""
        assert 34 in get_hot_items()

    def test_get_hot_items_by_category_keys(self):
        """get_hot_items_by_category returns 5 categories."""
        cats = get_hot_items_by_category()
        assert set(cats.keys()) == {
            "minerals",
            "isotopes",
            "fuel_blocks",
            "moon_materials",
            "production_materials",
        }

    def test_hot_items_no_overlap_minerals_isotopes(self):
        """Minerals and isotopes don't overlap."""
        assert MINERALS.isdisjoint(ISOTOPES)

    def test_hot_items_no_overlap_minerals_fuel(self):
        """Minerals and fuel blocks don't overlap."""
        assert MINERALS.isdisjoint(FUEL_BLOCKS)

    def test_hot_items_config_defaults(self):
        """HotItemsConfig has sensible defaults."""
        config = HotItemsConfig()
        assert config.redis_ttl_seconds == 300
        assert config.refresh_interval_seconds == 240
        assert config.postgres_ttl_seconds == 3600
        assert config.batch_size == 100

    def test_hot_items_config_custom(self):
        """HotItemsConfig can be customized."""
        config = HotItemsConfig(redis_ttl_seconds=60, batch_size=50)
        assert config.redis_ttl_seconds == 60
        assert config.batch_size == 50

    @pytest.mark.parametrize(
        "type_id,category",
        [
            (34, "minerals"),      # Tritanium
            (16274, "isotopes"),   # Helium Isotopes
            (4051, "fuel_blocks"), # Nitrogen Fuel Block
            (16633, "moon_materials"),  # Hydrocarbons
        ],
    )
    def test_item_in_correct_category(self, type_id, category):
        """Each sample item is in the expected category."""
        cats = get_hot_items_by_category()
        assert type_id in cats[category]
