"""Skillfarm management: SP tracking, profit calculation, character flagging."""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Cookie
import httpx

from eve_shared import get_db
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Skillfarm"])

MARKET_SERVICE_URL = "http://market-service:8000"
SKILL_EXTRACTOR_TYPE_ID = 40519
SKILL_INJECTOR_TYPE_ID = 40520
SP_PER_EXTRACTOR = 500_000
HOURS_PER_MONTH = 720


def _validate_session(session: Optional[str]) -> dict:
    """Validate session by calling auth-service."""
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


def _get_market_prices() -> dict:
    """Fetch Skill Injector and Extractor prices from market-service."""
    try:
        with httpx.Client(timeout=10) as client:
            inj_resp = client.get(f"{MARKET_SERVICE_URL}/api/market/price/{SKILL_INJECTOR_TYPE_ID}")
            ext_resp = client.get(f"{MARKET_SERVICE_URL}/api/market/price/{SKILL_EXTRACTOR_TYPE_ID}")
            injector_price = inj_resp.json().get("sell_price", 0) if inj_resp.status_code == 200 else 0
            extractor_price = ext_resp.json().get("sell_price", 0) if ext_resp.status_code == 200 else 0
    except httpx.RequestError:
        injector_price = 0
        extractor_price = 0
    return {
        "injector_price": injector_price,
        "extractor_price": extractor_price,
        "profit_per_extractor": injector_price - extractor_price,
    }


def _get_sp_per_hour(character_id: int) -> float:
    """Estimate SP/hour from active skill queue."""
    db = get_db()
    with db.cursor() as cur:
        cur.execute("""
            SELECT skill_name, training_start_sp, level_end_sp,
                   start_date, finish_date
            FROM character_skill_queue
            WHERE character_id = %s
              AND finish_date IS NOT NULL
              AND finish_date > NOW()
            ORDER BY queue_position
            LIMIT 1
        """, (character_id,))
        row = cur.fetchone()
    if not row or not row["start_date"] or not row["finish_date"]:
        return 0.0
    start = row["start_date"]
    finish = row["finish_date"]
    sp_delta = (row["level_end_sp"] or 0) - (row["training_start_sp"] or 0)
    hours = max((finish - start).total_seconds() / 3600, 0.001)
    return sp_delta / hours


@router.get("/skillfarm/characters")
def get_skillfarm_characters(session: Optional[str] = Cookie(None)):
    """List all account characters with skillfarm info."""
    account = _validate_session(session)
    characters = account.get("characters", [])
    if not characters:
        return {"characters": [], "prices": _get_market_prices()}

    char_ids = [c["character_id"] for c in characters]
    db = get_db()

    with db.cursor() as cur:
        # Get skillfarm flags
        cur.execute(
            "SELECT character_id, is_skillfarm FROM account_characters WHERE character_id = ANY(%s)",
            (char_ids,)
        )
        flags = {r["character_id"]: r.get("is_skillfarm", False) for r in cur.fetchall()}

        # Get total SP per character (latest entry)
        cur.execute("""
            SELECT DISTINCT ON (character_id) character_id, total_sp, unallocated_sp
            FROM character_sp_history
            WHERE character_id = ANY(%s)
            ORDER BY character_id, recorded_at DESC
        """, (char_ids,))
        sp_data = {r["character_id"]: r for r in cur.fetchall()}

        # Get queue status per character (first item)
        cur.execute("""
            SELECT DISTINCT ON (character_id)
                character_id, skill_name, finished_level, finish_date
            FROM character_skill_queue
            WHERE character_id = ANY(%s)
            ORDER BY character_id, queue_position
        """, (char_ids,))
        queue_data = {r["character_id"]: r for r in cur.fetchall()}

    prices = _get_market_prices()

    results = []
    for c in characters:
        cid = c["character_id"]
        sp_info = sp_data.get(cid, {})
        total_sp = sp_info.get("total_sp", 0) or 0
        queue = queue_data.get(cid)
        is_farm = flags.get(cid, False) or False

        sp_hour = _get_sp_per_hour(cid) if queue else 0
        sp_month = sp_hour * HOURS_PER_MONTH
        extractors_month = sp_month / SP_PER_EXTRACTOR if sp_month > 0 else 0
        profit_month = extractors_month * prices["profit_per_extractor"]

        results.append({
            "character_id": cid,
            "character_name": c.get("character_name", f"Character {cid}"),
            "is_skillfarm": is_farm,
            "total_sp": total_sp,
            "sp_per_hour": round(sp_hour, 1),
            "sp_per_month": round(sp_month),
            "extractors_per_month": round(extractors_month, 2),
            "profit_per_month": round(profit_month),
            "queue_active": queue is not None,
            "training_skill": queue["skill_name"] if queue else None,
            "training_level": queue["finished_level"] if queue else None,
            "queue_ends": queue["finish_date"].isoformat() if queue and queue.get("finish_date") else None,
        })

    return {"characters": results, "prices": prices}


@router.put("/skillfarm/characters/{character_id}/toggle")
def toggle_skillfarm(character_id: int, session: Optional[str] = Cookie(None)):
    """Toggle a character's skillfarm flag."""
    account = _validate_session(session)
    char_ids = [c["character_id"] for c in account.get("characters", [])]
    if character_id not in char_ids:
        raise HTTPException(status_code=403, detail="Character not in your account")

    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            "UPDATE account_characters SET is_skillfarm = NOT COALESCE(is_skillfarm, false) WHERE character_id = %s RETURNING is_skillfarm",
            (character_id,)
        )
        row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Character not found")
    return {"character_id": character_id, "is_skillfarm": row["is_skillfarm"]}


@router.get("/skillfarm/summary")
def get_skillfarm_summary(session: Optional[str] = Cookie(None)):
    """Aggregated skillfarm statistics."""
    account = _validate_session(session)
    characters = account.get("characters", [])
    if not characters:
        return {"total_farms": 0, "total_sp_month": 0, "total_profit_month": 0, "prices": _get_market_prices()}

    char_ids = [c["character_id"] for c in characters]
    db = get_db()

    with db.cursor() as cur:
        cur.execute(
            "SELECT character_id FROM account_characters WHERE character_id = ANY(%s) AND is_skillfarm = true",
            (char_ids,)
        )
        farm_ids = [r["character_id"] for r in cur.fetchall()]

    prices = _get_market_prices()
    total_sp_month = 0.0
    total_profit_month = 0.0

    for cid in farm_ids:
        sp_hour = _get_sp_per_hour(cid)
        sp_month = sp_hour * HOURS_PER_MONTH
        extractors = sp_month / SP_PER_EXTRACTOR if sp_month > 0 else 0
        profit = extractors * prices["profit_per_extractor"]
        total_sp_month += sp_month
        total_profit_month += profit

    return {
        "total_farms": len(farm_ids),
        "total_sp_month": round(total_sp_month),
        "total_profit_month": round(total_profit_month),
        "extractors_month": round(total_sp_month / SP_PER_EXTRACTOR, 2) if total_sp_month > 0 else 0,
        "prices": prices,
    }
