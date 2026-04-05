# tests/services/test_timezone_heatmap.py
from unittest.mock import MagicMock
from services.war_economy.timezone_heatmap import TimezoneHeatmapService


class TestTimezoneHeatmapService:
    """Test timezone heatmap aggregation logic."""

    def test_get_hourly_activity_returns_24_hours(self):
        """Should return activity for all 24 hours."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        # Simulate DB returning some hours with kills
        mock_cursor.fetchall.return_value = [
            (0, 10, 1000000000),   # hour 0: 10 kills, 1B ISK
            (14, 50, 5000000000),  # hour 14: 50 kills, 5B ISK
            (22, 25, 2500000000),  # hour 22: 25 kills, 2.5B ISK
        ]

        service = TimezoneHeatmapService(mock_conn)
        result = service.get_hourly_activity(days_back=7)

        assert len(result["hours"]) == 24
        assert result["hours"][0]["kills"] == 10
        assert result["hours"][14]["kills"] == 50
        assert result["hours"][1]["kills"] == 0  # No data = 0

    def test_identifies_peak_hours(self):
        """Should identify top 3 peak activity hours."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        mock_cursor.fetchall.return_value = [
            (14, 100, 10000000000),
            (15, 80, 8000000000),
            (16, 60, 6000000000),
            (4, 5, 500000000),
        ]

        service = TimezoneHeatmapService(mock_conn)
        result = service.get_hourly_activity(days_back=7)

        assert result["peak_hours"] == [14, 15, 16]

    def test_identifies_low_activity_windows(self):
        """Should identify 3 consecutive low-activity hours as defensive gap."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        # Hours 3-6 have very low activity
        mock_cursor.fetchall.return_value = [
            (14, 100, 10000000000),
            (3, 2, 100000000),
            (4, 1, 50000000),
            (5, 3, 150000000),
        ]

        service = TimezoneHeatmapService(mock_conn)
        result = service.get_hourly_activity(days_back=7)

        assert "defensive_gaps" in result
        # Hours 3-5 should be identified as gap (low activity)
        assert any(3 in gap for gap in result["defensive_gaps"])

    def test_get_alliance_comparison_returns_data_for_each_alliance(self):
        """Should return activity data for each requested alliance."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        # Return different data for each call
        mock_cursor.fetchall.return_value = [
            (14, 50, 5000000000),
        ]

        service = TimezoneHeatmapService(mock_conn)
        result = service.get_alliance_comparison([99001, 99002], days_back=7)

        assert "alliances" in result
        assert "99001" in result["alliances"]
        assert "99002" in result["alliances"]
        assert result["days_analyzed"] == 7
