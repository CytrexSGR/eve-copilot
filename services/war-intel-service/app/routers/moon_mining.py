"""
Moon Mining Intel Router - Track moon mining operations and value.

Uses ESI corporation mining observer endpoints.
Requires: esi-industry.read_corporation_mining.v1 scope
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query
import httpx

from app.database import db_cursor
from eve_shared.utils.error_handling import handle_endpoint_errors

logger = logging.getLogger(__name__)

router = APIRouter()

# ESI base URL
ESI_BASE = "https://esi.evetech.net/latest"

# Moon ore rarity values (approximate ISK/unit)
RARITY_VALUES = {
    'R64': 50000,
    'R32': 25000,
    'R16': 10000,
    'R8': 5000,
    'R4': 2000,
}


# ==============================================================================
# Helper Functions
# ==============================================================================

async def fetch_esi(endpoint: str, token: str, params: dict = None) -> dict:
    """Fetch data from ESI with authentication."""
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{ESI_BASE}{endpoint}",
            headers=headers,
            params=params,
            timeout=30.0
        )
        if response.status_code == 403:
            raise HTTPException(status_code=403, detail="Insufficient permissions for this endpoint")
        response.raise_for_status()
        return response.json()


def get_ore_rarity(type_id: int) -> Optional[str]:
    """Get moon ore rarity from database."""
    with db_cursor() as cur:
        cur.execute("SELECT rarity FROM moon_ore_types WHERE type_id = %s", (type_id,))
        row = cur.fetchone()
        return row['rarity'] if row else None


def estimate_ore_value(type_id: int, quantity: int) -> float:
    """Estimate ISK value for moon ore."""
    rarity = get_ore_rarity(type_id)
    if rarity and rarity in RARITY_VALUES:
        return quantity * RARITY_VALUES[rarity]
    return quantity * 1000  # Default for unknown


# ==============================================================================
# Public Endpoints (no auth required)
# ==============================================================================

@router.get("/ore-types")
def get_moon_ore_types():
    """Get all moon ore types with their rarity classifications."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT type_id, type_name, rarity, base_value
            FROM moon_ore_types
            ORDER BY
                CASE rarity
                    WHEN 'R64' THEN 1
                    WHEN 'R32' THEN 2
                    WHEN 'R16' THEN 3
                    WHEN 'R8' THEN 4
                    WHEN 'R4' THEN 5
                    ELSE 6
                END
        """)
        rows = cur.fetchall()

    ores_by_rarity = {}
    for row in rows:
        rarity = row['rarity']
        if rarity not in ores_by_rarity:
            ores_by_rarity[rarity] = []
        ores_by_rarity[rarity].append({
            "type_id": row['type_id'],
            "type_name": row['type_name'],
            "estimated_value": RARITY_VALUES.get(rarity, 1000)
        })

    return {
        "ore_types": ores_by_rarity,
        "rarity_order": ["R64", "R32", "R16", "R8", "R4"],
        "rarity_values": RARITY_VALUES
    }


@router.get("/summary/{corporation_id}")
def get_mining_summary(
    corporation_id: int,
    days: int = Query(30, ge=1, le=90, description="Days to look back")
):
    """Get moon mining summary for a corporation from cached data."""
    with db_cursor() as cur:
        # Get observer count
        cur.execute("""
            SELECT COUNT(*) as count
            FROM moon_mining_observers
            WHERE corporation_id = %s
        """, (corporation_id,))
        observer_count = cur.fetchone()['count']

        # Get mining by rarity
        cur.execute("""
            SELECT
                COALESCE(mot.rarity, 'unknown') as rarity,
                SUM(ml.quantity) as total_quantity,
                SUM(ml.estimated_value) as total_value
            FROM moon_mining_ledger ml
            JOIN moon_mining_observers mo ON ml.observer_id = mo.observer_id
            LEFT JOIN moon_ore_types mot ON ml.type_id = mot.type_id
            WHERE mo.corporation_id = %s
              AND ml.last_updated > NOW() - INTERVAL '%s days'
            GROUP BY mot.rarity
            ORDER BY total_value DESC NULLS LAST
        """, (corporation_id, days))
        by_rarity = [{
            "rarity": row['rarity'],
            "quantity": row['total_quantity'],
            "estimated_value": float(row['total_value']) if row['total_value'] else 0
        } for row in cur.fetchall()]

        # Get top miners
        cur.execute("""
            SELECT
                ml.character_id,
                ml.character_name,
                SUM(ml.quantity) as total_mined,
                SUM(ml.estimated_value) as total_value
            FROM moon_mining_ledger ml
            JOIN moon_mining_observers mo ON ml.observer_id = mo.observer_id
            WHERE mo.corporation_id = %s
              AND ml.last_updated > NOW() - INTERVAL '%s days'
            GROUP BY ml.character_id, ml.character_name
            ORDER BY total_value DESC NULLS LAST
            LIMIT 20
        """, (corporation_id, days))
        top_miners = [{
            "character_id": row['character_id'],
            "character_name": row['character_name'],
            "total_mined": row['total_mined'],
            "estimated_value": float(row['total_value']) if row['total_value'] else 0
        } for row in cur.fetchall()]

    total_value = sum(r['estimated_value'] for r in by_rarity)

    return {
        "corporation_id": corporation_id,
        "period_days": days,
        "observer_count": observer_count,
        "total_estimated_value": total_value,
        "by_rarity": by_rarity,
        "top_miners": top_miners
    }


@router.get("/observers/{corporation_id}")
def get_corporation_observers(corporation_id: int):
    """Get cached mining observers for a corporation."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT
                mo.observer_id,
                mo.observer_type,
                mo.structure_name,
                mo.system_id,
                mo.system_name,
                mo.total_mined_volume,
                mo.last_extraction,
                mo.last_updated
            FROM moon_mining_observers mo
            WHERE mo.corporation_id = %s
            ORDER BY mo.last_updated DESC
        """, (corporation_id,))
        observers = [{
            "observer_id": row['observer_id'],
            "observer_type": row['observer_type'],
            "structure_name": row['structure_name'],
            "system_id": row['system_id'],
            "system_name": row['system_name'],
            "total_mined_volume": row['total_mined_volume'],
            "last_extraction": row['last_extraction'].isoformat() if row['last_extraction'] else None,
            "last_updated": row['last_updated'].isoformat()
        } for row in cur.fetchall()]

    return {
        "corporation_id": corporation_id,
        "observer_count": len(observers),
        "observers": observers
    }


# ==============================================================================
# Authenticated Endpoints (require ESI token)
# ==============================================================================

@router.post("/sync/{corporation_id}")
@handle_endpoint_errors()
async def sync_mining_observers(
    corporation_id: int,
    token: str = Query(..., description="ESI access token with industry scope")
):
    """
    Sync mining observers from ESI for a corporation.

    Requires: esi-industry.read_corporation_mining.v1 scope
    """
    # Fetch observers from ESI
    observers = await fetch_esi(
        f"/corporation/{corporation_id}/mining/observers/",
        token
    )

    synced_count = 0
    for obs in observers:
        observer_id = obs['observer_id']

        with db_cursor() as cur:
            # Upsert observer
            cur.execute("""
                INSERT INTO moon_mining_observers (
                    observer_id, corporation_id, observer_type, last_updated
                ) VALUES (%s, %s, %s, %s)
                ON CONFLICT (observer_id) DO UPDATE SET
                    last_updated = EXCLUDED.last_updated,
                    updated_at = NOW()
            """, (
                observer_id,
                corporation_id,
                obs.get('observer_type', 'moon_drill'),
                obs['last_updated']
            ))
            synced_count += 1

        # Fetch ledger for this observer
        try:
            ledger = await fetch_esi(
                f"/corporation/{corporation_id}/mining/observers/{observer_id}/",
                token
            )

            for entry in ledger:
                estimated_value = estimate_ore_value(entry['type_id'], entry['quantity'])

                with db_cursor() as cur:
                    cur.execute("""
                        INSERT INTO moon_mining_ledger (
                            observer_id, character_id, type_id, quantity,
                            last_updated, estimated_value
                        ) VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (observer_id, character_id, type_id, last_updated)
                        DO UPDATE SET
                            quantity = EXCLUDED.quantity,
                            estimated_value = EXCLUDED.estimated_value
                    """, (
                        observer_id,
                        entry['character_id'],
                        entry['type_id'],
                        entry['quantity'],
                        entry['last_updated'],
                        estimated_value
                    ))

        except Exception as e:
            logger.warning(f"Failed to fetch ledger for observer {observer_id}: {e}")

    return {
        "message": "Sync completed",
        "corporation_id": corporation_id,
        "observers_synced": synced_count
    }


@router.get("/ledger/{observer_id}")
def get_observer_ledger(
    observer_id: int,
    days: int = Query(30, ge=1, le=90)
):
    """Get mining ledger for a specific observer from cache."""
    with db_cursor() as cur:
        # Get observer info
        cur.execute("""
            SELECT * FROM moon_mining_observers WHERE observer_id = %s
        """, (observer_id,))
        observer = cur.fetchone()

        if not observer:
            raise HTTPException(status_code=404, detail="Observer not found")

        # Get ledger entries
        cur.execute("""
            SELECT
                ml.character_id,
                ml.character_name,
                ml.type_id,
                mot.type_name,
                mot.rarity,
                ml.quantity,
                ml.estimated_value,
                ml.last_updated
            FROM moon_mining_ledger ml
            LEFT JOIN moon_ore_types mot ON ml.type_id = mot.type_id
            WHERE ml.observer_id = %s
              AND ml.last_updated > NOW() - INTERVAL '%s days'
            ORDER BY ml.last_updated DESC
        """, (observer_id, days))

        entries = [{
            "character_id": row['character_id'],
            "character_name": row['character_name'],
            "type_id": row['type_id'],
            "type_name": row['type_name'],
            "rarity": row['rarity'],
            "quantity": row['quantity'],
            "estimated_value": float(row['estimated_value']) if row['estimated_value'] else 0,
            "last_updated": row['last_updated'].isoformat()
        } for row in cur.fetchall()]

    return {
        "observer_id": observer_id,
        "structure_name": observer['structure_name'],
        "system_name": observer['system_name'],
        "period_days": days,
        "entry_count": len(entries),
        "entries": entries
    }


@router.get("/value-report/{corporation_id}")
def get_value_report(
    corporation_id: int,
    days: int = Query(30, ge=1, le=90)
):
    """Get detailed value report by ore type for a corporation."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT
                ml.type_id,
                mot.type_name,
                mot.rarity,
                SUM(ml.quantity) as total_quantity,
                SUM(ml.estimated_value) as total_value,
                COUNT(DISTINCT ml.character_id) as miner_count,
                COUNT(DISTINCT ml.observer_id) as structure_count
            FROM moon_mining_ledger ml
            JOIN moon_mining_observers mo ON ml.observer_id = mo.observer_id
            LEFT JOIN moon_ore_types mot ON ml.type_id = mot.type_id
            WHERE mo.corporation_id = %s
              AND ml.last_updated > NOW() - INTERVAL '%s days'
            GROUP BY ml.type_id, mot.type_name, mot.rarity
            ORDER BY total_value DESC NULLS LAST
        """, (corporation_id, days))

        by_ore = [{
            "type_id": row['type_id'],
            "type_name": row['type_name'],
            "rarity": row['rarity'],
            "quantity": row['total_quantity'],
            "estimated_value": float(row['total_value']) if row['total_value'] else 0,
            "miner_count": row['miner_count'],
            "structure_count": row['structure_count']
        } for row in cur.fetchall()]

    # Calculate totals
    total_value = sum(ore['estimated_value'] for ore in by_ore)
    r64_value = sum(ore['estimated_value'] for ore in by_ore if ore['rarity'] == 'R64')
    r32_value = sum(ore['estimated_value'] for ore in by_ore if ore['rarity'] == 'R32')

    return {
        "corporation_id": corporation_id,
        "period_days": days,
        "total_estimated_value": total_value,
        "r64_value": r64_value,
        "r32_value": r32_value,
        "high_value_percentage": (r64_value + r32_value) / total_value * 100 if total_value > 0 else 0,
        "by_ore_type": by_ore
    }
