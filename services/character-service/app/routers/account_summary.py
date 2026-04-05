"""Aggregated account summary across all linked characters."""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Cookie
import httpx

from app.services.auth_client import AuthClient
from app.services.character import CharacterService
from eve_shared import get_db, get_redis
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Account Summary"])


def _validate_session(session: Optional[str]) -> dict:
    """Validate session by calling auth-service /public/account endpoint."""
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(
                f"{settings.auth_service_url}/api/auth/public/account",
                cookies={"session": session},
            )
            if resp.status_code != 200:
                raise HTTPException(status_code=401, detail="Invalid session")
            return resp.json()
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="Auth service unavailable")


@router.get("/summary/account")
async def get_account_summary(session: Optional[str] = Cookie(None)):
    """Get aggregated summary for all characters in the account."""
    account_data = _validate_session(session)
    characters = account_data.get("characters", [])

    if not characters:
        return {
            "account_id": account_data.get("account_id"),
            "total_isk": 0,
            "total_sp": 0,
            "characters": [],
        }

    db = get_db()
    redis = get_redis()
    char_service = CharacterService(db, redis)
    auth_client = AuthClient()

    results = []
    total_isk = 0.0
    total_sp = 0

    for char in characters:
        cid = char["character_id"]
        entry = {
            "character_id": cid,
            "name": char["character_name"],
            "is_primary": char.get("is_primary", False),
            "isk": 0,
            "sp": 0,
            "location": None,
            "ship": None,
            "skill_queue_length": 0,
            "skill_queue_finish": None,
            "token_health": "unknown",
        }

        try:
            wallet = await char_service.get_wallet(cid)
            if wallet:
                entry["isk"] = wallet.balance
                total_isk += wallet.balance
        except Exception:
            pass

        try:
            skills = await char_service.get_skills(cid)
            if skills:
                entry["sp"] = skills.total_sp
                total_sp += skills.total_sp
        except Exception:
            pass

        try:
            queue = await char_service.get_skill_queue(cid)
            if queue and queue.queue:
                entry["skill_queue_length"] = queue.queue_length
                last_item = queue.queue[-1]
                entry["skill_queue_finish"] = last_item.finish_date
        except Exception:
            pass

        try:
            location = await char_service.get_location(cid)
            if location:
                entry["location"] = location.solar_system_name
        except Exception:
            pass

        try:
            ship = await char_service.get_ship(cid)
            if ship:
                entry["ship"] = ship.ship_type_name
        except Exception:
            pass

        # Token health (simple check)
        token = auth_client.get_valid_token(cid)
        entry["token_health"] = "valid" if token else "expired"

        results.append(entry)

    # Sort: primary first, then by SP descending
    results.sort(key=lambda c: (-int(c["is_primary"]), -c["sp"]))

    return {
        "account_id": account_data.get("account_id"),
        "total_isk": total_isk,
        "total_sp": total_sp,
        "characters": results,
    }
