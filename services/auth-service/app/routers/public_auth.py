"""Public authentication router for EVE SSO with JWT sessions."""

import os
import logging
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse,  urlencode

from fastapi import APIRouter, HTTPException, Query, Response, Cookie
from fastapi.responses import RedirectResponse

from app.config import settings
from app.services.eve_sso import EVESSOService
from app.services.jwt_service import JWTService
from app.repository.db_token_store import DatabaseTokenStore
from app.repository.subscription_store import subscription_repo
from app.repository.account_store import AccountRepository, should_update_corp_info
from app.repository.tier_store import TierRepository
from app.services.sso_handler import process_sso_login
from app.models.subscription import PublicProfile, ActiveSubscription

logger = logging.getLogger(__name__)

def _validate_redirect_url(url):
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
        cors = getattr(settings, 'cors_origins', '')
        if isinstance(cors, str):
            cors = [o.strip() for o in cors.split(',') if o.strip() and o.strip() != '*']
        for origin in cors:
            origin_parsed = urlparse(origin)
            if parsed.netloc == origin_parsed.netloc:
                return url
        return None
    except Exception:
        return None


router = APIRouter(prefix="/public", tags=["Public Auth"])


def get_sso_service() -> EVESSOService:
    """Get SSO service instance."""
    token_store = DatabaseTokenStore()
    return EVESSOService(token_store, settings)


def get_jwt_service() -> JWTService:
    """Get JWT service instance."""
    return JWTService()


@router.get("/login")
async def public_login(
    redirect_url: Optional[str] = Query(None, description="URL to redirect after auth")
):
    """Initiate EVE SSO login for public frontend.

    Returns an authorization URL for EVE SSO login. The client should redirect
    the user to this URL to begin the OAuth2 flow.
    """
    # Check if login is enabled
    if subscription_repo.get_config("login_enabled") != "true":
        raise HTTPException(status_code=503, detail="Login is currently disabled")

    redirect_url = _validate_redirect_url(redirect_url)
    sso = get_sso_service()
    auth_url = await sso.get_auth_url(redirect_url)
    return {"auth_url": auth_url}


@router.get("/callback")
async def public_callback(
    code: str = Query(..., description="Authorization code from EVE SSO"),
    state: str = Query(..., description="State parameter for CSRF protection"),
):
    """Handle OAuth2 callback from EVE SSO.

    Exchanges the authorization code for tokens, creates/updates the customer
    record, generates a JWT session token, and redirects to the frontend.
    """
    sso = get_sso_service()
    jwt_svc = get_jwt_service()
    redirect_url = None

    try:
        # Get redirect URL from state before processing (sync method, no await)
        auth_state = sso.token_store.get_state(state)
        redirect_url = auth_state.redirect_url if auth_state else None

        # Exchange code for token
        token_data = await sso.handle_callback(code, state)

        # Run shared SSO login pipeline (affiliation, roles, account, tier, JWT)
        result = await process_sso_login(
            character_id=token_data.character_id,
            character_name=token_data.character_name,
            access_token=token_data.access_token,
            jwt_service=jwt_svc,
        )

        # Build redirect
        if redirect_url:
            params = urlencode({
                "success": "true",
                "token": result.jwt_token,
                "character_id": token_data.character_id,
                "character_name": token_data.character_name,
            })
            redirect_response = RedirectResponse(url=f"{redirect_url}?{params}")
        else:
            redirect_response = RedirectResponse(url="/")

        # Set JWT as HttpOnly cookie
        redirect_response.set_cookie(
            key="session",
            value=result.jwt_token,
            httponly=True,
            secure=os.environ.get("COOKIE_SECURE", "true").lower() == "true",
            samesite="lax",
            max_age=30 * 24 * 60 * 60  # 30 days
        )

        return redirect_response

    except ValueError as e:
        logger.warning(f"Public callback validation error: {e}")
        if redirect_url:
            params = urlencode({"error": str(e)})
            return RedirectResponse(url=f"{redirect_url}?{params}")
        raise HTTPException(status_code=400, detail="Invalid authentication parameters")
    except Exception as e:
        logger.exception("Public authentication failed during callback")
        if redirect_url:
            params = urlencode({"error": "Authentication failed"})
            return RedirectResponse(url=f"{redirect_url}?{params}")
        raise HTTPException(status_code=500, detail="Authentication failed")


@router.get("/me", response_model=PublicProfile)
def get_public_profile(session: Optional[str] = Cookie(None)):
    """Get current user profile and subscriptions.

    Returns the authenticated user's profile including active subscriptions
    and available features.
    """
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    jwt_svc = get_jwt_service()
    payload = jwt_svc.validate_token(session)

    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    character_id = payload["character_id"]

    # Get customer
    customer = subscription_repo.get_customer(character_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Get active subscriptions
    subs = subscription_repo.get_active_subscriptions(character_id)
    active_subs = []
    all_features = set()

    for sub in subs:
        expires_at = sub.expires_at
        days_remaining = (expires_at - datetime.now(timezone.utc)).days

        active_subs.append(ActiveSubscription(
            product_slug=sub.product.slug,
            product_name=sub.product.name,
            features=sub.product.features or [],
            expires_at=expires_at,
            days_remaining=max(0, days_remaining)
        ))

        for feature in (sub.product.features or []):
            all_features.add(feature)

    return PublicProfile(
        character_id=character_id,
        character_name=payload["character_name"],
        subscriptions=active_subs,
        features=list(all_features)
    )


@router.post("/logout")
def public_logout(response: Response):
    """Clear session cookie.

    Logs out the user by deleting the session cookie.
    """
    response.delete_cookie(key="session")
    return {"message": "Logged out"}


@router.get("/config")
def get_public_config():
    """Get public configuration.

    Returns public system configuration flags for the frontend.
    """
    config = subscription_repo.get_all_config()
    return {
        "login_enabled": config.get("login_enabled") == "true",
        "subscription_enabled": config.get("subscription_enabled") == "true"
    }


@router.get("/account")
def get_account(session: Optional[str] = Cookie(None)):
    """Get full account info with linked characters and tier."""
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    jwt_svc = get_jwt_service()
    payload = jwt_svc.validate_token(session)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    account_repo = AccountRepository()
    account = account_repo.get_account_by_character(payload["character_id"])
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    characters = account_repo.get_account_characters(account["id"])

    tier_repo = TierRepository()
    tier_info = tier_repo.get_character_tier(payload["character_id"])
    effective_tier = tier_info.get("tier", "free") if tier_info else "free"

    # Resolve platform role
    role = "member"
    if account.get("corporation_id"):
        _tier_repo_role = TierRepository()
        _resolved_role = _tier_repo_role.get_role(account["corporation_id"], payload["character_id"])
        if _resolved_role:
            role = _resolved_role

    return {
        "account_id": account["id"],
        "primary_character_id": account["primary_character_id"],
        "primary_character_name": account["primary_character_name"],
        "tier": effective_tier,
        "role": role,
        "subscription_id": tier_info.get("subscription_id") if tier_info else None,
        "expires_at": tier_info.get("expires_at") if tier_info else None,
        "corporation_id": account["corporation_id"],
        "alliance_id": account["alliance_id"],
        "characters": [
            {
                "character_id": c["character_id"],
                "character_name": c["character_name"],
                "is_primary": c["is_primary"],
            }
            for c in characters
        ],
        "created_at": account["created_at"],
        "last_login": account["last_login"],
    }


@router.post("/account/add-character")
async def add_character_to_account(session: Optional[str] = Cookie(None)):
    """Initiate SSO flow to add another character to the account.

    Returns EVE SSO auth URL. The callback will link the new character.
    """
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    jwt_svc = get_jwt_service()
    payload = jwt_svc.validate_token(session)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    account_id = payload.get("account_id")
    if not account_id:
        raise HTTPException(status_code=400, detail="Account not found in token — please re-login")

    sso = get_sso_service()
    auth_url = await sso.get_auth_url(f"{settings.public_frontend_url}/auth/callback?link_account={account_id}")
    return {"auth_url": auth_url}
