"""
Sovereignty Router - ADM Tracking and Cyno Jammer Intel

Provides endpoints for:
- Sovereignty structures (TCU, IHUB) from ESI
- ADM levels for nullsec systems
- Manual cyno jammer intel (not available via public ESI)
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List
import httpx
from fastapi import APIRouter, HTTPException, Query

from app.models.base import CamelModel
from app.database import db_cursor
from app.config import settings
from eve_shared.utils.error_handling import handle_endpoint_errors

logger = logging.getLogger(__name__)

router = APIRouter()

# Structure type IDs
STRUCTURE_TCU = 32226
STRUCTURE_IHUB = 32458

# ESI endpoint
ESI_SOV_STRUCTURES = "https://esi.evetech.net/latest/sovereignty/structures/"


# ==============================================================================
# Models
# ==============================================================================

class SystemADM(CamelModel):
    """ADM level for a system with metadata."""
    solar_system_id: int
    solar_system_name: str
    region_id: int
    region_name: str
    security_status: float
    alliance_id: int
    alliance_name: str
    adm_level: float
    vulnerable_start_time: Optional[datetime] = None
    vulnerable_end_time: Optional[datetime] = None


class ADMResponse(CamelModel):
    """Response for ADM levels."""
    systems: List[SystemADM]
    count: int
    region_id: Optional[int] = None


class ADMSummaryResponse(CamelModel):
    """Summary statistics for ADM levels."""
    total_systems: int
    alliances: int
    avg_adm: float
    low_adm_count: int
    high_adm_count: int


class CynoJammer(CamelModel):
    """Cyno jammer intel."""
    id: Optional[int] = None
    solar_system_id: int
    solar_system_name: Optional[str] = None
    region_id: Optional[int] = None
    region_name: Optional[str] = None
    alliance_id: Optional[int] = None
    alliance_name: Optional[str] = None
    reported_by: Optional[str] = None
    confirmed: bool = False
    notes: Optional[str] = None
    reported_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    last_verified: Optional[datetime] = None
    status: Optional[str] = None


class CynoJammerListResponse(CamelModel):
    """Response for cyno jammer list."""
    jammers: List[CynoJammer]
    count: int
    region_id: Optional[int] = None


class CynoJammerCreateRequest(CamelModel):
    """Request to add cyno jammer intel."""
    solar_system_id: int
    alliance_id: Optional[int] = None
    reported_by: Optional[str] = None
    notes: Optional[str] = None
    expires_at: Optional[datetime] = None


class JammedSystemsResponse(CamelModel):
    """List of system IDs with active cyno jammers."""
    system_ids: List[int]
    count: int


class UpdateResponse(CamelModel):
    """Response for update operations."""
    updated: int
    message: str


# ==============================================================================
# ESI Fetch
# ==============================================================================

async def fetch_sov_structures_from_esi() -> List[dict]:
    """Fetch sovereignty structures from ESI."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            ESI_SOV_STRUCTURES,
            headers={"User-Agent": "EVE-Copilot/1.0"},
            timeout=30.0
        )
        response.raise_for_status()
        return response.json()


# ==============================================================================
# ADM Endpoints
# ==============================================================================

@router.get("/structures/update", response_model=UpdateResponse)
@handle_endpoint_errors()
async def update_structures():
    """
    Manually trigger ESI update for sovereignty structures.
    """
    try:
        esi_data = await fetch_sov_structures_from_esi()

        with db_cursor() as cur:
            count = 0
            for item in esi_data:
                cur.execute("""
                    INSERT INTO sovereignty_structures
                        (alliance_id, solar_system_id, structure_type_id,
                         vulnerability_occupancy_level, vulnerable_start_time,
                         vulnerable_end_time, last_updated)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (solar_system_id, structure_type_id)
                    DO UPDATE SET
                        alliance_id = EXCLUDED.alliance_id,
                        vulnerability_occupancy_level = EXCLUDED.vulnerability_occupancy_level,
                        vulnerable_start_time = EXCLUDED.vulnerable_start_time,
                        vulnerable_end_time = EXCLUDED.vulnerable_end_time,
                        last_updated = NOW()
                """, (
                    item.get("alliance_id", 0),
                    item["solar_system_id"],
                    item["structure_type_id"],
                    item.get("vulnerability_occupancy_level"),
                    item.get("vulnerable_start_time"),
                    item.get("vulnerable_end_time"),
                ))
                count += 1

        logger.info(f"Updated {count} sovereignty structures from ESI")
        return UpdateResponse(updated=count, message=f"Updated {count} sovereignty structures")

    except httpx.HTTPError as e:
        logger.error(f"ESI request failed: {e}")
        raise HTTPException(status_code=502, detail=f"ESI request failed: {e}")


@router.get("/adm", response_model=ADMResponse)
def get_adm_levels(
    region_id: Optional[int] = Query(None, description="Filter by region ID")
):
    """
    Get ADM levels for all nullsec systems.

    ADM 1-2: Vulnerable (red), ADM 3-4: Medium (yellow), ADM 5-6: Strong (green)
    """
    with db_cursor() as cur:
        query = """
            SELECT
                solar_system_id, solar_system_name, region_id, region_name,
                security_status, alliance_id, alliance_name, adm_level,
                vulnerable_start_time, vulnerable_end_time
            FROM v_sovereignty_adm
            WHERE structure_type_id = %s
        """
        params = [STRUCTURE_IHUB]

        if region_id:
            query += " AND region_id = %s"
            params.append(region_id)

        query += " ORDER BY region_name, solar_system_name"

        cur.execute(query, params)
        rows = cur.fetchall()

        systems = [
            SystemADM(
                solar_system_id=row['solar_system_id'],
                solar_system_name=row['solar_system_name'] or "Unknown",
                region_id=row['region_id'] or 0,
                region_name=row['region_name'] or "Unknown",
                security_status=row['security_status'] or 0.0,
                alliance_id=row['alliance_id'] or 0,
                alliance_name=row['alliance_name'] or "Unknown",
                adm_level=row['adm_level'] or 1.0,
                vulnerable_start_time=row['vulnerable_start_time'],
                vulnerable_end_time=row['vulnerable_end_time'],
            )
            for row in rows
        ]

    return ADMResponse(systems=systems, count=len(systems), region_id=region_id)


@router.get("/adm/summary", response_model=ADMSummaryResponse)
def get_adm_summary():
    """Get summary statistics for ADM levels galaxy-wide."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT
                COUNT(*) as total_systems,
                COUNT(DISTINCT alliance_id) as alliances,
                AVG(adm_level) as avg_adm,
                COUNT(*) FILTER (WHERE adm_level <= 2) as low_adm,
                COUNT(*) FILTER (WHERE adm_level >= 5) as high_adm
            FROM v_sovereignty_adm
            WHERE structure_type_id = %s
        """, (STRUCTURE_IHUB,))

        row = cur.fetchone()

    return ADMSummaryResponse(
        total_systems=row['total_systems'] or 0,
        alliances=row['alliances'] or 0,
        avg_adm=round(row['avg_adm'] or 0, 2),
        low_adm_count=row['low_adm'] or 0,
        high_adm_count=row['high_adm'] or 0,
    )


@router.get("/adm/vulnerable", response_model=ADMResponse)
def get_vulnerable_systems(
    max_adm: float = Query(3.0, description="Maximum ADM level")
):
    """Get systems with low ADM (vulnerable to attack)."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT
                solar_system_id, solar_system_name, region_id, region_name,
                security_status, alliance_id, alliance_name, adm_level,
                vulnerable_start_time, vulnerable_end_time
            FROM v_sovereignty_adm
            WHERE structure_type_id = %s AND adm_level <= %s
            ORDER BY adm_level ASC, region_name, solar_system_name
        """, (STRUCTURE_IHUB, max_adm))

        rows = cur.fetchall()

        systems = [
            SystemADM(
                solar_system_id=row['solar_system_id'],
                solar_system_name=row['solar_system_name'] or "Unknown",
                region_id=row['region_id'] or 0,
                region_name=row['region_name'] or "Unknown",
                security_status=row['security_status'] or 0.0,
                alliance_id=row['alliance_id'] or 0,
                alliance_name=row['alliance_name'] or "Unknown",
                adm_level=row['adm_level'] or 1.0,
                vulnerable_start_time=row['vulnerable_start_time'],
                vulnerable_end_time=row['vulnerable_end_time'],
            )
            for row in rows
        ]

    return ADMResponse(systems=systems, count=len(systems), region_id=None)


# ==============================================================================
# Cyno Jammer Intel Endpoints
# ==============================================================================

@router.get("/cynojammers", response_model=CynoJammerListResponse)
def get_cyno_jammers(
    region_id: Optional[int] = Query(None, description="Filter by region ID"),
    include_expired: bool = Query(False, description="Include expired intel")
):
    """
    Get all cyno jammer intel.

    Note: Cyno jammers are not available via public ESI - this is manual intel.
    """
    with db_cursor() as cur:
        query = """
            SELECT id, solar_system_id, solar_system_name, region_id, region_name,
                   alliance_id, alliance_name, reported_by, confirmed, notes,
                   reported_at, expires_at, last_verified, status
            FROM v_cyno_jammers
            WHERE 1=1
        """
        params = []

        if region_id:
            query += " AND region_id = %s"
            params.append(region_id)

        if not include_expired:
            query += " AND status != 'expired'"

        query += " ORDER BY region_name, solar_system_name"

        cur.execute(query, params)
        rows = cur.fetchall()

        jammers = [
            CynoJammer(
                id=row['id'],
                solar_system_id=row['solar_system_id'],
                solar_system_name=row['solar_system_name'],
                region_id=row['region_id'],
                region_name=row['region_name'],
                alliance_id=row['alliance_id'],
                alliance_name=row['alliance_name'],
                reported_by=row['reported_by'],
                confirmed=row['confirmed'],
                notes=row['notes'],
                reported_at=row['reported_at'],
                expires_at=row['expires_at'],
                last_verified=row['last_verified'],
                status=row['status'],
            )
            for row in rows
        ]

    return CynoJammerListResponse(jammers=jammers, count=len(jammers), region_id=region_id)


@router.get("/cynojammers/systems", response_model=JammedSystemsResponse)
def get_jammed_systems():
    """Get list of system IDs with active cyno jammers (for map layer)."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT solar_system_id
            FROM v_cyno_jammers
            WHERE status != 'expired'
        """)
        system_ids = [row['solar_system_id'] for row in cur.fetchall()]

    return JammedSystemsResponse(system_ids=system_ids, count=len(system_ids))


@router.post("/cynojammers", response_model=CynoJammer)
def add_cyno_jammer(request: CynoJammerCreateRequest):
    """Report a cyno jammer in a system."""
    with db_cursor() as cur:
        cur.execute("""
            INSERT INTO intel_cyno_jammers
                (solar_system_id, alliance_id, reported_by, notes, expires_at, reported_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
            ON CONFLICT (solar_system_id)
            DO UPDATE SET
                alliance_id = COALESCE(EXCLUDED.alliance_id, intel_cyno_jammers.alliance_id),
                reported_by = COALESCE(EXCLUDED.reported_by, intel_cyno_jammers.reported_by),
                notes = COALESCE(EXCLUDED.notes, intel_cyno_jammers.notes),
                expires_at = COALESCE(EXCLUDED.expires_at, intel_cyno_jammers.expires_at),
                last_verified = NOW()
            RETURNING id
        """, (
            request.solar_system_id,
            request.alliance_id,
            request.reported_by,
            request.notes,
            request.expires_at,
        ))
        jammer_id = cur.fetchone()['id']

        # Fetch the created/updated jammer
        cur.execute("""
            SELECT id, solar_system_id, solar_system_name, region_id, region_name,
                   alliance_id, alliance_name, reported_by, confirmed, notes,
                   reported_at, expires_at, last_verified, status
            FROM v_cyno_jammers WHERE id = %s
        """, (jammer_id,))
        row = cur.fetchone()

    return CynoJammer(
        id=row['id'],
        solar_system_id=row['solar_system_id'],
        solar_system_name=row['solar_system_name'],
        region_id=row['region_id'],
        region_name=row['region_name'],
        alliance_id=row['alliance_id'],
        alliance_name=row['alliance_name'],
        reported_by=row['reported_by'],
        confirmed=row['confirmed'],
        notes=row['notes'],
        reported_at=row['reported_at'],
        expires_at=row['expires_at'],
        last_verified=row['last_verified'],
        status=row['status'],
    )


@router.put("/cynojammers/{jammer_id}/confirm", response_model=CynoJammer)
def confirm_cyno_jammer(jammer_id: int):
    """Confirm a cyno jammer intel report."""
    with db_cursor() as cur:
        cur.execute("""
            UPDATE intel_cyno_jammers
            SET confirmed = TRUE, last_verified = NOW()
            WHERE id = %s
            RETURNING id
        """, (jammer_id,))

        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Cyno jammer not found")

        cur.execute("""
            SELECT id, solar_system_id, solar_system_name, region_id, region_name,
                   alliance_id, alliance_name, reported_by, confirmed, notes,
                   reported_at, expires_at, last_verified, status
            FROM v_cyno_jammers WHERE id = %s
        """, (jammer_id,))
        row = cur.fetchone()

    return CynoJammer(
        id=row['id'],
        solar_system_id=row['solar_system_id'],
        solar_system_name=row['solar_system_name'],
        region_id=row['region_id'],
        region_name=row['region_name'],
        alliance_id=row['alliance_id'],
        alliance_name=row['alliance_name'],
        reported_by=row['reported_by'],
        confirmed=row['confirmed'],
        notes=row['notes'],
        reported_at=row['reported_at'],
        expires_at=row['expires_at'],
        last_verified=row['last_verified'],
        status=row['status'],
    )


@router.delete("/cynojammers/{jammer_id}")
def remove_cyno_jammer(jammer_id: int):
    """Remove cyno jammer intel (jammer was taken down)."""
    with db_cursor() as cur:
        cur.execute("DELETE FROM intel_cyno_jammers WHERE id = %s", (jammer_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Cyno jammer not found")

    return {"deleted": True, "jammer_id": jammer_id}
