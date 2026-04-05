"""Validate X-Character-Id header against JWT character_ids claim.

Inserted between FeatureGateMiddleware and ProxyMiddleware.
If X-Character-Id is present, verify it belongs to the authenticated account.
If missing, default to the JWT's primary character_id (sub claim).
Injects validated X-Character-Id into proxied request headers.
"""
import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.middleware.gate_helpers import _decode_jwt_full

logger = logging.getLogger(__name__)


class CharacterContextMiddleware(BaseHTTPMiddleware):
    """Validate and propagate active character context."""

    async def dispatch(self, request: Request, call_next):
        session_token = request.cookies.get("session")
        if not session_token:
            return await call_next(request)

        payload = _decode_jwt_full(session_token)
        if not payload:
            return await call_next(request)

        requested_char = request.headers.get("X-Character-Id")
        allowed_ids = payload.get("character_ids", [])
        primary_id = payload.get("sub")

        if requested_char:
            try:
                char_id = int(requested_char)
            except (ValueError, TypeError):
                return JSONResponse(
                    status_code=400,
                    content={"error": "invalid_character_id", "message": "X-Character-Id must be numeric"},
                )

            if not allowed_ids:
                # Old JWT without character_ids claim — only allow primary
                if str(char_id) != str(primary_id):
                    logger.warning(
                        f"Character {char_id} != primary {primary_id} "
                        f"(no character_ids claim) for account {payload.get('account_id')}"
                    )
                    return JSONResponse(
                        status_code=403,
                        content={"error": "character_not_linked", "message": "Character does not belong to your account"},
                    )
            elif char_id not in allowed_ids:
                logger.warning(
                    f"Character {char_id} not in allowed list {allowed_ids} "
                    f"for account {payload.get('account_id')}"
                )
                return JSONResponse(
                    status_code=403,
                    content={"error": "character_not_linked", "message": "Character does not belong to your account"},
                )
        else:
            char_id = int(primary_id) if primary_id else None

        if char_id:
            request.state.character_id = char_id

        return await call_next(request)
