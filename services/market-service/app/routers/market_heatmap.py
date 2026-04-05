"""
Price Heatmap Router - Compare prices across trade hubs.
Migrated from monolith to market-service.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from app.services import UnifiedMarketRepository, ESIClient
from eve_shared.constants import JITA_REGION_ID

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/market/heatmap", tags=["Market Heatmap"])

# Trade hub display names -> region IDs
TRADE_HUBS = {
    "Jita": 10000002,
    "Amarr": 10000043,
    "Dodixie": 10000032,
    "Rens": 10000030,
    "Hek": 10000042,
}


class HeatmapItem(BaseModel):
    type_id: int
    type_name: str
    prices: dict  # hub_name -> price


class HeatmapResponse(BaseModel):
    items: List[HeatmapItem]
    hubs: List[str] = ["Jita", "Amarr", "Dodixie", "Rens", "Hek"]


def _get_market_repo(request: Request) -> UnifiedMarketRepository:
    """Get market repository from app state."""
    db = request.app.state.db
    redis = request.app.state.redis
    esi_client = ESIClient()
    return UnifiedMarketRepository(redis.client, db, esi_client)


def _get_type_names(type_ids: List[int], db) -> dict:
    """Get type names from SDE."""
    if not type_ids:
        return {}

    with db.cursor() as cur:
        cur.execute('''
            SELECT "typeID", "typeName"
            FROM "invTypes"
            WHERE "typeID" = ANY(%s)
        ''', (type_ids,))
        return {row['typeID']: row['typeName'] for row in cur.fetchall()}


@router.get("", response_model=HeatmapResponse)
def get_price_heatmap(
    request: Request,
    type_ids: str = Query(..., description="Comma-separated type IDs")
):
    """
    Get prices for items across all trade hubs.

    Args:
        type_ids: Comma-separated list of type IDs (e.g., "34,35,36")

    Returns:
        HeatmapResponse with prices per hub
    """
    try:
        ids = [int(x.strip()) for x in type_ids.split(",") if x.strip()]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid type_ids format")

    if not ids:
        raise HTTPException(status_code=400, detail="No type IDs provided")

    if len(ids) > 50:
        raise HTTPException(status_code=400, detail="Max 50 items per request")

    db = request.app.state.db
    repo = _get_market_repo(request)
    type_names = _get_type_names(ids, db)

    items = []
    for type_id in ids:
        prices = {}
        for hub_name, region_id in TRADE_HUBS.items():
            try:
                price = repo.get_price(type_id, region_id)
                if price and price.sell_price:
                    prices[hub_name] = round(price.sell_price, 2)
                else:
                    prices[hub_name] = None
            except Exception:
                prices[hub_name] = None

        items.append(HeatmapItem(
            type_id=type_id,
            type_name=type_names.get(type_id, f"Type {type_id}"),
            prices=prices
        ))

    return HeatmapResponse(items=items)


@router.get("/category/{category_id}", response_model=HeatmapResponse)
def get_category_heatmap(
    request: Request,
    category_id: int,
    limit: int = Query(20, ge=1, le=50)
):
    """
    Get prices for items in a category across all trade hubs.

    Args:
        category_id: EVE category ID (e.g., 4 for Materials)
        limit: Max items to return

    Returns:
        HeatmapResponse with prices per hub
    """
    db = request.app.state.db

    # Get type IDs from category
    with db.cursor() as cur:
        cur.execute('''
            SELECT t."typeID", t."typeName"
            FROM "invTypes" t
            JOIN "invGroups" g ON t."groupID" = g."groupID"
            WHERE g."categoryID" = %s
              AND t."published" = 1
              AND t."marketGroupID" IS NOT NULL
            ORDER BY t."typeName"
            LIMIT %s
        ''', (category_id, limit))
        rows = cur.fetchall()

    if not rows:
        raise HTTPException(status_code=404, detail="Category not found or empty")

    repo = _get_market_repo(request)

    items = []
    for row in rows:
        type_id = row['typeID']
        type_name = row['typeName']
        prices = {}
        for hub_name, region_id in TRADE_HUBS.items():
            try:
                price = repo.get_price(type_id, region_id)
                if price and price.sell_price:
                    prices[hub_name] = round(price.sell_price, 2)
                else:
                    prices[hub_name] = None
            except Exception:
                prices[hub_name] = None

        items.append(HeatmapItem(
            type_id=type_id,
            type_name=type_name,
            prices=prices
        ))

    return HeatmapResponse(items=items)


def _get_character_token(character_id: int) -> str:
    """Get valid access token for character from auth service."""
    import httpx
    from app.config import settings

    auth_url = getattr(settings, 'auth_service_url', 'http://localhost:8001')
    with httpx.Client(base_url=auth_url, timeout=10.0) as client:
        response = client.get(f"/api/auth/token/{character_id}")
        if response.status_code != 200:
            raise Exception(f"Failed to get token: {response.status_code}")
        data = response.json()
        return data.get("access_token")


def _get_character_orders_from_esi(character_id: int, token: str) -> List[dict]:
    """Get market orders for a character via ESI."""
    import httpx

    headers = {"Authorization": f"Bearer {token}"}
    with httpx.Client(timeout=30.0) as client:
        response = client.get(
            f"https://esi.evetech.net/latest/characters/{character_id}/orders/",
            headers=headers
        )
        if response.status_code != 200:
            logger.warning(f"ESI orders failed: {response.status_code}")
            return []
        return response.json()


@router.get("/portfolio/{character_id}", response_model=HeatmapResponse)
def get_portfolio_heatmap(
    request: Request,
    character_id: int,
    limit: int = Query(20, ge=1, le=50)
):
    """
    Get prices for items the character is trading (from active orders).

    Args:
        character_id: EVE character ID
        limit: Max items to return

    Returns:
        HeatmapResponse with prices per hub
    """
    db = request.app.state.db

    try:
        # Get token from auth service
        token = _get_character_token(character_id)

        # Fetch orders from ESI
        esi_orders = _get_character_orders_from_esi(character_id, token)

        if not esi_orders:
            return HeatmapResponse(items=[])

        # Get unique type IDs from orders
        type_ids = list(set(order.get('type_id') for order in esi_orders if order.get('type_id')))[:limit]

        if not type_ids:
            return HeatmapResponse(items=[])

        type_names = _get_type_names(type_ids, db)
        repo = _get_market_repo(request)

        items = []
        for type_id in type_ids:
            prices = {}
            for hub_name, region_id in TRADE_HUBS.items():
                try:
                    price = repo.get_price(type_id, region_id)
                    if price and price.sell_price:
                        prices[hub_name] = round(price.sell_price, 2)
                    else:
                        prices[hub_name] = None
                except Exception:
                    prices[hub_name] = None

            items.append(HeatmapItem(
                type_id=type_id,
                type_name=type_names.get(type_id, f"Type {type_id}"),
                prices=prices
            ))

        return HeatmapResponse(items=items)

    except Exception as e:
        logger.warning(f"Could not get portfolio for {character_id}: {e}")
        # Return empty response if auth/ESI not available
        return HeatmapResponse(items=[])
