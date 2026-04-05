"""Sovereignty asset tracking — snapshots and delta analysis."""
import logging
from typing import Optional
from fastapi import APIRouter, Request, Query
from app.database import db_cursor
from eve_shared.utils.error_handling import handle_endpoint_errors

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sov/assets", tags=["sovereignty"])


@router.post("/snapshot")
@handle_endpoint_errors()
def create_snapshot(request: Request):
    """Create asset snapshots for all tracked structures.

    Called by scheduler to track changes over time.
    """
    snapshots = 0

    with db_cursor() as cur:
        # Snapshot skyhooks
        cur.execute("""
            INSERT INTO sov_asset_snapshots (system_id, structure_type, structure_id, snapshot_data)
            SELECT system_id, 'skyhook', structure_id,
                   jsonb_build_object(
                       'power_output', power_output,
                       'workforce_output', workforce_output,
                       'reagent_stock', reagent_stock,
                       'state', state
                   )
            FROM skyhooks WHERE state = 'online'
        """)
        snapshots += cur.rowcount

        # Snapshot metenox drills
        cur.execute("""
            INSERT INTO sov_asset_snapshots (system_id, structure_type, structure_id, snapshot_data)
            SELECT system_id, 'metenox', structure_id,
                   jsonb_build_object(
                       'fuel_blocks_qty', fuel_blocks_qty,
                       'magmatic_gas_qty', magmatic_gas_qty,
                       'output_bay_used_m3', output_bay_used_m3,
                       'accumulated_ore', accumulated_ore,
                       'state', state
                   )
            FROM metenox_drills WHERE state = 'online'
        """)
        snapshots += cur.rowcount

    return {"snapshots_created": snapshots}


@router.get("/deltas")
@handle_endpoint_errors()
def get_asset_deltas(
    request: Request,
    system_id: Optional[int] = None,
    structure_type: Optional[str] = None,
    hours: int = Query(default=24, le=168),
):
    """Compare latest snapshot vs N hours ago to detect changes."""
    conditions = []
    params = {"hours": hours}

    if system_id:
        conditions.append("l.system_id = %(system_id)s")
        params["system_id"] = system_id
    if structure_type:
        conditions.append("l.structure_type = %(structure_type)s")
        params["structure_type"] = structure_type

    where = f"AND {' AND '.join(conditions)}" if conditions else ""

    with db_cursor() as cur:
        cur.execute(f"""
            WITH latest AS (
                SELECT DISTINCT ON (structure_id)
                    structure_id, system_id, structure_type, snapshot_data, snapshot_at
                FROM sov_asset_snapshots
                WHERE snapshot_at > NOW() - INTERVAL '2 hours'
                ORDER BY structure_id, snapshot_at DESC
            ),
            previous AS (
                SELECT DISTINCT ON (structure_id)
                    structure_id, snapshot_data, snapshot_at
                FROM sov_asset_snapshots
                WHERE snapshot_at < NOW() - INTERVAL '1 hour' * %(hours)s
                  AND snapshot_at > NOW() - INTERVAL '1 hour' * (%(hours)s + 6)
                ORDER BY structure_id, snapshot_at DESC
            )
            SELECT l.structure_id, l.system_id, l.structure_type,
                   l.snapshot_data as current_data,
                   p.snapshot_data as previous_data,
                   l.snapshot_at as current_at,
                   p.snapshot_at as previous_at
            FROM latest l
            LEFT JOIN previous p ON l.structure_id = p.structure_id
            WHERE TRUE {where}
            ORDER BY l.system_id
        """, params)
        rows = cur.fetchall()

    deltas = []
    for row in rows:
        current = row["current_data"] or {}
        previous = row["previous_data"] or {}
        changes = {}

        for key in set(list(current.keys()) + list(previous.keys())):
            if key in current and key in previous:
                if current[key] != previous[key]:
                    changes[key] = {"from": previous[key], "to": current[key]}

        if changes or not previous:
            deltas.append({
                "structure_id": row["structure_id"],
                "system_id": row["system_id"],
                "structure_type": row["structure_type"],
                "changes": changes,
                "is_new": not bool(previous),
                "current_at": str(row["current_at"]),
                "previous_at": str(row["previous_at"]) if row["previous_at"] else None,
            })

    return {"deltas": deltas, "count": len(deltas), "hours": hours}
