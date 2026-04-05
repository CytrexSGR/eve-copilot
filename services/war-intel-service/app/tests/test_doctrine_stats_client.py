"""Tests for doctrine stats HTTP client."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestGetDoctrineStats:
    """Test httpx calls to character-service."""

    @pytest.mark.asyncio
    async def test_success_returns_parsed_stats(self):
        from app.services.doctrine_stats_client import get_doctrine_stats, clear_cache
        clear_cache()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "offense": {"total_dps": 523.7, "weapon_dps": 480.0, "drone_dps": 43.7},
            "defense": {"total_ehp": 45000, "tank_type": "armor"},
            "capacitor": {"stable": True},
        }

        with patch("app.services.doctrine_stats_client.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            stats = await get_doctrine_stats(doctrine_id=12)
            assert stats["dps"] == 523.7
            assert stats["ehp"] == 45000
            assert stats["tank_type"] == "armor"
            assert stats["cap_stable"] is True
            assert stats["weapon_dps"] == 480.0
            assert stats["drone_dps"] == 43.7

    @pytest.mark.asyncio
    async def test_service_down_returns_none(self):
        from app.services.doctrine_stats_client import get_doctrine_stats, clear_cache
        clear_cache()

        with patch("app.services.doctrine_stats_client.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get.side_effect = Exception("Connection refused")
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            stats = await get_doctrine_stats(doctrine_id=99)
            assert stats is None

    @pytest.mark.asyncio
    async def test_http_error_returns_none(self):
        from app.services.doctrine_stats_client import get_doctrine_stats, clear_cache
        clear_cache()

        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch("app.services.doctrine_stats_client.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            stats = await get_doctrine_stats(doctrine_id=999)
            assert stats is None

    @pytest.mark.asyncio
    async def test_cache_hit(self):
        from app.services.doctrine_stats_client import get_doctrine_stats, clear_cache, _stats_cache
        clear_cache()
        _stats_cache[42] = {"dps": 100, "ehp": 5000, "tank_type": "shield", "cap_stable": True, "weapon_dps": 80, "drone_dps": 20}

        # Should return cached without HTTP call
        stats = await get_doctrine_stats(doctrine_id=42)
        assert stats["dps"] == 100


class TestGetDoctrineDps:
    @pytest.mark.asyncio
    async def test_returns_dps_value(self):
        from app.services.doctrine_stats_client import get_doctrine_dps, clear_cache, _stats_cache
        clear_cache()
        _stats_cache[12] = {"dps": 523.7, "ehp": 45000, "tank_type": "armor", "cap_stable": True, "weapon_dps": 480, "drone_dps": 43.7}

        dps = await get_doctrine_dps(12)
        assert dps == 523.7

    @pytest.mark.asyncio
    async def test_returns_none_on_failure(self):
        from app.services.doctrine_stats_client import get_doctrine_dps, clear_cache
        clear_cache()

        with patch("app.services.doctrine_stats_client.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get.side_effect = Exception("fail")
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            dps = await get_doctrine_dps(999)
            assert dps is None


class TestResolvDoctrineId:
    def test_found(self):
        from app.services.doctrine_stats_client import resolve_doctrine_id

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {"id": 12}
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)

        mock_db = MagicMock()
        mock_db.cursor.return_value = mock_cursor

        assert resolve_doctrine_id(mock_db, "Muninn") == 12

    def test_not_found(self):
        from app.services.doctrine_stats_client import resolve_doctrine_id

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)

        mock_db = MagicMock()
        mock_db.cursor.return_value = mock_cursor

        assert resolve_doctrine_id(mock_db, "NonexistentDoctrine") is None


class TestClearCache:
    def test_clear(self):
        from app.services.doctrine_stats_client import clear_cache, _stats_cache
        _stats_cache[1] = {"dps": 100}
        clear_cache()
        assert len(_stats_cache) == 0
