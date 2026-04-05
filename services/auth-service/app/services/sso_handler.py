"""Shared SSO callback logic used by both auth.py and public_auth.py.

Extracts the common post-token-exchange flow:
  1. Fetch corp/alliance affiliation from ESI
  2. Fetch ESI roles + auto-assign platform roles
  3. Create/update platform account
  4. Sync legacy customers table
  5. Resolve effective tier + active modules
  6. Mint enriched JWT
"""

import logging
from dataclasses import dataclass
from typing import Optional

import httpx

from app.repository.account_store import AccountRepository
from app.repository.subscription_store import subscription_repo
from app.repository.tier_store import TierRepository
from app.repository.module_store import (
    get_active_modules_for_account,
    resolve_active_modules,
    get_org_plan_for_character,
)
from app.services.director_detection import fetch_character_roles, build_role_assignment
from app.services.jwt_service import JWTService

logger = logging.getLogger(__name__)

ESI_BASE = "https://esi.evetech.net/latest"


@dataclass
class SSOLoginResult:
    """Result of the full SSO login processing pipeline."""

    jwt_token: str
    account_id: int
    character_id: int
    character_name: str
    effective_tier: str
    corporation_id: Optional[int]
    alliance_id: Optional[int]


async def fetch_esi_affiliation(character_id: int) -> tuple[Optional[int], Optional[int]]:
    """Fetch corporation_id + alliance_id from ESI public endpoint.

    Returns:
        Tuple of (corporation_id, alliance_id). Either may be None on failure.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{ESI_BASE}/characters/{character_id}/")
            if resp.status_code == 200:
                data = resp.json()
                return data.get("corporation_id"), data.get("alliance_id")
    except Exception as e:
        logger.warning(f"ESI affiliation fetch failed for {character_id}: {e}")
    return None, None


async def process_sso_login(
    character_id: int,
    character_name: str,
    access_token: str,
    jwt_service: JWTService,
) -> SSOLoginResult:
    """Run the full post-token-exchange SSO login pipeline.

    This covers everything after sso.handle_callback() succeeds:
      - ESI affiliation + role fetch
      - Platform role auto-assignment
      - Account creation/update
      - Legacy customer sync
      - Tier resolution + module resolution
      - Enriched JWT minting

    Args:
        character_id: EVE character ID from token exchange.
        character_name: EVE character name from token exchange.
        access_token: ESI access token for authenticated ESI calls.
        jwt_service: JWTService instance for token creation.

    Returns:
        SSOLoginResult with the minted JWT and resolved metadata.
    """
    # 1. Fetch corp/alliance from ESI public endpoint
    corp_id, alliance_id = await fetch_esi_affiliation(character_id)

    # 2. Fetch ESI roles for director detection
    esi_roles = await fetch_character_roles(character_id, access_token)

    # 3. Auto-assign platform role if Director/CEO/Officer
    role_assignment = build_role_assignment(
        character_id=character_id,
        corporation_id=corp_id,
        esi_roles=esi_roles,
    )
    if role_assignment and corp_id:
        tier_repo = TierRepository()
        existing_role = tier_repo.get_role(corp_id, character_id)
        if not existing_role or (
            existing_role == "officer" and role_assignment["role"] == "admin"
        ):
            tier_repo.set_role(
                corporation_id=corp_id,
                character_id=character_id,
                role=role_assignment["role"],
                granted_by=character_id,
            )
            logger.info(
                f"Auto-assigned {role_assignment['role']} role to "
                f"{character_name} for corp {corp_id}"
            )

    # 4. Create/update platform account
    account_repo = AccountRepository()
    account = account_repo.get_or_create_account(
        character_id=character_id,
        character_name=character_name,
        corporation_id=corp_id,
        alliance_id=alliance_id,
    )

    # 5. Keep customers table in sync (backward compat)
    subscription_repo.get_or_create_customer(
        character_id=character_id,
        character_name=character_name,
    )
    subscription_repo.update_customer_login(character_id)

    # 6. Resolve effective tier
    tier_repo2 = TierRepository()
    tier_info = tier_repo2.get_character_tier(character_id)
    effective_tier = tier_info.get("tier", "free") if tier_info else "free"

    # 7. Update cached tier on account
    account_repo.update_effective_tier(account["id"], effective_tier)

    # 8. Resolve active modules + org plan for JWT
    active_modules: list[str] = []
    org_plan = None
    try:
        from app.database import db_cursor

        with db_cursor() as cur:
            module_rows = get_active_modules_for_account(cur, account["id"])
            active_modules = resolve_active_modules(module_rows)
            org_plan = get_org_plan_for_character(
                cur, character_id, corp_id, alliance_id
            )
    except Exception:
        logger.warning("Failed to resolve module subscriptions for JWT", exc_info=True)

    # 8b. Fetch all linked characters for JWT character_ids claim
    linked_chars = account_repo.get_account_characters(account["id"])
    character_ids = [c["character_id"] for c in linked_chars]

    # 9. Create enriched JWT
    jwt_token = jwt_service.create_enriched_token(
        account_id=account["id"],
        character_id=character_id,
        character_name=character_name,
        tier=effective_tier,
        corporation_id=corp_id,
        alliance_id=alliance_id,
        active_modules=active_modules,
        org_plan=org_plan,
        character_ids=character_ids,
    )

    return SSOLoginResult(
        jwt_token=jwt_token,
        account_id=account["id"],
        character_id=character_id,
        character_name=character_name,
        effective_tier=effective_tier,
        corporation_id=corp_id,
        alliance_id=alliance_id,
    )
