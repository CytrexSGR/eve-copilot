"""Wormhole threat feed API."""
from fastapi import APIRouter, Query
from typing import Optional
from eve_shared.utils.error_handling import handle_endpoint_errors

from app.services.threat_analyzer import ThreatAnalyzer

router = APIRouter(prefix="/threats", tags=["threats"])
analyzer = ThreatAnalyzer()


@router.get("")
@handle_endpoint_errors()
def get_threats(
    wh_class: Optional[int] = Query(None, ge=1, le=18, description="Filter by WH class (1-6 standard, 13+ special)"),
    limit: int = Query(20, ge=1, le=50)
):
    """
    Get threat feed for J-Space residents.

    Returns capital sightings, hunter activity, and activity spikes.
    """
    threats = analyzer.get_threats(wh_class=wh_class, limit=limit)
    return {
        "count": len(threats),
        "filter": {"wh_class": wh_class},
        "threats": threats
    }
