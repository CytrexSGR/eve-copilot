"""Unit tests for CharacterContextMiddleware.

Tests ownership validation of X-Character-Id header against JWT character_ids claim.
Covers: valid/invalid IDs, missing header fallback, old JWTs, non-numeric IDs,
unauthenticated requests.
"""
import os
import time

import jwt as pyjwt
import pytest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from app.middleware.character_context import CharacterContextMiddleware

SECRET = os.environ.get("JWT_SECRET", "")
ALGORITHM = "HS256"

PRIMARY_CHAR = 1117367444
ALT_CHAR = 110592475
FOREIGN_CHAR = 999999999
ACCOUNT_ID = 2


def _make_jwt(
    character_id: int = PRIMARY_CHAR,
    character_ids: list[int] | None = None,
    account_id: int = ACCOUNT_ID,
    include_character_ids_claim: bool = True,
) -> str:
    """Create a signed JWT for testing."""
    payload = {
        "sub": str(character_id),
        "name": "TestPilot",
        "account_id": account_id,
        "tier": "pilot",
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,
        "type": "public_session",
        "active_modules": [],
        "org_plan": None,
    }
    if include_character_ids_claim:
        payload["character_ids"] = character_ids or [character_id]
    return pyjwt.encode(payload, SECRET, algorithm=ALGORITHM)


def _create_test_app() -> TestClient:
    """Create a minimal Starlette app with CharacterContextMiddleware."""

    async def echo_state(request: Request) -> JSONResponse:
        """Endpoint that echoes back the validated character_id from request.state."""
        char_id = getattr(request.state, "character_id", None)
        return JSONResponse({"character_id": char_id})

    app = Starlette(routes=[Route("/test", echo_state)])
    app.add_middleware(CharacterContextMiddleware)
    return TestClient(app)


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client():
    return _create_test_app()


@pytest.fixture
def token_with_alts():
    """JWT with primary + alt character."""
    return _make_jwt(
        character_id=PRIMARY_CHAR,
        character_ids=[PRIMARY_CHAR, ALT_CHAR],
    )


@pytest.fixture
def token_single_char():
    """JWT with only primary character."""
    return _make_jwt(character_id=PRIMARY_CHAR, character_ids=[PRIMARY_CHAR])


@pytest.fixture
def token_old_jwt():
    """Old-style JWT without character_ids claim."""
    return _make_jwt(
        character_id=PRIMARY_CHAR,
        include_character_ids_claim=False,
    )


# ---------------------------------------------------------------------------
# Happy path: valid character IDs
# ---------------------------------------------------------------------------


class TestValidCharacterAccess:
    """Requests with valid character IDs should pass through."""

    def test_primary_character_allowed(self, client, token_with_alts):
        resp = client.get(
            "/test",
            cookies={"session": token_with_alts},
            headers={"X-Character-Id": str(PRIMARY_CHAR)},
        )
        assert resp.status_code == 200
        assert resp.json()["character_id"] == PRIMARY_CHAR

    def test_alt_character_allowed(self, client, token_with_alts):
        resp = client.get(
            "/test",
            cookies={"session": token_with_alts},
            headers={"X-Character-Id": str(ALT_CHAR)},
        )
        assert resp.status_code == 200
        assert resp.json()["character_id"] == ALT_CHAR

    def test_single_char_jwt_allows_own_id(self, client, token_single_char):
        resp = client.get(
            "/test",
            cookies={"session": token_single_char},
            headers={"X-Character-Id": str(PRIMARY_CHAR)},
        )
        assert resp.status_code == 200
        assert resp.json()["character_id"] == PRIMARY_CHAR


# ---------------------------------------------------------------------------
# Default fallback: no X-Character-Id header
# ---------------------------------------------------------------------------


class TestDefaultFallback:
    """Without X-Character-Id header, middleware defaults to JWT primary."""

    def test_no_header_defaults_to_primary(self, client, token_with_alts):
        resp = client.get("/test", cookies={"session": token_with_alts})
        assert resp.status_code == 200
        assert resp.json()["character_id"] == PRIMARY_CHAR

    def test_no_header_single_char(self, client, token_single_char):
        resp = client.get("/test", cookies={"session": token_single_char})
        assert resp.status_code == 200
        assert resp.json()["character_id"] == PRIMARY_CHAR


# ---------------------------------------------------------------------------
# Ownership rejection: foreign character IDs
# ---------------------------------------------------------------------------


class TestOwnershipRejection:
    """Requests with character IDs not belonging to the account must be rejected."""

    def test_foreign_character_returns_403(self, client, token_with_alts):
        resp = client.get(
            "/test",
            cookies={"session": token_with_alts},
            headers={"X-Character-Id": str(FOREIGN_CHAR)},
        )
        assert resp.status_code == 403
        assert resp.json()["error"] == "character_not_linked"

    def test_single_char_rejects_foreign(self, client, token_single_char):
        resp = client.get(
            "/test",
            cookies={"session": token_single_char},
            headers={"X-Character-Id": str(ALT_CHAR)},
        )
        assert resp.status_code == 403
        assert resp.json()["error"] == "character_not_linked"


# ---------------------------------------------------------------------------
# Invalid header values
# ---------------------------------------------------------------------------


class TestInvalidHeaderValues:
    """Non-numeric or malformed X-Character-Id must return 400."""

    def test_non_numeric_returns_400(self, client, token_with_alts):
        resp = client.get(
            "/test",
            cookies={"session": token_with_alts},
            headers={"X-Character-Id": "abc"},
        )
        assert resp.status_code == 400
        assert resp.json()["error"] == "invalid_character_id"

    def test_empty_string_defaults_to_primary(self, client, token_with_alts):
        """Empty header is falsy — treated as absent, defaults to primary."""
        resp = client.get(
            "/test",
            cookies={"session": token_with_alts},
            headers={"X-Character-Id": ""},
        )
        assert resp.status_code == 200
        assert resp.json()["character_id"] == PRIMARY_CHAR

    def test_float_returns_400(self, client, token_with_alts):
        resp = client.get(
            "/test",
            cookies={"session": token_with_alts},
            headers={"X-Character-Id": "123.456"},
        )
        assert resp.status_code == 400
        assert resp.json()["error"] == "invalid_character_id"


# ---------------------------------------------------------------------------
# Old JWTs without character_ids claim
# ---------------------------------------------------------------------------


class TestOldJwtFallback:
    """Old JWTs without character_ids claim should only allow the primary character."""

    def test_old_jwt_allows_primary(self, client, token_old_jwt):
        resp = client.get(
            "/test",
            cookies={"session": token_old_jwt},
            headers={"X-Character-Id": str(PRIMARY_CHAR)},
        )
        assert resp.status_code == 200
        assert resp.json()["character_id"] == PRIMARY_CHAR

    def test_old_jwt_rejects_foreign(self, client, token_old_jwt):
        resp = client.get(
            "/test",
            cookies={"session": token_old_jwt},
            headers={"X-Character-Id": str(FOREIGN_CHAR)},
        )
        assert resp.status_code == 403
        assert resp.json()["error"] == "character_not_linked"

    def test_old_jwt_rejects_alt_without_claim(self, client, token_old_jwt):
        """Even a real alt is rejected if JWT doesn't list it."""
        resp = client.get(
            "/test",
            cookies={"session": token_old_jwt},
            headers={"X-Character-Id": str(ALT_CHAR)},
        )
        assert resp.status_code == 403
        assert resp.json()["error"] == "character_not_linked"

    def test_old_jwt_no_header_defaults_to_primary(self, client, token_old_jwt):
        resp = client.get("/test", cookies={"session": token_old_jwt})
        assert resp.status_code == 200
        assert resp.json()["character_id"] == PRIMARY_CHAR


# ---------------------------------------------------------------------------
# Unauthenticated requests (no session cookie)
# ---------------------------------------------------------------------------


class TestUnauthenticatedPassthrough:
    """Without a session cookie, middleware should pass through without blocking."""

    def test_no_cookie_passes_through(self, client):
        resp = client.get("/test")
        assert resp.status_code == 200
        assert resp.json()["character_id"] is None

    def test_no_cookie_with_spoofed_header(self, client):
        """X-Character-Id without session should not set request.state."""
        resp = client.get(
            "/test",
            headers={"X-Character-Id": str(FOREIGN_CHAR)},
        )
        assert resp.status_code == 200
        assert resp.json()["character_id"] is None

    def test_invalid_jwt_passes_through(self, client):
        resp = client.get(
            "/test",
            cookies={"session": "not.a.valid.jwt"},
        )
        assert resp.status_code == 200
        assert resp.json()["character_id"] is None

    def test_expired_jwt_passes_through(self, client):
        expired = pyjwt.encode(
            {
                "sub": str(PRIMARY_CHAR),
                "account_id": ACCOUNT_ID,
                "character_ids": [PRIMARY_CHAR],
                "iat": int(time.time()) - 7200,
                "exp": int(time.time()) - 3600,
            },
            SECRET,
            algorithm=ALGORITHM,
        )
        resp = client.get("/test", cookies={"session": expired})
        assert resp.status_code == 200
        assert resp.json()["character_id"] is None
