"""
Corporation Contract Monitor Router - Track contracts and courier efficiency.

Uses ESI corporation contracts endpoint.
Requires: esi-contracts.read_corporation_contracts.v1 scope
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

ESI_BASE = "https://esi.evetech.net/latest"


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
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        response.raise_for_status()
        return response.json()


# ==============================================================================
# Endpoints
# ==============================================================================

@router.get("/active/{corporation_id}")
def get_active_contracts(
    corporation_id: int,
    contract_type: Optional[str] = Query(None, description="Filter: courier, item_exchange, auction")
):
    """Get active (outstanding and in_progress) contracts."""
    with db_cursor() as cur:
        query = """
            SELECT
                contract_id, type, status, title,
                issuer_id, acceptor_id,
                price, reward, collateral, volume,
                date_issued, date_expired, date_accepted,
                start_location_id, end_location_id,
                days_to_complete
            FROM corp_contracts
            WHERE corporation_id = %s
              AND status IN ('outstanding', 'in_progress')
        """
        params = [corporation_id]

        if contract_type:
            query += " AND type = %s"
            params.append(contract_type)

        query += " ORDER BY date_issued DESC"

        cur.execute(query, params)
        rows = cur.fetchall()

    contracts = []
    for row in rows:
        contracts.append({
            "contract_id": row['contract_id'],
            "type": row['type'],
            "status": row['status'],
            "title": row['title'],
            "issuer_id": row['issuer_id'],
            "acceptor_id": row['acceptor_id'],
            "price": float(row['price']) if row['price'] else None,
            "reward": float(row['reward']) if row['reward'] else None,
            "collateral": float(row['collateral']) if row['collateral'] else None,
            "volume": row['volume'],
            "date_issued": row['date_issued'].isoformat() if row['date_issued'] else None,
            "date_expired": row['date_expired'].isoformat() if row['date_expired'] else None,
            "date_accepted": row['date_accepted'].isoformat() if row['date_accepted'] else None,
            "days_to_complete": row['days_to_complete']
        })

    summary = {
        "outstanding": len([c for c in contracts if c['status'] == 'outstanding']),
        "in_progress": len([c for c in contracts if c['status'] == 'in_progress']),
        "total": len(contracts)
    }

    return {
        "corporation_id": corporation_id,
        "summary": summary,
        "contracts": contracts
    }


@router.post("/sync/{corporation_id}")
@handle_endpoint_errors()
async def sync_contracts(
    corporation_id: int,
    token: str = Query(..., description="ESI access token with contracts scope")
):
    """
    Sync contracts from ESI.

    Requires: esi-contracts.read_corporation_contracts.v1 scope
    """
    contracts = await fetch_esi(
        f"/corporations/{corporation_id}/contracts/",
        token
    )

    synced = 0
    for contract in contracts:
        with db_cursor() as cur:
            # Track status changes before upsert
            cur.execute(
                "SELECT status FROM corp_contracts WHERE contract_id = %s",
                (contract['contract_id'],)
            )
            existing = cur.fetchone()
            if existing and existing['status'] != contract['status']:
                cur.execute("""
                    INSERT INTO contract_status_history (contract_id, old_status, new_status)
                    VALUES (%s, %s, %s)
                """, (contract['contract_id'], existing['status'], contract['status']))

            cur.execute("""
                INSERT INTO corp_contracts (
                    contract_id, corporation_id, acceptor_id, assignee_id,
                    availability, buyout, collateral, date_accepted, date_completed,
                    date_expired, date_issued, days_to_complete, end_location_id,
                    for_corporation, issuer_corporation_id, issuer_id, price, reward,
                    start_location_id, status, title, type, volume
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT (contract_id) DO UPDATE SET
                    acceptor_id = EXCLUDED.acceptor_id,
                    date_accepted = EXCLUDED.date_accepted,
                    date_completed = EXCLUDED.date_completed,
                    status = EXCLUDED.status,
                    synced_at = NOW()
            """, (
                contract['contract_id'],
                corporation_id,
                contract.get('acceptor_id'),
                contract.get('assignee_id'),
                contract.get('availability'),
                contract.get('buyout'),
                contract.get('collateral'),
                contract.get('date_accepted'),
                contract.get('date_completed'),
                contract.get('date_expired'),
                contract['date_issued'],
                contract.get('days_to_complete'),
                contract.get('end_location_id'),
                contract.get('for_corporation', False),
                contract.get('issuer_corporation_id'),
                contract.get('issuer_id'),
                contract.get('price'),
                contract.get('reward'),
                contract.get('start_location_id'),
                contract['status'],
                contract.get('title'),
                contract['type'],
                contract.get('volume')
            ))
        synced += 1

    return {
        "message": "Sync completed",
        "corporation_id": corporation_id,
        "contracts_synced": synced
    }


@router.get("/stats/{corporation_id}")
def get_contract_stats(
    corporation_id: int,
    days: int = Query(30, ge=1, le=90)
):
    """Get contract statistics."""
    with db_cursor() as cur:
        # By type and status
        cur.execute("""
            SELECT
                type, status,
                COUNT(*) as count,
                SUM(COALESCE(price, 0) + COALESCE(reward, 0)) as total_value
            FROM corp_contracts
            WHERE corporation_id = %s
              AND date_issued > NOW() - INTERVAL '%s days'
            GROUP BY type, status
            ORDER BY type, status
        """, (corporation_id, days))
        by_type_status = [{
            "type": row['type'],
            "status": row['status'],
            "count": row['count'],
            "total_value": float(row['total_value']) if row['total_value'] else 0
        } for row in cur.fetchall()]

        # Completion rates
        cur.execute("""
            SELECT
                type,
                COUNT(*) as total,
                SUM(CASE WHEN status IN ('finished', 'finished_issuer', 'finished_contractor') THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN status IN ('cancelled', 'rejected', 'failed', 'deleted') THEN 1 ELSE 0 END) as failed
            FROM corp_contracts
            WHERE corporation_id = %s
              AND date_issued > NOW() - INTERVAL '%s days'
            GROUP BY type
        """, (corporation_id, days))
        completion_rates = [{
            "type": row['type'],
            "total": row['total'],
            "completed": row['completed'],
            "failed": row['failed'],
            "completion_rate": row['completed'] / row['total'] * 100 if row['total'] > 0 else 0
        } for row in cur.fetchall()]

    return {
        "corporation_id": corporation_id,
        "period_days": days,
        "by_type_status": by_type_status,
        "completion_rates": completion_rates
    }


@router.get("/courier/{corporation_id}")
def get_courier_analysis(
    corporation_id: int,
    days: int = Query(30, ge=1, le=90)
):
    """Analyze courier contract efficiency."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT
                contract_id,
                issuer_id,
                acceptor_id,
                status,
                reward,
                collateral,
                volume,
                date_issued,
                date_accepted,
                date_completed,
                days_to_complete,
                CASE WHEN volume > 0 THEN reward / volume ELSE 0 END as isk_per_m3,
                CASE
                    WHEN date_completed IS NOT NULL AND date_accepted IS NOT NULL
                    THEN EXTRACT(EPOCH FROM (date_completed - date_accepted)) / 3600
                    ELSE NULL
                END as completion_hours
            FROM corp_contracts
            WHERE corporation_id = %s
              AND type = 'courier'
              AND date_issued > NOW() - INTERVAL '%s days'
            ORDER BY date_issued DESC
        """, (corporation_id, days))
        contracts = cur.fetchall()

    completed = [c for c in contracts if c['status'] in ('finished', 'finished_issuer', 'finished_contractor')]
    outstanding = [c for c in contracts if c['status'] == 'outstanding']
    in_progress = [c for c in contracts if c['status'] == 'in_progress']

    # Calculate averages for completed contracts
    avg_isk_m3 = sum(float(c['isk_per_m3'] or 0) for c in completed) / len(completed) if completed else 0
    avg_completion_hours = sum(float(c['completion_hours'] or 0) for c in completed if c['completion_hours']) / len([c for c in completed if c['completion_hours']]) if completed else 0
    total_reward = sum(float(c['reward'] or 0) for c in completed)
    total_volume = sum(float(c['volume'] or 0) for c in completed)

    # Top haulers
    hauler_stats = {}
    for c in completed:
        acceptor = c['acceptor_id']
        if acceptor:
            if acceptor not in hauler_stats:
                hauler_stats[acceptor] = {"count": 0, "volume": 0, "reward": 0}
            hauler_stats[acceptor]['count'] += 1
            hauler_stats[acceptor]['volume'] += float(c['volume'] or 0)
            hauler_stats[acceptor]['reward'] += float(c['reward'] or 0)

    top_haulers = sorted(
        [{"character_id": k, **v} for k, v in hauler_stats.items()],
        key=lambda x: x['volume'],
        reverse=True
    )[:10]

    return {
        "corporation_id": corporation_id,
        "period_days": days,
        "summary": {
            "total": len(contracts),
            "outstanding": len(outstanding),
            "in_progress": len(in_progress),
            "completed": len(completed),
            "completion_rate": len(completed) / len(contracts) * 100 if contracts else 0
        },
        "efficiency": {
            "average_isk_per_m3": round(avg_isk_m3, 2),
            "average_completion_hours": round(avg_completion_hours, 2),
            "total_reward_paid": total_reward,
            "total_volume_moved": total_volume
        },
        "top_haulers": top_haulers
    }


@router.get("/issuer/{corporation_id}/{issuer_id}")
def get_issuer_contracts(
    corporation_id: int,
    issuer_id: int,
    days: int = Query(30, ge=1, le=90)
):
    """Get contracts by a specific issuer."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT
                contract_id, type, status, title,
                price, reward, collateral, volume,
                date_issued, date_completed,
                acceptor_id
            FROM corp_contracts
            WHERE corporation_id = %s
              AND issuer_id = %s
              AND date_issued > NOW() - INTERVAL '%s days'
            ORDER BY date_issued DESC
        """, (corporation_id, issuer_id, days))
        rows = cur.fetchall()

    contracts = [{
        "contract_id": row['contract_id'],
        "type": row['type'],
        "status": row['status'],
        "title": row['title'],
        "price": float(row['price']) if row['price'] else None,
        "reward": float(row['reward']) if row['reward'] else None,
        "volume": row['volume'],
        "date_issued": row['date_issued'].isoformat() if row['date_issued'] else None,
        "date_completed": row['date_completed'].isoformat() if row['date_completed'] else None
    } for row in rows]

    return {
        "corporation_id": corporation_id,
        "issuer_id": issuer_id,
        "period_days": days,
        "contract_count": len(contracts),
        "contracts": contracts
    }


@router.get("/changes/{corporation_id}")
@handle_endpoint_errors()
def get_contract_changes(
    corporation_id: int,
    hours: int = Query(default=24, le=168),
):
    """Get contract status changes in the last N hours."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT csh.contract_id, csh.old_status, csh.new_status, csh.changed_at,
                   cc.type, cc.price, cc.reward, cc.issuer_id, cc.assignee_id
            FROM contract_status_history csh
            JOIN corp_contracts cc ON cc.contract_id = csh.contract_id
            WHERE cc.corporation_id = %s
              AND csh.changed_at > NOW() - INTERVAL '1 hour' * %s
            ORDER BY csh.changed_at DESC
        """, (corporation_id, hours))
        rows = cur.fetchall()

    changes = [{
        "contract_id": row["contract_id"],
        "old_status": row["old_status"],
        "new_status": row["new_status"],
        "changed_at": row["changed_at"].isoformat(),
        "type": row["type"],
        "price": float(row["price"]) if row["price"] else None,
        "reward": float(row["reward"]) if row["reward"] else None,
    } for row in rows]

    return {
        "corporation_id": corporation_id,
        "hours": hours,
        "changes": changes,
        "count": len(changes),
    }
