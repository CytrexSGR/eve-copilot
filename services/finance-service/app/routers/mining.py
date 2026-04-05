"""Mining Observer & Tax - Sync, ledger queries, tax summaries."""

from typing import List, Optional
from decimal import Decimal

from fastapi import APIRouter, Request, Query

from eve_shared import get_db
from eve_shared.utils.error_handling import handle_endpoint_errors

from app.models import MiningObserver, MiningLedgerEntry, MiningTaxSummary
from app.services.mining_tax import MiningTaxService

router = APIRouter(prefix="/mining", tags=["Mining"])


@router.get("/observers/{corporation_id}", response_model=List[MiningObserver])
@handle_endpoint_errors()
def get_observers(request: Request, corporation_id: int):
    """Get mining observers for a corporation."""
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            """SELECT observer_id, observer_type, last_updated
               FROM mining_observers
               WHERE corporation_id = %s
               ORDER BY last_updated DESC NULLS LAST""",
            (corporation_id,),
        )
        rows = cur.fetchall()

    return [
        MiningObserver(
            observer_id=row["observer_id"],
            observer_type=row["observer_type"],
            last_updated=row["last_updated"],
        )
        for row in rows
    ]


@router.get("/ledger/{corporation_id}", response_model=List[MiningLedgerEntry])
@handle_endpoint_errors()
def get_mining_ledger(
    request: Request,
    corporation_id: int,
    character_id: Optional[int] = None,
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(200, le=1000),
    offset: int = Query(0, ge=0),
):
    """Get mining ledger entries for a corporation."""
    db = get_db()
    with db.cursor() as cur:
        if character_id:
            cur.execute(
                """SELECT mol.observer_id, mol.character_id, mol.type_id,
                          it."typeName" as type_name,
                          mol.last_updated, mol.quantity
                   FROM mining_observer_ledger mol
                   JOIN mining_observers mo ON mol.observer_id = mo.observer_id
                   LEFT JOIN "invTypes" it ON mol.type_id = it."typeID"
                   WHERE mo.corporation_id = %s
                     AND mol.character_id = %s
                     AND mol.last_updated >= CURRENT_DATE - INTERVAL '1 day' * %s
                   ORDER BY mol.last_updated DESC
                   LIMIT %s OFFSET %s""",
                (corporation_id, character_id, days, limit, offset),
            )
        else:
            cur.execute(
                """SELECT mol.observer_id, mol.character_id, mol.type_id,
                          it."typeName" as type_name,
                          mol.last_updated, mol.quantity
                   FROM mining_observer_ledger mol
                   JOIN mining_observers mo ON mol.observer_id = mo.observer_id
                   LEFT JOIN "invTypes" it ON mol.type_id = it."typeID"
                   WHERE mo.corporation_id = %s
                     AND mol.last_updated >= CURRENT_DATE - INTERVAL '1 day' * %s
                   ORDER BY mol.last_updated DESC
                   LIMIT %s OFFSET %s""",
                (corporation_id, days, limit, offset),
            )
        rows = cur.fetchall()

    return [
        MiningLedgerEntry(
            observer_id=row["observer_id"],
            character_id=row["character_id"],
            type_id=row["type_id"],
            type_name=row["type_name"],
            last_updated=row["last_updated"],
            quantity=row["quantity"],
        )
        for row in rows
    ]


@router.post("/sync/{corporation_id}")
@handle_endpoint_errors()
async def sync_mining(
    request: Request,
    corporation_id: int,
    character_id: int = Query(..., description="Character with mining observer access"),
):
    """Sync all mining observers and ledgers for a corporation."""
    service = MiningTaxService()
    return await service.sync_all_observers(corporation_id, character_id)


@router.get("/tax-summary/{corporation_id}", response_model=List[MiningTaxSummary])
@handle_endpoint_errors()
def get_tax_summary(
    request: Request,
    corporation_id: int,
    days: int = Query(30, ge=1, le=365),
):
    """Get mining tax summary per character."""
    service = MiningTaxService()
    summaries = service.get_tax_summary(corporation_id, days)

    return [
        MiningTaxSummary(
            character_id=s["character_id"],
            total_mined_quantity=s.get("total_delta", 0) or 0,
            total_isk_value=Decimal(str(s.get("total_isk_value", 0) or 0)),
            total_tax=Decimal(str(s.get("total_tax", 0) or 0)),
        )
        for s in summaries
    ]


@router.get("/tax-detail/{corporation_id}/{character_id}")
@handle_endpoint_errors()
def get_tax_detail(
    request: Request,
    corporation_id: int,
    character_id: int,
    days: int = Query(30, ge=1, le=365),
):
    """Get ore breakdown for a specific character's mining tax."""
    service = MiningTaxService()
    return service.get_character_ore_breakdown(character_id, corporation_id, days)


@router.post("/sync-prices")
@handle_endpoint_errors()
async def sync_prices(request: Request):
    """Sync ore and mineral prices from Fuzzwork API."""
    service = MiningTaxService()
    return await service.sync_ore_prices()


@router.get("/config/{corporation_id}")
@handle_endpoint_errors()
def get_tax_config(request: Request, corporation_id: int):
    """Get mining tax configuration for a corporation."""
    service = MiningTaxService()
    return service._get_tax_config(corporation_id)


@router.put("/config/{corporation_id}")
@handle_endpoint_errors()
def update_tax_config(
    request: Request,
    corporation_id: int,
    tax_rate: float = Query(0.10, ge=0.0, le=1.0),
    reprocessing_yield: float = Query(0.85, ge=0.0, le=1.0),
    pricing_mode: str = Query("jita_split", pattern="^(jita_buy|jita_sell|jita_split)$"),
):
    """Update mining tax configuration for a corporation."""
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            """INSERT INTO mining_tax_config
               (corporation_id, tax_rate, reprocessing_yield, pricing_mode, updated_at)
               VALUES (%s, %s, %s, %s, NOW())
               ON CONFLICT (corporation_id) DO UPDATE SET
                   tax_rate = EXCLUDED.tax_rate,
                   reprocessing_yield = EXCLUDED.reprocessing_yield,
                   pricing_mode = EXCLUDED.pricing_mode,
                   updated_at = NOW()""",
            (corporation_id, tax_rate, reprocessing_yield, pricing_mode),
        )
    return {
        "corporation_id": corporation_id,
        "tax_rate": tax_rate,
        "reprocessing_yield": reprocessing_yield,
        "pricing_mode": pricing_mode,
    }


# --- Extraction & Performance Endpoints ---


@router.get("/extractions/{corporation_id}")
@handle_endpoint_errors()
def get_extractions(request: Request, corporation_id: int):
    """Get recent and upcoming moon extractions for a corporation."""
    service = MiningTaxService()
    return {
        "corporation_id": corporation_id,
        "extractions": service.get_extractions(corporation_id),
    }


@router.get("/performance/{corporation_id}")
@handle_endpoint_errors()
def get_performance(
    request: Request,
    corporation_id: int,
    days: int = Query(30, ge=1, le=365),
):
    """Get mining performance metrics per structure and ore breakdown."""
    service = MiningTaxService()
    return service.get_performance(corporation_id, days)


@router.post("/sync-extractions/{corporation_id}")
@handle_endpoint_errors()
async def sync_extractions(
    request: Request,
    corporation_id: int,
    character_id: int = Query(
        ..., description="Character with mining observer access"
    ),
):
    """Sync moon extraction schedules from ESI."""
    service = MiningTaxService()
    return await service.sync_extractions(corporation_id, character_id)


@router.get("/dashboard/{corporation_id}")
@handle_endpoint_errors()
def get_dashboard(
    request: Request,
    corporation_id: int,
    days: int = Query(30, ge=1, le=365),
):
    """Combined mining dashboard: observers, performance, extractions, tax summary."""
    service = MiningTaxService()
    db = get_db()

    with db.cursor() as cur:
        cur.execute(
            """SELECT observer_id, observer_type, last_updated
               FROM mining_observers
               WHERE corporation_id = %s
               ORDER BY last_updated DESC NULLS LAST""",
            (corporation_id,),
        )
        observers = [dict(row) for row in cur.fetchall()]

    performance = service.get_performance(corporation_id, days)
    extractions = service.get_extractions(corporation_id)
    tax_summary = service.get_tax_summary(corporation_id, days)

    return {
        "corporation_id": corporation_id,
        "days": days,
        "observers": observers,
        "performance": performance,
        "extractions": extractions,
        "tax_summary": [
            {
                "character_id": s["character_id"],
                "total_mined_quantity": s.get("total_delta", 0) or 0,
                "total_isk_value": float(s.get("total_isk_value", 0) or 0),
                "total_tax": float(s.get("total_tax", 0) or 0),
            }
            for s in tax_summary
        ],
    }
