"""Tests for character management endpoints."""
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from fastapi import FastAPI
from app.routers.character_management import router


def _make_app():
    app = FastAPI()
    app.include_router(router, prefix="/api/auth")
    return app


class TestTokenHealth:
    @patch("app.routers.character_management.JWTService")
    def test_no_session_returns_401(self, mock_jwt_cls):
        client = TestClient(_make_app())
        resp = client.get("/api/auth/public/characters/123/token-health")
        assert resp.status_code == 401

    @patch("app.routers.character_management.JWTService")
    def test_invalid_session_returns_401(self, mock_jwt_cls):
        mock_jwt_cls.return_value.validate_token.return_value = None
        client = TestClient(_make_app())
        resp = client.get("/api/auth/public/characters/123/token-health", cookies={"session": "bad"})
        assert resp.status_code == 401


class TestSetPrimary:
    @patch("app.routers.character_management.JWTService")
    def test_no_session_returns_401(self, mock_jwt_cls):
        client = TestClient(_make_app())
        resp = client.put("/api/auth/public/account/primary/123")
        assert resp.status_code == 401

    @patch("app.routers.character_management.JWTService")
    @patch("app.routers.character_management.db_cursor")
    def test_wrong_account_returns_403(self, mock_cursor_ctx, mock_jwt_cls):
        mock_jwt_cls.return_value.validate_token.return_value = {
            "character_id": 100, "character_name": "Test", "account_id": 2,
            "expires_at": datetime.now(timezone.utc) + timedelta(days=30),
        }
        mock_cur = MagicMock()
        mock_cursor_ctx.return_value.__enter__ = MagicMock(return_value=mock_cur)
        mock_cursor_ctx.return_value.__exit__ = MagicMock(return_value=False)
        mock_cur.fetchone.return_value = {"account_id": 999}  # different account
        client = TestClient(_make_app())
        resp = client.put("/api/auth/public/account/primary/123", cookies={"session": "fake"})
        assert resp.status_code == 403


class TestRemoveCharacter:
    @patch("app.routers.character_management.JWTService")
    def test_no_session_returns_401(self, mock_jwt_cls):
        client = TestClient(_make_app())
        resp = client.delete("/api/auth/public/account/characters/123")
        assert resp.status_code == 401

    @patch("app.routers.character_management.JWTService")
    @patch("app.routers.character_management.db_cursor")
    def test_remove_primary_returns_400(self, mock_cursor_ctx, mock_jwt_cls):
        mock_jwt_cls.return_value.validate_token.return_value = {
            "character_id": 100, "character_name": "Test", "account_id": 2,
            "expires_at": datetime.now(timezone.utc) + timedelta(days=30),
        }
        mock_cur = MagicMock()
        mock_cursor_ctx.return_value.__enter__ = MagicMock(return_value=mock_cur)
        mock_cursor_ctx.return_value.__exit__ = MagicMock(return_value=False)
        # First call: ownership check, Second call: primary check
        mock_cur.fetchone.side_effect = [
            {"account_id": 2},
            {"is_primary": True},
        ]
        client = TestClient(_make_app())
        resp = client.delete("/api/auth/public/account/characters/100", cookies={"session": "fake"})
        assert resp.status_code == 400
        assert "primary" in resp.json()["detail"].lower()
