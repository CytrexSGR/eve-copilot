"""
Doctrine Detection Router (War Intel Service Version)

API endpoints for accessing detected doctrines from DBSCAN clustering.
Provides access to doctrine templates and their derived items of interest.

Endpoints:
1. GET /economy/doctrines - List all detected doctrines
2. GET /economy/doctrines/{id} - Get doctrine details
3. GET /economy/doctrines/{id}/items - Get items of interest
4. GET /economy/doctrines/{id}/items/materials - Get items with production materials
5. POST /economy/doctrines/{id}/rename - Manual labeling
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
import logging

from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import Field

from app.models.base import CamelModel
from app.database import db_cursor
from eve_shared.utils.error_handling import handle_endpoint_errors
logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================
# Pydantic Models
# ============================================================

class DoctrineTemplate(CamelModel):
    """Doctrine template model."""
    id: int
    doctrine_name: Optional[str] = None
    alliance_id: Optional[int] = None
    alliance_name: Optional[str] = None
    region_id: Optional[int] = None
    region_name: Optional[str] = None
    composition: Dict[str, float] = {}
    composition_with_names: List[Dict[str, Any]] = []
    confidence_score: float = 0.0
    observation_count: int = 0
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    total_pilots_avg: Optional[float] = None
    primary_doctrine_type: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ItemOfInterest(CamelModel):
    """Item of interest model."""
    id: int
    doctrine_id: int
    type_id: int
    item_name: Optional[str] = None
    item_category: str
    consumption_rate: Optional[float] = None
    priority: int = 0
    created_at: Optional[datetime] = None


class DoctrineListResponse(CamelModel):
    """Response model for GET /economy/doctrines."""
    doctrines: List[DoctrineTemplate]
    total: int


class ItemsListResponse(CamelModel):
    """Response model for GET /economy/doctrines/{id}/items."""
    items: List[ItemOfInterest]


class RenameRequest(CamelModel):
    """Request model for POST /economy/doctrines/{id}/rename."""
    doctrine_name: str = Field(..., min_length=1, max_length=100)


class ProductionMaterial(CamelModel):
    """Material needed for production."""
    type_id: int
    type_name: str
    quantity: int


class ItemWithMaterials(CamelModel):
    """Doctrine item with its production materials."""
    id: int
    doctrine_id: int
    type_id: int
    item_name: str
    item_category: str
    consumption_rate: Optional[float]
    priority: int
    materials: List[ProductionMaterial]
    blueprint_id: Optional[int] = None
    blueprint_name: Optional[str] = None
    produced_quantity: int = 1


class ItemsMaterialsResponse(CamelModel):
    """Response model for GET /economy/doctrines/{id}/items/materials."""
    items: List[ItemWithMaterials]
    total_materials: Dict[int, ProductionMaterial]


# ============================================================
# Helper Functions
# ============================================================

def _enrich_doctrine_with_names(doctrine: DoctrineTemplate) -> DoctrineTemplate:
    """Enrich doctrine with ship names, region name, and alliance name."""
    with db_cursor() as cur:
        # Get ship names from SDE
        type_ids = [int(type_id) for type_id in doctrine.composition.keys()]

        if type_ids:
            placeholders = ','.join(['%s'] * len(type_ids))
            cur.execute(
                f'SELECT "typeID", "typeName" FROM "invTypes" WHERE "typeID" IN ({placeholders})',
                type_ids
            )
            type_names = {row["typeID"]: row["typeName"] for row in cur.fetchall()}
        else:
            type_names = {}

        # Build composition with names
        composition_with_names = [
            {
                "type_id": int(type_id),
                "type_name": type_names.get(int(type_id), f"Unknown Ship {type_id}"),
                "ratio": ratio
            }
            for type_id, ratio in doctrine.composition.items()
        ]

        # Sort by ratio descending
        composition_with_names.sort(key=lambda x: x["ratio"], reverse=True)
        doctrine.composition_with_names = composition_with_names

        # Get region name from SDE
        if doctrine.region_id:
            cur.execute(
                'SELECT "regionName" FROM "mapRegions" WHERE "regionID" = %s',
                (doctrine.region_id,)
            )
            row = cur.fetchone()
            if row:
                doctrine.region_name = row["regionName"]
            else:
                doctrine.region_name = f"Region {doctrine.region_id}"

    # Alliance name placeholder
    if doctrine.alliance_id:
        doctrine.alliance_name = f"Alliance {doctrine.alliance_id}"

    return doctrine


# ============================================================
# Endpoint 1: GET /economy/doctrines - List all doctrines
# ============================================================

@router.get("/economy/doctrines", response_model=DoctrineListResponse)
@handle_endpoint_errors()
def list_doctrines(
    limit: int = Query(50, ge=1, le=500, description="Maximum number of doctrines to return"),
    offset: int = Query(0, ge=0, description="Number of doctrines to skip"),
    region_id: Optional[int] = Query(None, description="Filter by region ID"),
    alliance_id: Optional[int] = Query(None, description="Filter by alliance ID"),
    doctrine_type: Optional[str] = Query(None, description="Filter by doctrine type (subcap, capital, supercap)"),
    since: Optional[str] = Query(None, description="Filter by last_seen timestamp (ISO format)")
):
    """
    List all detected doctrines with filtering and pagination.

    Query Parameters:
    - limit: Maximum results (1-500, default 50)
    - offset: Skip N results (default 0)
    - region_id: Filter by region
    - alliance_id: Filter by alliance
    - doctrine_type: Filter by type (subcap, capital, supercap)
    - since: Filter by last_seen timestamp (ISO format)
    """
    with db_cursor() as cur:
        # Build dynamic query
        conditions = []
        params = []

        if region_id is not None:
            conditions.append("region_id = %s")
            params.append(region_id)

        if alliance_id is not None:
            conditions.append("alliance_id = %s")
            params.append(alliance_id)

        if doctrine_type is not None:
            conditions.append("primary_doctrine_type = %s")
            params.append(doctrine_type)

        if since is not None:
            conditions.append("last_seen >= %s")
            params.append(since)

        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

        # Get total count
        count_query = f"SELECT COUNT(*) as cnt FROM doctrine_templates {where_clause}"
        cur.execute(count_query, params)
        total = cur.fetchone()["cnt"]

        # Get doctrines
        query = f"""
            SELECT
                id, doctrine_name, alliance_id, region_id,
                composition, confidence_score, observation_count,
                first_seen, last_seen, total_pilots_avg,
                primary_doctrine_type, created_at, updated_at
            FROM doctrine_templates
            {where_clause}
            ORDER BY last_seen DESC
            LIMIT %s OFFSET %s
        """
        params.extend([limit, offset])
        cur.execute(query, params)

        rows = cur.fetchall()

        doctrines = []
        for row in rows:
            doctrine = DoctrineTemplate(
                id=row["id"],
                doctrine_name=row["doctrine_name"],
                alliance_id=row["alliance_id"],
                region_id=row["region_id"],
                composition=row["composition"] or {},
                confidence_score=row["confidence_score"] or 0.0,
                observation_count=row["observation_count"] or 0,
                first_seen=row["first_seen"],
                last_seen=row["last_seen"],
                total_pilots_avg=row["total_pilots_avg"],
                primary_doctrine_type=row["primary_doctrine_type"],
                created_at=row["created_at"],
                updated_at=row["updated_at"]
            )
            # Enrich with names
            doctrine = _enrich_doctrine_with_names(doctrine)
            doctrines.append(doctrine)

        return DoctrineListResponse(doctrines=doctrines, total=total)

# ============================================================
# Endpoint 2: GET /economy/doctrines/{id} - Get doctrine details
# ============================================================

@router.get("/economy/doctrines/{doctrine_id}", response_model=DoctrineTemplate)
@handle_endpoint_errors()
def get_doctrine_by_id(doctrine_id: int):
    """Get detailed information about a specific doctrine."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT
                id, doctrine_name, alliance_id, region_id,
                composition, confidence_score, observation_count,
                first_seen, last_seen, total_pilots_avg,
                primary_doctrine_type, created_at, updated_at
            FROM doctrine_templates
            WHERE id = %s
        """, (doctrine_id,))

        row = cur.fetchone()

        if not row:
            raise HTTPException(
                status_code=404,
                detail=f"Doctrine {doctrine_id} not found"
            )

        doctrine = DoctrineTemplate(
            id=row["id"],
            doctrine_name=row["doctrine_name"],
            alliance_id=row["alliance_id"],
            region_id=row["region_id"],
            composition=row["composition"] or {},
            confidence_score=row["confidence_score"] or 0.0,
            observation_count=row["observation_count"] or 0,
            first_seen=row["first_seen"],
            last_seen=row["last_seen"],
            total_pilots_avg=row["total_pilots_avg"],
            primary_doctrine_type=row["primary_doctrine_type"],
            created_at=row["created_at"],
            updated_at=row["updated_at"]
        )

        # Enrich with names
        doctrine = _enrich_doctrine_with_names(doctrine)

        return doctrine

# ============================================================
# Endpoint 3: GET /economy/doctrines/{id}/items - Get items of interest
# ============================================================

@router.get("/economy/doctrines/{doctrine_id}/items", response_model=ItemsListResponse)
@handle_endpoint_errors()
def get_doctrine_items(doctrine_id: int):
    """Get all items of interest for a specific doctrine."""
    with db_cursor() as cur:
        # Verify doctrine exists
        cur.execute("SELECT id FROM doctrine_templates WHERE id = %s", (doctrine_id,))
        if not cur.fetchone():
            raise HTTPException(
                status_code=404,
                detail=f"Doctrine {doctrine_id} not found"
            )

        # Get items of interest
        cur.execute("""
            SELECT
                id, doctrine_id, type_id, item_name,
                item_category, consumption_rate, priority, created_at
            FROM doctrine_items_of_interest
            WHERE doctrine_id = %s
            ORDER BY priority ASC, item_category ASC
        """, (doctrine_id,))

        rows = cur.fetchall()

        items = []
        for row in rows:
            item = ItemOfInterest(
                id=row["id"],
                doctrine_id=row["doctrine_id"],
                type_id=row["type_id"],
                item_name=row["item_name"],
                item_category=row["item_category"],
                consumption_rate=row["consumption_rate"],
                priority=row["priority"],
                created_at=row["created_at"]
            )
            items.append(item)

        return ItemsListResponse(items=items)

# ============================================================
# Endpoint 3b: GET /economy/doctrines/{id}/items/materials
# ============================================================

@router.get("/economy/doctrines/{doctrine_id}/items/materials", response_model=ItemsMaterialsResponse)
@handle_endpoint_errors()
def get_doctrine_items_with_materials(doctrine_id: int):
    """Get all items of interest for a doctrine WITH their production materials."""
    with db_cursor() as cur:
        # Verify doctrine exists
        cur.execute("SELECT id FROM doctrine_templates WHERE id = %s", (doctrine_id,))
        if not cur.fetchone():
            raise HTTPException(
                status_code=404,
                detail=f"Doctrine {doctrine_id} not found"
            )

        # Get items of interest
        cur.execute("""
            SELECT
                id, doctrine_id, type_id, item_name,
                item_category, consumption_rate, priority, created_at
            FROM doctrine_items_of_interest
            WHERE doctrine_id = %s
            ORDER BY priority ASC, item_category ASC
        """, (doctrine_id,))

        rows = cur.fetchall()

        items_with_materials = []
        total_materials: Dict[int, ProductionMaterial] = {}

        for row in rows:
            item_type_id = row["type_id"]
            item_name = row["item_name"]

            # Find blueprint that produces this item
            cur.execute("""
                SELECT
                    bp."typeID" as blueprint_id,
                    t."typeName" as blueprint_name,
                    bp.quantity as produced_qty
                FROM "industryActivityProducts" bp
                JOIN "invTypes" t ON bp."typeID" = t."typeID"
                WHERE bp."productTypeID" = %s AND bp."activityID" = 1
                LIMIT 1
            """, (item_type_id,))

            bp_row = cur.fetchone()
            blueprint_id = None
            blueprint_name = None
            produced_qty = 1
            materials: List[ProductionMaterial] = []

            if bp_row:
                blueprint_id = bp_row["blueprint_id"]
                blueprint_name = bp_row["blueprint_name"]
                produced_qty = bp_row["produced_qty"] or 1

                # Get materials for this blueprint
                cur.execute("""
                    SELECT
                        m."materialTypeID" as material_type_id,
                        t."typeName" as material_name,
                        m.quantity
                    FROM "industryActivityMaterials" m
                    JOIN "invTypes" t ON m."materialTypeID" = t."typeID"
                    WHERE m."typeID" = %s AND m."activityID" = 1
                    ORDER BY m.quantity DESC
                """, (blueprint_id,))

                mat_rows = cur.fetchall()
                for mat_row in mat_rows:
                    mat = ProductionMaterial(
                        type_id=mat_row["material_type_id"],
                        type_name=mat_row["material_name"],
                        quantity=mat_row["quantity"]
                    )
                    materials.append(mat)

                    # Aggregate to total materials
                    if mat.type_id in total_materials:
                        total_materials[mat.type_id].quantity += mat.quantity
                    else:
                        total_materials[mat.type_id] = ProductionMaterial(
                            type_id=mat.type_id,
                            type_name=mat.type_name,
                            quantity=mat.quantity
                        )

            item_with_mats = ItemWithMaterials(
                id=row["id"],
                doctrine_id=row["doctrine_id"],
                type_id=item_type_id,
                item_name=item_name or f"Item {item_type_id}",
                item_category=row["item_category"],
                consumption_rate=row["consumption_rate"],
                priority=row["priority"],
                materials=materials,
                blueprint_id=blueprint_id,
                blueprint_name=blueprint_name,
                produced_quantity=produced_qty
            )
            items_with_materials.append(item_with_mats)

        return ItemsMaterialsResponse(
            items=items_with_materials,
            total_materials=total_materials
        )

# ============================================================
# Endpoint 4: POST /economy/doctrines/{id}/rename - Manual labeling
# ============================================================

@router.post("/economy/doctrines/{doctrine_id}/rename", response_model=DoctrineTemplate)
@handle_endpoint_errors()
def rename_doctrine(doctrine_id: int, request: RenameRequest):
    """Manually label a doctrine with a meaningful name."""
    # Validation
    if not request.doctrine_name or request.doctrine_name.strip() == "":
        raise HTTPException(
            status_code=400,
            detail="Doctrine name cannot be empty"
        )

    if len(request.doctrine_name) > 100:
        raise HTTPException(
            status_code=400,
            detail="Doctrine name cannot exceed 100 characters"
        )

    with db_cursor() as cur:
        # Verify doctrine exists
        cur.execute("SELECT id FROM doctrine_templates WHERE id = %s", (doctrine_id,))
        if not cur.fetchone():
            raise HTTPException(
                status_code=404,
                detail=f"Doctrine {doctrine_id} not found"
            )

        # Update doctrine name
        now = datetime.now()
        cur.execute("""
            UPDATE doctrine_templates
            SET doctrine_name = %s, updated_at = %s
            WHERE id = %s
        """, (request.doctrine_name.strip(), now, doctrine_id))

        # Return updated doctrine
        cur.execute("""
            SELECT
                id, doctrine_name, alliance_id, region_id,
                composition, confidence_score, observation_count,
                first_seen, last_seen, total_pilots_avg,
                primary_doctrine_type, created_at, updated_at
            FROM doctrine_templates
            WHERE id = %s
        """, (doctrine_id,))

        row = cur.fetchone()

        doctrine = DoctrineTemplate(
            id=row["id"],
            doctrine_name=row["doctrine_name"],
            alliance_id=row["alliance_id"],
            region_id=row["region_id"],
            composition=row["composition"] or {},
            confidence_score=row["confidence_score"] or 0.0,
            observation_count=row["observation_count"] or 0,
            first_seen=row["first_seen"],
            last_seen=row["last_seen"],
            total_pilots_avg=row["total_pilots_avg"],
            primary_doctrine_type=row["primary_doctrine_type"],
            created_at=row["created_at"],
            updated_at=row["updated_at"]
        )

        # Enrich with names
        doctrine = _enrich_doctrine_with_names(doctrine)

        return doctrine
