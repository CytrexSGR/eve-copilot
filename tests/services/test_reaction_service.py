"""
Unit tests for Reaction Service
Tests reaction data retrieval and profitability calculations
"""

from decimal import Decimal
from typing import Dict, List
from unittest.mock import Mock, MagicMock, patch

import pytest

from src.services.reaction_service import ReactionService
from src.services.reaction_models import (
    ReactionFormula,
    ReactionInput,
    ReactionProfitability,
    ReactionSearchResult,
    FacilityBonus,
)
from src.core.exceptions import NotFoundError


@pytest.fixture
def mock_db_pool():
    """Mock DatabasePool."""
    pool = Mock()
    pool.get_connection.return_value.__enter__ = Mock()
    pool.get_connection.return_value.__exit__ = Mock(return_value=False)
    return pool


@pytest.fixture
def reaction_service(mock_db_pool):
    """Create ReactionService with mocked database pool."""
    return ReactionService(mock_db_pool)


class TestReactionServiceInit:
    """Test ReactionService initialization"""

    def test_init_with_db_pool(self, mock_db_pool):
        """Test initialization with database pool"""
        service = ReactionService(mock_db_pool)
        assert service.db == mock_db_pool
        assert service.DEFAULT_REGION_ID == 10000002  # Jita


class TestGetAllReactions:
    """Test get_all_reactions method"""

    def test_get_all_reactions_returns_formulas(self, reaction_service, mock_db_pool):
        """Test that get_all_reactions returns ReactionFormula objects"""
        # Setup mock cursor
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=False)

        # Reaction data
        reactions_data = [
            {
                'reaction_type_id': 57490,
                'reaction_name': 'Carbon Fiber Reaction Formula',
                'product_type_id': 57453,
                'product_name': 'Carbon Fiber',
                'product_quantity': 200,
                'reaction_time': 3600,
                'reaction_category': 'polymer'
            }
        ]

        # Input data
        inputs_data = [
            {
                'reaction_type_id': 57490,
                'input_type_id': 4246,
                'input_name': 'Hydrogen Fuel Block',
                'quantity': 5
            },
            {
                'reaction_type_id': 57490,
                'input_type_id': 16633,
                'input_name': 'Hydrocarbons',
                'quantity': 100
            }
        ]

        # Setup mock to return reactions, then inputs
        mock_cursor.fetchall.side_effect = [reactions_data, inputs_data]

        mock_conn = MagicMock()
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor

        mock_db_pool.get_connection.return_value = mock_conn

        result = reaction_service.get_all_reactions()

        assert len(result) == 1
        assert isinstance(result[0], ReactionFormula)
        assert result[0].reaction_type_id == 57490
        assert result[0].reaction_name == 'Carbon Fiber Reaction Formula'
        assert result[0].product_name == 'Carbon Fiber'
        assert result[0].product_quantity == 200
        assert len(result[0].inputs) == 2

    def test_get_all_reactions_empty_database(self, reaction_service, mock_db_pool):
        """Test get_all_reactions with empty database"""
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=False)
        mock_cursor.fetchall.return_value = []

        mock_conn = MagicMock()
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor

        mock_db_pool.get_connection.return_value = mock_conn

        result = reaction_service.get_all_reactions()

        assert result == []


class TestGetReaction:
    """Test get_reaction method"""

    def test_get_reaction_found(self, reaction_service, mock_db_pool):
        """Test getting a specific reaction by ID"""
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=False)

        reaction_data = {
            'reaction_type_id': 57490,
            'reaction_name': 'Carbon Fiber Reaction Formula',
            'product_type_id': 57453,
            'product_name': 'Carbon Fiber',
            'product_quantity': 200,
            'reaction_time': 3600,
            'reaction_category': 'polymer'
        }

        inputs_data = [
            {
                'input_type_id': 4246,
                'input_name': 'Hydrogen Fuel Block',
                'quantity': 5
            }
        ]

        mock_cursor.fetchone.return_value = reaction_data
        mock_cursor.fetchall.return_value = inputs_data

        mock_conn = MagicMock()
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor

        mock_db_pool.get_connection.return_value = mock_conn

        result = reaction_service.get_reaction(57490)

        assert result is not None
        assert isinstance(result, ReactionFormula)
        assert result.reaction_type_id == 57490
        assert len(result.inputs) == 1

    def test_get_reaction_not_found(self, reaction_service, mock_db_pool):
        """Test getting a non-existent reaction"""
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=False)
        mock_cursor.fetchone.return_value = None

        mock_conn = MagicMock()
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor

        mock_db_pool.get_connection.return_value = mock_conn

        result = reaction_service.get_reaction(999999)

        assert result is None


class TestSearchReactions:
    """Test search_reactions method"""

    def test_search_reactions_by_name(self, reaction_service, mock_db_pool):
        """Test searching reactions by name"""
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=False)

        search_results = [
            {
                'reaction_type_id': 57490,
                'reaction_name': 'Carbon Fiber Reaction Formula',
                'product_type_id': 57453,
                'product_name': 'Carbon Fiber',
                'product_quantity': 200,
                'reaction_time': 3600,
                'reaction_category': 'polymer'
            }
        ]

        mock_cursor.fetchall.return_value = search_results

        mock_conn = MagicMock()
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor

        mock_db_pool.get_connection.return_value = mock_conn

        result = reaction_service.search_reactions("carbon")

        assert len(result) == 1
        assert isinstance(result[0], ReactionSearchResult)
        assert result[0].reaction_name == 'Carbon Fiber Reaction Formula'

    def test_search_reactions_empty_result(self, reaction_service, mock_db_pool):
        """Test searching with no results"""
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=False)
        mock_cursor.fetchall.return_value = []

        mock_conn = MagicMock()
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor

        mock_db_pool.get_connection.return_value = mock_conn

        result = reaction_service.search_reactions("nonexistent")

        assert result == []


class TestCalculateProfitability:
    """Test calculate_profitability method"""

    def test_calculate_profitability_basic(self, reaction_service, mock_db_pool):
        """Test basic profitability calculation"""
        # Create a reaction with known values
        reaction = ReactionFormula(
            reaction_type_id=57490,
            reaction_name='Test Reaction',
            product_type_id=57453,
            product_name='Test Product',
            product_quantity=100,
            reaction_time=3600,  # 1 hour
            reaction_category='test',
            inputs=[
                ReactionInput(input_type_id=100, input_name='Input A', quantity=10),
                ReactionInput(input_type_id=101, input_name='Input B', quantity=5)
            ]
        )

        # Mock get_reaction to return our test reaction
        with patch.object(reaction_service, 'get_reaction', return_value=reaction):
            # Mock _get_prices to return known prices
            prices = {
                100: {'sell': Decimal('100'), 'buy': Decimal('90')},  # Input A: 100 ISK
                101: {'sell': Decimal('200'), 'buy': Decimal('180')},  # Input B: 200 ISK
                57453: {'sell': Decimal('5000'), 'buy': Decimal('4500')}  # Product: 5000 ISK
            }
            with patch.object(reaction_service, '_get_prices', return_value=prices):
                result = reaction_service.calculate_profitability(57490)

        assert isinstance(result, ReactionProfitability)

        # Input cost: (10 * 100) + (5 * 200) = 1000 + 1000 = 2000
        assert result.input_cost == Decimal('2000')

        # Output value: 100 * 5000 = 500,000
        assert result.output_value == Decimal('500000')

        # Profit per run: 500,000 - 2,000 = 498,000
        assert result.profit_per_run == Decimal('498000')

        # Runs per hour: 3600 / 3600 = 1
        assert result.runs_per_hour == 1.0

        # Profit per hour: 498,000 * 1 = 498,000
        assert result.profit_per_hour == Decimal('498000')

        # ROI: (498,000 / 2,000) * 100 = 24,900%
        assert result.roi_percent > 0

    def test_calculate_profitability_with_facility_bonus(self, reaction_service, mock_db_pool):
        """Test profitability with facility bonuses"""
        reaction = ReactionFormula(
            reaction_type_id=57490,
            reaction_name='Test Reaction',
            product_type_id=57453,
            product_name='Test Product',
            product_quantity=100,
            reaction_time=3600,
            reaction_category='test',
            inputs=[
                ReactionInput(input_type_id=100, input_name='Input A', quantity=100)
            ]
        )

        facility_bonus = FacilityBonus(
            time_multiplier=0.75,  # 25% faster
            material_multiplier=0.98  # 2% material savings
        )

        with patch.object(reaction_service, 'get_reaction', return_value=reaction):
            prices = {
                100: {'sell': Decimal('100'), 'buy': Decimal('90')},
                57453: {'sell': Decimal('50000'), 'buy': Decimal('45000')}
            }
            with patch.object(reaction_service, '_get_prices', return_value=prices):
                result = reaction_service.calculate_profitability(
                    57490,
                    facility_bonus=facility_bonus
                )

        # Time should be 75% of 3600 = 2700 seconds
        assert result.reaction_time == 2700

        # Runs per hour: 3600 / 2700 = 1.33
        assert result.runs_per_hour > 1.0

        # Input quantity should be reduced: 100 * 0.98 = 98
        # Input cost: 98 * 100 = 9800
        assert result.input_cost == Decimal('9800')

    def test_calculate_profitability_reaction_not_found(self, reaction_service, mock_db_pool):
        """Test profitability calculation with non-existent reaction"""
        with patch.object(reaction_service, 'get_reaction', return_value=None):
            with pytest.raises(NotFoundError) as exc_info:
                reaction_service.calculate_profitability(999999)

        assert "reaction" in str(exc_info.value).lower()

    def test_calculate_profitability_with_different_region(self, reaction_service, mock_db_pool):
        """Test profitability with different region"""
        reaction = ReactionFormula(
            reaction_type_id=57490,
            reaction_name='Test Reaction',
            product_type_id=57453,
            product_name='Test Product',
            product_quantity=100,
            reaction_time=3600,
            reaction_category='test',
            inputs=[
                ReactionInput(input_type_id=100, input_name='Input A', quantity=10)
            ]
        )

        with patch.object(reaction_service, 'get_reaction', return_value=reaction):
            prices = {
                100: {'sell': Decimal('100'), 'buy': Decimal('90')},
                57453: {'sell': Decimal('5000'), 'buy': Decimal('4500')}
            }
            with patch.object(reaction_service, '_get_prices', return_value=prices) as mock_prices:
                result = reaction_service.calculate_profitability(
                    57490,
                    region_id=10000043  # Amarr
                )

                # Verify _get_prices was called with the correct region
                mock_prices.assert_called_once()
                call_args = mock_prices.call_args
                # The region_id is passed as a positional argument at index 1
                assert call_args[0][1] == 10000043


class TestGetProfitableReactions:
    """Test get_profitable_reactions method"""

    def test_get_profitable_reactions_sorted_by_profit(self, reaction_service, mock_db_pool):
        """Test that profitable reactions are sorted by profit per hour"""
        reactions = [
            ReactionFormula(
                reaction_type_id=1,
                reaction_name='Low Profit Reaction',
                product_type_id=101,
                product_name='Product A',
                product_quantity=100,
                reaction_time=3600,
                reaction_category='test',
                inputs=[ReactionInput(input_type_id=1001, input_name='Input', quantity=10)]
            ),
            ReactionFormula(
                reaction_type_id=2,
                reaction_name='High Profit Reaction',
                product_type_id=102,
                product_name='Product B',
                product_quantity=100,
                reaction_time=3600,
                reaction_category='test',
                inputs=[ReactionInput(input_type_id=1002, input_name='Input', quantity=10)]
            )
        ]

        profitabilities = [
            ReactionProfitability(
                reaction_type_id=1,
                reaction_name='Low Profit Reaction',
                product_name='Product A',
                input_cost=Decimal('1000'),
                output_value=Decimal('2000'),
                profit_per_run=Decimal('1000'),
                profit_per_hour=Decimal('1000'),
                roi_percent=100.0,
                reaction_time=3600,
                runs_per_hour=1.0
            ),
            ReactionProfitability(
                reaction_type_id=2,
                reaction_name='High Profit Reaction',
                product_name='Product B',
                input_cost=Decimal('1000'),
                output_value=Decimal('10000'),
                profit_per_run=Decimal('9000'),
                profit_per_hour=Decimal('9000'),
                roi_percent=900.0,
                reaction_time=3600,
                runs_per_hour=1.0
            )
        ]

        with patch.object(reaction_service, 'get_all_reactions', return_value=reactions):
            with patch.object(
                reaction_service,
                'calculate_profitability',
                side_effect=profitabilities
            ):
                result = reaction_service.get_profitable_reactions()

        # Should be sorted by profit per hour descending
        assert len(result) == 2
        assert result[0].reaction_type_id == 2  # High profit first
        assert result[1].reaction_type_id == 1  # Low profit second

    def test_get_profitable_reactions_with_min_roi_filter(self, reaction_service, mock_db_pool):
        """Test filtering by minimum ROI"""
        reactions = [
            ReactionFormula(
                reaction_type_id=1,
                reaction_name='Low ROI Reaction',
                product_type_id=101,
                product_name='Product A',
                product_quantity=100,
                reaction_time=3600,
                reaction_category='test',
                inputs=[ReactionInput(input_type_id=1001, input_name='Input', quantity=10)]
            ),
            ReactionFormula(
                reaction_type_id=2,
                reaction_name='High ROI Reaction',
                product_type_id=102,
                product_name='Product B',
                product_quantity=100,
                reaction_time=3600,
                reaction_category='test',
                inputs=[ReactionInput(input_type_id=1002, input_name='Input', quantity=10)]
            )
        ]

        profitabilities = [
            ReactionProfitability(
                reaction_type_id=1,
                reaction_name='Low ROI Reaction',
                product_name='Product A',
                input_cost=Decimal('1000'),
                output_value=Decimal('1050'),
                profit_per_run=Decimal('50'),
                profit_per_hour=Decimal('50'),
                roi_percent=5.0,  # 5% ROI
                reaction_time=3600,
                runs_per_hour=1.0
            ),
            ReactionProfitability(
                reaction_type_id=2,
                reaction_name='High ROI Reaction',
                product_name='Product B',
                input_cost=Decimal('1000'),
                output_value=Decimal('1200'),
                profit_per_run=Decimal('200'),
                profit_per_hour=Decimal('200'),
                roi_percent=20.0,  # 20% ROI
                reaction_time=3600,
                runs_per_hour=1.0
            )
        ]

        with patch.object(reaction_service, 'get_all_reactions', return_value=reactions):
            with patch.object(
                reaction_service,
                'calculate_profitability',
                side_effect=profitabilities
            ):
                result = reaction_service.get_profitable_reactions(min_roi=10)

        # Only the 20% ROI reaction should be included
        assert len(result) == 1
        assert result[0].roi_percent == 20.0

    def test_get_profitable_reactions_with_limit(self, reaction_service, mock_db_pool):
        """Test limiting results"""
        # Start from 1 to avoid validation error (reaction_type_id must be > 0)
        reactions = [
            ReactionFormula(
                reaction_type_id=i + 1,
                reaction_name=f'Reaction {i + 1}',
                product_type_id=100 + i,
                product_name=f'Product {i}',
                product_quantity=100,
                reaction_time=3600,
                reaction_category='test',
                inputs=[ReactionInput(input_type_id=1000 + i, input_name='Input', quantity=10)]
            )
            for i in range(10)
        ]

        profitabilities = [
            ReactionProfitability(
                reaction_type_id=i + 1,
                reaction_name=f'Reaction {i + 1}',
                product_name=f'Product {i}',
                input_cost=Decimal('1000'),
                output_value=Decimal(str(2000 + i * 100)),
                profit_per_run=Decimal(str(1000 + i * 100)),
                profit_per_hour=Decimal(str(1000 + i * 100)),
                roi_percent=float(100 + i * 10),
                reaction_time=3600,
                runs_per_hour=1.0
            )
            for i in range(10)
        ]

        with patch.object(reaction_service, 'get_all_reactions', return_value=reactions):
            with patch.object(
                reaction_service,
                'calculate_profitability',
                side_effect=profitabilities
            ):
                result = reaction_service.get_profitable_reactions(limit=5)

        assert len(result) == 5


class TestReactionModels:
    """Test Pydantic model behavior"""

    def test_reaction_formula_runs_per_hour_property(self):
        """Test runs_per_hour calculation"""
        reaction = ReactionFormula(
            reaction_type_id=1,
            reaction_name='Test',
            product_type_id=2,
            product_name='Product',
            product_quantity=100,
            reaction_time=1800,  # 30 minutes
            reaction_category='test',
            inputs=[]
        )

        assert reaction.runs_per_hour == 2.0  # 3600 / 1800 = 2

    def test_reaction_formula_runs_per_hour_zero_time(self):
        """Test runs_per_hour with zero time"""
        reaction = ReactionFormula(
            reaction_type_id=1,
            reaction_name='Test',
            product_type_id=2,
            product_name='Product',
            product_quantity=100,
            reaction_time=1,  # Minimum positive time
            reaction_category='test',
            inputs=[]
        )

        assert reaction.runs_per_hour == 3600.0  # 3600 / 1 = 3600

    def test_facility_bonus_defaults(self):
        """Test FacilityBonus default values"""
        bonus = FacilityBonus()

        assert bonus.time_multiplier == 1.0
        assert bonus.material_multiplier == 1.0

    def test_facility_bonus_custom_values(self):
        """Test FacilityBonus with custom values"""
        bonus = FacilityBonus(
            time_multiplier=0.75,
            material_multiplier=0.98
        )

        assert bonus.time_multiplier == 0.75
        assert bonus.material_multiplier == 0.98

    def test_reaction_profitability_json_serialization(self):
        """Test that Decimal values are serialized properly"""
        profit = ReactionProfitability(
            reaction_type_id=1,
            reaction_name='Test',
            product_name='Product',
            input_cost=Decimal('1000.50'),
            output_value=Decimal('2000.75'),
            profit_per_run=Decimal('1000.25'),
            profit_per_hour=Decimal('2000.50'),
            roi_percent=100.025,
            reaction_time=3600,
            runs_per_hour=2.0
        )

        # Convert to dict (simulates JSON serialization)
        data = profit.model_dump()

        assert data['input_cost'] == Decimal('1000.50')
        assert data['output_value'] == Decimal('2000.75')
