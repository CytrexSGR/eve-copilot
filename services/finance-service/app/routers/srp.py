"""SRP & Doctrine Management Router.

Endpoints for fleet doctrine CRUD, SRP request management,
pricing sync, and SRP configuration.
"""

import logging
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Request, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from eve_shared.utils.error_handling import handle_endpoint_errors
from app.models.schemas import (
    DoctrineCreate, DoctrineUpdate, DoctrineImportEft, DoctrineImportDna, DoctrineImportFitting,
    DoctrineResponse, DoctrineCloneRequest, DoctrineChangelogEntry,
    DoctrineAutoPriceResponse,
    SrpSubmitRequest, SrpReviewRequest, SrpResponse,
    SrpConfigUpdate,
)
from app.services.doctrine import DoctrineService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["SRP & Doctrines"])


def _doctrine_service() -> DoctrineService:
    return DoctrineService()


# ═══════════════════════════════════════════════════════════════════════════
#  DOCTRINE CRUD
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/doctrines/{corporation_id}")
@handle_endpoint_errors()
def list_doctrines(
    corporation_id: int,
    active_only: bool = Query(True, description="Only return active doctrines"),
):
    """List all doctrines for a corporation."""
    svc = _doctrine_service()
    doctrines = svc.list_doctrines(corporation_id, active_only=active_only)
    return {"doctrines": doctrines, "total": len(doctrines)}


@router.get("/doctrine/{doctrine_id}")
@handle_endpoint_errors()
def get_doctrine(doctrine_id: int):
    """Get a single doctrine by ID."""
    svc = _doctrine_service()
    doctrine = svc.get_doctrine(doctrine_id)
    if not doctrine:
        raise HTTPException(status_code=404, detail="Doctrine not found")
    return doctrine


@router.post("/doctrine", status_code=201)
@handle_endpoint_errors()
def create_doctrine(req: DoctrineCreate):
    """Create a new doctrine with an explicit fitting structure."""
    svc = _doctrine_service()
    result = svc.create_doctrine(
        corporation_id=req.corporation_id,
        name=req.name,
        ship_type_id=req.ship_type_id,
        fitting=req.fitting.model_dump(),
        base_payout=float(req.base_payout) if req.base_payout else None,
        created_by=req.created_by,
    )
    return result


@router.post("/doctrine/import/eft", status_code=201)
@handle_endpoint_errors()
def import_doctrine_eft(req: DoctrineImportEft):
    """Import a doctrine from EFT text format.

    The system parses the EFT text, resolves type names via SDE,
    and creates the doctrine with normalized JSONB fitting.
    """
    svc = _doctrine_service()
    result = svc.import_from_eft(
        corporation_id=req.corporation_id,
        eft_text=req.eft_text,
        base_payout=float(req.base_payout) if req.base_payout else None,
        created_by=req.created_by,
    )
    if not result:
        raise HTTPException(
            status_code=422,
            detail="Failed to parse EFT text. Check format and module names.",
        )
    return result


@router.post("/doctrine/import/dna", status_code=201)
@handle_endpoint_errors()
def import_doctrine_dna(req: DoctrineImportDna):
    """Import a doctrine from DNA string format.

    DNA format: shipTypeID:moduleID;qty:moduleID;qty::
    """
    svc = _doctrine_service()
    result = svc.import_from_dna(
        corporation_id=req.corporation_id,
        name=req.name,
        dna_string=req.dna_string,
        base_payout=float(req.base_payout) if req.base_payout else None,
        created_by=req.created_by,
    )
    if not result:
        raise HTTPException(
            status_code=422,
            detail="Failed to parse DNA string.",
        )
    return result


@router.post("/doctrine/import/fitting", status_code=201)
@handle_endpoint_errors()
def import_doctrine_fitting(req: DoctrineImportFitting):
    """Import a doctrine from an existing fitting's items.

    Converts flag-based fitting items to slot-based doctrine format.
    """
    svc = _doctrine_service()
    result = svc.import_from_fitting(
        corporation_id=req.corporation_id,
        name=req.name,
        ship_type_id=req.ship_type_id,
        items=[item.model_dump() for item in req.items],
        base_payout=float(req.base_payout) if req.base_payout else 0,
        category=req.category or "general",
        created_by=req.created_by,
    )
    if not result:
        raise HTTPException(status_code=422, detail="Failed to import fitting.")
    return result


@router.put("/doctrine/{doctrine_id}")
@handle_endpoint_errors()
def update_doctrine(doctrine_id: int, req: DoctrineUpdate):
    """Update a doctrine's mutable fields."""
    svc = _doctrine_service()
    updates = {}
    if req.name is not None:
        updates["name"] = req.name
    if req.is_active is not None:
        updates["is_active"] = req.is_active
    if req.base_payout is not None:
        updates["base_payout"] = float(req.base_payout)
    if req.fitting is not None:
        updates["fitting"] = req.fitting.model_dump()

    result = svc.update_doctrine(doctrine_id, updates)
    if not result:
        raise HTTPException(status_code=404, detail="Doctrine not found")
    return result


@router.delete("/doctrine/{doctrine_id}")
@handle_endpoint_errors()
def archive_doctrine(doctrine_id: int):
    """Archive (soft-delete) a doctrine by setting is_active = FALSE."""
    svc = _doctrine_service()
    success = svc.archive_doctrine(doctrine_id)
    if not success:
        raise HTTPException(status_code=404, detail="Doctrine not found or already archived")
    return {"status": "archived", "doctrine_id": doctrine_id}





# ═══════════════════════════════════════════════════════════════════════════
#  DOCTRINE CLONE, PRICING & CHANGELOG
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/doctrine/{doctrine_id}/clone", status_code=201)
@handle_endpoint_errors()
def clone_doctrine(doctrine_id: int, req: DoctrineCloneRequest):
    """Clone a doctrine with a new name and optional category."""
    svc = _doctrine_service()
    result = svc.clone_doctrine(
        doctrine_id=doctrine_id,
        new_name=req.new_name,
        category=req.category,
        actor_id=0,
        actor_name="API",
    )
    if not result:
        raise HTTPException(status_code=404, detail="Doctrine not found")
    return result


@router.get("/doctrine/{doctrine_id}/price")
@handle_endpoint_errors()
def get_doctrine_price(doctrine_id: int):
    """Calculate fitting price from cached Jita sell prices."""
    svc = _doctrine_service()
    result = svc.calculate_doctrine_price(doctrine_id)
    if not result:
        raise HTTPException(status_code=404, detail="Doctrine not found")
    return result


@router.get("/doctrine/{doctrine_id}/changelog")
@handle_endpoint_errors()
def get_doctrine_changelog(
    doctrine_id: int,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Get changelog for a specific doctrine."""
    svc = _doctrine_service()
    entries = svc.get_doctrine_changelog(
        doctrine_id=doctrine_id,
        limit=limit,
        offset=offset,
    )
    return {"entries": entries, "total": len(entries)}


@router.get("/doctrines/{corp_id}/changelog")
@handle_endpoint_errors()
def get_corp_doctrine_changelog(
    corp_id: int,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Get changelog for all doctrines of a corporation."""
    svc = _doctrine_service()
    entries = svc.get_doctrine_changelog(
        corporation_id=corp_id,
        limit=limit,
        offset=offset,
    )
    return {"entries": entries, "total": len(entries)}


# ═══════════════════════════════════════════════════════════════════════════
#  SRP REQUESTS
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/srp/requests/{corporation_id}")
@handle_endpoint_errors()
def list_srp_requests(
    corporation_id: int,
    status: Optional[str] = Query(None, pattern="^(pending|approved|rejected|paid)$"),
    character_id: Optional[int] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List SRP requests for a corporation with optional filters."""
    from eve_shared import get_db
    db = get_db()

    where_clauses = ["r.corporation_id = %s"]
    params: list = [corporation_id]

    if status:
        where_clauses.append("r.status = %s")
        params.append(status)
    if character_id:
        where_clauses.append("r.character_id = %s")
        params.append(character_id)

    where = " AND ".join(where_clauses)

    with db.cursor() as cur:
        cur.execute(
            f"""
            SELECT r.*, d.name as doctrine_name
            FROM srp_requests r
            LEFT JOIN fleet_doctrines d ON d.id = r.doctrine_id
            WHERE {where}
            ORDER BY r.submitted_at DESC
            LIMIT %s OFFSET %s
            """,
            params + [limit, offset],
        )
        rows = cur.fetchall()

        cur.execute(
            f"""
            SELECT COUNT(*) as total
            FROM srp_requests r
            LEFT JOIN fleet_doctrines d ON d.id = r.doctrine_id
            WHERE {where}
            """,
            params,
        )
        total = cur.fetchone()["total"]

    return {"requests": [dict(r) for r in rows], "total": total}


@router.get("/srp/request/{request_id}")
@handle_endpoint_errors()
def get_srp_request(request_id: int):
    """Get a single SRP request by ID."""
    from eve_shared import get_db
    db = get_db()

    with db.cursor() as cur:
        cur.execute(
            """
            SELECT r.*, d.name as doctrine_name
            FROM srp_requests r
            LEFT JOIN fleet_doctrines d ON d.id = r.doctrine_id
            WHERE r.id = %s
            """,
            (request_id,),
        )
        row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="SRP request not found")
    return dict(row)


@router.put("/srp/request/{request_id}/review")
@handle_endpoint_errors()
def review_srp_request(request_id: int, req: SrpReviewRequest):
    """Approve or reject an SRP request."""
    from eve_shared import get_db
    db = get_db()

    with db.cursor() as cur:
        cur.execute(
            """
            UPDATE srp_requests
            SET status = %s,
                reviewed_by = %s,
                reviewed_at = NOW(),
                review_note = %s
            WHERE id = %s AND status = 'pending'
            RETURNING id, status
            """,
            (req.status, req.reviewed_by, req.review_note, request_id),
        )
        row = cur.fetchone()

    if not row:
        raise HTTPException(
            status_code=404,
            detail="SRP request not found or not in pending status",
        )
    return {"id": row["id"], "status": row["status"], "message": f"Request {req.status}"}


# ═══════════════════════════════════════════════════════════════════════════
#  SRP CONFIG
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/srp/config/{corporation_id}")
@handle_endpoint_errors()
def get_srp_config(corporation_id: int):
    """Get SRP configuration for a corporation."""
    from eve_shared import get_db
    db = get_db()

    with db.cursor() as cur:
        cur.execute(
            "SELECT * FROM srp_config WHERE corporation_id = %s",
            (corporation_id,),
        )
        row = cur.fetchone()

    if not row:
        # Return defaults
        return {
            "corporation_id": corporation_id,
            "pricing_mode": "jita_split",
            "default_insurance_level": "none",
            "auto_approve_threshold": 0.90,
            "max_payout": None,
        }
    return dict(row)


@router.put("/srp/config/{corporation_id}")
@handle_endpoint_errors()
def update_srp_config(corporation_id: int, req: SrpConfigUpdate):
    """Update SRP configuration for a corporation (upsert)."""
    from eve_shared import get_db
    db = get_db()

    updates = req.model_dump(exclude_none=True)
    if not updates:
        return get_srp_config(corporation_id)

    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO srp_config (corporation_id, pricing_mode,
                                     default_insurance_level,
                                     auto_approve_threshold, max_payout)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (corporation_id) DO UPDATE
            SET pricing_mode = COALESCE(EXCLUDED.pricing_mode, srp_config.pricing_mode),
                default_insurance_level = COALESCE(EXCLUDED.default_insurance_level, srp_config.default_insurance_level),
                auto_approve_threshold = COALESCE(EXCLUDED.auto_approve_threshold, srp_config.auto_approve_threshold),
                max_payout = COALESCE(EXCLUDED.max_payout, srp_config.max_payout),
                updated_at = NOW()
            RETURNING *
            """,
            (
                corporation_id,
                updates.get("pricing_mode", "jita_split"),
                updates.get("default_insurance_level", "none"),
                updates.get("auto_approve_threshold", 0.90),
                updates.get("max_payout"),
            ),
        )
        row = cur.fetchone()

    return dict(row)


# ═══════════════════════════════════════════════════════════════════════════
#  SRP WORKFLOW
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/srp/submit", status_code=201)
@handle_endpoint_errors()
async def submit_srp_request(req: SrpSubmitRequest):
    """Submit a new SRP request.

    Fetches killmail from ESI, auto-matches against active doctrines,
    calculates payout, and creates the SRP request record.
    High-confidence matches (>= auto_approve_threshold) are auto-approved.
    """
    from app.services.srp_workflow import SRPWorkflow
    wf = SRPWorkflow()

    result = await wf.submit_request(
        corporation_id=req.corporation_id,
        character_id=req.character_id,
        character_name=req.character_name,
        killmail_id=req.killmail_id,
        killmail_hash=req.killmail_hash,
        doctrine_id=req.doctrine_id,
    )

    if "error" in result:
        raise HTTPException(status_code=422, detail=result["error"])

    return result


class BatchPaidRequest(BaseModel):
    request_ids: List[int]


@router.post("/srp/batch-paid")
@handle_endpoint_errors()
def batch_mark_paid(req: BatchPaidRequest):
    """Mark multiple approved SRP requests as paid."""
    from app.services.srp_workflow import SRPWorkflow
    wf = SRPWorkflow()

    updated = wf.batch_mark_paid(req.request_ids)
    return {"marked_paid": updated, "total_requested": len(req.request_ids)}


@router.get("/srp/payout-list/{corporation_id}")
@handle_endpoint_errors()
def get_payout_list(
    corporation_id: int,
    status: str = Query("approved", pattern="^(approved|pending)$"),
):
    """Generate TSV payout list for EVE client mass payout.

    Returns tab-separated text: CharacterName\\tAmount\\tReason
    Copy this directly into EVE's "Send ISK" window.
    """
    from app.services.srp_workflow import SRPWorkflow
    wf = SRPWorkflow()

    tsv = wf.get_payout_list(corporation_id, status=status)
    if not tsv:
        return PlainTextResponse("", media_type="text/plain")
    return PlainTextResponse(tsv, media_type="text/tab-separated-values")


@router.post("/srp/sync-prices")
@handle_endpoint_errors()
async def sync_item_prices(
    corporation_id: int = Query(..., description="Corporation to sync prices for"),
):
    """Sync item prices from Fuzzwork API for all active doctrine items.

    Fetches current Jita buy/sell/split prices for every module
    referenced in active doctrines of this corporation.
    """
    from app.services.pricing import PricingEngine
    from app.services.doctrine import DoctrineService
    import json

    pricing = PricingEngine()
    doctrine_svc = DoctrineService()

    doctrines = doctrine_svc.list_doctrines(corporation_id, active_only=True)

    all_type_ids = set()
    for doc in doctrines:
        fitting = doc.get("fitting_json", {})
        if isinstance(fitting, str):
            fitting = json.loads(fitting)
        type_ids = pricing.collect_fitting_type_ids(fitting)
        all_type_ids.update(type_ids)

    if not all_type_ids:
        return {"synced": 0, "message": "No active doctrines found"}

    count = await pricing.sync_item_prices(list(all_type_ids))
    return {"synced": count, "total_types": len(all_type_ids)}
