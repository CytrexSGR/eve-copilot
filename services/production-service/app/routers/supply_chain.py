"""
Supply Chain Intelligence API Router

Migrated to production-service using eve_shared pattern.
"""

from fastapi import APIRouter, HTTPException, Request
from typing import Optional, List, Dict, Any
from datetime import datetime
import sys
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Add supply_chain_intelligence to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent.parent / "alliance_report_blueprint" / "scripts"))

try:
    from supply_chain_intelligence.industry_index import (
        IndustryIndexAnalyzer,
        generate_alliance_report as gen_industry
    )
    from supply_chain_intelligence.cyno_highway import (
        CynoHighwayAnalyzer,
        generate_logistics_report as gen_logistics
    )
    from supply_chain_intelligence.cargo_fingerprint import (
        CargoFingerprintAnalyzer,
        generate_cargo_report as gen_cargo
    )
    from supply_chain_intelligence.config import TRACKED_ALLIANCES
    from supply_chain_intelligence.database import execute_query
    SUPPLY_CHAIN_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Supply chain intelligence module not available: {e}")
    SUPPLY_CHAIN_AVAILABLE = False
    TRACKED_ALLIANCES = []

    def execute_query(*args, **kwargs):
        return []

    def gen_industry(*args, **kwargs):
        return {}

    def gen_logistics(*args, **kwargs):
        return {}

    def gen_cargo(*args, **kwargs):
        return {}


router = APIRouter(prefix="/api/supply-chain", tags=["Supply Chain Intelligence"])


def _check_availability():
    """Check if supply chain intelligence is available."""
    if not SUPPLY_CHAIN_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Supply chain intelligence module not available"
        )


@router.get("/alliances")
def get_tracked_alliances(request: Request) -> List[Dict[str, Any]]:
    """Get list of alliances with supply chain data availability."""
    _check_availability()
    db = request.app.state.db

    result = []
    for alliance in TRACKED_ALLIANCES:
        # Check if we have data
        with db.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) FROM sovereignty_map_cache
                WHERE alliance_id = %s
            """, (alliance["id"],))
            has_industry = cur.fetchone()

            cur.execute("""
                SELECT COUNT(*) FROM cargo_fingerprints
                WHERE victim_alliance_id = %s
            """, (alliance["id"],))
            has_cargo = cur.fetchone()

        result.append({
            **alliance,
            "has_industry_data": has_industry[0] > 0 if has_industry else False,
            "has_cargo_data": has_cargo[0] > 0 if has_cargo else False
        })

    return result


@router.get("/{alliance_id}")
def get_supply_chain_report(alliance_id: int) -> Dict[str, Any]:
    """Get complete supply chain intelligence for an alliance."""
    _check_availability()

    # Find alliance info
    alliance = next((a for a in TRACKED_ALLIANCES if a["id"] == alliance_id), None)
    if not alliance:
        alliance = {"id": alliance_id, "name": f"Alliance-{alliance_id}", "ticker": "???"}

    try:
        industry = gen_industry(alliance_id)
        logistics = gen_logistics(alliance_id)
        cargo = gen_cargo(alliance_id)

        return {
            "alliance": alliance,
            "generated_at": datetime.now().isoformat(),
            "industry": industry,
            "logistics": logistics,
            "cargo": cargo
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{alliance_id}/industry")
def get_industry_profile(alliance_id: int) -> Dict[str, Any]:
    """Get industry cost index profile for an alliance."""
    _check_availability()
    try:
        return gen_industry(alliance_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{alliance_id}/logistics")
def get_logistics_profile(alliance_id: int) -> Dict[str, Any]:
    """Get logistics route profile for an alliance."""
    _check_availability()
    try:
        return gen_logistics(alliance_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{alliance_id}/cargo")
def get_cargo_profile(alliance_id: int) -> Dict[str, Any]:
    """Get cargo fingerprint profile for an alliance."""
    _check_availability()
    try:
        return gen_cargo(alliance_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/surges/manufacturing")
def get_manufacturing_surges() -> List[Dict[str, Any]]:
    """Get systems with manufacturing activity surges."""
    _check_availability()
    analyzer = IndustryIndexAnalyzer()
    return analyzer.detect_surges(threshold_percent=150)


@router.get("/cargo/recent")
def get_recent_cargo_kills(request: Request, limit: int = 20) -> List[Dict[str, Any]]:
    """Get recent cargo-analyzed hauler kills."""
    _check_availability()
    db = request.app.state.db

    with db.cursor() as cur:
        cur.execute("""
            SELECT
                cf.killmail_id,
                cf.killmail_time,
                cf.solar_system_id,
                cf.victim_alliance_id,
                cf.ship_type_id,
                cf.ship_value,
                cf.primary_category,
                cf.confidence,
                cf.total_cargo_value,
                cf.mission_assessment,
                t."typeName" as ship_name,
                ms."solarSystemName" as system_name
            FROM cargo_fingerprints cf
            LEFT JOIN "invTypes" t ON cf.ship_type_id = t."typeID"
            LEFT JOIN "mapSolarSystems" ms ON cf.solar_system_id = ms."solarSystemID"
            ORDER BY cf.killmail_time DESC
            LIMIT %s
        """, (limit,))
        rows = cur.fetchall()

    return [
        {
            "killmail_id": row[0],
            "killmail_time": row[1].isoformat() if row[1] else None,
            "solar_system_id": row[2],
            "victim_alliance_id": row[3],
            "ship_type_id": row[4],
            "ship_value": row[5],
            "primary_category": row[6],
            "confidence": float(row[7]) if row[7] else 0,
            "total_cargo_value": row[8],
            "mission_assessment": row[9],
            "ship_name": row[10],
            "system_name": row[11]
        }
        for row in rows
    ]


@router.get("/midpoints/all")
def get_all_midpoints(request: Request) -> List[Dict[str, Any]]:
    """Get all identified logistics midpoints."""
    _check_availability()
    db = request.app.state.db

    with db.cursor() as cur:
        cur.execute("""
            SELECT
                lm.solar_system_id,
                lm.alliance_id,
                lm.cyno_deaths_30d,
                lm.hauler_deaths_30d,
                lm.confidence_score,
                lm.last_activity,
                ms."solarSystemName" as system_name,
                ms.security
            FROM logistics_midpoints lm
            LEFT JOIN "mapSolarSystems" ms ON lm.solar_system_id = ms."solarSystemID"
            WHERE lm.confidence_score > 0.3
            ORDER BY lm.cyno_deaths_30d DESC
            LIMIT 50
        """)
        rows = cur.fetchall()

    return [
        {
            "solar_system_id": row[0],
            "alliance_id": row[1],
            "cyno_deaths": row[2],
            "hauler_deaths": row[3],
            "confidence": float(row[4]) if row[4] else 0,
            "last_activity": row[5].isoformat() if row[5] else None,
            "system_name": row[6],
            "security": float(row[7]) if row[7] else 0
        }
        for row in rows
    ]
