"""Authentication router for EVE SSO OAuth2 with PKCE."""

import logging
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import RedirectResponse
from typing import Optional
from urllib.parse import urlencode, urlparse, parse_qs

from app.config import settings
from app.services.jwt_service import JWTService
from app.services.sso_handler import process_sso_login

logger = logging.getLogger(__name__)
from app.models.token import (
    AuthUrlResponse,
    OAuthTokenResponse,
    CharacterInfo,
    CharacterListResponse,
)
from app.services.eve_sso import EVESSOService

def _validate_redirect_url(url: str | None) -> str | None:
    """Validate redirect URL against allowed origins to prevent open redirect."""
    if not url:
        return None
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return None
        allowed = settings.public_frontend_url
        allowed_parsed = urlparse(allowed)
        if parsed.netloc == allowed_parsed.netloc:
            return url
        # Also allow CORS origins
        cors = settings.cors_origins
        if isinstance(cors, str):
            cors = [o.strip() for o in cors.split(",") if o.strip() and o.strip() != "*"]
        for origin in cors:
            origin_parsed = urlparse(origin)
            if parsed.netloc == origin_parsed.netloc:
                return url
        return None
    except Exception:
        return None

from app.repository.db_token_store import DatabaseTokenStore


router = APIRouter()


def get_sso_service() -> EVESSOService:
    """Dependency injection for SSO service."""
    token_store = DatabaseTokenStore()
    return EVESSOService(token_store, settings)


def _get_jwt_service() -> JWTService:
    """Lazy JWT service init (env vars not available at import time in Docker)."""
    return JWTService()


@router.get("/login", response_model=AuthUrlResponse)
async def login(
    redirect_url: Optional[str] = Query(None, description="URL to redirect after auth"),
    sso: EVESSOService = Depends(get_sso_service)
):
    """Initiate EVE SSO login with PKCE."""
    redirect_url = _validate_redirect_url(redirect_url)
    auth_url = await sso.get_auth_url(redirect_url)
    return AuthUrlResponse(auth_url=auth_url)


@router.get("/callback")
async def callback(
    code: str = Query(..., description="Authorization code from EVE SSO"),
    state: str = Query(..., description="State parameter for CSRF protection"),
    sso: EVESSOService = Depends(get_sso_service)
):
    """Handle OAuth2 callback from EVE SSO.

    Supports two flows:
    1. Normal login: creates platform account, mints JWT, redirects to frontend.
    2. Link character: adds character to existing account, redirects without new JWT.

    The link flow is triggered when redirect_url contains a link_account= param
    (set by the add-character endpoint).
    """
    redirect_url = None
    base_redirect = None
    try:
        # Get the redirect URL from state before processing (it gets deleted during handle_callback)
        auth_state = sso.token_store.get_state(state)
        redirect_url = auth_state.redirect_url if auth_state else None

        token_data = await sso.handle_callback(code, state)

        if redirect_url:
            # Parse redirect URL to detect link flow and strip internal params
            parsed = urlparse(redirect_url)
            query_params = parse_qs(parsed.query)
            link_account_id = query_params.get("link_account", [None])[0]
            base_redirect = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

            if link_account_id:
                # Link flow: add character to existing account (don't create new one)
                from app.repository.account_store import AccountRepository
                account_repo = AccountRepository()
                account_repo.add_character_to_account(
                    account_id=int(link_account_id),
                    character_id=token_data.character_id,
                    character_name=token_data.character_name,
                )
                logger.info(
                    f"Linked character {token_data.character_name} ({token_data.character_id}) "
                    f"to account {link_account_id}"
                )
                # Redirect to frontend without new JWT (keep existing session)
                params = urlencode({
                    "success": "true",
                    "linked": "true",
                    "character_id": token_data.character_id,
                    "character_name": token_data.character_name,
                })
                return RedirectResponse(url=f"{base_redirect}?{params}")

            # Normal login flow: create full session
            result = await process_sso_login(
                character_id=token_data.character_id,
                character_name=token_data.character_name,
                access_token=token_data.access_token,
                jwt_service=_get_jwt_service(),
            )

            # Pass token in URL — frontend sets cookie on its own origin
            params = urlencode({
                "success": "true",
                "token": result.jwt_token,
                "character_id": token_data.character_id,
                "character_name": token_data.character_name,
            })
            return RedirectResponse(url=f"{base_redirect}?{params}")

        # Internal auth flow: return JSON
        return token_data
    except ValueError as e:
        logger.warning(f"Callback validation error: {e}")
        if base_redirect or redirect_url:
            target = base_redirect or redirect_url
            params = urlencode({"error": str(e)})
            return RedirectResponse(url=f"{target}?{params}")
        raise HTTPException(status_code=400, detail="Invalid authentication parameters")
    except Exception as e:
        logger.exception("Authentication failed during callback")
        if base_redirect or redirect_url:
            target = base_redirect or redirect_url
            params = urlencode({"error": "Authentication failed"})
            return RedirectResponse(url=f"{target}?{params}")
        raise HTTPException(status_code=500, detail="Authentication failed")


@router.get("/characters", response_model=CharacterListResponse)
async def list_characters(
    sso: EVESSOService = Depends(get_sso_service)
):
    """List all authenticated characters."""
    characters = await sso.get_authenticated_characters()
    return CharacterListResponse(characters=characters)


@router.post("/refresh/{character_id}", response_model=OAuthTokenResponse)
async def refresh_token(
    character_id: int,
    sso: EVESSOService = Depends(get_sso_service)
):
    """Refresh access token for a character."""
    try:
        token_data = await sso.refresh_token(character_id)
        return token_data
    except ValueError as e:
        logger.warning(f"Token refresh validation error for character {character_id}: {e}")
        raise HTTPException(status_code=404, detail="Character not found or token unavailable")
    except Exception as e:
        logger.exception(f"Token refresh failed for character {character_id}")
        raise HTTPException(status_code=500, detail="Token refresh failed")


@router.delete("/character/{character_id}")
async def logout_character(
    character_id: int,
    sso: EVESSOService = Depends(get_sso_service)
):
    """Remove character authentication."""
    success = await sso.logout_character(character_id)
    if not success:
        raise HTTPException(status_code=404, detail="Character not found")
    return {"message": f"Character {character_id} logged out"}


@router.get("/token/{character_id}")
async def get_token(
    character_id: int,
    sso: EVESSOService = Depends(get_sso_service)
):
    """
    Get valid access token for a character.

    This endpoint is used by other microservices (e.g., character-service)
    to get a valid access token for ESI API calls.

    The token will be automatically refreshed if expired or near expiry.
    """
    try:
        access_token = await sso.get_valid_token(character_id)
        return {"access_token": access_token, "character_id": character_id}
    except ValueError as e:
        logger.warning(f"Token retrieval failed for character {character_id}: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception(f"Unexpected error getting token for character {character_id}")
        raise HTTPException(status_code=500, detail="Failed to retrieve token")


@router.get("/scopes")
def get_scopes():
    """Get list of required ESI scopes."""
    from app.services.eve_sso import ESI_SCOPES
    return {"scopes": ESI_SCOPES, "count": len(ESI_SCOPES)}


@router.post("/rekey-tokens")
def rekey_tokens():
    """Re-encrypt all tokens with the current primary encryption key.

    Used after key rotation: add new key as first in ESI_SECRET_KEY,
    then call this endpoint to re-encrypt all tokens with the new key.
    Tokens already encrypted with the current key are skipped.
    """
    from app.repository.db_token_store import DatabaseTokenStore, _get_encryption
    from app.database import db_cursor

    enc = _get_encryption()
    if not enc or not enc.is_enabled:
        return {"rekeyed": 0, "skipped": 0, "errors": 0, "message": "Encryption not enabled"}

    rekeyed = 0
    skipped = 0
    errors = 0

    with db_cursor() as cur:
        cur.execute("""
            SELECT character_id, refresh_token_encrypted
            FROM oauth_tokens
            WHERE is_encrypted = TRUE AND refresh_token_encrypted IS NOT NULL
        """)
        rows = cur.fetchall()

    for row in rows:
        char_id = row["character_id"]
        ciphertext = bytes(row["refresh_token_encrypted"])

        if not enc.needs_rekey(ciphertext):
            skipped += 1
            continue

        new_ciphertext = enc.rekey(ciphertext)
        if new_ciphertext is None:
            errors += 1
            logger.warning(f"Failed to rekey token for character {char_id}")
            continue

        with db_cursor() as cur:
            cur.execute(
                "UPDATE oauth_tokens SET refresh_token_encrypted = %s WHERE character_id = %s",
                (new_ciphertext, char_id),
            )
        rekeyed += 1

    logger.info(f"Token rekey complete: {rekeyed} rekeyed, {skipped} skipped, {errors} errors")
    return {"rekeyed": rekeyed, "skipped": skipped, "errors": errors}
