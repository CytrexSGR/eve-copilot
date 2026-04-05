"""Financial Reports - Income, expenses, P&L summaries."""

from typing import List
from datetime import date

from fastapi import APIRouter, Request, Query

from eve_shared.utils.error_handling import handle_endpoint_errors
from app.models import IncomeBreakdown, ExpenseSummary, PnlReport
from app.services.reports import ReportsService

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/income/{corporation_id}", response_model=List[IncomeBreakdown])
@handle_endpoint_errors()
def get_income_breakdown(
    request: Request,
    corporation_id: int,
    days: int = Query(30, ge=1, le=365),
    division_id: int = Query(1, ge=1, le=7),
):
    """Get income breakdown by ref_type category."""
    service = ReportsService()
    results = service.get_income_breakdown(corporation_id, days, division_id)
    return [
        IncomeBreakdown(
            category=r["category"],
            ref_types=r.get("ref_types", []),
            total_amount=r["total_amount"],
            transaction_count=r["transaction_count"],
        )
        for r in results
    ]


@router.get("/expenses/{corporation_id}", response_model=List[ExpenseSummary])
@handle_endpoint_errors()
def get_expense_summary(
    request: Request,
    corporation_id: int,
    days: int = Query(30, ge=1, le=365),
):
    """Get expense summary by division."""
    service = ReportsService()
    results = service.get_expense_summary(corporation_id, days)
    return [
        ExpenseSummary(
            division_id=r["division_id"],
            division_name=r.get("division_name"),
            total_amount=r["total_amount"],
            transaction_count=r["transaction_count"],
        )
        for r in results
    ]


@router.get("/pnl/{corporation_id}")
@handle_endpoint_errors()
def get_pnl_report(
    request: Request,
    corporation_id: int,
    period_start: date = Query(...),
    period_end: date = Query(...),
):
    """Get Profit & Loss report for a period."""
    service = ReportsService()
    return service.get_pnl_report(
        corporation_id,
        period_start.isoformat(),
        period_end.isoformat(),
    )


@router.get("/ratting-tax/{corporation_id}")
@handle_endpoint_errors()
def get_ratting_tax_audit(
    request: Request,
    corporation_id: int,
    days: int = Query(30, ge=1, le=365),
):
    """Ratting tax audit - compare corp bounty income with member activity."""
    service = ReportsService()
    return service.get_ratting_tax_audit(corporation_id, days)
