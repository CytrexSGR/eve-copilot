"""Buyback appraisal and request management router."""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Query
from pydantic import BaseModel

from eve_shared.utils.error_handling import handle_endpoint_errors
from app.services.buyback import BuybackService

logger = logging.getLogger(__name__)
router = APIRouter()


class AppraiseRequest(BaseModel):
    """Request for item appraisal."""
    raw_text: str
    config_id: Optional[int] = None


class SubmitRequest(BaseModel):
    """Request to submit a buyback."""
    raw_text: str
    config_id: int
    character_id: int
    character_name: Optional[str] = None
    corporation_id: int


class ConfigCreate(BaseModel):
    """Create a buyback config."""
    corporation_id: int
    name: str
    base_discount: float = 10.0
    ore_modifier: float = 0.0
    notes: Optional[str] = None


@router.post("/buyback/appraise")
@handle_endpoint_errors()
def appraise_items(request: Request, body: AppraiseRequest) -> dict:
    """Appraise pasted EVE text — returns Jita prices and optional buyback calculation.

    Paste items from EVE inventory (TSV) or manual format (Item x Qty).
    If config_id is provided, also calculates buyback values.
    """
    db = request.app.state.db
    service = BuybackService(db)

    items = service.parse_eve_text(body.raw_text)
    if not items:
        raise HTTPException(status_code=400, detail="No items found in text")

    appraised = service.appraise_items(items)

    result = {
        "items": appraised,
        "summary": {
            "item_count": len(appraised),
            "total_jita_sell": sum(i["jita_sell_total"] for i in appraised),
            "total_jita_buy": sum(i["jita_buy_total"] for i in appraised),
            "total_volume": sum(i["total_volume"] for i in appraised),
        },
    }

    # If config_id provided, also calculate buyback
    if body.config_id:
        buyback = service.calculate_buyback(appraised, body.config_id)
        result["buyback"] = buyback["summary"]
        result["items"] = buyback["items"]
        result["config"] = buyback["config"]

    return result


@router.post("/buyback/submit", status_code=201)
@handle_endpoint_errors()
def submit_buyback(request: Request, body: SubmitRequest) -> dict:
    """Submit a buyback request — appraises, calculates, and saves."""
    db = request.app.state.db
    service = BuybackService(db)
    return service.submit_request(
        body.character_id,
        body.character_name,
        body.corporation_id,
        body.config_id,
        body.raw_text,
    )


@router.get("/buyback/requests")
@handle_endpoint_errors()
def list_requests(
    request: Request,
    corporation_id: Optional[int] = Query(default=None),
    character_id: Optional[int] = Query(default=None),
    status: Optional[str] = Query(default=None),
    limit: int = Query(default=50, le=200),
) -> dict:
    """List buyback requests with optional filters."""
    db = request.app.state.db
    service = BuybackService(db)
    requests_list = service.list_requests(
        corporation_id=corporation_id,
        character_id=character_id,
        status=status,
        limit=limit,
    )
    return {"requests": requests_list, "count": len(requests_list)}


@router.get("/buyback/configs")
@handle_endpoint_errors()
def list_configs(
    request: Request,
    corporation_id: Optional[int] = Query(default=None),
    active_only: bool = Query(default=True),
) -> dict:
    """List buyback configurations."""
    db = request.app.state.db
    service = BuybackService(db)
    configs = service.list_configs(
        corporation_id=corporation_id, active_only=active_only
    )
    return {"configs": configs, "count": len(configs)}


@router.post("/buyback/configs", status_code=201)
@handle_endpoint_errors()
def create_config(request: Request, body: ConfigCreate) -> dict:
    """Create a new buyback configuration."""
    db = request.app.state.db
    service = BuybackService(db)
    return service.create_config(body.model_dump())
