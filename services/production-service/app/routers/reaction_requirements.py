"""Reaction Requirements endpoint — shows reaction materials needed for an item."""

import logging
import math

from fastapi import APIRouter, Request, HTTPException
from psycopg2.extras import RealDictCursor

from app.services.chains import ProductionChainService
from app.routers.pi._helpers import MarketPriceAdapter
from eve_shared.constants import JITA_REGION_ID
from eve_shared.utils.error_handling import handle_endpoint_errors

logger = logging.getLogger(__name__)

router = APIRouter()
MOON_GOO_GROUP_ID = 427


def _get_reaction_product_ids(db, type_ids: list[int]) -> dict[int, dict]:
    """Identify which type_ids are reaction products.

    Returns dict of type_id -> {type_name, reaction_category}.
    """
    if not type_ids:
        return {}

    with db.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT product_type_id, product_name, reaction_category
            FROM reaction_formulas
            WHERE product_type_id = ANY(%s)
        """, (list(type_ids),))
        results = {}
        for row in cur.fetchall():
            results[row['product_type_id']] = {
                'type_name': row['product_name'],
                'reaction_category': row['reaction_category'],
            }
        return results


def _load_all_reaction_products(db) -> dict[int, dict]:
    """Load all reaction products for chain-building lookups."""
    with db.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT product_type_id, product_name, reaction_category
            FROM reaction_formulas
        """)
        return {
            row['product_type_id']: {
                'type_name': row['product_name'],
                'reaction_category': row['reaction_category'],
            }
            for row in cur.fetchall()
        }


def _load_moon_goo_ids(db) -> set[int]:
    """Load all moon material type IDs (groupID=427)."""
    with db.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT DISTINCT rfi.input_type_id
            FROM reaction_formula_inputs rfi
            JOIN "invTypes" t ON rfi.input_type_id = t."typeID"
            JOIN "invGroups" g ON t."groupID" = g."groupID"
            WHERE g."groupID" = %s
        """, (MOON_GOO_GROUP_ID,))
        return {row['input_type_id'] for row in cur.fetchall()}


def _get_reaction_formula(db, product_type_id: int) -> dict | None:
    """Get reaction formula and its inputs for a product."""
    with db.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT reaction_type_id, reaction_name, product_type_id,
                   product_name, product_quantity, reaction_time, reaction_category
            FROM reaction_formulas
            WHERE product_type_id = %s
        """, (product_type_id,))
        formula = cur.fetchone()
        if not formula:
            return None

        cur.execute("""
            SELECT input_type_id, input_name, quantity
            FROM reaction_formula_inputs
            WHERE reaction_type_id = %s
            ORDER BY input_name
        """, (formula['reaction_type_id'],))
        formula['inputs'] = cur.fetchall()

        return dict(formula)


def _build_reaction_chain(
    db,
    product_type_id: int,
    quantity: int,
    all_reaction_products: dict,
    moon_goo_ids: set,
    visited: set | None = None,
) -> dict:
    """Build recursive reaction chain tree down to moon goo."""
    if visited is None:
        visited = set()

    if product_type_id in visited:
        return {
            'type_id': product_type_id,
            'type_name': all_reaction_products.get(product_type_id, {}).get('type_name', 'Unknown'),
            'quantity_needed': quantity,
            'is_reaction_product': True,
            'is_moon_goo': False,
            'children': [],
        }

    formula = _get_reaction_formula(db, product_type_id)
    if not formula:
        return {
            'type_id': product_type_id,
            'type_name': all_reaction_products.get(product_type_id, {}).get('type_name', 'Unknown'),
            'quantity_needed': quantity,
            'is_reaction_product': False,
            'is_moon_goo': product_type_id in moon_goo_ids,
            'children': [],
        }

    visited = visited | {product_type_id}

    runs_needed = math.ceil(quantity / formula['product_quantity'])

    children = []
    for inp in formula['inputs']:
        input_qty = inp['quantity'] * runs_needed
        input_type_id = inp['input_type_id']

        if input_type_id in all_reaction_products:
            child = _build_reaction_chain(
                db, input_type_id, input_qty,
                all_reaction_products, moon_goo_ids, visited,
            )
        else:
            child = {
                'type_id': input_type_id,
                'type_name': inp['input_name'],
                'quantity_needed': input_qty,
                'is_reaction_product': False,
                'is_moon_goo': input_type_id in moon_goo_ids,
                'children': [],
            }
        children.append(child)

    return {
        'type_id': product_type_id,
        'type_name': formula['product_name'],
        'reaction_type_id': formula['reaction_type_id'],
        'reaction_category': formula['reaction_category'],
        'quantity_needed': quantity,
        'runs_needed': runs_needed,
        'is_reaction_product': True,
        'is_moon_goo': False,
        'children': children,
    }


def _collect_moon_goo(node: dict, aggregate: dict):
    """Walk chain tree and aggregate moon goo quantities."""
    if node.get('is_moon_goo') and not node.get('children'):
        tid = node['type_id']
        if tid in aggregate:
            aggregate[tid]['quantity'] += node['quantity_needed']
        else:
            aggregate[tid] = {
                'type_id': tid,
                'type_name': node['type_name'],
                'quantity': node['quantity_needed'],
            }
    for child in node.get('children', []):
        _collect_moon_goo(child, aggregate)


@router.get("/reaction-requirements/{type_id}")
@handle_endpoint_errors()
def get_reaction_requirements(type_id: int, request: Request):
    """Get reaction materials required to manufacture an item.

    Walks the full production chain to leaf materials, identifies which
    are reaction products, and returns their costs and reaction chains
    down to moon goo.
    """
    db = request.app.state.db

    chain_service = ProductionChainService(db)
    flat_result = chain_service.get_chain_tree(type_id, quantity=1, format="flat")

    if "error" in flat_result:
        raise HTTPException(status_code=404, detail=flat_result["error"])

    materials = flat_result.get("materials", [])
    type_name = flat_result.get("name", "Unknown")
    empty_response = {
        "type_id": type_id,
        "type_name": type_name,
        "reaction_materials": [],
        "moon_goo_summary": [],
        "total_reaction_cost": 0.0,
        "total_production_cost": 0.0,
        "reaction_cost_percentage": 0.0,
    }

    if not materials:
        return empty_response

    leaf_type_ids = [m["type_id"] for m in materials]
    reaction_products = _get_reaction_product_ids(db, leaf_type_ids)

    if not reaction_products:
        return empty_response

    # Pre-load lookup tables for chain building
    all_reaction_products = _load_all_reaction_products(db)
    moon_goo_ids = _load_moon_goo_ids(db)

    # Get prices for all leaf materials
    market = MarketPriceAdapter(db)
    all_prices = {}
    for m in materials:
        price = market.get_price(m["type_id"], JITA_REGION_ID)
        all_prices[m["type_id"]] = price or 0.0

    reaction_materials = []
    total_reaction_cost = 0.0
    total_production_cost = 0.0
    moon_goo_aggregate: dict[int, dict] = {}

    for m in materials:
        tid = m["type_id"]
        qty = m["quantity"]
        price = all_prices.get(tid, 0.0)
        mat_cost = price * qty
        total_production_cost += mat_cost

        if tid not in reaction_products:
            continue

        total_reaction_cost += mat_cost

        chain = _build_reaction_chain(
            db, tid, qty, all_reaction_products, moon_goo_ids,
        )
        _collect_moon_goo(chain, moon_goo_aggregate)

        reaction_materials.append({
            "type_id": tid,
            "type_name": reaction_products[tid]["type_name"],
            "quantity": qty,
            "unit_price": price,
            "total_cost": mat_cost,
            "reaction_category": reaction_products[tid]["reaction_category"],
            "reaction_chain": chain,
        })

    reaction_materials.sort(key=lambda x: -x["total_cost"])

    pct = (total_reaction_cost / total_production_cost * 100) if total_production_cost > 0 else 0.0

    return {
        "type_id": type_id,
        "type_name": type_name,
        "reaction_materials": reaction_materials,
        "moon_goo_summary": sorted(moon_goo_aggregate.values(), key=lambda x: -x["quantity"]),
        "total_reaction_cost": round(total_reaction_cost, 2),
        "total_production_cost": round(total_production_cost, 2),
        "reaction_cost_percentage": round(pct, 1),
    }
