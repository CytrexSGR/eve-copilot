"""Tests for org management endpoints — auth guard (401 without session)."""

from unittest.mock import patch
from fastapi.testclient import TestClient
from fastapi import FastAPI
from app.routers.org_management import router


def _make_app():
    app = FastAPI()
    app.include_router(router, prefix="/api/auth")
    return app


class TestOrgManagement401:
    """All endpoints must return 401 when no session cookie is provided."""

    @patch("app.routers.org_management.JWTService")
    def test_members_no_session_returns_401(self, mock_jwt_cls):
        client = TestClient(_make_app())
        resp = client.get("/api/auth/public/org/members")
        assert resp.status_code == 401

    @patch("app.routers.org_management.JWTService")
    def test_overview_no_session_returns_401(self, mock_jwt_cls):
        client = TestClient(_make_app())
        resp = client.get("/api/auth/public/org/overview")
        assert resp.status_code == 401

    @patch("app.routers.org_management.JWTService")
    def test_audit_no_session_returns_401(self, mock_jwt_cls):
        client = TestClient(_make_app())
        resp = client.get("/api/auth/public/org/audit")
        assert resp.status_code == 401

    @patch("app.routers.org_management.JWTService")
    def test_permissions_get_no_session_returns_401(self, mock_jwt_cls):
        client = TestClient(_make_app())
        resp = client.get("/api/auth/public/org/permissions")
        assert resp.status_code == 401

    @patch("app.routers.org_management.JWTService")
    def test_change_role_no_session_returns_401(self, mock_jwt_cls):
        client = TestClient(_make_app())
        resp = client.put(
            "/api/auth/public/org/members/123/role",
            json={"role": "officer"},
        )
        assert resp.status_code == 401

    @patch("app.routers.org_management.JWTService")
    def test_remove_member_no_session_returns_401(self, mock_jwt_cls):
        client = TestClient(_make_app())
        resp = client.delete("/api/auth/public/org/members/123")
        assert resp.status_code == 401
