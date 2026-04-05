"""Tax Invoicing - Generation, payment matching, compliance tracking."""

from typing import List, Optional

from fastapi import APIRouter, Request, Query, HTTPException

from eve_shared.utils.error_handling import handle_endpoint_errors
from app.models import TaxInvoice, InvoiceGenerateRequest
from app.services.invoicing import InvoicingService

router = APIRouter(prefix="/invoices", tags=["Invoices"])


@router.get("", response_model=List[TaxInvoice])
@handle_endpoint_errors()
def list_invoices(
    request: Request,
    corporation_id: Optional[int] = None,
    character_id: Optional[int] = None,
    status: Optional[str] = Query(None, pattern="^(pending|partial|paid|overdue)$"),
    limit: int = Query(50, le=200),
):
    """List tax invoices with optional filters."""
    service = InvoicingService()
    rows = service.list_invoices(
        corp_id=corporation_id,
        char_id=character_id,
        status=status,
        limit=limit,
    )
    return [_row_to_invoice(row) for row in rows]


@router.get("/{invoice_id}", response_model=TaxInvoice)
@handle_endpoint_errors()
def get_invoice(request: Request, invoice_id: int):
    """Get a specific invoice with payment history."""
    service = InvoicingService()
    invoice = service.get_invoice(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return _row_to_invoice(invoice)


@router.post("/generate")
@handle_endpoint_errors()
def generate_invoices(request: Request, gen_req: InvoiceGenerateRequest):
    """Auto-generate monthly invoices from mining tax ledger."""
    service = InvoicingService()
    invoices = service.generate_invoices(
        corp_id=gen_req.corporation_id,
        period_start=gen_req.period_start.isoformat(),
        period_end=gen_req.period_end.isoformat(),
        tax_rate=float(gen_req.tax_rate),
    )
    return {"generated": len(invoices), "invoices": invoices}


@router.post("/match-payments/{corporation_id}")
@handle_endpoint_errors()
def match_payments(request: Request, corporation_id: int):
    """Scan wallet journal for payments matching open invoices."""
    service = InvoicingService()
    return service.match_payments(corporation_id)


def _row_to_invoice(row: dict) -> TaxInvoice:
    """Convert a database row dict to TaxInvoice model."""
    return TaxInvoice(
        id=row.get("id"),
        character_id=row["character_id"],
        period_start=row["period_start"],
        period_end=row["period_end"],
        total_mined_value=row.get("total_mined_value", 0),
        tax_rate=row.get("tax_rate", 0.10),
        amount_due=row.get("amount_due", 0),
        amount_paid=row.get("amount_paid", 0),
        remaining_balance=row.get("remaining_balance", 0),
        status=row.get("status", "pending"),
        created_at=row.get("created_at"),
    )
