"""Tests for ItemsDeriver service.

This module tests the derivation of market items (ammunition, fuel, modules)
from detected doctrine compositions. Follows TDD approach.
"""

import pytest
from datetime import datetime
from services.war_economy.doctrine.items_deriver import ItemsDeriver
from services.war_economy.doctrine.models import DoctrineTemplate, ItemOfInterest


@pytest.fixture
def items_deriver():
    """Create ItemsDeriver instance for testing."""
    return ItemsDeriver()


@pytest.fixture
def subcap_doctrine():
    """Create a subcap doctrine (Machariel fleet) for testing."""
    return DoctrineTemplate(
        id=1,
        doctrine_name="Test Machariel Fleet",
        alliance_id=99000001,
        region_id=10000002,
        composition={
            "17738": 0.60,  # Machariel (60%)
            "29990": 0.25,   # Loki (25%)
            "11978": 0.15,   # Scimitar (15%)
        },
        confidence_score=0.85,
        observation_count=12,
        first_seen=datetime(2026, 1, 1),
        last_seen=datetime(2026, 1, 14),
        total_pilots_avg=45,
        primary_doctrine_type="subcap",
        created_at=datetime(2026, 1, 1),
        updated_at=datetime(2026, 1, 14),
    )


@pytest.fixture
def capital_doctrine_amarr():
    """Create an Amarr capital doctrine for testing."""
    return DoctrineTemplate(
        id=2,
        doctrine_name="Test Amarr Capital Fleet",
        alliance_id=99000002,
        region_id=10000043,
        composition={
            "19720": 0.40,  # Revelation (40%)
            "37604": 0.35,  # Apostle (35%)
            "29990": 0.25,  # Loki (25%)
        },
        confidence_score=0.90,
        observation_count=15,
        first_seen=datetime(2026, 1, 1),
        last_seen=datetime(2026, 1, 14),
        total_pilots_avg=30,
        primary_doctrine_type="capital",
        created_at=datetime(2026, 1, 1),
        updated_at=datetime(2026, 1, 14),
    )


@pytest.fixture
def capital_doctrine_caldari():
    """Create a Caldari capital doctrine for testing."""
    return DoctrineTemplate(
        id=3,
        doctrine_name="Test Caldari Capital Fleet",
        alliance_id=99000003,
        region_id=10000002,
        composition={
            "19726": 0.45,  # Phoenix (45%)
            "23915": 0.30,  # Chimera (30%)
            "17738": 0.25,  # Machariel (25%)
        },
        confidence_score=0.88,
        observation_count=10,
        first_seen=datetime(2026, 1, 1),
        last_seen=datetime(2026, 1, 14),
        total_pilots_avg=25,
        primary_doctrine_type="capital",
        created_at=datetime(2026, 1, 1),
        updated_at=datetime(2026, 1, 14),
    )


@pytest.fixture
def mixed_doctrine():
    """Create a mixed doctrine with various ship types."""
    return DoctrineTemplate(
        id=4,
        doctrine_name="Test Mixed Fleet",
        alliance_id=99000004,
        region_id=10000030,
        composition={
            "17738": 0.30,  # Machariel (30%)
            "19720": 0.20,  # Revelation (20%)
            "29990": 0.25,  # Loki (25%)
            "11978": 0.15,  # Scimitar (15%)
            "22852": 0.10,  # Hel (10%)
        },
        confidence_score=0.87,
        observation_count=8,
        first_seen=datetime(2026, 1, 1),
        last_seen=datetime(2026, 1, 14),
        total_pilots_avg=50,
        primary_doctrine_type="mixed",
        created_at=datetime(2026, 1, 1),
        updated_at=datetime(2026, 1, 14),
    )


class TestItemsDeriver:
    """Test suite for ItemsDeriver service."""

    def test_derive_items_returns_list(self, items_deriver, subcap_doctrine):
        """Test that derive_items_for_doctrine returns a list."""
        items = items_deriver.derive_items_for_doctrine(subcap_doctrine)
        assert isinstance(items, list)
        assert len(items) > 0

    def test_derive_items_returns_item_of_interest_objects(self, items_deriver, subcap_doctrine):
        """Test that all returned items are ItemOfInterest instances."""
        items = items_deriver.derive_items_for_doctrine(subcap_doctrine)
        for item in items:
            assert isinstance(item, ItemOfInterest)
            assert item.doctrine_id == subcap_doctrine.id

    def test_critical_modules_always_included(self, items_deriver, subcap_doctrine):
        """Test that critical modules (Nanite Paste, Strontium) are always included."""
        items = items_deriver.derive_items_for_doctrine(subcap_doctrine)

        type_ids = {item.type_id for item in items}

        # Critical modules
        assert 28668 in type_ids, "Nanite Paste should always be included"
        assert 16275 in type_ids, "Strontium Clathrates should always be included"

        # Check priority and category
        for item in items:
            if item.type_id == 28668:
                assert item.priority == 1
                assert item.item_category == "module"
                assert item.item_name == "Nanite Repair Paste"
            elif item.type_id == 16275:
                assert item.priority == 1
                assert item.item_category == "fuel"
                assert item.item_name == "Strontium Clathrates"

    def test_derive_ammunition_for_machariel(self, items_deriver, subcap_doctrine):
        """Test ammunition derivation for Machariel-heavy doctrine."""
        items = items_deriver.derive_items_for_doctrine(subcap_doctrine)

        type_ids = {item.type_id for item in items}

        # Machariel uses large projectile turrets
        # Should include Republic Fleet EMP and Hail
        assert 21894 in type_ids, "Republic Fleet EMP L should be derived"
        assert 12779 in type_ids, "Hail L should be derived"

        # Check details
        for item in items:
            if item.type_id == 21894:
                assert item.item_category == "ammunition"
                assert item.priority == 1
                assert item.consumption_rate == 5000.0  # Large ammo rate
                assert "Republic Fleet EMP" in item.item_name
            elif item.type_id == 12779:
                assert item.item_category == "ammunition"
                assert item.priority == 1
                assert item.consumption_rate == 5000.0

    def test_derive_ammunition_for_loki(self, items_deriver, subcap_doctrine):
        """Test ammunition derivation for Loki-heavy doctrine."""
        items = items_deriver.derive_items_for_doctrine(subcap_doctrine)

        type_ids = {item.type_id for item in items}

        # Loki uses medium projectile turrets
        # Should include T2 medium projectile ammo
        assert 12777 in type_ids or 12773 in type_ids, "Should include medium projectile ammo"

        # Check medium ammo consumption rate
        for item in items:
            if item.type_id in (12777, 12773):
                assert item.item_category == "ammunition"
                assert item.consumption_rate == 7500.0  # Medium ammo rate

    def test_derive_fuel_for_amarr_capitals(self, items_deriver, capital_doctrine_amarr):
        """Test fuel derivation for Amarr capital ships."""
        items = items_deriver.derive_items_for_doctrine(capital_doctrine_amarr)

        type_ids = {item.type_id for item in items}

        # Amarr capitals use Heavy Water (16272)
        assert 16272 in type_ids, "Heavy Water should be derived for Amarr capitals"

        # Check details
        for item in items:
            if item.type_id == 16272 and item.item_category == "fuel" and "Heavy Water" in item.item_name:
                assert item.priority == 1
                assert item.consumption_rate == 100.0  # Fuel consumption rate per capital

    def test_derive_fuel_for_caldari_capitals(self, items_deriver, capital_doctrine_caldari):
        """Test fuel derivation for Caldari capital ships."""
        items = items_deriver.derive_items_for_doctrine(capital_doctrine_caldari)

        type_ids = {item.type_id for item in items}

        # Caldari capitals use Liquid Ozone
        assert 16273 in type_ids, "Liquid Ozone should be derived for Caldari capitals"

        # Check details
        for item in items:
            if item.type_id == 16273:
                assert item.item_category == "fuel"
                assert item.priority == 1
                assert item.consumption_rate == 100.0
                assert "Liquid Ozone" in item.item_name

    def test_no_duplicate_items(self, items_deriver, mixed_doctrine):
        """Test that no duplicate type_ids are returned."""
        items = items_deriver.derive_items_for_doctrine(mixed_doctrine)

        type_ids = [item.type_id for item in items]
        unique_type_ids = set(type_ids)

        assert len(type_ids) == len(unique_type_ids), "No duplicate items should be returned"

    def test_items_have_created_at_timestamp(self, items_deriver, subcap_doctrine):
        """Test that all items have a created_at timestamp."""
        items = items_deriver.derive_items_for_doctrine(subcap_doctrine)

        for item in items:
            assert item.created_at is not None
            assert isinstance(item.created_at, datetime)

    def test_priority_values_are_valid(self, items_deriver, mixed_doctrine):
        """Test that all priority values are within valid range (1-3)."""
        items = items_deriver.derive_items_for_doctrine(mixed_doctrine)

        for item in items:
            assert 1 <= item.priority <= 3, f"Priority {item.priority} is invalid for {item.type_id}"

    def test_consumption_rates_are_positive(self, items_deriver, mixed_doctrine):
        """Test that consumption rates are positive or None."""
        items = items_deriver.derive_items_for_doctrine(mixed_doctrine)

        for item in items:
            if item.consumption_rate is not None:
                assert item.consumption_rate > 0, f"Invalid consumption rate for {item.type_id}"

    def test_empty_composition_returns_critical_modules_only(self, items_deriver):
        """Test that empty composition still returns critical modules."""
        empty_doctrine = DoctrineTemplate(
            id=99,
            doctrine_name="Empty Doctrine",
            alliance_id=99000099,
            region_id=10000002,
            composition={},
            confidence_score=0.5,
            observation_count=1,
            first_seen=datetime(2026, 1, 14),
            last_seen=datetime(2026, 1, 14),
            total_pilots_avg=0,
            primary_doctrine_type="subcap",
            created_at=datetime(2026, 1, 14),
            updated_at=datetime(2026, 1, 14),
        )

        items = items_deriver.derive_items_for_doctrine(empty_doctrine)

        # Should still have critical modules
        type_ids = {item.type_id for item in items}
        assert 28668 in type_ids, "Nanite Paste should be included"
        assert 16275 in type_ids, "Strontium Clathrates should be included"

    def test_ammunition_for_multiple_weapon_types(self, items_deriver, mixed_doctrine):
        """Test that mixed doctrines derive ammunition for multiple weapon types."""
        items = items_deriver.derive_items_for_doctrine(mixed_doctrine)

        ammunition_items = [item for item in items if item.item_category == "ammunition"]

        # Mixed doctrine has Machariel (large projectile), Loki (medium projectile)
        # Should have ammunition for both
        assert len(ammunition_items) > 0, "Should derive ammunition for mixed doctrine"

        # Check for different ammunition sizes
        consumption_rates = {item.consumption_rate for item in ammunition_items}
        assert 5000.0 in consumption_rates or 7500.0 in consumption_rates, \
            "Should have ammunition with different consumption rates"

    def test_item_names_are_set(self, items_deriver, subcap_doctrine):
        """Test that item names are properly set."""
        items = items_deriver.derive_items_for_doctrine(subcap_doctrine)

        for item in items:
            assert item.item_name is not None
            assert len(item.item_name) > 0
            assert isinstance(item.item_name, str)

    def test_doctrine_id_matches_input(self, items_deriver, subcap_doctrine):
        """Test that all derived items have the correct doctrine_id."""
        items = items_deriver.derive_items_for_doctrine(subcap_doctrine)

        for item in items:
            assert item.doctrine_id == subcap_doctrine.id

    def test_multiple_capital_factions_in_same_doctrine(self, items_deriver):
        """Test fuel derivation when doctrine has capitals from multiple factions."""
        multi_faction_doctrine = DoctrineTemplate(
            id=5,
            doctrine_name="Test Multi-Faction Capital Fleet",
            alliance_id=99000005,
            region_id=10000002,
            composition={
                "19720": 0.30,  # Revelation (Amarr)
                "19726": 0.30,  # Phoenix (Caldari)
                "24483": 0.20,  # Nidhoggur (Minmatar)
                "23911": 0.20,  # Thanatos (Gallente)
            },
            confidence_score=0.92,
            observation_count=20,
            first_seen=datetime(2026, 1, 1),
            last_seen=datetime(2026, 1, 14),
            total_pilots_avg=40,
            primary_doctrine_type="capital",
            created_at=datetime(2026, 1, 1),
            updated_at=datetime(2026, 1, 14),
        )

        items = items_deriver.derive_items_for_doctrine(multi_faction_doctrine)

        fuel_items = [item for item in items if item.item_category == "fuel"]
        fuel_type_ids = {item.type_id for item in fuel_items}

        # Should have fuel for all four factions
        assert 16272 in fuel_type_ids, "Heavy Water (Amarr)"
        assert 16273 in fuel_type_ids, "Liquid Ozone (Caldari)"
        assert 44 in fuel_type_ids, "Enriched Uranium (Gallente)"
        # Note: Minmatar also uses Liquid Ozone (16273), same as Caldari

    def test_item_categories_are_valid(self, items_deriver, mixed_doctrine):
        """Test that all item categories are valid."""
        items = items_deriver.derive_items_for_doctrine(mixed_doctrine)

        valid_categories = {"ammunition", "fuel", "module"}

        for item in items:
            assert item.item_category in valid_categories, \
                f"Invalid category {item.item_category} for {item.type_id}"


class TestAmmunitionDerivation:
    """Detailed tests for ammunition derivation logic."""

    def test_large_projectile_ammunition(self, items_deriver):
        """Test ammunition for large projectile weapons (Machariel)."""
        doctrine = DoctrineTemplate(
            id=10,
            doctrine_name="Pure Machariel",
            composition={"17738": 1.0},
            confidence_score=0.9,
            observation_count=10,
            first_seen=datetime(2026, 1, 1),
            last_seen=datetime(2026, 1, 14),
            created_at=datetime(2026, 1, 1),
            updated_at=datetime(2026, 1, 14),
        )

        items = items_deriver.derive_items_for_doctrine(doctrine)
        ammo_items = [i for i in items if i.item_category == "ammunition"]

        assert len(ammo_items) > 0
        # Should include Republic Fleet EMP and Hail
        type_ids = {i.type_id for i in ammo_items}
        assert 21894 in type_ids  # Republic Fleet EMP L
        assert 12779 in type_ids  # Hail L

    def test_medium_projectile_ammunition(self, items_deriver):
        """Test ammunition for medium projectile weapons (Loki)."""
        doctrine = DoctrineTemplate(
            id=11,
            doctrine_name="Pure Loki",
            composition={"29990": 1.0},
            confidence_score=0.9,
            observation_count=10,
            first_seen=datetime(2026, 1, 1),
            last_seen=datetime(2026, 1, 14),
            created_at=datetime(2026, 1, 1),
            updated_at=datetime(2026, 1, 14),
        )

        items = items_deriver.derive_items_for_doctrine(doctrine)
        ammo_items = [i for i in items if i.item_category == "ammunition"]

        assert len(ammo_items) > 0
        # Check consumption rate for medium ammo
        for item in ammo_items:
            assert item.consumption_rate == 7500.0


class TestFuelDerivation:
    """Detailed tests for fuel derivation logic."""

    def test_amarr_capital_fuel(self, items_deriver):
        """Test fuel for Amarr capital ships."""
        doctrine = DoctrineTemplate(
            id=20,
            doctrine_name="Pure Revelation",
            composition={"19720": 1.0},  # Revelation
            confidence_score=0.9,
            observation_count=10,
            first_seen=datetime(2026, 1, 1),
            last_seen=datetime(2026, 1, 14),
            created_at=datetime(2026, 1, 1),
            updated_at=datetime(2026, 1, 14),
        )

        items = items_deriver.derive_items_for_doctrine(doctrine)
        fuel_items = [i for i in items if i.item_category == "fuel" and "Heavy Water" in i.item_name]

        assert len(fuel_items) > 0
        assert fuel_items[0].type_id == 16272

    def test_caldari_capital_fuel(self, items_deriver):
        """Test fuel for Caldari capital ships."""
        doctrine = DoctrineTemplate(
            id=21,
            doctrine_name="Pure Phoenix",
            composition={"19726": 1.0},  # Phoenix
            confidence_score=0.9,
            observation_count=10,
            first_seen=datetime(2026, 1, 1),
            last_seen=datetime(2026, 1, 14),
            created_at=datetime(2026, 1, 1),
            updated_at=datetime(2026, 1, 14),
        )

        items = items_deriver.derive_items_for_doctrine(doctrine)
        fuel_items = [i for i in items if i.item_category == "fuel" and "Liquid Ozone" in i.item_name]

        assert len(fuel_items) > 0
        assert fuel_items[0].type_id == 16273

    def test_gallente_capital_fuel(self, items_deriver):
        """Test fuel for Gallente capital ships."""
        doctrine = DoctrineTemplate(
            id=22,
            doctrine_name="Pure Thanatos",
            composition={"23911": 1.0},  # Thanatos
            confidence_score=0.9,
            observation_count=10,
            first_seen=datetime(2026, 1, 1),
            last_seen=datetime(2026, 1, 14),
            created_at=datetime(2026, 1, 1),
            updated_at=datetime(2026, 1, 14),
        )

        items = items_deriver.derive_items_for_doctrine(doctrine)
        fuel_items = [i for i in items if i.item_category == "fuel" and "Enriched Uranium" in i.item_name]

        assert len(fuel_items) > 0
        assert fuel_items[0].type_id == 44

    def test_minmatar_capital_fuel(self, items_deriver):
        """Test fuel for Minmatar capital ships."""
        doctrine = DoctrineTemplate(
            id=23,
            doctrine_name="Pure Nidhoggur",
            composition={"24483": 1.0},  # Nidhoggur
            confidence_score=0.9,
            observation_count=10,
            first_seen=datetime(2026, 1, 1),
            last_seen=datetime(2026, 1, 14),
            created_at=datetime(2026, 1, 1),
            updated_at=datetime(2026, 1, 14),
        )

        items = items_deriver.derive_items_for_doctrine(doctrine)
        fuel_items = [i for i in items if i.item_category == "fuel" and "Liquid Ozone" in i.item_name]

        assert len(fuel_items) > 0
        assert fuel_items[0].type_id == 16273  # Minmatar uses same as Caldari


class TestCriticalModules:
    """Detailed tests for critical module inclusion."""

    def test_nanite_paste_always_present(self, items_deriver, subcap_doctrine):
        """Test that Nanite Paste is always included."""
        items = items_deriver.derive_items_for_doctrine(subcap_doctrine)

        nanite_items = [i for i in items if i.type_id == 28668]
        assert len(nanite_items) == 1

        nanite = nanite_items[0]
        assert nanite.item_name == "Nanite Repair Paste"
        assert nanite.item_category == "module"
        assert nanite.priority == 1

    def test_strontium_always_present(self, items_deriver, subcap_doctrine):
        """Test that Strontium Clathrates is always included."""
        items = items_deriver.derive_items_for_doctrine(subcap_doctrine)

        stront_items = [i for i in items if i.type_id == 16275 and i.item_category == "fuel"]
        assert len(stront_items) == 1

        stront = stront_items[0]
        assert stront.item_name == "Strontium Clathrates"
        assert stront.item_category == "fuel"
        assert stront.priority == 1
