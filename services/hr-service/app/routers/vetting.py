"""Automated Vetting Engine - Applicant screening pipeline."""

from typing import List

from fastapi import APIRouter, Request, HTTPException
from eve_shared.utils.error_handling import handle_endpoint_errors

from app.models import VettingCheckRequest, VettingReport
from app.services.vetting_engine import VettingEngine

router = APIRouter(prefix="/vetting", tags=["Vetting"])


def _get_engine() -> VettingEngine:
    return VettingEngine()


@router.post("/check", response_model=VettingReport)
@handle_endpoint_errors()
async def check_applicant(request: Request, check: VettingCheckRequest):
    """Run full vetting pipeline for a character."""
    engine = _get_engine()
    result = await engine.check_applicant(
        character_id=check.character_id,
        check_contacts=check.check_contacts,
        check_wallet=check.check_wallet,
        check_skills=check.check_skills,
    )
    return result


@router.get("/report/{character_id}", response_model=VettingReport)
@handle_endpoint_errors()
def get_report(request: Request, character_id: int):
    """Get latest vetting report for a character."""
    engine = _get_engine()
    report = engine.get_report(character_id)
    if not report:
        raise HTTPException(status_code=404, detail="No vetting report found")
    return report


@router.get("/history/{character_id}")
@handle_endpoint_errors()
def get_vetting_history(request: Request, character_id: int):
    """Get all vetting reports for a character."""
    engine = _get_engine()
    return engine.get_history(character_id)
