"""
Alliance Doctrine Fingerprints Router

API endpoints for accessing alliance ship usage patterns and doctrine fingerprints.
Data is derived from killmail analysis showing which ships each alliance commonly uses.

Endpoints:
1. GET /fingerprints/ - List fingerprints with filtering
2. GET /fingerprints/{alliance_id} - Get single alliance fingerprint
3. GET /fingerprints/coalitions/list - List coalitions with member counts
4. GET /fingerprints/doctrines/distribution - Doctrine type distribution
"""

from datetime import datetime
from typing import Optional, List
import logging

from fastapi import APIRouter, HTTPException, Query
from pydantic import Field

from app.models.base import CamelModel
from app.database import db_cursor
from eve_shared.utils.error_handling import handle_endpoint_errors
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/fingerprints", tags=["fingerprints"])


# ============================================================
# Pydantic Models
# ============================================================

class ShipUsage(CamelModel):
    """Ship usage entry in fingerprint."""
    type_id: int
    type_name: str
    ship_class: str
    uses: int
    percentage: float


class AllianceFingerprint(CamelModel):
    """Alliance doctrine fingerprint model."""
    alliance_id: int
    alliance_name: Optional[str] = None
    total_uses: int = 0
    unique_ships: int = 0
    primary_doctrine: Optional[str] = None
    coalition_id: Optional[int] = None
    coalition_leader_name: Optional[str] = None
    ship_fingerprint: List[ShipUsage] = []
    data_period_days: int = 30
    last_updated: Optional[datetime] = None
    created_at: Optional[datetime] = None


class FingerprintListResponse(CamelModel):
    """Response model for GET /fingerprints/."""
    fingerprints: List[AllianceFingerprint]
    total: int


class CoalitionMember(CamelModel):
    """Alliance member of a coalition."""
    alliance_id: int
    alliance_name: Optional[str] = None
    total_uses: int = 0
    primary_doctrine: Optional[str] = None


class CoalitionSummary(CamelModel):
    """Coalition summary with member alliances."""
    coalition_id: int
    leader_name: str
    member_count: int = 0
    total_ship_uses: int = 0
    primary_doctrines: List[str] = []
    members: List[CoalitionMember] = []


class DoctrineDistribution(CamelModel):
    """Doctrine type distribution entry."""
    doctrine: str
    alliances: int
    total_ships: int


class DoctrineDistributionResponse(CamelModel):
    """Response model for GET /fingerprints/doctrines/distribution."""
    distribution: List[DoctrineDistribution]


class CoalitionListResponse(CamelModel):
    """Response model for GET /fingerprints/coalitions/list."""
    coalitions: List[CoalitionSummary]
    total: int


# ============================================================
# Helper Functions
# ============================================================

def _parse_ship_fingerprint(fingerprint_data) -> List[ShipUsage]:
    """Parse JSONB ship fingerprint into ShipUsage list."""
    if not fingerprint_data:
        return []

    result = []
    for entry in fingerprint_data:
        try:
            result.append(ShipUsage(
                type_id=entry.get("type_id", 0),
                type_name=entry.get("type_name", "Unknown"),
                ship_class=entry.get("ship_class", "Unknown"),
                uses=entry.get("uses", 0),
                percentage=entry.get("percentage", 0.0)
            ))
        except Exception as e:
            logger.warning(f"Failed to parse ship fingerprint entry: {entry}, error: {e}")

    return result


def _row_to_fingerprint(row) -> AllianceFingerprint:
    """Convert database row to AllianceFingerprint model."""
    return AllianceFingerprint(
        alliance_id=row["alliance_id"],
        alliance_name=row.get("alliance_name"),
        total_uses=row.get("total_uses", 0),
        unique_ships=row.get("unique_ships", 0),
        primary_doctrine=row.get("primary_doctrine"),
        coalition_id=row.get("coalition_id"),
        coalition_leader_name=row.get("coalition_leader_name"),
        ship_fingerprint=_parse_ship_fingerprint(row.get("ship_fingerprint")),
        data_period_days=row.get("data_period_days", 30),
        last_updated=row.get("last_updated"),
        created_at=row.get("created_at")
    )


# ============================================================
# Endpoint 1: GET /fingerprints/ - List fingerprints
# ============================================================

@router.get("/", response_model=FingerprintListResponse)
@handle_endpoint_errors()
def list_fingerprints(
    limit: int = Query(50, ge=1, le=500, description="Maximum number of fingerprints to return"),
    offset: int = Query(0, ge=0, description="Number of fingerprints to skip"),
    doctrine: Optional[str] = Query(None, description="Filter by primary doctrine type"),
    coalition_id: Optional[int] = Query(None, description="Filter by coalition ID"),
    search: Optional[str] = Query(None, description="Search by alliance name"),
    min_activity: Optional[int] = Query(None, description="Minimum total_uses threshold")
):
    """
    List all alliance doctrine fingerprints with filtering and pagination.

    Query Parameters:
    - limit: Maximum results (1-500, default 50)
    - offset: Skip N results (default 0)
    - doctrine: Filter by primary doctrine type (e.g., "HAC Fleet", "Battleship Fleet")
    - coalition_id: Filter by coalition ID (leader alliance_id)
    - search: Search alliance names (case-insensitive partial match)
    - min_activity: Minimum total_uses threshold
    """
    with db_cursor() as cur:
        # Build dynamic query
        conditions = []
        params = []

        if doctrine is not None:
            conditions.append("primary_doctrine = %s")
            params.append(doctrine)

        if coalition_id is not None:
            conditions.append("coalition_id = %s")
            params.append(coalition_id)

        if search is not None:
            conditions.append("alliance_name ILIKE %s")
            params.append(f"%{search}%")

        if min_activity is not None:
            conditions.append("total_uses >= %s")
            params.append(min_activity)

        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

        # Get total count
        count_where = where_clause.replace('primary_doctrine', 'f.primary_doctrine').replace('coalition_id', 'f.coalition_id').replace('alliance_name', 'f.alliance_name').replace('total_uses', 'f.total_uses')
        count_query = f"SELECT COUNT(*) as cnt FROM alliance_doctrine_fingerprints f {count_where}"
        cur.execute(count_query, params)
        total = cur.fetchone()["cnt"]

        # Get fingerprints with coalition leader name
        query = f"""
            SELECT
                f.alliance_id, f.alliance_name, f.total_uses, f.unique_ships,
                f.ship_fingerprint, f.primary_doctrine, f.coalition_id,
                f.data_period_days, f.last_updated, f.created_at,
                leader.alliance_name as coalition_leader_name
            FROM alliance_doctrine_fingerprints f
            LEFT JOIN alliance_doctrine_fingerprints leader ON f.coalition_id = leader.alliance_id
            {where_clause.replace('primary_doctrine', 'f.primary_doctrine').replace('coalition_id', 'f.coalition_id').replace('alliance_name', 'f.alliance_name').replace('total_uses', 'f.total_uses')}
            ORDER BY f.total_uses DESC, f.alliance_name ASC
            LIMIT %s OFFSET %s
        """
        params.extend([limit, offset])
        cur.execute(query, params)

        rows = cur.fetchall()
        fingerprints = [_row_to_fingerprint(row) for row in rows]

        return FingerprintListResponse(fingerprints=fingerprints, total=total)


# ============================================================
# Endpoint 2: GET /fingerprints/{alliance_id} - Get single fingerprint
# ============================================================

@router.get("/{alliance_id}", response_model=AllianceFingerprint)
@handle_endpoint_errors()
def get_fingerprint(alliance_id: int):
    """Get detailed fingerprint for a specific alliance."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT
                f.alliance_id, f.alliance_name, f.total_uses, f.unique_ships,
                f.ship_fingerprint, f.primary_doctrine, f.coalition_id,
                f.data_period_days, f.last_updated, f.created_at,
                leader.alliance_name as coalition_leader_name
            FROM alliance_doctrine_fingerprints f
            LEFT JOIN alliance_doctrine_fingerprints leader ON f.coalition_id = leader.alliance_id
            WHERE f.alliance_id = %s
        """, (alliance_id,))

        row = cur.fetchone()

        if not row:
            raise HTTPException(
                status_code=404,
                detail=f"Fingerprint for alliance {alliance_id} not found"
            )

        return _row_to_fingerprint(row)


# ============================================================
# Endpoint 3: GET /fingerprints/coalitions/list - List coalitions
# ============================================================

@router.get("/coalitions/list", response_model=CoalitionListResponse)
@handle_endpoint_errors()
def list_coalitions(
    min_members: int = Query(2, ge=1, description="Minimum number of members to include coalition")
):
    """
    List all coalitions (Power Blocs) with their member alliances.

    Coalition membership is determined by fights_together / fights_against ratio:
    - Alliances must fight TOGETHER at least 3x more than AGAINST each other
    - This correctly separates enemy blocs (e.g., Imperium vs PandaFam)

    Query Parameters:
    - min_members: Minimum members required (default 2)
    """
    from app.routers.war.utils import get_coalition_memberships

    # Get correct coalition memberships using friend/enemy ratio logic
    memberships = get_coalition_memberships()

    # Group alliances by coalition leader
    coalitions_map = {}  # leader_id -> list of member_ids
    for alliance_id, leader_id in memberships.items():
        if leader_id not in coalitions_map:
            coalitions_map[leader_id] = []
        coalitions_map[leader_id].append(alliance_id)

    # Filter by min_members
    coalitions_map = {
        leader: members
        for leader, members in coalitions_map.items()
        if len(members) >= min_members
    }

    with db_cursor() as cur:
        # Get all alliance data we need
        all_alliance_ids = list(set(
            aid for members in coalitions_map.values() for aid in members
        ))

        if not all_alliance_ids:
            return CoalitionListResponse(coalitions=[], total=0)

        placeholders = ','.join(['%s'] * len(all_alliance_ids))
        cur.execute(f"""
            SELECT
                alliance_id, alliance_name, total_uses, primary_doctrine
            FROM alliance_doctrine_fingerprints
            WHERE alliance_id IN ({placeholders})
        """, all_alliance_ids)

        alliance_data = {row["alliance_id"]: row for row in cur.fetchall()}

        # Also get names from cache for alliances not in fingerprints
        cur.execute(f"""
            SELECT alliance_id, alliance_name, ticker
            FROM alliance_name_cache
            WHERE alliance_id IN ({placeholders})
        """, all_alliance_ids)
        name_cache = {row["alliance_id"]: row for row in cur.fetchall()}

        coalitions = []
        for leader_id, member_ids in coalitions_map.items():
            # Get leader name
            leader_data = alliance_data.get(leader_id) or name_cache.get(leader_id)
            leader_name = (
                leader_data.get("alliance_name") if leader_data
                else f"Coalition {leader_id}"
            )

            # Build member list
            members = []
            total_uses = 0
            doctrines = set()

            for mid in sorted(member_ids, key=lambda x: alliance_data.get(x, {}).get("total_uses", 0), reverse=True):
                m_data = alliance_data.get(mid)
                m_name = name_cache.get(mid)

                if m_data:
                    members.append(CoalitionMember(
                        alliance_id=mid,
                        alliance_name=m_data.get("alliance_name") or (m_name.get("alliance_name") if m_name else f"Alliance {mid}"),
                        total_uses=m_data.get("total_uses", 0),
                        primary_doctrine=m_data.get("primary_doctrine")
                    ))
                    total_uses += m_data.get("total_uses", 0)
                    if m_data.get("primary_doctrine"):
                        doctrines.add(m_data["primary_doctrine"])
                elif m_name:
                    members.append(CoalitionMember(
                        alliance_id=mid,
                        alliance_name=m_name.get("alliance_name", f"Alliance {mid}"),
                        total_uses=0,
                        primary_doctrine=None
                    ))

            coalitions.append(CoalitionSummary(
                coalition_id=leader_id,
                leader_name=leader_name,
                member_count=len(members),
                total_ship_uses=total_uses,
                primary_doctrines=list(doctrines)[:5],
                members=members
            ))

        # Sort by total activity
        coalitions.sort(key=lambda c: c.total_ship_uses, reverse=True)

        return CoalitionListResponse(coalitions=coalitions, total=len(coalitions))


# ============================================================
# Endpoint 4: GET /fingerprints/doctrines/distribution - Doctrine distribution
# ============================================================

@router.get("/doctrines/distribution", response_model=DoctrineDistributionResponse)
@handle_endpoint_errors()
def get_doctrine_distribution():
    """
    Get distribution of doctrine types across all alliances.

    Returns count of alliances and total ships used for each doctrine type.
    """
    with db_cursor() as cur:
        cur.execute("""
            SELECT
                COALESCE(primary_doctrine, 'Unknown') as doctrine,
                COUNT(DISTINCT alliance_id) as alliances,
                SUM(total_uses) as total_ships
            FROM alliance_doctrine_fingerprints
            GROUP BY COALESCE(primary_doctrine, 'Unknown')
            ORDER BY alliances DESC, total_ships DESC
        """)

        rows = cur.fetchall()
        distribution = [
            DoctrineDistribution(
                doctrine=row["doctrine"],
                alliances=row["alliances"],
                total_ships=row["total_ships"] or 0
            )
            for row in rows
        ]

        return DoctrineDistributionResponse(distribution=distribution)
