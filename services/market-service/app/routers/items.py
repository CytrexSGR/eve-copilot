"""
Items router - Item search, groups, materials, regions, routes, cargo, and systems endpoints.
Migrated from monolith to market-service.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from eve_shared.constants import TRADE_HUB_REGIONS, TRADE_HUB_SYSTEMS

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Items & Catalog"])

# Alias for backward compatibility (used throughout this file)
REGIONS = TRADE_HUB_REGIONS


class CargoItem(BaseModel):
    """Single item for cargo calculation."""
    type_id: int
    quantity: int


class CargoCalculateRequest(BaseModel):
    """Request body for cargo calculation."""
    items: List[CargoItem]


def get_item_info(type_id: int, db) -> Optional[dict]:
    """Get item info from database."""
    with db.cursor() as cur:
        cur.execute('''
            SELECT t."typeID", t."typeName", t."description", t."volume", t."mass",
                   g."groupID", g."groupName", c."categoryID", c."categoryName",
                   t."marketGroupID"
            FROM "invTypes" t
            JOIN "invGroups" g ON t."groupID" = g."groupID"
            JOIN "invCategories" c ON g."categoryID" = c."categoryID"
            WHERE t."typeID" = %s
        ''', (type_id,))
        row = cur.fetchone()
        if row:
            return {
                "typeID": row['typeID'],
                "typeName": row['typeName'],
                "description": row['description'],
                "volume": float(row['volume']) if row['volume'] else 0,
                "mass": float(row['mass']) if row['mass'] else 0,
                "groupID": row['groupID'],
                "groupName": row['groupName'],
                "categoryID": row['categoryID'],
                "categoryName": row['categoryName'],
                "marketGroupID": row['marketGroupID']
            }
        return None


def get_item_by_name(q: str, db, group_id: Optional[int] = None, market_group_id: Optional[int] = None) -> List[dict]:
    """Search items by name."""
    with db.cursor() as cur:
        where_clauses = ["t.\"published\" = 1"]
        params = []

        if q:
            where_clauses.append("t.\"typeName\" ILIKE %s")
            params.append(f"%{q}%")

        if group_id:
            where_clauses.append("t.\"groupID\" = %s")
            params.append(group_id)

        if market_group_id:
            where_clauses.append("t.\"marketGroupID\" = %s")
            params.append(market_group_id)

        cur.execute(f'''
            SELECT t."typeID", t."typeName", g."groupName"
            FROM "invTypes" t
            JOIN "invGroups" g ON t."groupID" = g."groupID"
            WHERE {" AND ".join(where_clauses)}
            ORDER BY t."typeName"
            LIMIT 100
        ''', params)

        return [{"typeID": row['typeID'], "typeName": row['typeName'], "groupName": row['groupName']} for row in cur.fetchall()]


def get_group_by_name(q: str, db) -> List[dict]:
    """Search groups by name."""
    with db.cursor() as cur:
        cur.execute('''
            SELECT g."groupID", g."groupName", c."categoryName"
            FROM "invGroups" g
            JOIN "invCategories" c ON g."categoryID" = c."categoryID"
            WHERE g."groupName" ILIKE %s AND g."published" = 1
            ORDER BY g."groupName"
            LIMIT 50
        ''', (f"%{q}%",))
        return [{"groupID": row['groupID'], "groupName": row['groupName'], "categoryName": row['categoryName']} for row in cur.fetchall()]


def get_material_composition(type_id: int, db) -> List[dict]:
    """Get manufacturing materials for an item."""
    with db.cursor() as cur:
        cur.execute('''
            SELECT m."materialTypeID", t."typeName", m."quantity"
            FROM "industryActivityMaterials" m
            JOIN "invTypes" t ON m."materialTypeID" = t."typeID"
            WHERE m."typeID" = %s AND m."activityID" = 1
            ORDER BY m."quantity" DESC
        ''', (type_id,))
        return [
            {"material_type_id": row['materialTypeID'], "material_name": row['typeName'], "quantity": row['quantity']}
            for row in cur.fetchall()
        ]


# ============================================================
# Items & Groups
# ============================================================

@router.get("/api/items/search")
def api_item_search(
    request: Request,
    q: str = Query("", min_length=0),
    group_id: Optional[int] = Query(None),
    market_group_id: Optional[int] = Query(None)
):
    """Search for items by name, optionally filtered by inventory group or market group"""
    if not q and not group_id and not market_group_id:
        raise HTTPException(status_code=422, detail="Either 'q' (min 2 chars), 'group_id', or 'market_group_id' must be provided")
    if q and len(q) < 2 and not group_id and not market_group_id:
        raise HTTPException(status_code=422, detail="Search query must be at least 2 characters")

    db = request.app.state.db
    items = get_item_by_name(q, db, group_id=group_id, market_group_id=market_group_id)
    return {"query": q, "results": items, "count": len(items)}


@router.get("/api/items/{type_id}")
def api_item_info(request: Request, type_id: int):
    """Get item information by typeID"""
    db = request.app.state.db
    item = get_item_info(type_id, db)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@router.get("/api/groups/search")
def api_group_search(request: Request, q: str = Query(..., min_length=2)):
    """Search for item groups by name"""
    db = request.app.state.db
    groups = get_group_by_name(q, db)
    return {"query": q, "results": groups, "count": len(groups)}


@router.get("/api/regions")
def api_regions():
    """Get list of known regions"""
    return REGIONS


# ============================================================
# Materials
# ============================================================

@router.get("/api/materials/{type_id}/composition")
def api_material_composition(request: Request, type_id: int):
    """Get manufacturing composition for an item"""
    db = request.app.state.db
    composition = get_material_composition(type_id, db)
    item = get_item_info(type_id, db)
    return {
        "type_id": type_id,
        "item_name": item["typeName"] if item else f"Type {type_id}",
        "is_craftable": len(composition) > 0,
        "materials": [
            {"type_id": m["material_type_id"], "name": m["material_name"], "quantity": m["quantity"]}
            for m in composition
        ]
    }


@router.get("/api/materials/{type_id}/volumes")
def api_material_volumes(request: Request, type_id: int):
    """Get available volumes for a material across all trade hub regions"""
    db = request.app.state.db
    item = get_item_info(type_id, db)

    # Get market repository
    from app.services import UnifiedMarketRepository, ESIClient
    redis = request.app.state.redis
    esi = ESIClient()
    repo = UnifiedMarketRepository(redis.client, db, esi)

    volumes = {}
    for region_name, region_id in REGIONS.items():
        try:
            price = repo.get_price(type_id, region_id)
            if price:
                volumes[region_name] = {
                    "sell_volume": price.sell_volume,
                    "lowest_sell": price.sell_price,
                    "lowest_sell_volume": price.sell_volume,
                    "sell_orders": 0,  # Not available in simplified model
                    "buy_volume": price.buy_volume,
                    "highest_buy": price.buy_price,
                }
            else:
                volumes[region_name] = {
                    "sell_volume": 0,
                    "lowest_sell": None,
                    "lowest_sell_volume": 0,
                    "sell_orders": 0,
                    "buy_volume": 0,
                    "highest_buy": None,
                }
        except Exception as e:
            logger.error(f"Error getting volume for {type_id} in {region_name}: {e}")
            volumes[region_name] = {
                "sell_volume": 0,
                "lowest_sell": None,
                "lowest_sell_volume": 0,
                "sell_orders": 0,
                "buy_volume": 0,
                "highest_buy": None,
            }

    best_availability = max(
        [(r, v["sell_volume"]) for r, v in volumes.items()],
        key=lambda x: x[1], default=(None, 0)
    )
    return {
        "type_id": type_id,
        "item_name": item["typeName"] if item else f"Type {type_id}",
        "volumes_by_region": volumes,
        "best_availability_region": best_availability[0],
        "best_availability_volume": best_availability[1]
    }


# ============================================================
# Routes & Navigation
# ============================================================

def get_system_by_name(name: str, db) -> Optional[dict]:
    """Get system info by name."""
    with db.cursor() as cur:
        cur.execute('''
            SELECT "solarSystemID", "solarSystemName", "security"
            FROM "mapSolarSystems"
            WHERE LOWER("solarSystemName") = LOWER(%s)
        ''', (name,))
        row = cur.fetchone()
        if row:
            return {"system_id": row['solarSystemID'], "system_name": row['solarSystemName'], "security": float(row['security']) if row['security'] else 0}
        return None


def search_systems(q: str, db, limit: int = 10) -> List[dict]:
    """Search solar systems by name."""
    with db.cursor() as cur:
        cur.execute('''
            SELECT "solarSystemID", "solarSystemName", "security"
            FROM "mapSolarSystems"
            WHERE "solarSystemName" ILIKE %s
            ORDER BY "solarSystemName"
            LIMIT %s
        ''', (f"%{q}%", limit))
        return [
            {"system_id": row['solarSystemID'], "system_name": row['solarSystemName'], "security": float(row['security']) if row['security'] else 0}
            for row in cur.fetchall()
        ]


@router.get("/api/route/hubs")
def api_get_trade_hubs(request: Request):
    """Get list of known trade hub systems"""
    db = request.app.state.db
    result = {}
    for name, sys_id in TRADE_HUB_SYSTEMS.items():
        sys_info = get_system_by_name(name, db) or {}
        result[name] = {
            'system_id': sys_id,
            'system_name': sys_info.get('system_name', name.capitalize()),
            'security': sys_info.get('security', 0)
        }
    return result


@router.get("/api/route/distances/{from_system}")
def api_hub_distances(request: Request, from_system: str = "isikemi"):
    """Get distances from a system to all trade hubs"""
    # Simplified - would need full route calculation implementation
    return {"message": "Route calculation not yet implemented in market-service"}


@router.get("/api/route/{from_system}/{to_system}")
def api_calculate_route(
    request: Request,
    from_system: str,
    to_system: str,
    highsec_only: bool = Query(True)
):
    """Calculate route between two systems using A* pathfinding"""
    # Simplified - would need full route calculation implementation
    db = request.app.state.db
    from_sys = get_system_by_name(from_system, db)
    to_sys = get_system_by_name(to_system, db)

    if not from_sys:
        raise HTTPException(status_code=404, detail=f"System not found: {from_system}")
    if not to_sys:
        raise HTTPException(status_code=404, detail=f"System not found: {to_system}")

    return {
        "from": from_sys,
        "to": to_sys,
        "message": "Full route calculation not yet implemented in market-service",
        "highsec_only": highsec_only
    }


@router.get("/api/systems/search")
def api_search_systems(request: Request, q: str = Query(..., min_length=2)):
    """Search for solar systems by name"""
    db = request.app.state.db
    results = search_systems(q, db, limit=10)
    return {"query": q, "results": results}


# ============================================================
# Cargo & Logistics
# ============================================================

def get_item_volume(type_id: int, db) -> Optional[float]:
    """Get item volume from database."""
    with db.cursor() as cur:
        cur.execute('''
            SELECT "volume" FROM "invTypes" WHERE "typeID" = %s
        ''', (type_id,))
        row = cur.fetchone()
        return float(row['volume']) if row and row['volume'] else None


def format_volume(volume: float) -> str:
    """Format volume with appropriate units."""
    if volume >= 1000000:
        return f"{volume / 1000000:.2f} million m³"
    elif volume >= 1000:
        return f"{volume / 1000:.2f}k m³"
    else:
        return f"{volume:.2f} m³"


def calculate_cargo_volume(items: List[CargoItem], db) -> dict:
    """Calculate total cargo volume for items."""
    total_volume = 0
    item_details = []

    for item in items:
        volume = get_item_volume(item.type_id, db)
        if volume:
            item_volume = volume * item.quantity
            total_volume += item_volume
            item_details.append({
                "type_id": item.type_id,
                "quantity": item.quantity,
                "unit_volume": volume,
                "total_volume": item_volume
            })

    return {
        "total_volume_m3": total_volume,
        "formatted_volume": format_volume(total_volume),
        "item_count": len(items),
        "items": item_details
    }


def recommend_ship(volume: float) -> dict:
    """Recommend ship based on cargo volume."""
    ships = [
        {"name": "Venture", "cargo": 50, "type": "frigate"},
        {"name": "Heron", "cargo": 400, "type": "frigate"},
        {"name": "Tayra", "cargo": 4250, "type": "industrial"},
        {"name": "Badger", "cargo": 3900, "type": "industrial"},
        {"name": "Mammoth", "cargo": 5850, "type": "industrial"},
        {"name": "Occator", "cargo": 62500, "type": "deep_space_transport"},
        {"name": "Charon", "cargo": 435000, "type": "freighter"},
    ]

    for ship in ships:
        if volume <= ship["cargo"]:
            return ship

    return {"name": "Jump Freighter", "cargo": 320000, "type": "jump_freighter", "note": "Consider splitting load"}


@router.post("/api/cargo/calculate")
def api_calculate_cargo(request: Request, cargo_request: CargoCalculateRequest):
    """Calculate total cargo volume for a list of items"""
    db = request.app.state.db
    volume_info = calculate_cargo_volume(cargo_request.items, db)
    ship_recommendation = recommend_ship(volume_info['total_volume_m3'])
    return {**volume_info, 'ship_recommendation': ship_recommendation}


@router.get("/api/cargo/item/{type_id}")
def api_item_volume(request: Request, type_id: int, quantity: int = Query(1)):
    """Get volume for a single item"""
    db = request.app.state.db
    volume = get_item_volume(type_id, db)
    if volume is None:
        raise HTTPException(status_code=404, detail="Item not found or has no volume")
    total = volume * quantity
    return {
        'type_id': type_id,
        'quantity': quantity,
        'unit_volume': volume,
        'total_volume': total,
        'formatted': format_volume(total)
    }
