"""Tests for extended economics service with tax and facility profile support."""
import pytest
from decimal import Decimal
from unittest.mock import MagicMock, patch, PropertyMock
from services.production.economics_service import ProductionEconomicsService
from src.services.production.tax_models import TaxProfile, FacilityProfile, SystemCostIndex


class TestEconomicsServiceWithTaxProfile:
    """Test economics calculations with tax profiles applied."""

    @pytest.fixture
    def mock_economics_data(self):
        """Base economics data returned by repository."""
        return {
            'type_id': 648,
            'region_id': 10000002,
            'material_cost': 1000000.0,
            'base_job_cost': 50000.0,
            'total_cost': 1050000.0,
            'market_sell_price': 1500000.0,
            'market_buy_price': 1200000.0,
            'profit_sell': 450000.0,
            'profit_buy': 150000.0,
            'roi_sell_percent': 42.86,
            'roi_buy_percent': 14.29,
            'base_production_time': 3600,
            'updated_at': '2026-01-17T12:00:00'
        }

    @pytest.fixture
    def tax_profile(self):
        """Sample tax profile with custom rates."""
        return TaxProfile(
            id=1,
            name="Skilled Trader",
            broker_fee_buy=Decimal("1.50"),
            broker_fee_sell=Decimal("2.00"),
            sales_tax=Decimal("3.00"),
            is_default=False,
        )

    def test_calculate_with_tax_profile(self, mock_economics_data, tax_profile):
        """Tax profile should apply broker fees and sales tax to revenue."""
        service = ProductionEconomicsService()

        with patch.object(service.repo, 'get', return_value=mock_economics_data), \
             patch.object(service, '_get_item_info', return_value={'name': 'Badger', 'type_id': 648}), \
             patch.object(service, '_get_region_name', return_value='The Forge'), \
             patch('services.production.economics_service.get_db_connection') as mock_db:

            # Mock the tax profile repository
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.__enter__ = MagicMock(return_value=mock_conn)
            mock_conn.__exit__ = MagicMock(return_value=False)
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
            mock_db.return_value = mock_conn

            # Simulate tax profile found in DB
            mock_cursor.fetchone.return_value = (
                1, "Skilled Trader", None, Decimal("1.50"), Decimal("2.00"),
                Decimal("3.00"), False, None, None
            )

            result = service.get_economics(
                type_id=648,
                region_id=10000002,
                me=10,
                te=20,
                tax_profile_id=1
            )

            # Verify tax profile is included in response
            assert 'tax_profile' in result
            assert result['tax_profile'] is not None
            assert result['tax_profile']['name'] == "Skilled Trader"

            # Verify broker fee and sales tax are calculated
            # sell_price = 1500000
            # broker_fee = 1500000 * (2.00 / 100) = 30000
            # sales_tax = 1500000 * (3.00 / 100) = 45000
            assert 'broker_fee' in result['costs']
            assert 'sales_tax' in result['costs']
            assert result['costs']['broker_fee'] == pytest.approx(30000.0, rel=0.01)
            assert result['costs']['sales_tax'] == pytest.approx(45000.0, rel=0.01)

    def test_calculate_without_tax_profile(self, mock_economics_data):
        """Without tax profile, broker_fee and sales_tax should be zero."""
        service = ProductionEconomicsService()

        with patch.object(service.repo, 'get', return_value=mock_economics_data), \
             patch.object(service, '_get_item_info', return_value={'name': 'Badger', 'type_id': 648}), \
             patch.object(service, '_get_region_name', return_value='The Forge'):

            result = service.get_economics(
                type_id=648,
                region_id=10000002,
                me=10,
                te=20
            )

            # Without tax profile, these should be zero or not present
            assert result.get('tax_profile') is None
            # Broker fee and sales tax should default to 0
            assert result['costs'].get('broker_fee', 0) == 0
            assert result['costs'].get('sales_tax', 0) == 0


class TestEconomicsServiceWithFacilityBonus:
    """Test economics calculations with facility ME/TE bonuses."""

    @pytest.fixture
    def mock_economics_data(self):
        """Base economics data returned by repository."""
        return {
            'type_id': 648,
            'region_id': 10000002,
            'material_cost': 1000000.0,
            'base_job_cost': 50000.0,
            'total_cost': 1050000.0,
            'market_sell_price': 1500000.0,
            'market_buy_price': 1200000.0,
            'profit_sell': 450000.0,
            'profit_buy': 150000.0,
            'roi_sell_percent': 42.86,
            'roi_buy_percent': 14.29,
            'base_production_time': 3600,
            'updated_at': '2026-01-17T12:00:00'
        }

    @pytest.fixture
    def facility_profile(self):
        """Sample facility profile with bonuses."""
        return FacilityProfile(
            id=1,
            name="Raitaru Engineering Complex",
            system_id=30000142,
            structure_type="engineering_complex",
            me_bonus=Decimal("1.0"),
            te_bonus=Decimal("15.0"),
            cost_bonus=Decimal("3.0"),
            facility_tax=Decimal("0.0"),
        )

    def test_calculate_with_facility_bonus(self, mock_economics_data, facility_profile):
        """Facility ME bonus should be added to blueprint ME for material cost calculation."""
        service = ProductionEconomicsService()

        with patch.object(service.repo, 'get', return_value=mock_economics_data), \
             patch.object(service, '_get_item_info', return_value={'name': 'Badger', 'type_id': 648}), \
             patch.object(service, '_get_region_name', return_value='The Forge'), \
             patch('services.production.economics_service.get_db_connection') as mock_db:

            # Mock the facility profile lookup
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.__enter__ = MagicMock(return_value=mock_conn)
            mock_conn.__exit__ = MagicMock(return_value=False)
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
            mock_db.return_value = mock_conn

            # Facility profile query result
            mock_cursor.fetchone.return_value = (
                1, "Raitaru Engineering Complex", 30000142, "engineering_complex",
                Decimal("1.0"), Decimal("15.0"), Decimal("3.0"), Decimal("0.0"),
                Decimal("0.0"), Decimal("0.0"), Decimal("0.0"), "Jita", None, None
            )

            result = service.get_economics(
                type_id=648,
                region_id=10000002,
                me=10,  # Blueprint ME
                te=20,
                facility_id=1
            )

            # Verify facility is included in response
            assert 'facility' in result
            assert result['facility'] is not None
            assert result['facility']['name'] == "Raitaru Engineering Complex"
            assert result['facility']['me_bonus'] == 1.0

            # Material cost with combined ME:
            # base_material_cost = 1000000
            # blueprint_me = 10, facility_me = 1
            # final_me = 10 + 1 = 11
            # adjusted_material_cost = 1000000 * (1 - 11/100) = 1000000 * 0.89 = 890000
            assert result['costs']['material_cost'] == pytest.approx(890000.0, rel=0.01)

    def test_calculate_without_facility(self, mock_economics_data):
        """Without facility, only blueprint ME should be applied."""
        service = ProductionEconomicsService()

        with patch.object(service.repo, 'get', return_value=mock_economics_data), \
             patch.object(service, '_get_item_info', return_value={'name': 'Badger', 'type_id': 648}), \
             patch.object(service, '_get_region_name', return_value='The Forge'):

            result = service.get_economics(
                type_id=648,
                region_id=10000002,
                me=10,
                te=20
            )

            # Without facility, facility should be None
            assert result.get('facility') is None

            # Material cost with only blueprint ME:
            # base_material_cost = 1000000
            # adjusted_material_cost = 1000000 * (1 - 10/100) = 900000
            assert result['costs']['material_cost'] == pytest.approx(900000.0, rel=0.01)


class TestEconomicsServiceWithSystemCostIndex:
    """Test economics calculations with system cost index applied."""

    @pytest.fixture
    def mock_economics_data(self):
        """Base economics data returned by repository."""
        return {
            'type_id': 648,
            'region_id': 10000002,
            'material_cost': 1000000.0,
            'base_job_cost': 50000.0,
            'total_cost': 1050000.0,
            'market_sell_price': 1500000.0,
            'market_buy_price': 1200000.0,
            'profit_sell': 450000.0,
            'profit_buy': 150000.0,
            'roi_sell_percent': 42.86,
            'roi_buy_percent': 14.29,
            'base_production_time': 3600,
            'updated_at': '2026-01-17T12:00:00'
        }

    @pytest.fixture
    def facility_with_sci(self):
        """Facility profile in a system with cost index."""
        return FacilityProfile(
            id=1,
            name="Jita Factory",
            system_id=30000142,
            structure_type="station",
            me_bonus=Decimal("0.0"),
            te_bonus=Decimal("0.0"),
            cost_bonus=Decimal("0.0"),
            facility_tax=Decimal("0.0"),
        )

    @pytest.fixture
    def system_cost_index(self):
        """System cost index for Jita."""
        return SystemCostIndex(
            system_id=30000142,
            system_name="Jita",
            manufacturing_index=Decimal("0.05"),  # 5% cost index
        )

    def test_calculate_with_system_cost_index(self, mock_economics_data, facility_with_sci, system_cost_index):
        """System cost index should be applied to job cost."""
        service = ProductionEconomicsService()

        with patch.object(service.repo, 'get', return_value=mock_economics_data), \
             patch.object(service, '_get_item_info', return_value={'name': 'Badger', 'type_id': 648}), \
             patch.object(service, '_get_region_name', return_value='The Forge'), \
             patch('services.production.economics_service.get_db_connection') as mock_db:

            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.__enter__ = MagicMock(return_value=mock_conn)
            mock_conn.__exit__ = MagicMock(return_value=False)
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
            mock_db.return_value = mock_conn

            # First call: facility profile lookup
            # Second call: system cost index lookup
            mock_cursor.fetchone.side_effect = [
                # Facility profile
                (1, "Jita Factory", 30000142, "station",
                 Decimal("0.0"), Decimal("0.0"), Decimal("0.0"), Decimal("0.0"),
                 Decimal("0.0"), Decimal("0.0"), Decimal("0.0"), "Jita", None, None),
                # System cost index
                (30000142, "Jita", Decimal("0.05"), Decimal("0.0"), Decimal("0.0"),
                 Decimal("0.0"), Decimal("0.0"), Decimal("0.0"), None),
            ]

            result = service.get_economics(
                type_id=648,
                region_id=10000002,
                me=10,
                te=20,
                facility_id=1
            )

            # Job cost with SCI:
            # base_job_cost = 50000
            # system_cost_index = 0.05 (5%)
            # adjusted_job_cost = 50000 * (1 + 0.05) = 52500
            assert result['costs']['job_cost'] == pytest.approx(52500.0, rel=0.01)


class TestEconomicsServiceNetRevenue:
    """Test net revenue calculation with all factors."""

    @pytest.fixture
    def mock_economics_data(self):
        """Base economics data returned by repository."""
        return {
            'type_id': 648,
            'region_id': 10000002,
            'material_cost': 1000000.0,
            'base_job_cost': 50000.0,
            'total_cost': 1050000.0,
            'market_sell_price': 1500000.0,
            'market_buy_price': 1200000.0,
            'profit_sell': 450000.0,
            'profit_buy': 150000.0,
            'roi_sell_percent': 42.86,
            'roi_buy_percent': 14.29,
            'base_production_time': 3600,
            'updated_at': '2026-01-17T12:00:00'
        }

    def test_net_revenue_calculation(self, mock_economics_data):
        """Net revenue should account for broker fees and sales tax."""
        service = ProductionEconomicsService()

        with patch.object(service.repo, 'get', return_value=mock_economics_data), \
             patch.object(service, '_get_item_info', return_value={'name': 'Badger', 'type_id': 648}), \
             patch.object(service, '_get_region_name', return_value='The Forge'), \
             patch('services.production.economics_service.get_db_connection') as mock_db:

            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.__enter__ = MagicMock(return_value=mock_conn)
            mock_conn.__exit__ = MagicMock(return_value=False)
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
            mock_db.return_value = mock_conn

            # Tax profile with specific rates
            mock_cursor.fetchone.return_value = (
                1, "Skilled Trader", None, Decimal("1.50"), Decimal("2.00"),
                Decimal("3.00"), False, None, None
            )

            result = service.get_economics(
                type_id=648,
                region_id=10000002,
                me=10,
                te=20,
                tax_profile_id=1
            )

            # Calculate expected values:
            # sell_price = 1500000
            # broker_fee = 1500000 * 0.02 = 30000
            # sales_tax = 1500000 * 0.03 = 45000
            # net_revenue = 1500000 - 30000 - 45000 = 1425000
            #
            # material_cost = 1000000 * (1 - 10/100) = 900000
            # job_cost = 50000
            # total_cost = 900000 + 50000 = 950000
            #
            # profit = 1425000 - 950000 = 475000

            assert result['profitability']['profit_sell'] == pytest.approx(475000.0, rel=0.01)


class TestEconomicsServiceCombinedProfile:
    """Test economics with both tax and facility profiles."""

    @pytest.fixture
    def mock_economics_data(self):
        """Base economics data returned by repository."""
        return {
            'type_id': 648,
            'region_id': 10000002,
            'material_cost': 1000000.0,
            'base_job_cost': 50000.0,
            'total_cost': 1050000.0,
            'market_sell_price': 1500000.0,
            'market_buy_price': 1200000.0,
            'profit_sell': 450000.0,
            'profit_buy': 150000.0,
            'roi_sell_percent': 42.86,
            'roi_buy_percent': 14.29,
            'base_production_time': 3600,
            'updated_at': '2026-01-17T12:00:00'
        }

    def test_combined_tax_and_facility_profiles(self, mock_economics_data):
        """Both tax and facility profiles should be applied together."""
        service = ProductionEconomicsService()

        with patch.object(service.repo, 'get', return_value=mock_economics_data), \
             patch.object(service, '_get_item_info', return_value={'name': 'Badger', 'type_id': 648}), \
             patch.object(service, '_get_region_name', return_value='The Forge'), \
             patch('services.production.economics_service.get_db_connection') as mock_db:

            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.__enter__ = MagicMock(return_value=mock_conn)
            mock_conn.__exit__ = MagicMock(return_value=False)
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
            mock_db.return_value = mock_conn

            # Multiple queries: tax profile, facility profile, system cost index
            mock_cursor.fetchone.side_effect = [
                # Tax profile
                (1, "Skilled Trader", None, Decimal("1.50"), Decimal("2.00"),
                 Decimal("3.00"), False, None, None),
                # Facility profile
                (1, "Raitaru", 30000142, "engineering_complex",
                 Decimal("1.0"), Decimal("15.0"), Decimal("3.0"), Decimal("0.0"),
                 Decimal("0.0"), Decimal("0.0"), Decimal("0.0"), "Jita", None, None),
                # System cost index
                (30000142, "Jita", Decimal("0.05"), Decimal("0.0"), Decimal("0.0"),
                 Decimal("0.0"), Decimal("0.0"), Decimal("0.0"), None),
            ]

            result = service.get_economics(
                type_id=648,
                region_id=10000002,
                me=10,
                te=20,
                tax_profile_id=1,
                facility_id=1
            )

            # Both profiles should be present
            assert result['tax_profile'] is not None
            assert result['facility'] is not None

            # Calculate expected values:
            # Material cost with combined ME (10 + 1 = 11):
            # adjusted_material_cost = 1000000 * (1 - 11/100) = 890000
            assert result['costs']['material_cost'] == pytest.approx(890000.0, rel=0.01)

            # Job cost with SCI (5%):
            # adjusted_job_cost = 50000 * (1 + 0.05) = 52500
            assert result['costs']['job_cost'] == pytest.approx(52500.0, rel=0.01)

            # Tax calculations:
            # broker_fee = 1500000 * 0.02 = 30000
            # sales_tax = 1500000 * 0.03 = 45000
            assert result['costs']['broker_fee'] == pytest.approx(30000.0, rel=0.01)
            assert result['costs']['sales_tax'] == pytest.approx(45000.0, rel=0.01)
