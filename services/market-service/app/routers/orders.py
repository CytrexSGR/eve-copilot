"""
Orders router - Multi-account order aggregation and management.
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from eve_shared.utils.error_handling import handle_endpoint_errors
from eve_shared.constants import JITA_REGION_ID

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/orders", tags=["Orders"])


# Pydantic Models

class MarketStatus(BaseModel):
    """Market status for an order (outbid/undercut detection)."""
    current_best_buy: float
    current_best_sell: float
    is_outbid: bool
    outbid_by: float
    spread_percent: float


class AggregatedOrder(BaseModel):
    """Single order with character info and market status."""
    order_id: int
    character_id: int
    character_name: str
    type_id: int
    type_name: str
    is_buy_order: bool
    price: float
    volume_remain: int
    volume_total: int
    location_name: str
    region_name: str
    issued: str
    duration: int
    market_status: MarketStatus


class CharacterOrderSummary(BaseModel):
    """Order summary for a single character."""
    character_id: int
    character_name: str
    buy_orders: int
    sell_orders: int
    order_slots_used: int
    order_slots_max: int
    isk_in_escrow: float
    isk_in_sell_orders: float


class AggregatedOrdersSummary(BaseModel):
    """Summary of all aggregated orders."""
    total_characters: int
    total_buy_orders: int
    total_sell_orders: int
    total_isk_in_buy_orders: float
    total_isk_in_sell_orders: float
    outbid_count: int
    undercut_count: int


class AggregatedOrdersResponse(BaseModel):
    """Response for aggregated orders endpoint."""
    summary: AggregatedOrdersSummary
    by_character: List[CharacterOrderSummary]
    orders: List[AggregatedOrder]
    generated_at: str


class OrdersService:
    """Service for multi-account order aggregation."""

    def __init__(self, db, redis):
        self.db = db
        self.redis = redis
        self._esi_client = None
        self._auth_client = None

    @property
    def esi_client(self):
        """Lazy-load ESI client."""
        if self._esi_client is None:
            from app.services.esi_client import ESIClient
            self._esi_client = ESIClient(redis_client=self.redis)
        return self._esi_client

    def _get_auth_client(self):
        """Get auth service client."""
        import httpx
        from app.config import settings
        return httpx.Client(base_url=settings.auth_service_url, timeout=10.0)

    def get_all_characters(self) -> List[Dict[str, Any]]:
        """Get all authenticated characters from auth service."""
        try:
            with self._get_auth_client() as client:
                response = client.get("/api/auth/characters")
                if response.status_code == 200:
                    data = response.json()
                    # API returns {"characters": [...]}
                    return data.get("characters", [])
                return []
        except Exception as e:
            logger.warning(f"Failed to get characters from auth service: {e}")
            return []

    def get_character_token(self, character_id: int) -> Optional[str]:
        """Get valid access token for character from auth service."""
        try:
            with self._get_auth_client() as client:
                response = client.get(f"/api/auth/token/{character_id}")
                if response.status_code == 200:
                    data = response.json()
                    return data.get("access_token")
                return None
        except Exception as e:
            logger.warning(f"Failed to get token for {character_id}: {e}")
            return None

    def get_character_orders(self, character_id: int, token: str) -> List[Dict]:
        """Get market orders for a character via ESI."""
        import httpx
        from app.config import settings

        try:
            with httpx.Client(timeout=settings.esi_timeout) as client:
                response = client.get(
                    f"{settings.esi_base_url}/characters/{character_id}/orders/",
                    headers={"Authorization": f"Bearer {token}"},
                    params={"datasource": "tranquility"}
                )
                if response.status_code == 200:
                    return response.json()
                return []
        except Exception as e:
            logger.warning(f"Failed to get orders for {character_id}: {e}")
            return []

    def get_market_stats(self, region_id: int, type_id: int) -> Dict[str, Any]:
        """Get market statistics for an item in a region."""
        return self.esi_client.get_market_stats(region_id, type_id)

    def get_item_name(self, type_id: int) -> str:
        """Get item name from database."""
        try:
            with self.db.cursor() as cur:
                cur.execute(
                    'SELECT "typeName" FROM "invTypes" WHERE "typeID" = %s',
                    (type_id,)
                )
                row = cur.fetchone()
                if row:
                    return row["typeName"]
        except Exception as e:
            logger.debug(f"Could not get item name for {type_id}: {e}")
        return f"Type {type_id}"

    def get_region_name(self, region_id: int) -> str:
        """Get region name from database."""
        try:
            with self.db.cursor() as cur:
                cur.execute(
                    'SELECT "regionName" FROM "mapRegions" WHERE "regionID" = %s',
                    (region_id,)
                )
                row = cur.fetchone()
                if row:
                    return row["regionName"]
        except Exception as e:
            logger.debug(f"Could not get region name for {region_id}: {e}")
        return f"Region {region_id}"

    def get_station_name(self, location_id: int) -> str:
        """Get station/structure name."""
        # Try NPC station first
        try:
            with self.db.cursor() as cur:
                cur.execute(
                    'SELECT "stationName" FROM "staStations" WHERE "stationID" = %s',
                    (location_id,)
                )
                row = cur.fetchone()
                if row:
                    return row["stationName"]
        except Exception:
            pass
        return f"Station {location_id}"


@router.get("/aggregated", response_model=AggregatedOrdersResponse)
@handle_endpoint_errors()
def get_aggregated_orders(
    request: Request,
    character_ids: Optional[List[int]] = Query(
        None, description="Filter to specific character IDs"
    ),
    order_type: Optional[str] = Query(
        None, description="Filter: 'buy' or 'sell'"
    )
):
    """
    Get aggregated orders across all authenticated characters.

    Reads from character_orders DB table (populated by character sync)
    instead of making live ESI calls. Market stats for outbid detection
    are deduplicated by (region_id, type_id) and Redis-cached (60s TTL).
    """
    db = request.app.state.db
    redis = request.app.state.redis
    service = OrdersService(db, redis)

    empty_response = AggregatedOrdersResponse(
        summary=AggregatedOrdersSummary(
            total_characters=0, total_buy_orders=0, total_sell_orders=0,
            total_isk_in_buy_orders=0, total_isk_in_sell_orders=0,
            outbid_count=0, undercut_count=0
        ),
        by_character=[], orders=[],
        generated_at=datetime.now(timezone.utc).isoformat()
    )

    # 1. Read active orders from DB (populated by character sync)
    with db.cursor() as cur:
        sql = """
            SELECT co.order_id, co.character_id, co.type_id, co.type_name,
                   co.location_id, co.location_name, co.region_id,
                   co.is_buy_order, co.price, co.volume_total, co.volume_remain,
                   co.duration, co.escrow, co.issued,
                   c.character_name
            FROM character_orders co
            JOIN characters c ON c.character_id = co.character_id
            WHERE co.state = 'active'
        """
        params = []
        if character_ids:
            sql += " AND co.character_id = ANY(%s)"
            params.append(character_ids)
        if order_type == 'buy':
            sql += " AND co.is_buy_order = TRUE"
        elif order_type == 'sell':
            sql += " AND co.is_buy_order = FALSE"

        cur.execute(sql, params or None)
        db_orders = cur.fetchall()

        if not db_orders:
            return empty_response

        # 2. Batch resolve region names from SDE
        region_ids = list({o["region_id"] for o in db_orders if o.get("region_id")})
        region_names = {}
        if region_ids:
            cur.execute(
                'SELECT "regionID", "regionName" FROM "mapRegions" WHERE "regionID" = ANY(%s)',
                (region_ids,)
            )
            region_names = {r["regionID"]: r["regionName"] for r in cur.fetchall()}

    # 3. Batch market stats for outbid detection (deduplicated by region+type)
    unique_pairs = list({
        (o.get("region_id") or JITA_REGION_ID, o["type_id"])
        for o in db_orders
    })
    market_stats_cache = {}
    for region_id, type_id in unique_pairs:
        try:
            market_stats_cache[(region_id, type_id)] = service.get_market_stats(
                region_id, type_id
            )
        except Exception:
            market_stats_cache[(region_id, type_id)] = {}

    # 4. Assemble response (pure computation, no I/O)
    all_orders = []
    char_data: Dict[int, Dict[str, Any]] = {}

    for o in db_orders:
        char_id = o["character_id"]
        char_name = o["character_name"]
        is_buy = o["is_buy_order"]
        order_price = float(o["price"] or 0)
        region_id = o.get("region_id") or JITA_REGION_ID

        # Accumulate per-character stats
        if char_id not in char_data:
            char_data[char_id] = {
                "name": char_name,
                "buy": 0, "sell": 0, "total": 0,
                "escrow": 0.0, "sell_isk": 0.0,
            }
        cd = char_data[char_id]
        cd["total"] += 1
        if is_buy:
            cd["buy"] += 1
            cd["escrow"] += float(o.get("escrow") or 0)
        else:
            cd["sell"] += 1
            cd["sell_isk"] += order_price * (o.get("volume_remain") or 0)

        # Market stats for outbid detection
        stats = market_stats_cache.get((region_id, o["type_id"]), {})
        best_buy = stats.get("highest_buy", 0) or 0
        best_sell = stats.get("lowest_sell") or float("inf")

        if is_buy:
            is_outbid = order_price < best_buy
            outbid_by = best_buy - order_price if is_outbid else 0
        else:
            is_outbid = order_price > best_sell if best_sell < float("inf") else False
            outbid_by = order_price - best_sell if is_outbid else 0

        if best_buy > 0 and best_sell < float("inf"):
            spread = (best_sell - best_buy) / best_buy * 100
        else:
            spread = 0

        all_orders.append(AggregatedOrder(
            order_id=o["order_id"],
            character_id=char_id,
            character_name=char_name,
            type_id=o["type_id"],
            type_name=o.get("type_name") or f"Type {o['type_id']}",
            is_buy_order=is_buy,
            price=order_price,
            volume_remain=o.get("volume_remain") or 0,
            volume_total=o.get("volume_total") or 0,
            location_name=o.get("location_name") or f"Station {o.get('location_id', 0)}",
            region_name=region_names.get(region_id, f"Region {region_id}"),
            issued=str(o.get("issued") or ""),
            duration=o.get("duration") or 0,
            market_status=MarketStatus(
                current_best_buy=best_buy,
                current_best_sell=best_sell if best_sell < float("inf") else 0,
                is_outbid=is_outbid,
                outbid_by=outbid_by,
                spread_percent=round(spread, 2)
            )
        ))

    # 5. Build per-character summaries
    by_character = [
        CharacterOrderSummary(
            character_id=cid,
            character_name=cd["name"],
            buy_orders=cd["buy"],
            sell_orders=cd["sell"],
            order_slots_used=cd["total"],
            order_slots_max=100,
            isk_in_escrow=cd["escrow"],
            isk_in_sell_orders=cd["sell_isk"],
        )
        for cid, cd in char_data.items()
    ]

    # 6. Build summary
    buy_list = [o for o in all_orders if o.is_buy_order]
    sell_list = [o for o in all_orders if not o.is_buy_order]

    summary = AggregatedOrdersSummary(
        total_characters=len(by_character),
        total_buy_orders=len(buy_list),
        total_sell_orders=len(sell_list),
        total_isk_in_buy_orders=sum(c.isk_in_escrow for c in by_character),
        total_isk_in_sell_orders=sum(c.isk_in_sell_orders for c in by_character),
        outbid_count=len([o for o in buy_list if o.market_status.is_outbid]),
        undercut_count=len([o for o in sell_list if o.market_status.is_outbid])
    )

    return AggregatedOrdersResponse(
        summary=summary,
        by_character=by_character,
        orders=all_orders,
        generated_at=datetime.now(timezone.utc).isoformat()
    )
