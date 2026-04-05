"""Tests for account summary endpoint."""
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI
from app.routers.account_summary import router


def _make_app():
    app = FastAPI()
    app.include_router(router, prefix="/api/characters")
    return app


class TestAccountSummary:
    def test_no_session_returns_401(self):
        client = TestClient(_make_app())
        resp = client.get("/api/characters/summary/account")
        assert resp.status_code == 401

    @patch("app.routers.account_summary.httpx.Client")
    def test_invalid_session_returns_401(self, mock_client_cls):
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=MagicMock(get=MagicMock(return_value=mock_resp)))
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        client = TestClient(_make_app())
        resp = client.get("/api/characters/summary/account", cookies={"session": "bad"})
        assert resp.status_code == 401
