import pytest
from unittest.mock import Mock, patch
from services.portfolio_service import PortfolioService

@pytest.fixture
def portfolio_service():
    return PortfolioService()

@pytest.fixture
def character_ids():
    return [526379435, 1117367444, 110592475]  # Artallus, Cytrex, Cytricia

def test_get_character_summaries(portfolio_service, character_ids):
    """Should return summary for all characters"""
    with patch('services.portfolio_service.character_api') as mock_char:
        mock_char.get_wallet_balance.return_value = {'balance': 250000000}
        mock_char.get_character_location.return_value = {'solar_system_id': 30001365}
        mock_char.get_industry_jobs.return_value = {'jobs': []}
        mock_char.get_skill_queue.return_value = {'queue': []}

        result = portfolio_service.get_character_summaries(character_ids)

        assert len(result) == 3
        assert all('character_id' in char for char in result)

def test_get_total_portfolio_value(portfolio_service, character_ids):
    """Should calculate total ISK across all characters"""
    with patch('services.portfolio_service.character_api') as mock_char:
        mock_char.get_wallet_balance.side_effect = [
            {'balance': 250000000},
            {'balance': 180000000},
            {'balance': 95000000}
        ]

        result = portfolio_service.get_total_portfolio_value(character_ids)

        assert result == 525000000
