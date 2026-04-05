"""
Portfolio Router - Portfolio snapshots and history.
Migrated from monolith to market-service.
"""

import logging
from typing import List, Optional
from datetime import date, timedelta

import httpx
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

CHARACTER_SERVICE_URL = "http://eve-character-service:8000"

router = APIRouter(prefix="/api/portfolio", tags=["Portfolio"])


class PortfolioSnapshot(BaseModel):
    character_id: int
    snapshot_date: date
    wallet_balance: float
    sell_order_value: float
    buy_order_escrow: float
    total_liquid: float


class PortfolioHistory(BaseModel):
    character_id: int
    snapshots: List[PortfolioSnapshot]
    period_days: int
    growth_absolute: float
    growth_percent: float


@router.get("/{character_id}/history", response_model=PortfolioHistory)
def get_portfolio_history(
    request: Request,
    character_id: int,
    days: int = Query(30, ge=1, le=365, description="Days of history")
):
    """
    Get portfolio value history for a character.

    Returns daily snapshots of wallet + orders value.

    Args:
        character_id: EVE character ID
        days: Number of days to return

    Returns:
        PortfolioHistory with snapshots and growth metrics
    """
    start_date = date.today() - timedelta(days=days)

    db = request.app.state.db
    with db.cursor() as cur:
        cur.execute('''
            SELECT character_id, snapshot_date, wallet_balance,
                   sell_order_value, buy_order_escrow, total_liquid
            FROM portfolio_snapshots
            WHERE character_id = %s AND snapshot_date >= %s
            ORDER BY snapshot_date ASC
        ''', (character_id, start_date))
        rows = cur.fetchall()

    snapshots = [
        PortfolioSnapshot(
            character_id=row['character_id'],
            snapshot_date=row['snapshot_date'],
            wallet_balance=float(row['wallet_balance']) if row['wallet_balance'] else 0,
            sell_order_value=float(row['sell_order_value']) if row['sell_order_value'] else 0,
            buy_order_escrow=float(row['buy_order_escrow']) if row['buy_order_escrow'] else 0,
            total_liquid=float(row['total_liquid']) if row['total_liquid'] else 0
        )
        for row in rows
    ]

    # Calculate growth
    if len(snapshots) >= 2:
        first_value = snapshots[0].total_liquid
        last_value = snapshots[-1].total_liquid
        growth_absolute = last_value - first_value
        growth_percent = (growth_absolute / first_value * 100) if first_value > 0 else 0
    else:
        growth_absolute = 0
        growth_percent = 0

    return PortfolioHistory(
        character_id=character_id,
        snapshots=snapshots,
        period_days=days,
        growth_absolute=round(growth_absolute, 2),
        growth_percent=round(growth_percent, 2)
    )


@router.post("/snapshot")
async def create_portfolio_snapshot(
    request: Request,
    character_ids: Optional[List[int]] = None
):
    """
    Create portfolio snapshots for characters.

    If no character_ids provided, creates for all authenticated characters.
    This endpoint is called by the daily cron job.

    Note: This endpoint requires character service integration for full functionality.
    Currently returns a placeholder response.

    Args:
        character_ids: Optional list of character IDs

    Returns:
        Dict with created snapshot count
    """
    db = request.app.state.db
    today = date.today()

    # If no character_ids provided, get from auth table
    if not character_ids:
        with db.cursor() as cur:
            cur.execute("SELECT character_id FROM oauth_tokens")
            rows = cur.fetchall()
            character_ids = [row['character_id'] for row in rows]

    if not character_ids:
        return {
            "created": 0,
            "errors": [],
            "date": today.isoformat(),
            "message": "No characters found"
        }

    created = 0
    errors = []

    # Pre-fetch all order data from own aggregated endpoint (uses ESI directly)
    order_data: dict[int, dict] = {}
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            r = await client.get("http://localhost:8000/api/orders/aggregated")
            if r.status_code == 200:
                for cs in r.json().get("by_character", []):
                    order_data[cs["character_id"]] = {
                        "sell": cs.get("isk_in_sell_orders", 0.0),
                        "escrow": cs.get("isk_in_escrow", 0.0),
                    }
        except Exception as e:
            logger.warning(f"Failed to fetch aggregated orders: {e}")

    async with httpx.AsyncClient(timeout=15) as client:
      for char_id in character_ids:
        try:
            # Check if snapshot already exists with real data
            with db.cursor() as cur:
                cur.execute('''
                    SELECT total_liquid FROM portfolio_snapshots
                    WHERE character_id = %s AND snapshot_date = %s
                ''', (char_id, today))
                existing = cur.fetchone()
                if existing and existing['total_liquid'] > 0:
                    logger.debug(f"Snapshot already exists for {char_id} on {today}")
                    continue

            # Fetch wallet balance from character-service
            wallet_balance = 0.0
            try:
                r = await client.get(f"{CHARACTER_SERVICE_URL}/api/character/{char_id}/wallet")
                if r.status_code == 200:
                    wallet_balance = r.json().get("balance", 0.0)
            except Exception as e:
                logger.warning(f"Failed to fetch wallet for {char_id}: {e}")

            # Use pre-fetched order data
            char_orders = order_data.get(char_id, {})
            sell_order_value = char_orders.get("sell", 0.0)
            buy_escrow = char_orders.get("escrow", 0.0)

            total_liquid = wallet_balance + sell_order_value + buy_escrow

            with db.cursor() as cur:
                cur.execute('''
                    INSERT INTO portfolio_snapshots
                    (character_id, snapshot_date, wallet_balance,
                     sell_order_value, buy_order_escrow, total_liquid)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (character_id, snapshot_date)
                    DO UPDATE SET
                        wallet_balance = EXCLUDED.wallet_balance,
                        sell_order_value = EXCLUDED.sell_order_value,
                        buy_order_escrow = EXCLUDED.buy_order_escrow,
                        total_liquid = EXCLUDED.total_liquid
                ''', (char_id, today, wallet_balance, sell_order_value, buy_escrow, total_liquid))

            created += 1
            logger.info(f"Created snapshot for {char_id}: wallet={wallet_balance:.0f}, sell={sell_order_value:.0f}, buy={buy_escrow:.0f}")

        except Exception as e:
            errors.append({"character_id": char_id, "error": str(e)})
            logger.error(f"Error creating snapshot for {char_id}: {e}")

    return {
        "created": created,
        "errors": errors,
        "date": today.isoformat(),
    }


@router.get("/{character_id}/latest")
def get_latest_snapshot(
    request: Request,
    character_id: int
):
    """
    Get the latest portfolio snapshot for a character.

    Args:
        character_id: EVE character ID

    Returns:
        Latest PortfolioSnapshot or 404 if none exists
    """
    db = request.app.state.db
    with db.cursor() as cur:
        cur.execute('''
            SELECT character_id, snapshot_date, wallet_balance,
                   sell_order_value, buy_order_escrow, total_liquid
            FROM portfolio_snapshots
            WHERE character_id = %s
            ORDER BY snapshot_date DESC
            LIMIT 1
        ''', (character_id,))
        row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="No snapshot found for this character")

    return PortfolioSnapshot(
        character_id=row['character_id'],
        snapshot_date=row['snapshot_date'],
        wallet_balance=float(row['wallet_balance']) if row['wallet_balance'] else 0,
        sell_order_value=float(row['sell_order_value']) if row['sell_order_value'] else 0,
        buy_order_escrow=float(row['buy_order_escrow']) if row['buy_order_escrow'] else 0,
        total_liquid=float(row['total_liquid']) if row['total_liquid'] else 0
    )


@router.get("/summary/all")
def get_all_portfolios_summary(request: Request):
    """
    Get summary of all characters' latest portfolios.

    Returns:
        List of latest snapshots for all characters
    """
    db = request.app.state.db
    with db.cursor() as cur:
        cur.execute('''
            SELECT DISTINCT ON (character_id)
                   character_id, snapshot_date, wallet_balance,
                   sell_order_value, buy_order_escrow, total_liquid
            FROM portfolio_snapshots
            ORDER BY character_id, snapshot_date DESC
        ''')
        rows = cur.fetchall()

    snapshots = [
        PortfolioSnapshot(
            character_id=row['character_id'],
            snapshot_date=row['snapshot_date'],
            wallet_balance=float(row['wallet_balance']) if row['wallet_balance'] else 0,
            sell_order_value=float(row['sell_order_value']) if row['sell_order_value'] else 0,
            buy_order_escrow=float(row['buy_order_escrow']) if row['buy_order_escrow'] else 0,
            total_liquid=float(row['total_liquid']) if row['total_liquid'] else 0
        )
        for row in rows
    ]

    total_liquid = sum(s.total_liquid for s in snapshots)

    return {
        "snapshots": snapshots,
        "total_characters": len(snapshots),
        "combined_liquid": round(total_liquid, 2)
    }
