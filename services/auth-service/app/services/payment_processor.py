"""
Payment Processing Pipeline.

Orchestrates: ESI wallet fetch → payment matching → verification → subscription activation.
"""
import logging
from typing import Dict, Any, List

from app.services.payment_poller import match_payment
from app.services.wallet_journal import fetch_wallet_journal
from app.repository.tier_store import TierRepository

logger = logging.getLogger(__name__)


def determine_subscription_params(
    payment: Dict[str, Any],
    tier: str,
    duration_days: int,
    corporation_id: int = None,
    alliance_id: int = None,
) -> Dict[str, Any]:
    """Build subscription creation params from a verified payment."""
    return {
        "tier": tier,
        "paid_by": payment["character_id"],
        "corporation_id": corporation_id,
        "alliance_id": alliance_id,
        "duration_days": duration_days,
    }


def build_activation_summary(
    reference_code: str,
    tier: str,
    character_id: int,
    journal_id: int,
) -> Dict[str, Any]:
    """Build a summary dict for a successfully activated subscription."""
    return {
        "reference_code": reference_code,
        "tier": tier,
        "character_id": character_id,
        "esi_journal_id": journal_id,
        "status": "activated",
    }


def _lookup_affiliation(character_id: int) -> tuple:
    """Get corp/alliance from platform_accounts."""
    from app.repository.account_store import AccountRepository
    repo = AccountRepository()
    account = repo.get_account_by_character(character_id)
    if account:
        return account.get("corporation_id"), account.get("alliance_id")
    return None, None


async def process_payments(
    holding_character_id: int,
    access_token: str,
    last_ref_id: int,
) -> Dict[str, Any]:
    """
    Full payment processing pipeline:
    1. Fetch new journal entries from ESI
    2. Match against pending payments
    3. Verify + create subscription for each match
    4. Update last_journal_ref_id watermark

    Returns: {"verified": int, "new_ref_id": int, "activations": [...]}
    """
    repo = TierRepository()

    # 1. Fetch new journal entries
    donations = await fetch_wallet_journal(
        holding_character_id, access_token, last_ref_id,
    )
    if not donations:
        return {"verified": 0, "new_ref_id": last_ref_id, "activations": []}

    # 2. Get pending payments
    pending = repo.get_pending_payments()
    if not pending:
        # Update watermark even if no pending payments (skip old entries next time)
        max_id = max(d["id"] for d in donations)
        return {"verified": 0, "new_ref_id": max_id, "activations": []}

    # 3. Match + verify + activate
    activations = []
    new_ref_id = last_ref_id

    for entry in sorted(donations, key=lambda e: e["id"]):
        new_ref_id = max(new_ref_id, entry["id"])

        matched = match_payment(entry, pending)
        if not matched:
            continue

        # Verify in DB (marks payment as verified, dedup by esi_journal_id)
        verified = repo.verify_payment(
            reference_code=matched["reference_code"],
            esi_journal_id=entry["id"],
        )
        if not verified:
            continue

        # Read tier from payment record (stored at subscribe time)
        tier = matched.get("tier") or "pilot"
        duration_days = 30
        pricing = repo.get_pricing()
        for p in pricing:
            if p["tier"] == tier:
                duration_days = p["duration_days"]
                break

        # Determine corp/alliance from payment record or platform_accounts
        corp_id = matched.get("corporation_id")
        alliance_id = matched.get("alliance_id")
        if not corp_id and not alliance_id:
            corp_id, alliance_id = _lookup_affiliation(matched["character_id"])

        # Create subscription
        repo.create_subscription(
            tier=tier,
            paid_by=matched["character_id"],
            corporation_id=corp_id if tier in ("corporation", "alliance") else None,
            alliance_id=alliance_id if tier == "alliance" else None,
            duration_days=duration_days,
        )

        # Update platform_accounts effective_tier
        from app.repository.account_store import AccountRepository
        account_repo = AccountRepository()
        account = account_repo.get_account_by_character(matched["character_id"])
        if account:
            account_repo.update_effective_tier(account["id"], tier)

        activations.append(build_activation_summary(
            reference_code=matched["reference_code"],
            tier=tier,
            character_id=matched["character_id"],
            journal_id=entry["id"],
        ))

        # Remove from pending list to prevent double-match in this batch
        pending = [p for p in pending if p["reference_code"] != matched["reference_code"]]

        logger.info(
            f"Payment verified: {matched['reference_code']} → {tier} tier "
            f"for character {matched['character_id']}"
        )

    return {
        "verified": len(activations),
        "new_ref_id": new_ref_id,
        "activations": activations,
    }
