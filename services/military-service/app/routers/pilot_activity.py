"""Pilot Activity Router — Personal fleet participation stats & dashboard data."""

import logging
from typing import Optional

from fastapi import APIRouter, Cookie, Query

from app.database import db_cursor, sde_cursor
from app.services.auth import get_current_user, require_permission

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pilot", tags=["Pilot Activity"])


def _enrich_ship_names(rows: list[dict], key: str = "ship_type_id") -> list[dict]:
    """Look up ship type names from SDE for rows containing a ship_type_id column."""
    type_ids = {r[key] for r in rows if r.get(key)}
    if not type_ids:
        return rows
    try:
        with sde_cursor() as cur:
            cur.execute(
                """SELECT "typeID", "typeName" FROM "invTypes" WHERE "typeID" = ANY(%s)""",
                (list(type_ids),),
            )
            name_map = {r["typeID"]: r["typeName"] for r in cur.fetchall()}
    except Exception:
        logger.warning("Could not look up ship type names from SDE", exc_info=True)
        name_map = {}
    for r in rows:
        tid = r.get(key)
        if tid and tid in name_map:
            r["ship_type_name"] = name_map[tid]
        elif "ship_type_name" not in r:
            r["ship_type_name"] = r.get("ship_name")
    return rows


@router.get("/{character_id}/activity")
async def get_pilot_activity(
    character_id: int,
    session: Optional[str] = Cookie(None),
    months: int = Query(default=6, ge=1, le=24, description="Months of history for monthly breakdown"),
):
    """Return comprehensive fleet participation stats for a single pilot.

    Includes summary totals, top ships flown, recent ops, and monthly breakdown.
    """
    user = await get_current_user(session)
    require_permission(user, "fleet.view")

    # --- 1. Summary: total ops, total snapshots, last fleet date ---
    with db_cursor() as cur:
        cur.execute(
            """
            SELECT
                COUNT(DISTINCT fp.operation_id)  AS total_ops,
                COALESCE(SUM(fp.snapshot_count), 0) AS total_snapshots,
                MAX(fp.last_seen)                AS last_fleet_date
            FROM fleet_participation fp
            WHERE fp.character_id = %s
            """,
            (character_id,),
        )
        summary = cur.fetchone()

    total_ops = summary["total_ops"] or 0
    total_snapshots = summary["total_snapshots"] or 0
    last_fleet_date = summary["last_fleet_date"]

    # --- 2. Average participation percentage across all ops ---
    with db_cursor() as cur:
        cur.execute(
            """
            SELECT COALESCE(AVG(pap_pct), 0) AS avg_participation_pct
            FROM (
                SELECT
                    fp.operation_id,
                    (fp.snapshot_count::float / NULLIF(total.snap_count, 0)) * 100 AS pap_pct
                FROM fleet_participation fp
                JOIN (
                    SELECT operation_id, COUNT(*) AS snap_count
                    FROM fleet_snapshots
                    GROUP BY operation_id
                ) total ON total.operation_id = fp.operation_id
                WHERE fp.character_id = %s
            ) sub
            """,
            (character_id,),
        )
        pap_row = cur.fetchone()

    avg_participation_pct = round(float(pap_row["avg_participation_pct"]), 2)

    # --- 3. Top 10 ships flown ---
    with db_cursor() as cur:
        cur.execute(
            """
            SELECT
                fp.ship_type_id,
                fp.ship_name,
                COUNT(*) AS count
            FROM fleet_participation fp
            WHERE fp.character_id = %s
              AND fp.ship_type_id IS NOT NULL
            GROUP BY fp.ship_type_id, fp.ship_name
            ORDER BY count DESC
            LIMIT 10
            """,
            (character_id,),
        )
        ships_flown = [dict(r) for r in cur.fetchall()]

    ships_flown = _enrich_ship_names(ships_flown)

    # --- 4. Recent 20 ops with details ---
    with db_cursor() as cur:
        cur.execute(
            """
            SELECT
                fo.id                       AS op_id,
                fo.fleet_name,
                fo.fc_name,
                fo.start_time               AS date,
                fp.ship_name,
                fp.ship_type_id,
                ROUND(
                    (fp.snapshot_count::numeric / NULLIF(total.snap_count, 0)) * 100, 2
                )                           AS participation_pct,
                EXTRACT(EPOCH FROM (
                    COALESCE(fo.end_time, NOW()) - fo.start_time
                ))::int / 60                AS duration_minutes
            FROM fleet_participation fp
            JOIN fleet_operations fo ON fo.id = fp.operation_id
            LEFT JOIN (
                SELECT operation_id, COUNT(*) AS snap_count
                FROM fleet_snapshots
                GROUP BY operation_id
            ) total ON total.operation_id = fp.operation_id
            WHERE fp.character_id = %s
            ORDER BY fo.start_time DESC
            LIMIT 20
            """,
            (character_id,),
        )
        recent_ops = [dict(r) for r in cur.fetchall()]

    recent_ops = _enrich_ship_names(recent_ops)

    # Convert date/datetime to ISO strings for JSON serialisation
    for op in recent_ops:
        if op.get("date"):
            op["date"] = op["date"].isoformat()
        if op.get("participation_pct") is not None:
            op["participation_pct"] = float(op["participation_pct"])

    # --- 5. Monthly breakdown (last N months) ---
    with db_cursor() as cur:
        cur.execute(
            """
            SELECT
                TO_CHAR(fo.start_time, 'YYYY-MM') AS month,
                COUNT(DISTINCT fp.operation_id)    AS ops_count,
                ROUND(AVG(
                    (fp.snapshot_count::numeric / NULLIF(total.snap_count, 0)) * 100
                ), 2)                              AS avg_pap
            FROM fleet_participation fp
            JOIN fleet_operations fo ON fo.id = fp.operation_id
            LEFT JOIN (
                SELECT operation_id, COUNT(*) AS snap_count
                FROM fleet_snapshots
                GROUP BY operation_id
            ) total ON total.operation_id = fp.operation_id
            WHERE fp.character_id = %s
              AND fo.start_time >= NOW() - (%s || ' months')::INTERVAL
            GROUP BY TO_CHAR(fo.start_time, 'YYYY-MM')
            ORDER BY month DESC
            """,
            (character_id, str(months)),
        )
        monthly_breakdown = [dict(r) for r in cur.fetchall()]

    for m in monthly_breakdown:
        if m.get("avg_pap") is not None:
            m["avg_pap"] = float(m["avg_pap"])

    # --- Build response ---
    return {
        "character_id": character_id,
        "total_ops": total_ops,
        "total_snapshots": total_snapshots,
        "avg_participation_pct": avg_participation_pct,
        "last_fleet_date": last_fleet_date.isoformat() if last_fleet_date else None,
        "ships_flown": ships_flown,
        "recent_ops": recent_ops,
        "monthly_breakdown": monthly_breakdown,
    }
