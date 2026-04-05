"""Tests for ESI helper functions -- parallel alliance name fetching."""
import pytest
from unittest.mock import MagicMock, patch


class TestFetchAllianceNamesFromEsi:
    def test_empty_ids_returns_empty(self):
        from app.routers.reports._helpers import _fetch_alliance_names_from_esi
        cur = MagicMock()
        result = _fetch_alliance_names_from_esi([], cur)
        assert result == {}

    def test_returns_fetched_names(self):
        from app.routers.reports._helpers import _fetch_alliance_names_from_esi
        cur = MagicMock()
        with patch("app.routers.reports._helpers.httpx") as mock_httpx:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"name": "Test Alliance", "ticker": "TEST"}
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.return_value = mock_resp
            mock_httpx.Client.return_value = mock_client
            result = _fetch_alliance_names_from_esi([99003581], cur)
            assert 99003581 in result
            assert result[99003581] == "Test Alliance"

    def test_handles_failure_gracefully(self):
        from app.routers.reports._helpers import _fetch_alliance_names_from_esi
        cur = MagicMock()
        with patch("app.routers.reports._helpers.httpx") as mock_httpx:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.side_effect = Exception("timeout")
            mock_httpx.Client.return_value = mock_client
            result = _fetch_alliance_names_from_esi([99003581], cur)
            assert result == {}

    def test_caches_in_db(self):
        from app.routers.reports._helpers import _fetch_alliance_names_from_esi
        cur = MagicMock()
        with patch("app.routers.reports._helpers.httpx") as mock_httpx:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"name": "A", "ticker": "T"}
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.return_value = mock_resp
            mock_httpx.Client.return_value = mock_client
            _fetch_alliance_names_from_esi([123], cur)
            cur.execute.assert_called_once()
            args = cur.execute.call_args
            assert "INSERT INTO alliance_name_cache" in args[0][0]

    def test_limits_to_20(self):
        from app.routers.reports._helpers import _fetch_alliance_names_from_esi
        cur = MagicMock()
        with patch("app.routers.reports._helpers.httpx") as mock_httpx:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"name": "A", "ticker": "T"}
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.return_value = mock_resp
            mock_httpx.Client.return_value = mock_client
            _fetch_alliance_names_from_esi(list(range(30)), cur)
            assert mock_client.get.call_count == 20

    def test_404_skipped(self):
        from app.routers.reports._helpers import _fetch_alliance_names_from_esi
        cur = MagicMock()
        with patch("app.routers.reports._helpers.httpx") as mock_httpx:
            mock_resp = MagicMock()
            mock_resp.status_code = 404
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.return_value = mock_resp
            mock_httpx.Client.return_value = mock_client
            result = _fetch_alliance_names_from_esi([99], cur)
            assert result == {}
            cur.execute.assert_not_called()
