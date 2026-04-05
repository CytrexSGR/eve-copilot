"""
Dashboard API Router

Provides aggregated data for the EVE Co-Pilot dashboard:
- Active projects with progress tracking
- Character summaries (proxied to character-service)
- Portfolio overview (proxied to market-service)

Migrated from monolith to api-gateway.
"""

import logging
from typing import List, Dict, Any

from fastapi import APIRouter, Query, Request, HTTPException
import httpx

from app.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/projects")
def get_active_projects(request: Request) -> List[Dict[str, Any]]:
    """
    Get active projects (shopping lists) with item counts and progress.

    Returns:
        List of projects with:
        - id: Shopping list ID
        - name: Shopping list name
        - total_items: Total number of items in the list
        - checked_items: Number of purchased items (is_purchased=true)
        - progress: Completion percentage (0-100)
    """
    db = request.app.state.db
    with db.cursor() as cur:
        # Query shopping lists with item counts
        cur.execute('''
            SELECT
                sl.id,
                sl.name,
                COUNT(sli.id) as total_items,
                COUNT(sli.id) FILTER (WHERE sli.is_purchased = true) as checked_items
            FROM shopping_lists sl
            LEFT JOIN shopping_list_items sli ON sl.id = sli.list_id
            GROUP BY sl.id, sl.name
            ORDER BY sl.updated_at DESC, sl.created_at DESC
        ''')

        projects = []
        for row in cur.fetchall():
            total = int(row[2])
            checked = int(row[3])

            # Calculate progress percentage
            if total > 0:
                progress = round((checked / total) * 100, 1)
            else:
                progress = 0.0

            projects.append({
                'id': row[0],
                'name': row[1],
                'total_items': total,
                'checked_items': checked,
                'progress': progress
            })

        return projects


@router.get("/opportunities")
def get_dashboard_opportunities(
    request: Request,
    limit: int = Query(10, ge=1, le=50, description="Maximum opportunities to return")
) -> List[Dict[str, Any]]:
    """
    Get top opportunities across all categories.

    Returns opportunities from:
    - Manufacturing (from manufacturing_opportunities table)

    Sorted by profit descending.
    """
    db = request.app.state.db
    opportunities = []

    # Get production opportunities from database
    with db.cursor() as cur:
        cur.execute("""
            SELECT
                product_id,
                product_name,
                profit,
                roi,
                difficulty,
                cheapest_material_cost,
                best_sell_price
            FROM manufacturing_opportunities
            WHERE profit > 1000000
            ORDER BY profit DESC
            LIMIT %s
        """, (limit,))

        for row in cur.fetchall():
            opportunities.append({
                'category': 'production',
                'type_id': row['product_id'],
                'name': row['product_name'],
                'profit': float(row['profit']) if row['profit'] else 0.0,
                'roi': float(row['roi']) if row['roi'] else 0.0,
                'difficulty': row['difficulty'],
                'material_cost': float(row['cheapest_material_cost']) if row['cheapest_material_cost'] else 0.0,
                'sell_price': float(row['best_sell_price']) if row['best_sell_price'] else 0.0
            })

    return opportunities


@router.get("/opportunities/{category}")
async def get_dashboard_opportunities_by_category(
    category: str,
    limit: int = Query(10, ge=1, le=50)
) -> List[Dict[str, Any]]:
    """
    Get opportunities for specific category.

    Categories: production, trade, war_demand
    """
    all_ops = await get_dashboard_opportunities(limit=100)
    filtered = [op for op in all_ops if op.get('category') == category]
    return filtered[:limit]


@router.get("/characters/summary")
async def get_dashboard_character_summaries() -> List[Dict[str, Any]]:
    """
    Get summary for all configured characters.

    Proxies to character-service for actual data.

    Returns:
    - Character name
    - ISK balance
    - Current location
    - Active industry jobs
    - Skill queue status
    """
    # Known character IDs
    character_ids = [526379435, 1117367444, 110592475]  # Artallus, Cytrex, Cytricia

    summaries = []
    async with httpx.AsyncClient(timeout=30.0) as client:
        for char_id in character_ids:
            try:
                # Get character info from character-service
                info_response = await client.get(
                    f"{settings.character_service_url}/api/character/{char_id}/info"
                )
                if info_response.status_code == 200:
                    info = info_response.json()
                    summaries.append({
                        "character_id": char_id,
                        "name": info.get("name", "Unknown"),
                        "corporation": info.get("corporation_name", "Unknown"),
                        "status": "active"
                    })
                else:
                    summaries.append({
                        "character_id": char_id,
                        "name": "Unknown",
                        "status": "error",
                        "error": f"Character service returned {info_response.status_code}"
                    })
            except httpx.RequestError as e:
                logger.warning(f"Failed to fetch character {char_id} info: {e}")
                summaries.append({
                    "character_id": char_id,
                    "name": "Unknown",
                    "status": "unavailable",
                    "error": "Character service unavailable"
                })

    return summaries


@router.get("/characters/portfolio")
async def get_dashboard_portfolio() -> Dict[str, Any]:
    """
    Get aggregated portfolio data across all characters.

    Proxies to market-service portfolio endpoint.

    Returns:
    - Total ISK
    - Total asset value
    - Character count
    """
    character_ids = [526379435, 1117367444, 110592475]

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{settings.market_service_url}/api/portfolio/summary/all"
            )
            if response.status_code == 200:
                data = response.json()
                return {
                    'total_isk': data.get('combined_liquid', 0),
                    'character_count': data.get('total_characters', len(character_ids)),
                    'characters': character_ids,
                    'source': 'market-service'
                }
    except httpx.RequestError as e:
        logger.warning(f"Failed to fetch portfolio from market-service: {e}")

    # Fallback response
    return {
        'total_isk': 0,
        'character_count': len(character_ids),
        'characters': character_ids,
        'source': 'fallback',
        'note': 'Market service unavailable'
    }
