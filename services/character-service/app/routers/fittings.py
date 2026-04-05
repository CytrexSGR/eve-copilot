# routers/fittings.py
"""Fitting analysis REST API.
Migrated from monolith to character-service.
Extended with combined stats + custom fitting CRUD.
"""

import json
from fastapi import APIRouter, HTTPException, Query, Request
from typing import List, Optional
from pydantic import BaseModel

from psycopg2.extras import RealDictCursor

from app.services.fitting_service import (
    FittingService,
    ESIFitting,
    FittingAnalysis,
    FittingItem,
)
from app.services.fitting_stats import (
    FittingStatsService,
    FittingStatsRequest,
    FittingStatsResponse,
)

router = APIRouter()


# --- Custom fitting models ---

class CustomFittingCreate(BaseModel):
    name: str
    description: str = ""
    ship_type_id: int
    items: List[FittingItem]
    charges: dict = {}  # flag → charge_type_id
    tags: List[str] = []
    is_public: bool = False
    creator_character_id: int


class CustomFittingUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    items: Optional[List[FittingItem]] = None
    charges: Optional[dict] = None
    tags: Optional[List[str]] = None
    is_public: Optional[bool] = None


class CustomFitting(BaseModel):
    id: int
    creator_character_id: int
    name: str
    description: str
    ship_type_id: int
    ship_name: str = ""
    items: List[FittingItem]
    charges: dict = {}
    tags: List[str]
    is_public: bool
    created_at: str
    updated_at: str


# --- Combined stats endpoint ---

@router.post(
    "/stats",
    response_model=FittingStatsResponse,
    summary="Get combined fitting stats",
    description="Calculate DPS, EHP, PG/CPU usage, slot counts for a fitting.",
)
def get_fitting_stats(request: Request, req: FittingStatsRequest) -> FittingStatsResponse:
    """Calculate combined fitting stats."""
    service = FittingStatsService(request.app.state.db, request.app.state.redis)
    return service.calculate_stats(req)


# --- Custom fitting CRUD ---

@router.post(
    "/save",
    response_model=CustomFitting,
    summary="Save custom fitting",
    description="Save a user-created fitting.",
)
def save_fitting(request: Request, fitting: CustomFittingCreate) -> CustomFitting:
    """Save a custom fitting."""
    db = request.app.state.db

    items_json = json.dumps([i.model_dump() for i in fitting.items])
    charges_json = json.dumps(fitting.charges)

    with db.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            INSERT INTO custom_fittings
            (creator_character_id, name, description, ship_type_id, items, charges, tags, is_public)
            VALUES (%s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s)
            RETURNING id, creator_character_id, name, description, ship_type_id,
                      items, charges, tags, is_public, created_at, updated_at
        """, (
            fitting.creator_character_id,
            fitting.name,
            fitting.description,
            fitting.ship_type_id,
            items_json,
            charges_json,
            fitting.tags,
            fitting.is_public,
        ))
        row = cur.fetchone()

    return _row_to_custom_fitting(row, db)


@router.put(
    "/custom/{fitting_id}",
    response_model=CustomFitting,
    summary="Update custom fitting",
)
def update_fitting(
    request: Request,
    fitting_id: int,
    update: CustomFittingUpdate,
) -> CustomFitting:
    """Update a custom fitting."""
    db = request.app.state.db

    # Build SET clause dynamically
    set_parts = []
    params = []

    if update.name is not None:
        set_parts.append("name = %s")
        params.append(update.name)
    if update.description is not None:
        set_parts.append("description = %s")
        params.append(update.description)
    if update.items is not None:
        set_parts.append("items = %s::jsonb")
        params.append(json.dumps([i.model_dump() for i in update.items]))
    if update.charges is not None:
        set_parts.append("charges = %s::jsonb")
        params.append(json.dumps(update.charges))
    if update.tags is not None:
        set_parts.append("tags = %s")
        params.append(update.tags)
    if update.is_public is not None:
        set_parts.append("is_public = %s")
        params.append(update.is_public)

    if not set_parts:
        raise HTTPException(status_code=400, detail="No fields to update")

    set_parts.append("updated_at = NOW()")
    params.append(fitting_id)

    with db.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(f"""
            UPDATE custom_fittings
            SET {', '.join(set_parts)}
            WHERE id = %s
            RETURNING id, creator_character_id, name, description, ship_type_id,
                      items, charges, tags, is_public, created_at, updated_at
        """, params)
        row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Fitting not found")

    return _row_to_custom_fitting(row, db)


@router.delete(
    "/custom/{fitting_id}",
    summary="Delete custom fitting",
)
def delete_fitting(request: Request, fitting_id: int):
    """Delete a custom fitting."""
    db = request.app.state.db

    with db.cursor() as cur:
        cur.execute("DELETE FROM custom_fittings WHERE id = %s", (fitting_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Fitting not found")

    return {"deleted": True, "id": fitting_id}


@router.get(
    "/custom/{character_id}",
    response_model=List[CustomFitting],
    summary="Get character's custom fittings",
)
def get_custom_fittings(
    request: Request,
    character_id: int,
    ship_type_id: Optional[int] = Query(None),
) -> List[CustomFitting]:
    """Get all custom fittings for a character."""
    db = request.app.state.db

    conditions = ["creator_character_id = %s"]
    params = [character_id]

    if ship_type_id:
        conditions.append("ship_type_id = %s")
        params.append(ship_type_id)

    where = " AND ".join(conditions)

    with db.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(f"""
            SELECT id, creator_character_id, name, description, ship_type_id,
                   items, charges, tags, is_public, created_at, updated_at
            FROM custom_fittings
            WHERE {where}
            ORDER BY updated_at DESC
        """, params)
        rows = cur.fetchall()

    return [_row_to_custom_fitting(r, db) for r in rows]


@router.get(
    "/shared",
    response_model=List[CustomFitting],
    summary="Browse shared fittings",
)
def get_shared_fittings(
    request: Request,
    ship_type_id: Optional[int] = Query(None),
    tag: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> List[CustomFitting]:
    """Browse public shared fittings."""
    db = request.app.state.db

    conditions = ["is_public = TRUE"]
    params = {}

    if ship_type_id:
        conditions.append("ship_type_id = %(ship_type_id)s")
        params["ship_type_id"] = ship_type_id

    if tag:
        conditions.append("%(tag)s = ANY(tags)")
        params["tag"] = tag

    if search:
        conditions.append("name ILIKE %(search)s")
        params["search"] = f"%{search}%"

    where = " AND ".join(conditions)
    params["limit"] = limit
    params["offset"] = offset

    with db.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(f"""
            SELECT id, creator_character_id, name, description, ship_type_id,
                   items, charges, tags, is_public, created_at, updated_at
            FROM custom_fittings
            WHERE {where}
            ORDER BY updated_at DESC
            LIMIT %(limit)s OFFSET %(offset)s
        """, params)
        rows = cur.fetchall()

    return [_row_to_custom_fitting(r, db) for r in rows]


@router.get(
    "/detail/{fitting_id}",
    response_model=CustomFitting,
    summary="Get single custom fitting by ID",
)
def get_fitting_by_id(request: Request, fitting_id: int) -> CustomFitting:
    """Get a single custom fitting by its database ID."""
    db = request.app.state.db

    with db.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT id, creator_character_id, name, description, ship_type_id,
                   items, charges, tags, is_public, created_at, updated_at
            FROM custom_fittings
            WHERE id = %s
        """, (fitting_id,))
        row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Fitting not found")

    return _row_to_custom_fitting(row, db)


# --- Fit comparison ---

class CompareRequest(BaseModel):
    fittings: List[FittingStatsRequest]  # 2-4 fittings to compare


@router.post("/compare")
def compare_fittings(req: CompareRequest, request: Request):
    """Compare 2-4 fittings side by side."""
    if len(req.fittings) < 2 or len(req.fittings) > 4:
        raise HTTPException(status_code=400, detail="2-4 fittings required for comparison")

    service = FittingStatsService(request.app.state.db, request.app.state.redis)
    results = []
    for fitting_req in req.fittings:
        stats = service.calculate_stats(fitting_req)
        results.append(stats.model_dump())
    return {"comparisons": results}


# --- Fleet boost endpoints ---

@router.get("/boost-presets", summary="Get fleet boost presets")
def get_boost_presets():
    """Return pre-built fleet boost presets (e.g., shield_t2_max, armor_t2_max)."""
    from app.services.fitting_stats.fleet_boosts import BOOST_PRESETS, BUFF_DEFINITIONS
    result = {}
    for name, boosts in BOOST_PRESETS.items():
        result[name] = [
            {
                "buff_id": b["buff_id"],
                "value": b["value"],
                "name": BUFF_DEFINITIONS[b["buff_id"]]["name"],
            }
            for b in boosts
        ]
    return result


@router.get("/projected-presets", summary="Get projected effect presets")
def get_projected_presets():
    """Return pre-built projected effect presets (e.g., single_web, double_web)."""
    from app.services.fitting_stats.projected import PROJECTED_PRESETS
    return PROJECTED_PRESETS


@router.get("/boost-definitions", summary="Get all fleet boost buff definitions")
def get_boost_definitions():
    """Return all available fleet boost buff definitions with attribute mappings."""
    from app.services.fitting_stats.fleet_boosts import BUFF_DEFINITIONS
    return {str(k): {"buff_id": k, **v} for k, v in BUFF_DEFINITIONS.items()}


# --- Existing ESI fitting endpoints ---

@router.get(
    "/{character_id}",
    response_model=List[ESIFitting],
    summary="Get character fittings",
    description="Fetch all saved fittings for a character from ESI."
)
def get_fittings(request: Request, character_id: int) -> List[ESIFitting]:
    """Get all fittings for character."""
    service = FittingService(request.app.state.db, request.app.state.redis)
    return service.get_character_fittings(character_id)


@router.get(
    "/{character_id}/{fitting_id}/analyze",
    response_model=FittingAnalysis,
    summary="Analyze fitting",
    description="Analyze a specific fitting for DPS calculation."
)
def analyze_fitting(
    request: Request,
    character_id: int,
    fitting_id: int,
    ammo_id: int = Query(..., description="Ammunition type ID"),
    active_modules: Optional[str] = Query(None, description="Comma-separated active module type IDs")
) -> FittingAnalysis:
    """Analyze a specific fitting."""
    service = FittingService(request.app.state.db, request.app.state.redis)

    active = []
    if active_modules:
        active = [int(x.strip()) for x in active_modules.split(',')]

    result = service.analyze_fitting_by_id(
        character_id=character_id,
        fitting_id=fitting_id,
        ammo_type_id=ammo_id,
        active_modules=active,
    )

    if not result:
        raise HTTPException(status_code=404, detail="Fitting not found")

    return result


@router.post(
    "/analyze",
    response_model=FittingAnalysis,
    summary="Analyze custom fitting",
    description="Analyze a custom fitting without saving."
)
def analyze_custom_fitting(
    request: Request,
    fitting: ESIFitting,
    character_id: int = Query(..., description="Character ID for skill checks"),
    ammo_id: int = Query(..., description="Ammunition type ID"),
    active_modules: Optional[str] = Query(None, description="Comma-separated active module type IDs")
) -> FittingAnalysis:
    """Analyze a custom fitting."""
    service = FittingService(request.app.state.db, request.app.state.redis)

    active = []
    if active_modules:
        active = [int(x.strip()) for x in active_modules.split(',')]

    return service.analyze_fitting(
        fitting=fitting,
        character_id=character_id,
        ammo_type_id=ammo_id,
        active_modules=active,
    )


# --- Helpers ---

def _row_to_custom_fitting(row: dict, db) -> CustomFitting:
    """Convert DB row to CustomFitting model."""
    items_data = row["items"]
    if isinstance(items_data, str):
        items_data = json.loads(items_data)

    items = [FittingItem(**i) for i in items_data]

    charges_data = row.get("charges") or {}
    if isinstance(charges_data, str):
        charges_data = json.loads(charges_data)
    charges = {int(k): v for k, v in charges_data.items()} if charges_data else {}

    # Resolve ship name
    ship_name = ""
    with db.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            'SELECT "typeName" FROM "invTypes" WHERE "typeID" = %s',
            (row["ship_type_id"],)
        )
        ship_row = cur.fetchone()
        if ship_row:
            ship_name = ship_row["typeName"]

    return CustomFitting(
        id=row["id"],
        creator_character_id=row["creator_character_id"],
        name=row["name"],
        description=row["description"] or "",
        ship_type_id=row["ship_type_id"],
        ship_name=ship_name,
        items=items,
        charges=charges,
        tags=row["tags"] or [],
        is_public=row["is_public"],
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )
