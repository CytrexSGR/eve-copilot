# tests/jobs/test_market_hot_items_refresher.py
"""Tests for Hot Items background refresh job."""
import pytest
from unittest.mock import Mock, MagicMock
from jobs.market_hot_items_refresher import HotItemsRefresher


class TestHotItemsRefresher:
    """Test hot items refresh job."""

    @pytest.fixture
    def mock_repo(self):
        """Mock market repository."""
        return MagicMock()

    @pytest.fixture
    def refresher(self, mock_repo):
        """Create refresher with mocked dependencies."""
        return HotItemsRefresher(repository=mock_repo)

    def test_refresh_fetches_hot_items(self, refresher, mock_repo):
        """Test that refresh fetches all hot items."""
        mock_repo.refresh_hot_items.return_value = {
            "refreshed": 56,
            "errors": 0,
            "duration_ms": 1500
        }

        result = refresher.refresh()

        mock_repo.refresh_hot_items.assert_called_once()
        assert result["refreshed"] == 56

    def test_refresh_logs_stats(self, refresher, mock_repo):
        """Test that refresh logs statistics."""
        mock_repo.refresh_hot_items.return_value = {
            "refreshed": 200,
            "errors": 0,
            "duration_ms": 1500
        }

        result = refresher.refresh()

        assert result["refreshed"] == 200
        assert "duration_ms" in result

    def test_refresh_handles_errors(self, refresher, mock_repo):
        """Test graceful error handling."""
        mock_repo.refresh_hot_items.side_effect = Exception("Network error")

        result = refresher.refresh()

        assert result["success"] is False
        assert "error" in result
