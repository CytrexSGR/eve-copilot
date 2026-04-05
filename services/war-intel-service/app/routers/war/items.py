"""
Item combat statistics endpoints for War Intel API.

Provides endpoints for analyzing item destruction and combat statistics.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query

from app.database import db_cursor
from eve_shared.utils.error_handling import handle_endpoint_errors

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/item/{type_id}/stats")
@handle_endpoint_errors()
def get_item_combat_stats(
    type_id: int,
    days: int = Query(7, ge=1, le=30)
):
    """Get combat stats for a specific item."""
    with db_cursor() as cur:
        # Get item info
        cur.execute("""
            SELECT t."typeName", g."groupName", c."categoryName"
            FROM "invTypes" t
            JOIN "invGroups" g ON t."groupID" = g."groupID"
            JOIN "invCategories" c ON g."categoryID" = c."categoryID"
            WHERE t."typeID" = %s
        """, (type_id,))
        item_info = cur.fetchone()

        if not item_info:
            raise HTTPException(status_code=404, detail=f"Item {type_id} not found")

        # Get destruction stats
        cur.execute("""
            SELECT
                COALESCE(SUM(ki.quantity), 0) as quantity_destroyed,
                COUNT(DISTINCT k.killmail_id) as killmails_involved,
                COUNT(DISTINCT k.region_id) as regions_affected
            FROM killmail_items ki
            JOIN killmails k ON ki.killmail_id = k.killmail_id
            WHERE ki.item_type_id = %s
            AND k.killmail_time >= NOW() - INTERVAL '%s days'
            AND ki.was_destroyed = true
        """, (type_id, days))
        destruction = cur.fetchone()

        # Get drop stats
        cur.execute("""
            SELECT COALESCE(SUM(ki.quantity), 0) as quantity_dropped
            FROM killmail_items ki
            JOIN killmails k ON ki.killmail_id = k.killmail_id
            WHERE ki.item_type_id = %s
            AND k.killmail_time >= NOW() - INTERVAL '%s days'
            AND ki.was_destroyed = false
        """, (type_id, days))
        drops = cur.fetchone()

        # Get top regions
        cur.execute("""
            SELECT
                k.region_id,
                r."regionName" as region_name,
                SUM(ki.quantity) as quantity
            FROM killmail_items ki
            JOIN killmails k ON ki.killmail_id = k.killmail_id
            JOIN "mapRegions" r ON k.region_id = r."regionID"
            WHERE ki.item_type_id = %s
            AND k.killmail_time >= NOW() - INTERVAL '%s days'
            AND ki.was_destroyed = true
            GROUP BY k.region_id, r."regionName"
            ORDER BY quantity DESC
            LIMIT 5
        """, (type_id, days))
        top_regions = cur.fetchall()

    return {
        "type_id": type_id,
        "name": item_info["typeName"],
        "group": item_info["groupName"],
        "category": item_info["categoryName"],
        "period_days": days,
        "destroyed": {
            "quantity": int(destruction["quantity_destroyed"]),
            "killmails": destruction["killmails_involved"],
            "regions": destruction["regions_affected"]
        },
        "dropped": {
            "quantity": int(drops["quantity_dropped"])
        },
        "top_regions": [{
            "region_id": row["region_id"],
            "region_name": row["region_name"],
            "quantity": int(row["quantity"])
        } for row in top_regions],
        "generated_at": datetime.now(timezone.utc).isoformat()
    }
