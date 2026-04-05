"""Unit tests for tax and facility profile models."""
import pytest
from decimal import Decimal
from src.services.production.tax_models import (
    TaxProfile,
    TaxProfileCreate,
    TaxProfileUpdate,
    FacilityProfile,
    FacilityProfileCreate,
    SystemCostIndex,
)


class TestTaxProfile:
    def test_tax_profile_defaults(self):
        """Tax profile should have sensible defaults."""
        profile = TaxProfile(
            id=1,
            name="Test Profile",
        )
        assert profile.broker_fee_buy == Decimal("3.00")
        assert profile.broker_fee_sell == Decimal("3.00")
        assert profile.sales_tax == Decimal("3.60")
        assert profile.is_default is False
        assert profile.character_id is None

    def test_tax_profile_custom_values(self):
        """Tax profile should accept custom values."""
        profile = TaxProfile(
            id=1,
            name="Skilled Trader",
            broker_fee_buy=Decimal("1.50"),
            broker_fee_sell=Decimal("1.50"),
            sales_tax=Decimal("2.25"),
            character_id=12345,
            is_default=True,
        )
        assert profile.broker_fee_buy == Decimal("1.50")
        assert profile.sales_tax == Decimal("2.25")
        assert profile.character_id == 12345

    def test_tax_profile_create(self):
        """TaxProfileCreate should not require id."""
        create = TaxProfileCreate(
            name="New Profile",
            broker_fee_buy=Decimal("2.00"),
        )
        assert create.name == "New Profile"
        assert create.broker_fee_buy == Decimal("2.00")


class TestFacilityProfile:
    def test_facility_profile_defaults(self):
        """Facility profile should have zero bonuses by default."""
        profile = FacilityProfile(
            id=1,
            name="Test Facility",
            system_id=30000142,
        )
        assert profile.me_bonus == Decimal("0")
        assert profile.te_bonus == Decimal("0")
        assert profile.facility_tax == Decimal("0")
        assert profile.structure_type == "station"

    def test_engineering_complex_bonuses(self):
        """Engineering complex should accept bonuses."""
        profile = FacilityProfile(
            id=1,
            name="Raitaru",
            system_id=30000142,
            structure_type="engineering_complex",
            me_bonus=Decimal("1.0"),
            te_bonus=Decimal("15.0"),
            cost_bonus=Decimal("3.0"),
        )
        assert profile.me_bonus == Decimal("1.0")
        assert profile.te_bonus == Decimal("15.0")
        assert profile.structure_type == "engineering_complex"


class TestSystemCostIndex:
    def test_system_cost_index(self):
        """System cost index should store all activity indices."""
        sci = SystemCostIndex(
            system_id=30000142,
            system_name="Jita",
            manufacturing_index=Decimal("0.0512"),
            reaction_index=Decimal("0.0001"),
        )
        assert sci.system_id == 30000142
        assert sci.manufacturing_index == Decimal("0.0512")
