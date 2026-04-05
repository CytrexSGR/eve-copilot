"""
Unit tests for PI Profitability Service
Tests market-based profit calculations for PI products.
"""

from unittest.mock import Mock

import pytest

from src.services.pi.profitability_service import PIProfitabilityService
from src.services.pi.models import (
    PISchematic,
    PISchematicInput,
    PIProfitability,
)


@pytest.fixture
def mock_repo():
    """Create a mock PIRepository."""
    return Mock()


@pytest.fixture
def mock_market():
    """Create a mock market price provider."""
    return Mock()


@pytest.fixture
def profitability_service(mock_repo, mock_market):
    """Create PIProfitabilityService with mocked dependencies."""
    return PIProfitabilityService(mock_repo, mock_market)


class TestPIProfitabilityServiceInit:
    """Test PIProfitabilityService initialization."""

    def test_init_with_dependencies(self, mock_repo, mock_market):
        """Test initialization with repository and market service."""
        service = PIProfitabilityService(mock_repo, mock_market)
        assert service.repo == mock_repo
        assert service.market == mock_market

    def test_default_region_id(self):
        """Test default region ID is Jita."""
        assert PIProfitabilityService.DEFAULT_REGION_ID == 10000002


class TestCalculateProfitabilityP1:
    """Test calculate_profitability for P1 products."""

    def test_calculate_p1_profitability(self, profitability_service, mock_repo, mock_market):
        """Test profitability calculation for P1 product (Bacteria)."""
        # P1 Bacteria: 40 Microorganisms -> 20 Bacteria, 30 min cycle
        mock_repo.get_schematic_for_output.return_value = PISchematic(
            schematic_id=65,
            schematic_name="Bacteria",
            cycle_time=1800,  # 30 minutes
            tier=1,
            inputs=[PISchematicInput(type_id=2073, type_name="Microorganisms", quantity=40)],
            output_type_id=2393,
            output_name="Bacteria",
            output_quantity=20,
        )

        # Mock market prices
        def mock_get_price(type_id, region_id):
            prices = {
                2073: 5.0,    # Microorganisms: 5 ISK each
                2393: 50.0,   # Bacteria: 50 ISK each
            }
            return prices.get(type_id)

        mock_market.get_price.side_effect = mock_get_price

        result = profitability_service.calculate_profitability(2393)

        assert result is not None
        assert isinstance(result, PIProfitability)
        assert result.type_id == 2393
        assert result.type_name == "Bacteria"
        assert result.tier == 1
        assert result.schematic_id == 65

        # Input cost: 40 * 5 = 200 ISK
        assert result.input_cost == 200.0
        # Output value: 20 * 50 = 1000 ISK
        assert result.output_value == 1000.0
        # Profit per run: 1000 - 200 = 800 ISK
        assert result.profit_per_run == 800.0
        # Cycles per hour: 3600 / 1800 = 2
        # Profit per hour: 800 * 2 = 1600 ISK
        assert result.profit_per_hour == 1600.0
        # ROI: (800 / 200) * 100 = 400%
        assert result.roi_percent == 400.0
        assert result.cycle_time == 1800

    def test_calculate_with_custom_region(self, profitability_service, mock_repo, mock_market):
        """Test profitability calculation with non-default region."""
        mock_repo.get_schematic_for_output.return_value = PISchematic(
            schematic_id=65,
            schematic_name="Bacteria",
            cycle_time=1800,
            tier=1,
            inputs=[PISchematicInput(type_id=2073, type_name="Microorganisms", quantity=40)],
            output_type_id=2393,
            output_name="Bacteria",
            output_quantity=20,
        )

        mock_market.get_price.return_value = 100.0

        # Calculate for Amarr region (10000043)
        result = profitability_service.calculate_profitability(2393, region_id=10000043)

        assert result is not None
        # Verify market was called with correct region
        mock_market.get_price.assert_any_call(2073, 10000043)
        mock_market.get_price.assert_any_call(2393, 10000043)


class TestCalculateProfitabilityP2:
    """Test calculate_profitability for P2 products."""

    def test_calculate_p2_profitability(self, profitability_service, mock_repo, mock_market):
        """Test profitability calculation for P2 product (Coolant)."""
        # P2 Coolant: 40 Electrolytes + 40 Water -> 5 Coolant, 1h cycle
        mock_repo.get_schematic_for_output.return_value = PISchematic(
            schematic_id=126,
            schematic_name="Coolant",
            cycle_time=3600,  # 1 hour
            tier=2,
            inputs=[
                PISchematicInput(type_id=2389, type_name="Electrolytes", quantity=40),
                PISchematicInput(type_id=2390, type_name="Water", quantity=40),
            ],
            output_type_id=9832,
            output_name="Coolant",
            output_quantity=5,
        )

        def mock_get_price(type_id, region_id):
            prices = {
                2389: 100.0,   # Electrolytes: 100 ISK each
                2390: 100.0,   # Water: 100 ISK each
                9832: 2000.0,  # Coolant: 2000 ISK each
            }
            return prices.get(type_id)

        mock_market.get_price.side_effect = mock_get_price

        result = profitability_service.calculate_profitability(9832)

        assert result is not None
        assert result.type_id == 9832
        assert result.type_name == "Coolant"
        assert result.tier == 2

        # Input cost: (40 * 100) + (40 * 100) = 8000 ISK
        assert result.input_cost == 8000.0
        # Output value: 5 * 2000 = 10000 ISK
        assert result.output_value == 10000.0
        # Profit per run: 10000 - 8000 = 2000 ISK
        assert result.profit_per_run == 2000.0
        # Cycles per hour: 3600 / 3600 = 1
        # Profit per hour: 2000 * 1 = 2000 ISK
        assert result.profit_per_hour == 2000.0
        # ROI: (2000 / 8000) * 100 = 25%
        assert result.roi_percent == 25.0


class TestCalculateProfitabilityEdgeCases:
    """Test edge cases for calculate_profitability."""

    def test_returns_none_for_non_pi_item(self, profitability_service, mock_repo, mock_market):
        """Test returns None when item has no schematic (not PI)."""
        mock_repo.get_schematic_for_output.return_value = None

        result = profitability_service.calculate_profitability(999999)

        assert result is None
        mock_market.get_price.assert_not_called()

    def test_returns_none_when_input_price_unavailable(
        self, profitability_service, mock_repo, mock_market
    ):
        """Test returns None when input price is unavailable."""
        mock_repo.get_schematic_for_output.return_value = PISchematic(
            schematic_id=65,
            schematic_name="Bacteria",
            cycle_time=1800,
            tier=1,
            inputs=[PISchematicInput(type_id=2073, type_name="Microorganisms", quantity=40)],
            output_type_id=2393,
            output_name="Bacteria",
            output_quantity=20,
        )

        # Input price is None
        mock_market.get_price.return_value = None

        result = profitability_service.calculate_profitability(2393)

        assert result is None

    def test_returns_none_when_input_price_zero(
        self, profitability_service, mock_repo, mock_market
    ):
        """Test returns None when input price is zero."""
        mock_repo.get_schematic_for_output.return_value = PISchematic(
            schematic_id=65,
            schematic_name="Bacteria",
            cycle_time=1800,
            tier=1,
            inputs=[PISchematicInput(type_id=2073, type_name="Microorganisms", quantity=40)],
            output_type_id=2393,
            output_name="Bacteria",
            output_quantity=20,
        )

        # Input price is zero
        mock_market.get_price.return_value = 0.0

        result = profitability_service.calculate_profitability(2393)

        assert result is None

    def test_returns_none_when_output_price_unavailable(
        self, profitability_service, mock_repo, mock_market
    ):
        """Test returns None when output price is unavailable."""
        mock_repo.get_schematic_for_output.return_value = PISchematic(
            schematic_id=65,
            schematic_name="Bacteria",
            cycle_time=1800,
            tier=1,
            inputs=[PISchematicInput(type_id=2073, type_name="Microorganisms", quantity=40)],
            output_type_id=2393,
            output_name="Bacteria",
            output_quantity=20,
        )

        def mock_get_price(type_id, region_id):
            if type_id == 2073:
                return 5.0  # Input has price
            return None  # Output has no price

        mock_market.get_price.side_effect = mock_get_price

        result = profitability_service.calculate_profitability(2393)

        assert result is None

    def test_returns_none_when_output_price_zero(
        self, profitability_service, mock_repo, mock_market
    ):
        """Test returns None when output price is zero."""
        mock_repo.get_schematic_for_output.return_value = PISchematic(
            schematic_id=65,
            schematic_name="Bacteria",
            cycle_time=1800,
            tier=1,
            inputs=[PISchematicInput(type_id=2073, type_name="Microorganisms", quantity=40)],
            output_type_id=2393,
            output_name="Bacteria",
            output_quantity=20,
        )

        def mock_get_price(type_id, region_id):
            if type_id == 2073:
                return 5.0  # Input has price
            return 0.0  # Output price is zero

        mock_market.get_price.side_effect = mock_get_price

        result = profitability_service.calculate_profitability(2393)

        assert result is None

    def test_negative_profit(self, profitability_service, mock_repo, mock_market):
        """Test calculation with negative profit (loss)."""
        mock_repo.get_schematic_for_output.return_value = PISchematic(
            schematic_id=65,
            schematic_name="Bacteria",
            cycle_time=1800,
            tier=1,
            inputs=[PISchematicInput(type_id=2073, type_name="Microorganisms", quantity=40)],
            output_type_id=2393,
            output_name="Bacteria",
            output_quantity=20,
        )

        def mock_get_price(type_id, region_id):
            prices = {
                2073: 100.0,  # Expensive input
                2393: 10.0,   # Cheap output
            }
            return prices.get(type_id)

        mock_market.get_price.side_effect = mock_get_price

        result = profitability_service.calculate_profitability(2393)

        assert result is not None
        # Input cost: 40 * 100 = 4000 ISK
        assert result.input_cost == 4000.0
        # Output value: 20 * 10 = 200 ISK
        assert result.output_value == 200.0
        # Profit per run: 200 - 4000 = -3800 ISK (loss)
        assert result.profit_per_run == -3800.0
        # ROI: (-3800 / 4000) * 100 = -95%
        assert result.roi_percent == -95.0

    def test_zero_cycle_time_handled(self, profitability_service, mock_repo, mock_market):
        """Test that zero cycle time is handled gracefully."""
        mock_repo.get_schematic_for_output.return_value = PISchematic(
            schematic_id=65,
            schematic_name="Bacteria",
            cycle_time=0,  # Edge case: zero cycle time
            tier=1,
            inputs=[PISchematicInput(type_id=2073, type_name="Microorganisms", quantity=40)],
            output_type_id=2393,
            output_name="Bacteria",
            output_quantity=20,
        )

        mock_market.get_price.return_value = 10.0

        result = profitability_service.calculate_profitability(2393)

        assert result is not None
        assert result.profit_per_hour == 0.0  # No cycles possible with 0 time


class TestGetOpportunities:
    """Test get_opportunities method."""

    def test_get_opportunities_returns_sorted_by_profit(
        self, profitability_service, mock_repo, mock_market
    ):
        """Test that opportunities are sorted by profit_per_hour descending."""
        # Create three schematics with different profitabilities
        mock_repo.get_all_schematics.return_value = [
            PISchematic(
                schematic_id=1,
                schematic_name="Low Profit",
                cycle_time=3600,
                tier=1,
                inputs=[PISchematicInput(type_id=101, type_name="Input A", quantity=10)],
                output_type_id=201,
                output_name="Output A",
                output_quantity=10,
            ),
            PISchematic(
                schematic_id=2,
                schematic_name="High Profit",
                cycle_time=3600,
                tier=1,
                inputs=[PISchematicInput(type_id=102, type_name="Input B", quantity=10)],
                output_type_id=202,
                output_name="Output B",
                output_quantity=10,
            ),
            PISchematic(
                schematic_id=3,
                schematic_name="Medium Profit",
                cycle_time=3600,
                tier=1,
                inputs=[PISchematicInput(type_id=103, type_name="Input C", quantity=10)],
                output_type_id=203,
                output_name="Output C",
                output_quantity=10,
            ),
        ]

        def mock_get_price(type_id, region_id):
            prices = {
                101: 10.0, 201: 20.0,   # Low profit: 200-100=100
                102: 10.0, 202: 100.0,  # High profit: 1000-100=900
                103: 10.0, 203: 50.0,   # Medium profit: 500-100=400
            }
            return prices.get(type_id)

        mock_market.get_price.side_effect = mock_get_price

        result = profitability_service.get_opportunities()

        assert len(result) == 3
        # Sorted by profit_per_hour descending
        assert result[0].type_id == 202  # High profit first
        assert result[0].profit_per_hour == 900.0
        assert result[1].type_id == 203  # Medium profit second
        assert result[1].profit_per_hour == 400.0
        assert result[2].type_id == 201  # Low profit last
        assert result[2].profit_per_hour == 100.0

    def test_get_opportunities_with_tier_filter(
        self, profitability_service, mock_repo, mock_market
    ):
        """Test filtering opportunities by tier."""
        mock_repo.get_all_schematics.return_value = [
            PISchematic(
                schematic_id=1,
                schematic_name="P1 Product",
                cycle_time=1800,
                tier=1,
                inputs=[PISchematicInput(type_id=101, type_name="Input", quantity=10)],
                output_type_id=201,
                output_name="P1 Output",
                output_quantity=10,
            ),
        ]

        mock_market.get_price.return_value = 100.0

        result = profitability_service.get_opportunities(tier=1)

        mock_repo.get_all_schematics.assert_called_once_with(tier=1)
        assert len(result) == 1
        assert result[0].tier == 1

    def test_get_opportunities_with_limit(
        self, profitability_service, mock_repo, mock_market
    ):
        """Test limiting number of results."""
        # Create 5 schematics
        schematics = [
            PISchematic(
                schematic_id=i,
                schematic_name=f"Product {i}",
                cycle_time=3600,
                tier=1,
                inputs=[PISchematicInput(type_id=100+i, type_name=f"Input {i}", quantity=10)],
                output_type_id=200+i,
                output_name=f"Output {i}",
                output_quantity=10,
            )
            for i in range(1, 6)
        ]
        mock_repo.get_all_schematics.return_value = schematics

        mock_market.get_price.return_value = 100.0

        result = profitability_service.get_opportunities(limit=3)

        assert len(result) == 3

    def test_get_opportunities_with_min_roi_filter(
        self, profitability_service, mock_repo, mock_market
    ):
        """Test ROI percentage filter works correctly."""
        mock_repo.get_all_schematics.return_value = [
            # Low ROI product
            PISchematic(
                schematic_id=1,
                schematic_name="Low ROI",
                cycle_time=3600,
                tier=1,
                inputs=[PISchematicInput(type_id=101, type_name="Input A", quantity=100)],
                output_type_id=201,
                output_name="Output A",
                output_quantity=10,
            ),
            # High ROI product
            PISchematic(
                schematic_id=2,
                schematic_name="High ROI",
                cycle_time=3600,
                tier=1,
                inputs=[PISchematicInput(type_id=102, type_name="Input B", quantity=10)],
                output_type_id=202,
                output_name="Output B",
                output_quantity=10,
            ),
        ]

        def mock_get_price(type_id, region_id):
            prices = {
                101: 10.0, 201: 20.0,   # Low ROI: (200-1000)/1000 = -80%
                102: 10.0, 202: 100.0,  # High ROI: (1000-100)/100 = 900%
            }
            return prices.get(type_id)

        mock_market.get_price.side_effect = mock_get_price

        # Filter for 0% ROI (removes negative ROI)
        result = profitability_service.get_opportunities(min_roi=0)

        assert len(result) == 1
        assert result[0].type_id == 202
        assert result[0].roi_percent == 900.0

    def test_get_opportunities_skips_unavailable_prices(
        self, profitability_service, mock_repo, mock_market
    ):
        """Test that products without prices are skipped."""
        mock_repo.get_all_schematics.return_value = [
            PISchematic(
                schematic_id=1,
                schematic_name="Has Prices",
                cycle_time=3600,
                tier=1,
                inputs=[PISchematicInput(type_id=101, type_name="Input A", quantity=10)],
                output_type_id=201,
                output_name="Output A",
                output_quantity=10,
            ),
            PISchematic(
                schematic_id=2,
                schematic_name="No Prices",
                cycle_time=3600,
                tier=1,
                inputs=[PISchematicInput(type_id=102, type_name="Input B", quantity=10)],
                output_type_id=202,
                output_name="Output B",
                output_quantity=10,
            ),
        ]

        def mock_get_price(type_id, region_id):
            prices = {
                101: 10.0,
                201: 100.0,
                # 102 and 202 have no prices
            }
            return prices.get(type_id)

        mock_market.get_price.side_effect = mock_get_price

        result = profitability_service.get_opportunities()

        assert len(result) == 1
        assert result[0].type_id == 201

    def test_get_opportunities_empty_when_no_schematics(
        self, profitability_service, mock_repo, mock_market
    ):
        """Test returns empty list when no schematics found."""
        mock_repo.get_all_schematics.return_value = []

        result = profitability_service.get_opportunities()

        assert result == []

    def test_get_opportunities_with_custom_region(
        self, profitability_service, mock_repo, mock_market
    ):
        """Test using custom region for price lookups."""
        mock_repo.get_all_schematics.return_value = [
            PISchematic(
                schematic_id=1,
                schematic_name="Test Product",
                cycle_time=3600,
                tier=1,
                inputs=[PISchematicInput(type_id=101, type_name="Input", quantity=10)],
                output_type_id=201,
                output_name="Output",
                output_quantity=10,
            ),
        ]

        mock_market.get_price.return_value = 100.0

        # Use Amarr region
        result = profitability_service.get_opportunities(region_id=10000043)

        # Verify prices were fetched with correct region
        mock_market.get_price.assert_any_call(101, 10000043)
        mock_market.get_price.assert_any_call(201, 10000043)

    def test_get_opportunities_handles_calculation_errors(
        self, profitability_service, mock_repo, mock_market
    ):
        """Test that calculation errors are handled gracefully."""
        mock_repo.get_all_schematics.return_value = [
            PISchematic(
                schematic_id=1,
                schematic_name="Good Product",
                cycle_time=3600,
                tier=1,
                inputs=[PISchematicInput(type_id=101, type_name="Input A", quantity=10)],
                output_type_id=201,
                output_name="Output A",
                output_quantity=10,
            ),
            PISchematic(
                schematic_id=2,
                schematic_name="Problematic Product",
                cycle_time=3600,
                tier=1,
                inputs=[PISchematicInput(type_id=102, type_name="Input B", quantity=10)],
                output_type_id=202,
                output_name="Output B",
                output_quantity=10,
            ),
        ]

        call_count = 0

        def mock_get_price(type_id, region_id):
            nonlocal call_count
            call_count += 1
            if type_id in [102, 202]:
                raise ValueError("Mock error")
            return 100.0

        mock_market.get_price.side_effect = mock_get_price

        result = profitability_service.get_opportunities()

        # Should return only the good product
        assert len(result) == 1
        assert result[0].type_id == 201


class TestCalculateSchematicProfitability:
    """Test _calculate_schematic_profitability internal method."""

    def test_rounding_precision(self, profitability_service, mock_repo, mock_market):
        """Test that values are rounded to 2 decimal places."""
        schematic = PISchematic(
            schematic_id=1,
            schematic_name="Test",
            cycle_time=3600,
            tier=1,
            inputs=[PISchematicInput(type_id=101, type_name="Input", quantity=3)],
            output_type_id=201,
            output_name="Output",
            output_quantity=1,
        )

        def mock_get_price(type_id, region_id):
            # Prices that would produce non-round numbers
            if type_id == 101:
                return 33.333333
            return 111.111111

        mock_market.get_price.side_effect = mock_get_price

        result = profitability_service._calculate_schematic_profitability(
            schematic, 10000002
        )

        assert result is not None
        # Input cost: 3 * 33.333333 = 99.999999 -> rounds to 100.0
        assert result.input_cost == 100.0
        # Output value: 1 * 111.111111 = 111.111111 -> rounds to 111.11
        assert result.output_value == 111.11
        # Profit: 111.111111 - 99.999999 = 11.111112 -> rounds to 11.11
        assert result.profit_per_run == 11.11

    def test_multiple_inputs(self, profitability_service, mock_repo, mock_market):
        """Test calculation with multiple inputs (P3/P4 products)."""
        schematic = PISchematic(
            schematic_id=1,
            schematic_name="Complex Product",
            cycle_time=3600,
            tier=3,
            inputs=[
                PISchematicInput(type_id=101, type_name="Input A", quantity=10),
                PISchematicInput(type_id=102, type_name="Input B", quantity=10),
                PISchematicInput(type_id=103, type_name="Input C", quantity=10),
            ],
            output_type_id=201,
            output_name="Output",
            output_quantity=3,
        )

        def mock_get_price(type_id, region_id):
            prices = {
                101: 100.0,
                102: 200.0,
                103: 300.0,
                201: 5000.0,
            }
            return prices.get(type_id)

        mock_market.get_price.side_effect = mock_get_price

        result = profitability_service._calculate_schematic_profitability(
            schematic, 10000002
        )

        assert result is not None
        # Input cost: 10*100 + 10*200 + 10*300 = 6000 ISK
        assert result.input_cost == 6000.0
        # Output value: 3 * 5000 = 15000 ISK
        assert result.output_value == 15000.0
        # Profit per run: 15000 - 6000 = 9000 ISK
        assert result.profit_per_run == 9000.0


class TestProfitabilityIntegration:
    """Integration-style tests verifying full calculation flow."""

    def test_realistic_p1_calculation(self, profitability_service, mock_repo, mock_market):
        """Test with realistic P1 values."""
        # Bacteria: real cycle time is 30 min, produces 20 from 40 raw
        mock_repo.get_schematic_for_output.return_value = PISchematic(
            schematic_id=65,
            schematic_name="Bacteria",
            cycle_time=1800,
            tier=1,
            inputs=[PISchematicInput(type_id=2073, type_name="Microorganisms", quantity=40)],
            output_type_id=2393,
            output_name="Bacteria",
            output_quantity=20,
        )

        # Realistic prices
        def mock_get_price(type_id, region_id):
            prices = {
                2073: 4.50,   # P0 Microorganisms
                2393: 75.00,  # P1 Bacteria
            }
            return prices.get(type_id)

        mock_market.get_price.side_effect = mock_get_price

        result = profitability_service.calculate_profitability(2393)

        assert result is not None
        # Input: 40 * 4.50 = 180 ISK
        assert result.input_cost == 180.0
        # Output: 20 * 75 = 1500 ISK
        assert result.output_value == 1500.0
        # Profit: 1500 - 180 = 1320 ISK
        assert result.profit_per_run == 1320.0
        # 2 cycles/hour * 1320 = 2640 ISK/hour
        assert result.profit_per_hour == 2640.0
        # ROI: 1320/180 * 100 = 733.33%
        assert result.roi_percent == 733.33

    def test_realistic_p4_calculation(self, profitability_service, mock_repo, mock_market):
        """Test with realistic P4 values."""
        # Broadcast Node: P4, 6h cycle
        mock_repo.get_schematic_for_output.return_value = PISchematic(
            schematic_id=130,
            schematic_name="Broadcast Node",
            cycle_time=21600,  # 6 hours
            tier=4,
            inputs=[
                PISchematicInput(type_id=2867, type_name="Data Chips", quantity=6),
                PISchematicInput(type_id=9836, type_name="High-Tech Transmitters", quantity=6),
                PISchematicInput(type_id=2869, type_name="Neocoms", quantity=6),
            ],
            output_type_id=2870,
            output_name="Broadcast Node",
            output_quantity=1,
        )

        def mock_get_price(type_id, region_id):
            prices = {
                2867: 50000.0,   # Data Chips
                9836: 50000.0,   # High-Tech Transmitters
                2869: 50000.0,   # Neocoms
                2870: 1500000.0, # Broadcast Node
            }
            return prices.get(type_id)

        mock_market.get_price.side_effect = mock_get_price

        result = profitability_service.calculate_profitability(2870)

        assert result is not None
        assert result.tier == 4
        # Input: 6*50000 + 6*50000 + 6*50000 = 900000 ISK
        assert result.input_cost == 900000.0
        # Output: 1 * 1500000 = 1500000 ISK
        assert result.output_value == 1500000.0
        # Profit: 1500000 - 900000 = 600000 ISK
        assert result.profit_per_run == 600000.0
        # 0.167 cycles/hour * 600000 = 100000 ISK/hour
        assert result.profit_per_hour == 100000.0
        # ROI: 600000/900000 * 100 = 66.67%
        assert result.roi_percent == 66.67
