"""PI Requirements endpoint — shows PI materials needed for an item."""

import logging
from typing import Optional

from fastapi import APIRouter, Request, HTTPException

from app.services.chains import ProductionChainService
from app.routers.pi._helpers import (
    PISchematicService,
    MarketPriceAdapter,
    P0_PLANET_MAP,
)
from app.services.pi.repository import PIRepository
from eve_shared.constants import JITA_REGION_ID
from eve_shared.utils.error_handling import handle_endpoint_errors

logger = logging.getLogger(__name__)

router = APIRouter()
PI_CATEGORY_ID = 43


def _get_pi_type_ids(db, type_ids: list[int]) -> dict[int, dict]:
    """Identify which type_ids are PI materials (categoryID=43).

    Returns dict of type_id → {type_name, group_name, tier}.
    """
    if not type_ids:
        return {}

    with db.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT t."typeID", t."typeName", g."groupName"
                FROM "invTypes" t
                JOIN "invGroups" g ON t."groupID" = g."groupID"
                JOIN "invCategories" c ON g."categoryID" = c."categoryID"
                WHERE c."categoryID" = %s AND t."typeID" = ANY(%s)
                """,
                (PI_CATEGORY_ID, list(type_ids)),
            )
            results = {}
            for row in cur.fetchall():
                type_id, type_name, group_name = row[0], row[1], row[2]
                tier = _parse_tier(group_name)
                results[type_id] = {
                    "type_name": type_name,
                    "group_name": group_name,
                    "tier": tier,
                }
            return results


def _parse_tier(group_name: str) -> int:
    """Parse PI tier from SDE group name.

    Group names: 'Basic Commodities - Tier 1',
    'Refined Commodities - Tier 2', etc.
    """
    if not group_name:
        return -1
    gn = group_name.lower()
    if "tier 1" in gn or "basic" in gn:
        return 1
    if "tier 2" in gn or "refined" in gn:
        return 2
    if "tier 3" in gn or "specialized" in gn:
        return 3
    if "tier 4" in gn or "advanced" in gn:
        return 4
    return -1


def _chain_node_to_dict(node, p0_planet_map: dict) -> dict:
    """Convert PIChainNode to response dict with planet_sources on P0."""
    result = {
        "type_id": node.type_id,
        "type_name": node.type_name,
        "tier": node.tier,
        "quantity_needed": node.quantity_needed,
        "children": [_chain_node_to_dict(c, p0_planet_map) for c in node.children],
    }
    if node.tier == 0:
        result["planet_sources"] = p0_planet_map.get(node.type_name, [])
    return result


@router.get("/pi-requirements/{type_id}")
@handle_endpoint_errors()
def get_pi_requirements(type_id: int, request: Request):
    """Get PI materials required to manufacture an item.

    Walks the full production chain to leaf materials, identifies which
    are Planetary Commodities (categoryID=43), and returns their costs
    and PI production chains.
    """
    db = request.app.state.db

    # Build production chain and flatten to leaf materials
    chain_service = ProductionChainService(db)
    flat_result = chain_service.get_chain_tree(type_id, quantity=1, format="flat")

    if "error" in flat_result:
        raise HTTPException(status_code=404, detail=flat_result["error"])

    materials = flat_result.get("materials", [])
    if not materials:
        return {
            "type_id": type_id,
            "type_name": flat_result.get("name", "Unknown"),
            "pi_materials": [],
            "total_pi_cost": 0.0,
            "total_production_cost": 0.0,
            "pi_cost_percentage": 0.0,
        }

    # Identify which leaf materials are PI
    leaf_type_ids = [m["type_id"] for m in materials]
    pi_types = _get_pi_type_ids(db, leaf_type_ids)

    if not pi_types:
        return {
            "type_id": type_id,
            "type_name": flat_result.get("name", "Unknown"),
            "pi_materials": [],
            "total_pi_cost": 0.0,
            "total_production_cost": 0.0,
            "pi_cost_percentage": 0.0,
        }

    # Get prices for all leaf materials (PI and non-PI)
    market = MarketPriceAdapter(db)
    all_prices = {}
    for m in materials:
        price = market.get_price(m["type_id"], JITA_REGION_ID)
        all_prices[m["type_id"]] = price or 0.0

    # Build PI material details with chains
    pi_repo = PIRepository(db)
    pi_schematic_service = PISchematicService(pi_repo)

    pi_materials = []
    total_pi_cost = 0.0
    total_production_cost = 0.0

    # Aggregate P0 materials across all PI chains
    p0_aggregate: dict[int, dict] = {}

    for m in materials:
        tid = m["type_id"]
        qty = m["quantity"]
        price = all_prices.get(tid, 0.0)
        mat_cost = price * qty
        total_production_cost += mat_cost

        if tid not in pi_types:
            continue

        pi_info = pi_types[tid]
        total_pi_cost += mat_cost

        # Get PI production chain
        chain = pi_schematic_service.get_production_chain(tid, quantity=qty)
        chain_dict = _chain_node_to_dict(chain, P0_PLANET_MAP) if chain else None

        # Get flat P0 inputs
        p0_inputs = pi_schematic_service.get_flat_inputs(tid, quantity=qty)
        for p0 in p0_inputs:
            p0_id = p0["type_id"]
            if p0_id in p0_aggregate:
                p0_aggregate[p0_id]["quantity"] += p0["quantity"]
            else:
                p0_aggregate[p0_id] = {
                    "type_id": p0_id,
                    "type_name": p0["type_name"],
                    "quantity": p0["quantity"],
                    "planet_sources": P0_PLANET_MAP.get(p0["type_name"], []),
                }

        pi_materials.append({
            "type_id": tid,
            "type_name": pi_info["type_name"],
            "tier": pi_info["tier"],
            "quantity": qty,
            "unit_price": price,
            "total_cost": mat_cost,
            "pi_chain": chain_dict,
        })

    # Sort PI materials by tier descending, then by total_cost descending
    pi_materials.sort(key=lambda x: (-x["tier"], -x["total_cost"]))

    pi_pct = (total_pi_cost / total_production_cost * 100) if total_production_cost > 0 else 0.0

    return {
        "type_id": type_id,
        "type_name": flat_result.get("name", "Unknown"),
        "pi_materials": pi_materials,
        "p0_summary": sorted(p0_aggregate.values(), key=lambda x: -x["quantity"]),
        "total_pi_cost": round(total_pi_cost, 2),
        "total_production_cost": round(total_production_cost, 2),
        "pi_cost_percentage": round(pi_pct, 1),
    }
