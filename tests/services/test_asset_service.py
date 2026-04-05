"""
Tests for AssetService - Character Asset Caching and Lookup.

Tests cover:
- refresh_character_assets: Fetch and cache assets from ESI
- get_asset_summary: Aggregated asset summary by type
- find_assets_for_types: Find quantities for specific types
- get_cache_status: Cache freshness info
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, Mock

from services.asset_service import AssetService


@pytest.fixture
def asset_service():
    """Create AssetService instance for testing."""
    return AssetService()


@pytest.fixture
def mock_db_connection():
    """Mock database connection context manager."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    mock_conn.__enter__ = MagicMock(return_value=mock_conn)
    mock_conn.__exit__ = MagicMock(return_value=False)
    return mock_conn, mock_cursor


@pytest.fixture
def sample_esi_assets():
    """Sample ESI asset response."""
    return [
        {
            "item_id": 1000000001,
            "type_id": 587,
            "quantity": 5,
            "location_id": 60003760,
            "location_type": "station",
            "location_flag": "Hangar"
        },
        {
            "item_id": 1000000002,
            "type_id": 587,
            "quantity": 3,
            "location_id": 60003760,
            "location_type": "station",
            "location_flag": "Hangar"
        },
        {
            "item_id": 1000000003,
            "type_id": 638,
            "quantity": 1,
            "location_id": 60003760,
            "location_type": "station",
            "location_flag": "Hangar"
        },
        {
            "item_id": 1000000004,
            "type_id": 34,
            "quantity": 10000,
            "location_id": 60003760,
            "location_type": "station",
            "location_flag": "Hangar"
        }
    ]


class TestAssetServiceInit:
    """Test AssetService initialization."""

    def test_can_instantiate(self):
        """Should be able to create AssetService instance."""
        service = AssetService()
        assert service is not None


class TestRefreshCharacterAssets:
    """Tests for refresh_character_assets method."""

    def test_returns_asset_count(self, asset_service, sample_esi_assets, mock_db_connection):
        """Should return number of assets cached."""
        mock_conn, mock_cursor = mock_db_connection
        character_id = 526379435

        with patch('services.asset_service.get_db_connection', return_value=mock_conn):
            with patch('services.asset_service.character_api') as mock_char_api:
                mock_char_api.get_assets.return_value = {
                    "character_id": character_id,
                    "total_items": len(sample_esi_assets),
                    "assets": sample_esi_assets
                }

                with patch('services.asset_service.get_item_info') as mock_item_info:
                    mock_item_info.return_value = {"typeName": "Rifter"}

                    result = asset_service.refresh_character_assets(character_id)

                    assert isinstance(result, int)
                    assert result == len(sample_esi_assets)

    def test_clears_old_assets_before_refresh(self, asset_service, sample_esi_assets, mock_db_connection):
        """Should delete existing cached assets before inserting new ones."""
        mock_conn, mock_cursor = mock_db_connection
        character_id = 526379435

        with patch('services.asset_service.get_db_connection', return_value=mock_conn):
            with patch('services.asset_service.character_api') as mock_char_api:
                mock_char_api.get_assets.return_value = {
                    "character_id": character_id,
                    "total_items": 1,
                    "assets": [sample_esi_assets[0]]
                }

                with patch('services.asset_service.get_item_info') as mock_item_info:
                    mock_item_info.return_value = {"typeName": "Rifter"}

                    asset_service.refresh_character_assets(character_id)

                    # Verify DELETE was called before INSERT
                    calls = [str(call) for call in mock_cursor.execute.call_args_list]
                    delete_found = any("DELETE" in call for call in calls)
                    assert delete_found, "Should delete old assets before refresh"

    def test_handles_esi_error(self, asset_service, mock_db_connection):
        """Should handle ESI errors gracefully."""
        mock_conn, mock_cursor = mock_db_connection
        character_id = 526379435

        with patch('services.asset_service.get_db_connection', return_value=mock_conn):
            with patch('services.asset_service.character_api') as mock_char_api:
                mock_char_api.get_assets.return_value = {
                    "error": "No valid token for character"
                }

                result = asset_service.refresh_character_assets(character_id)

                # Should return 0 on error
                assert result == 0

    def test_resolves_type_names(self, asset_service, sample_esi_assets, mock_db_connection):
        """Should resolve type_id to type_name from SDE."""
        mock_conn, mock_cursor = mock_db_connection
        character_id = 526379435

        with patch('services.asset_service.get_db_connection', return_value=mock_conn):
            with patch('services.asset_service.character_api') as mock_char_api:
                mock_char_api.get_assets.return_value = {
                    "character_id": character_id,
                    "total_items": 1,
                    "assets": [sample_esi_assets[0]]
                }

                with patch('services.asset_service.get_item_info') as mock_item_info:
                    mock_item_info.return_value = {"typeName": "Rifter"}

                    asset_service.refresh_character_assets(character_id)

                    # Verify get_item_info was called for type resolution
                    mock_item_info.assert_called()


class TestGetAssetSummary:
    """Tests for get_asset_summary method."""

    def test_returns_list(self, asset_service, mock_db_connection):
        """Should return list of aggregated assets."""
        mock_conn, mock_cursor = mock_db_connection
        character_id = 526379435

        mock_cursor.fetchall.return_value = [
            (587, "Rifter", 8),
            (638, "Vexor", 1),
            (34, "Tritanium", 10000)
        ]

        with patch('services.asset_service.get_db_connection', return_value=mock_conn):
            result = asset_service.get_asset_summary(character_id)

            assert isinstance(result, list)

    def test_aggregates_by_type(self, asset_service, mock_db_connection):
        """Should group assets by type_id and sum quantities."""
        mock_conn, mock_cursor = mock_db_connection
        character_id = 526379435

        mock_cursor.fetchall.return_value = [
            (587, "Rifter", 8),
            (638, "Vexor", 1)
        ]

        with patch('services.asset_service.get_db_connection', return_value=mock_conn):
            result = asset_service.get_asset_summary(character_id)

            assert len(result) == 2
            rifter = next((a for a in result if a['type_id'] == 587), None)
            assert rifter is not None
            assert rifter['total_quantity'] == 8

    def test_includes_type_name(self, asset_service, mock_db_connection):
        """Should include type_name in each result."""
        mock_conn, mock_cursor = mock_db_connection
        character_id = 526379435

        mock_cursor.fetchall.return_value = [
            (587, "Rifter", 8)
        ]

        with patch('services.asset_service.get_db_connection', return_value=mock_conn):
            result = asset_service.get_asset_summary(character_id)

            assert 'type_name' in result[0]
            assert result[0]['type_name'] == "Rifter"

    def test_empty_cache_returns_empty_list(self, asset_service, mock_db_connection):
        """Should return empty list if no cached assets."""
        mock_conn, mock_cursor = mock_db_connection
        character_id = 526379435

        mock_cursor.fetchall.return_value = []

        with patch('services.asset_service.get_db_connection', return_value=mock_conn):
            result = asset_service.get_asset_summary(character_id)

            assert result == []


class TestFindAssetsForTypes:
    """Tests for find_assets_for_types method."""

    def test_returns_dict(self, asset_service, mock_db_connection):
        """Should return dict mapping type_id to quantity."""
        mock_conn, mock_cursor = mock_db_connection
        character_id = 526379435
        type_ids = [587, 638, 34]

        mock_cursor.fetchall.return_value = [
            (587, 8),
            (638, 1),
            (34, 10000)
        ]

        with patch('services.asset_service.get_db_connection', return_value=mock_conn):
            result = asset_service.find_assets_for_types(character_id, type_ids)

            assert isinstance(result, dict)

    def test_includes_all_requested_types(self, asset_service, mock_db_connection):
        """Should include all requested type_ids, even if not found."""
        mock_conn, mock_cursor = mock_db_connection
        character_id = 526379435
        type_ids = [587, 638, 999]  # 999 doesn't exist in cache

        mock_cursor.fetchall.return_value = [
            (587, 8),
            (638, 1)
        ]

        with patch('services.asset_service.get_db_connection', return_value=mock_conn):
            result = asset_service.find_assets_for_types(character_id, type_ids)

            assert 587 in result
            assert 638 in result
            assert 999 in result
            assert result[999] == 0  # Not found should be 0

    def test_sums_quantities_across_locations(self, asset_service, mock_db_connection):
        """Should sum quantities for same type across different locations."""
        mock_conn, mock_cursor = mock_db_connection
        character_id = 526379435
        type_ids = [587]

        # DB returns aggregated sum already
        mock_cursor.fetchall.return_value = [
            (587, 15)  # Total from all locations
        ]

        with patch('services.asset_service.get_db_connection', return_value=mock_conn):
            result = asset_service.find_assets_for_types(character_id, type_ids)

            assert result[587] == 15

    def test_empty_type_ids_returns_empty_dict(self, asset_service, mock_db_connection):
        """Should return empty dict for empty type_ids list."""
        mock_conn, mock_cursor = mock_db_connection
        character_id = 526379435

        with patch('services.asset_service.get_db_connection', return_value=mock_conn):
            result = asset_service.find_assets_for_types(character_id, [])

            assert result == {}


class TestGetCacheStatus:
    """Tests for get_cache_status method."""

    def test_returns_dict_with_required_keys(self, asset_service, mock_db_connection):
        """Should return dict with last_cached and total_items."""
        mock_conn, mock_cursor = mock_db_connection
        character_id = 526379435

        now = datetime.now()
        mock_cursor.fetchone.return_value = (now, 100)

        with patch('services.asset_service.get_db_connection', return_value=mock_conn):
            result = asset_service.get_cache_status(character_id)

            assert isinstance(result, dict)
            assert 'last_cached' in result
            assert 'total_items' in result

    def test_returns_none_if_never_cached(self, asset_service, mock_db_connection):
        """Should return None for last_cached if no cache exists."""
        mock_conn, mock_cursor = mock_db_connection
        character_id = 526379435

        mock_cursor.fetchone.return_value = None

        with patch('services.asset_service.get_db_connection', return_value=mock_conn):
            result = asset_service.get_cache_status(character_id)

            assert result['last_cached'] is None
            assert result['total_items'] == 0

    def test_returns_correct_timestamp(self, asset_service, mock_db_connection):
        """Should return correct cached_at timestamp."""
        mock_conn, mock_cursor = mock_db_connection
        character_id = 526379435

        expected_time = datetime(2026, 1, 17, 12, 0, 0)
        mock_cursor.fetchone.return_value = (expected_time, 50)

        with patch('services.asset_service.get_db_connection', return_value=mock_conn):
            result = asset_service.get_cache_status(character_id)

            assert result['last_cached'] == expected_time
            assert result['total_items'] == 50


class TestIntegration:
    """Integration tests (require database connection)."""

    @pytest.mark.integration
    def test_refresh_and_query_assets(self, asset_service):
        """Integration test: refresh assets and query them."""
        # This test is marked for integration and requires real DB
        # Will be skipped in unit test runs
        character_id = 526379435  # Artallus

        # Refresh assets from ESI
        count = asset_service.refresh_character_assets(character_id)
        assert count >= 0

        # Get summary
        summary = asset_service.get_asset_summary(character_id)
        assert isinstance(summary, list)

        # Check cache status
        status = asset_service.get_cache_status(character_id)
        # Note: total_items may be less than count due to UPSERT merging
        # items with same (character_id, type_id, location_id)
        assert status['total_items'] > 0
        assert status['last_cached'] is not None
