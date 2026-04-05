"""
Tier management endpoints for SaaS feature-gating.

Internal endpoints (called by API Gateway): /tier/internal/*
Public endpoints (called by frontend): /tier/*
"""
from fastapi import APIRouter, HTTPException
from fastapi.requests import Request
from typing import Optional
import logging

from app.repository.tier_store import TierRepository, TIER_HIERARCHY, compute_subscription_status_detail

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tier", tags=["tier"])

_jwt_service = None


def _get_jwt_service():
    """Lazy-init JWT service (avoids import-time config errors)."""
    global _jwt_service
    if _jwt_service is None:
        from app.services.jwt_service import JWTService
        _jwt_service = JWTService()
    return _jwt_service


def _get_repo() -> TierRepository:
    return TierRepository()


def _get_character_id(request: Request) -> Optional[int]:
    """Extract character_id from JWT session cookie."""
    token = request.cookies.get("session")
    if not token:
        return None
    return _get_jwt_service().get_character_id(token)


# --- Internal Endpoints (Gateway calls these) ---

@router.get("/internal/resolve/{character_id}")
def resolve_tier(character_id: int):
    """
    Internal: Resolve effective tier for a character.
    Called by API Gateway FeatureGateMiddleware.
    """
    repo = _get_repo()
    return repo.get_character_tier(character_id)


# --- Public Endpoints ---

@router.get("/pricing")
def get_pricing():
    """List all tier pricing."""
    repo = _get_repo()
    return repo.get_pricing()


@router.get("/my-tier")
def get_my_tier(request: Request):
    """Get current user's effective tier and subscription info."""
    character_id = _get_character_id(request)
    if not character_id:
        return {"tier": "free", "subscription_id": None, "expires_at": None}
    repo = _get_repo()
    return repo.get_character_tier(character_id)


@router.post("/subscribe")
def subscribe(
    request: Request,
    tier: str,
    corporation_id: int = None,
    alliance_id: int = None,
):
    """
    Initiate subscription purchase. Returns payment instructions.
    Does NOT activate — activation happens after ISK verification.
    """
    character_id = _get_character_id(request)
    if not character_id:
        raise HTTPException(401, "Login required")

    if tier not in TIER_HIERARCHY or tier == "free":
        raise HTTPException(400, f"Invalid tier: {tier}")

    if tier == "corporation" and not corporation_id:
        raise HTTPException(400, "corporation_id required for Corporation tier")
    if tier == "alliance" and not alliance_id:
        raise HTTPException(400, "alliance_id required for Alliance tier")

    repo = _get_repo()

    pricing = repo.get_pricing(tier)
    if not pricing:
        raise HTTPException(404, f"No pricing for tier: {tier}")
    price = pricing[0]

    code = repo.generate_reference_code()

    repo.create_payment_record(
        character_id=character_id,
        amount=price["base_price_isk"],
        reference_code=code,
        tier=tier,
        corporation_id=corporation_id,
        alliance_id=alliance_id,
    )

    wallet = repo.get_active_wallet()
    billing_name = wallet["character_name"] if wallet else "EVE Copilot Service"

    return {
        "reference_code": code,
        "amount_isk": price["base_price_isk"],
        "per_pilot_isk": price["per_pilot_isk"],
        "billing_character": billing_name,
        "tier": tier,
        "duration_days": price["duration_days"],
        "instructions": (
            f"Transfer {price['base_price_isk']:,} ISK to '{billing_name}' "
            f"with reason: {code}"
        ),
    }


@router.get("/payment-status/{reference_code}")
def get_payment_status(reference_code: str, request: Request):
    """Check status of a payment by reference code."""
    character_id = _get_character_id(request)
    if not character_id:
        raise HTTPException(401, "Login required")

    repo = _get_repo()
    with repo._db_cursor() as cur:
        cur.execute("""
            SELECT id, reference_code, amount, status, verified_at,
                   subscription_id, created_at
            FROM tier_payments
            WHERE reference_code = %s AND character_id = %s
        """, (reference_code, character_id))
        row = cur.fetchone()

    if not row:
        raise HTTPException(404, "Payment not found")
    return dict(row)


@router.get("/my-subscription")
def get_my_subscription(request: Request):
    """Get current user's active subscription details."""
    character_id = _get_character_id(request)
    if not character_id:
        raise HTTPException(401, "Login required")

    repo = _get_repo()
    tier_info = repo.get_character_tier(character_id)

    # Get subscription details if any
    sub = None
    if tier_info.get("subscription_id"):
        with repo._db_cursor() as cur:
            cur.execute("""
                SELECT id, tier, paid_by, corporation_id, alliance_id,
                       status, expires_at, auto_renew, created_at
                FROM tier_subscriptions WHERE id = %s
            """, (tier_info["subscription_id"],))
            row = cur.fetchone()
            sub = dict(row) if row else None

    # Get recent payments
    with repo._db_cursor() as cur:
        cur.execute("""
            SELECT id, reference_code, amount, status, verified_at, created_at
            FROM tier_payments
            WHERE character_id = %s
            ORDER BY created_at DESC LIMIT 10
        """, (character_id,))
        payments = [dict(r) for r in cur.fetchall()]

    return {
        "effective_tier": tier_info["tier"],
        "subscription": sub,
        "status_detail": compute_subscription_status_detail(sub),
        "payments": payments,
    }


@router.get("/corp-info")
def get_corp_info(request: Request):
    """Get corporation management info for current user's corp.

    Returns: corp subscription status, user's role, member count.
    Only returns data if user has admin/officer role.
    """
    character_id = _get_character_id(request)
    if not character_id:
        raise HTTPException(401, "Login required")

    # Get user's corp from platform_accounts
    from app.repository.account_store import AccountRepository
    account_repo = AccountRepository()
    account = account_repo.get_account_by_character(character_id)
    if not account or not account.get("corporation_id"):
        raise HTTPException(404, "No corporation found")

    corp_id = account["corporation_id"]
    repo = _get_repo()

    # Check role
    role = repo.get_role(corp_id, character_id)
    if not role or role not in ("admin", "officer"):
        return {
            "corporation_id": corp_id,
            "role": role,
            "has_management_access": False,
        }

    # Get corp subscription
    with repo._db_cursor() as cur:
        cur.execute("""
            SELECT id, tier, status, expires_at, paid_by, auto_renew
            FROM tier_subscriptions
            WHERE corporation_id = %s AND status IN ('active', 'grace')
            ORDER BY expires_at DESC LIMIT 1
        """, (corp_id,))
        sub_row = cur.fetchone()

    # Get member count (platform roles)
    roles = repo.list_roles(corp_id)

    return {
        "corporation_id": corp_id,
        "role": role,
        "has_management_access": True,
        "subscription": dict(sub_row) if sub_row else None,
        "members": len(roles),
        "roles": roles,
    }


# --- Module Subscription Endpoints ---

@router.get("/modules/active")
def get_active_modules(request: Request):
    """Get current user's active modules and org plan."""
    from app.database import db_cursor
    from app.repository.account_store import AccountRepository
    from app.repository.module_store import (
        get_active_modules_for_account,
        resolve_active_modules,
        get_org_plan_for_character,
    )

    character_id = _get_character_id(request)
    if not character_id:
        return {"modules": [], "org_plan": None}

    account_repo = AccountRepository()
    account = account_repo.get_account_by_character(character_id)
    if not account:
        return {"modules": [], "org_plan": None}

    with db_cursor() as cur:
        rows = get_active_modules_for_account(cur, account["id"])
        modules = resolve_active_modules(rows)
        org_plan = get_org_plan_for_character(
            cur,
            character_id,
            account.get("corporation_id"),
            account.get("alliance_id"),
        )

    return {"modules": modules, "org_plan": org_plan}


@router.post("/modules/trial/{module_name}")
def activate_module_trial(module_name: str, request: Request):
    """Activate a 24-hour free trial for a module (or bundle)."""
    from app.database import db_cursor
    from app.repository.account_store import AccountRepository
    from app.repository.module_store import (
        get_active_modules_for_account,
        is_trial_available,
        expand_bundle,
        create_module_subscription,
    )
    from starlette.responses import JSONResponse

    character_id = _get_character_id(request)
    if not character_id:
        raise HTTPException(401, "Login required")

    account_repo = AccountRepository()
    account = account_repo.get_account_by_character(character_id)
    if not account:
        raise HTTPException(404, "No account found")

    # Expand bundle into individual modules
    modules_to_activate = expand_bundle(module_name)

    with db_cursor() as cur:
        # Get existing subscriptions to check trial availability
        existing = get_active_modules_for_account(cur, account["id"])

        # Check trial availability for each module
        for mod in modules_to_activate:
            if not is_trial_available(existing, mod):
                return JSONResponse(
                    status_code=409,
                    content={"error": "trial_already_used", "module": mod},
                )

        # Create trial subscriptions
        subscription_ids = []
        for mod in modules_to_activate:
            sub_id = create_module_subscription(
                cur,
                account_id=account["id"],
                module_name=mod,
                duration_days=1,
                is_trial=True,
            )
            subscription_ids.append(sub_id)

    return {
        "activated": modules_to_activate,
        "expires_in_hours": 24,
        "subscription_ids": subscription_ids,
    }


@router.get("/modules/pricing")
def get_module_pricing():
    """List all active module pricing."""
    from app.database import db_cursor

    with db_cursor() as cur:
        cur.execute("""
            SELECT * FROM module_pricing
            WHERE is_active = TRUE
            ORDER BY category, base_price_isk
        """)
        rows = cur.fetchall()

    return {"pricing": [dict(r) for r in rows]}


# --- Role Management ---

@router.get("/roles/{corporation_id}")
def list_roles(corporation_id: int, request: Request):
    """List platform roles for a corporation."""
    character_id = _get_character_id(request)
    if not character_id:
        raise HTTPException(401, "Login required")

    repo = _get_repo()
    caller_role = repo.get_role(corporation_id, character_id)
    if caller_role not in ("admin", "officer"):
        raise HTTPException(403, "Admin or officer role required")

    return repo.list_roles(corporation_id)


@router.put("/roles/{corporation_id}/{target_character_id}")
def set_role(
    corporation_id: int,
    target_character_id: int,
    role: str,
    request: Request,
):
    """Assign platform role. Only admins can assign roles."""
    character_id = _get_character_id(request)
    if not character_id:
        raise HTTPException(401, "Login required")

    if role not in ("admin", "officer", "member"):
        raise HTTPException(400, f"Invalid role: {role}")

    repo = _get_repo()
    caller_role = repo.get_role(corporation_id, character_id)
    if caller_role != "admin":
        raise HTTPException(403, "Admin role required")

    return repo.set_role(corporation_id, target_character_id, role, character_id)


@router.delete("/roles/{corporation_id}/{target_character_id}")
def remove_role(
    corporation_id: int,
    target_character_id: int,
    request: Request,
):
    """Remove platform role. Only admins can remove roles."""
    character_id = _get_character_id(request)
    if not character_id:
        raise HTTPException(401, "Login required")

    repo = _get_repo()
    caller_role = repo.get_role(corporation_id, character_id)
    if caller_role != "admin":
        raise HTTPException(403, "Admin role required")

    if not repo.remove_role(corporation_id, target_character_id):
        raise HTTPException(404, "Role not found")
    return {"status": "removed"}


# --- Internal: Scheduler-triggered ---

@router.post("/internal/expire-subscriptions")
def expire_subscriptions():
    """Internal: Check and expire stale subscriptions."""
    repo = _get_repo()
    count = repo.expire_subscriptions()
    return {"expired": count}


@router.post("/internal/poll-payments")
async def poll_payments():
    """Internal: Poll holding character wallet journal for payment matching."""
    from app.services.payment_processor import process_payments
    from app.repository.token_store import TokenStore
    from app.config import settings
    from datetime import datetime, timezone

    repo = _get_repo()
    wallet = repo.get_active_wallet()
    if not wallet:
        return {"verified": 0, "message": "No active service wallet configured"}

    # Get ESI access token for holding character
    token_store = TokenStore(settings.token_file, settings.state_file)
    stored_token = await token_store.get_token(wallet["character_id"])
    if not stored_token:
        return {"verified": 0, "message": f"No token for holding character {wallet['character_id']}"}

    # Check if token needs refresh — call own refresh endpoint via httpx
    # (avoids eve_sso.refresh_token async/sync mismatch with TokenStore)
    if stored_token.expires_at < datetime.now(timezone.utc):
        import httpx
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(f"http://localhost:8000/api/auth/refresh/{wallet['character_id']}")
                if resp.status_code != 200:
                    logger.warning(f"Token refresh returned {resp.status_code}")
                    return {"verified": 0, "message": "Token refresh failed"}
            # Re-read refreshed token
            stored_token = await token_store.get_token(wallet["character_id"])
            if not stored_token:
                return {"verified": 0, "message": "Token missing after refresh"}
        except Exception as e:
            logger.warning(f"Token refresh failed for holding char: {e}")
            return {"verified": 0, "message": "Token refresh failed"}

    # Process payments
    result = await process_payments(
        holding_character_id=wallet["character_id"],
        access_token=stored_token.access_token,
        last_ref_id=wallet.get("last_journal_ref_id") or 0,
    )

    # Update watermark
    if result["new_ref_id"] > (wallet.get("last_journal_ref_id") or 0):
        repo.update_wallet_journal_ref(wallet["id"], result["new_ref_id"])

    return {
        "verified": result["verified"],
        "new_ref_id": result["new_ref_id"],
        "activations": result["activations"],
    }
