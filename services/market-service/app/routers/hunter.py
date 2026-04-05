"""
Market Hunter Router
Endpoints for finding profitable manufacturing opportunities.
Migrated from monolith to market-service.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

from eve_shared.utils.error_handling import handle_endpoint_errors

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/hunter", tags=["Market Hunter"])


@router.get("/categories")
@handle_endpoint_errors()
def get_categories(request: Request):
    """
    Get all available categories and groups for filtering.
    Returns hierarchical structure of Category -> Groups.
    """
    db = request.app.state.db
    with db.cursor() as cur:
        cur.execute("""
            SELECT category, group_name, COUNT(*) as count
            FROM manufacturing_opportunities
            GROUP BY category, group_name
            ORDER BY category, count DESC
        """)
        rows = cur.fetchall()

        # Build hierarchical structure
        categories = {}
        for row in rows:
            cat = row['category'] or "Unknown"
            group = row['group_name']
            count = row['count']

            if cat not in categories:
                categories[cat] = {"count": 0, "groups": []}
            categories[cat]["count"] += count
            categories[cat]["groups"].append({"name": group, "count": count})

        return {
            "categories": categories,
            "total_items": sum(c["count"] for c in categories.values())
        }


@router.get("/market-tree")
@handle_endpoint_errors()
def get_market_tree(request: Request):
    """
    Get EVE Online market group hierarchy (3 levels) with item counts.
    Returns tree structure like: Ships > Frigates > Standard Frigates > Amarr
    """
    db = request.app.state.db
    with db.cursor() as cur:
        # Get 3-level market hierarchy with item counts
        cur.execute('''
            SELECT
                mg1."marketGroupID" as level1_id,
                mg1."marketGroupName" as level1,
                mg2."marketGroupID" as level2_id,
                mg2."marketGroupName" as level2,
                mg3."marketGroupID" as level3_id,
                mg3."marketGroupName" as level3,
                COUNT(DISTINCT mo.product_id) as items
            FROM manufacturing_opportunities mo
            JOIN "invTypes" t ON mo.product_id = t."typeID"
            LEFT JOIN "invMarketGroups" mg3 ON t."marketGroupID" = mg3."marketGroupID"
            LEFT JOIN "invMarketGroups" mg2 ON mg3."parentGroupID" = mg2."marketGroupID"
            LEFT JOIN "invMarketGroups" mg1 ON mg2."parentGroupID" = mg1."marketGroupID"
            GROUP BY mg1."marketGroupID", mg1."marketGroupName",
                     mg2."marketGroupID", mg2."marketGroupName",
                     mg3."marketGroupID", mg3."marketGroupName"
            ORDER BY mg1."marketGroupName", mg2."marketGroupName", mg3."marketGroupName"
        ''')
        rows = cur.fetchall()

        # Build tree structure
        tree = {}
        for row in rows:
            level1_id = row['level1_id']
            level1 = row['level1'] or "Other"
            level2_id = row['level2_id']
            level2 = row['level2'] or "Other"
            level3_id = row['level3_id']
            level3 = row['level3'] or "Other"
            items = row['items']

            if level1 not in tree:
                tree[level1] = {"id": level1_id, "count": 0, "children": {}}

            if level2 not in tree[level1]["children"]:
                tree[level1]["children"][level2] = {"id": level2_id, "count": 0, "children": {}}

            tree[level1]["children"][level2]["children"][level3] = {
                "id": level3_id,
                "count": items
            }
            tree[level1]["children"][level2]["count"] += items
            tree[level1]["count"] += items

        return {"tree": tree}


@router.get("/scan")
@handle_endpoint_errors()
def hunter_scan(
    request: Request,
    min_roi: float = Query(0, description="Minimum ROI percentage"),
    min_profit: float = Query(0, description="Minimum profit in ISK"),
    max_difficulty: int = Query(5, ge=1, le=5, description="Maximum difficulty level"),
    min_volume: int = Query(0, ge=0, description="Minimum average daily volume"),
    top: int = Query(100, ge=1, le=500, description="Number of results"),
    category: str = Query(None, description="Filter by category"),
    groups: str = Query(None, description="Comma-separated group names to filter"),
    market_group: int = Query(None, description="Filter by EVE market group ID"),
    search: str = Query(None, description="Search product name"),
    sort_by: str = Query("profit", description="Sort field: profit, roi, material_cost, sell_price, name, volume")
):
    """
    Get T1 manufacturing opportunities from database.

    Returns results instantly from pre-calculated data.
    Data is refreshed every 5 minutes by background job.

    Filter modes:
    - Profit mode: Use min_roi, min_profit filters
    - Browse mode: Set min_roi=0, min_profit=0 and use category/groups/search/market_group
    """
    db = request.app.state.db
    with db.cursor() as cur:
        # Build query with filters
        where_clauses = ["mo.roi >= %s", "mo.profit >= %s", "mo.difficulty <= %s"]
        params = [min_roi, min_profit, max_difficulty]
        joins = []

        if category and category != "All":
            where_clauses.append("mo.category = %s")
            params.append(category)

        # Group filter (comma-separated list)
        if groups:
            group_list = [g.strip() for g in groups.split(",") if g.strip()]
            if group_list:
                placeholders = ", ".join(["%s"] * len(group_list))
                where_clauses.append(f"mo.group_name IN ({placeholders})")
                params.extend(group_list)

        # Market group filter - matches this group or any child groups
        if market_group:
            joins.append('JOIN "invTypes" t ON mo.product_id = t."typeID"')
            joins.append('LEFT JOIN "invMarketGroups" mg3 ON t."marketGroupID" = mg3."marketGroupID"')
            joins.append('LEFT JOIN "invMarketGroups" mg2 ON mg3."parentGroupID" = mg2."marketGroupID"')
            joins.append('LEFT JOIN "invMarketGroups" mg1 ON mg2."parentGroupID" = mg1."marketGroupID"')
            where_clauses.append(
                "(t.\"marketGroupID\" = %s OR mg3.\"parentGroupID\" = %s OR mg2.\"parentGroupID\" = %s OR mg1.\"marketGroupID\" = %s)"
            )
            params.extend([market_group, market_group, market_group, market_group])

        # Volume filter
        if min_volume > 0:
            where_clauses.append("mo.avg_daily_volume >= %s")
            params.append(min_volume)

        # Text search in product name
        if search:
            where_clauses.append("mo.product_name ILIKE %s")
            params.append(f"%{search}%")

        # Determine sort order
        sort_column = "mo.profit"
        sort_direction = "DESC"
        if sort_by == "roi":
            sort_column = "mo.roi"
        elif sort_by == "material_cost":
            sort_column = "mo.cheapest_material_cost"
        elif sort_by == "sell_price":
            sort_column = "mo.best_sell_price"
        elif sort_by == "volume":
            sort_column = "mo.avg_daily_volume"
        elif sort_by == "name":
            sort_column = "mo.product_name"
            sort_direction = "ASC"

        join_clause = " ".join(joins) if joins else ""
        query = f"""
            SELECT
                mo.product_id, mo.blueprint_id, mo.product_name, mo.category, mo.group_name,
                mo.difficulty, mo.cheapest_material_cost, mo.best_sell_price, mo.profit, mo.roi,
                mo.avg_daily_volume, mo.sell_volume, mo.risk_score,
                mo.days_to_sell, mo.net_profit, mo.net_roi,
                mo.updated_at
            FROM manufacturing_opportunities mo
            {join_clause}
            WHERE {' AND '.join(where_clauses)}
            ORDER BY {sort_column} {sort_direction}
            LIMIT %s
        """
        params.append(top)

        cur.execute(query, params)
        rows = cur.fetchall()

        # Get total count for stats
        cur.execute("SELECT COUNT(*) as cnt, MAX(updated_at) as max_updated FROM manufacturing_opportunities")
        stats_row = cur.fetchone()
        total_in_db = stats_row['cnt'] if stats_row else 0
        last_updated = stats_row['max_updated'] if stats_row else None

        results = []
        for row in rows:
            results.append({
                "product_id": row['product_id'],
                "blueprint_id": row['blueprint_id'],
                "product_name": row['product_name'],
                "category": row['category'] or "Unknown",
                "group_name": row['group_name'],
                "difficulty": row['difficulty'],
                "material_cost": float(row['cheapest_material_cost']) if row['cheapest_material_cost'] else 0,
                "sell_price": float(row['best_sell_price']) if row['best_sell_price'] else 0,
                "profit": float(row['profit']) if row['profit'] else 0,
                "roi": min(float(row['roi']), 9999) if row['roi'] else 0,
                "volume_available": 0,
                "avg_daily_volume": row.get('avg_daily_volume') or 0,
                "sell_volume": row.get('sell_volume') or 0,
                "risk_score": row.get('risk_score') or 50,
                "days_to_sell": float(row['days_to_sell']) if row.get('days_to_sell') else None,
                "net_profit": float(row['net_profit']) if row.get('net_profit') is not None else float(row.get('profit') or 0),
                "net_roi": float(row['net_roi']) if row.get('net_roi') is not None else float(row.get('roi') or 0),
            })

        return {
            "scan_id": last_updated.isoformat() if last_updated else "unknown",
            "results": results,
            "summary": {
                "total_scanned": total_in_db,
                "profitable": len(results),
                "avg_roi": sum(r['roi'] for r in results) / len(results) if results else 0
            },
            "cached": True,
            "last_updated": last_updated.isoformat() if last_updated else None
        }


@router.get("/opportunities")
@handle_endpoint_errors()
def get_opportunities(
    request: Request,
    min_roi: float = Query(15, description="Minimum ROI percentage"),
    min_profit: float = Query(500000, description="Minimum profit in ISK"),
    max_difficulty: int = Query(3, ge=1, le=5, description="Maximum difficulty level"),
    limit: int = Query(20, ge=1, le=100, description="Number of results")
):
    """
    Get pre-calculated manufacturing opportunities (alias for /scan with defaults).

    This endpoint provides quick access to profitable opportunities with sensible defaults.
    """
    db = request.app.state.db
    with db.cursor() as cur:
        cur.execute("""
            SELECT
                product_id, blueprint_id, product_name, category, group_name,
                difficulty, cheapest_material_cost, best_sell_price, profit, roi,
                avg_daily_volume, sell_volume, risk_score,
                days_to_sell, net_profit, net_roi,
                updated_at
            FROM manufacturing_opportunities
            WHERE roi >= %s AND profit >= %s AND difficulty <= %s
            ORDER BY profit DESC
            LIMIT %s
        """, (min_roi, min_profit, max_difficulty, limit))

        rows = cur.fetchall()

        results = []
        for row in rows:
            results.append({
                "product_id": row['product_id'],
                "blueprint_id": row['blueprint_id'],
                "product_name": row['product_name'],
                "category": row['category'] or "Unknown",
                "group_name": row['group_name'],
                "difficulty": row['difficulty'],
                "material_cost": float(row['cheapest_material_cost']) if row['cheapest_material_cost'] else 0,
                "sell_price": float(row['best_sell_price']) if row['best_sell_price'] else 0,
                "profit": float(row['profit']) if row['profit'] else 0,
                "roi": min(float(row['roi']), 9999) if row['roi'] else 0,
                "volume_available": 0,
                "avg_daily_volume": row.get('avg_daily_volume') or 0,
                "sell_volume": row.get('sell_volume') or 0,
                "risk_score": row.get('risk_score') or 50,
                "days_to_sell": float(row['days_to_sell']) if row.get('days_to_sell') else None,
                "net_profit": float(row['net_profit']) if row.get('net_profit') is not None else float(row.get('profit') or 0),
                "net_roi": float(row['net_roi']) if row.get('net_roi') is not None else float(row.get('roi') or 0),
            })

        return {
            "results": results,
            "count": len(results)
        }
