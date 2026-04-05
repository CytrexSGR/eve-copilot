"""
Corporation Wallet Analysis Router - Track SRP, taxes, and major transactions.

Uses ESI corporation wallet endpoints.
Requires: esi-wallet.read_corporation_wallets.v1 scope
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
import httpx

from app.database import db_cursor
from eve_shared.utils.error_handling import handle_endpoint_errors

logger = logging.getLogger(__name__)

router = APIRouter()

ESI_BASE = "https://esi.evetech.net/latest"

# Common ref_types categorization
REF_TYPE_CATEGORIES = {
    'income': [
        'bounty_prizes', 'agent_mission_reward', 'agent_mission_time_bonus_reward',
        'corporate_reward_tax', 'industry_job_tax', 'planetary_export_tax',
        'reprocessing_tax', 'brokers_fee', 'market_transaction'
    ],
    'srp': ['player_donation', 'corporation_account_withdrawal'],
    'operations': [
        'structure_gate_jump', 'jump_clone_activation_fee',
        'jump_clone_installation_fee', 'office_rental_fee'
    ],
    'market': ['market_escrow', 'market_transaction', 'transaction_tax'],
    'industry': ['industry_job_tax', 'manufacturing', 'copying', 'invention']
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
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        response.raise_for_status()
        return response.json()


def categorize_ref_type(ref_type: str) -> str:
    """Categorize a ref_type into a broader category."""
    for category, types in REF_TYPE_CATEGORIES.items():
        if ref_type in types:
            return category
    return 'other'


# ==============================================================================
# Endpoints
# ==============================================================================

@router.get("/balances/{corporation_id}")
def get_wallet_balances(corporation_id: int):
    """Get current wallet division balances from cache."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT division, name, balance, purpose, last_synced
            FROM corp_wallet_divisions
            WHERE corporation_id = %s
            ORDER BY division
        """, (corporation_id,))
        rows = cur.fetchall()

    total = sum(row['balance'] or 0 for row in rows)

    return {
        "corporation_id": corporation_id,
        "total_balance": float(total),
        "divisions": [{
            "division": row['division'],
            "name": row['name'],
            "balance": float(row['balance']) if row['balance'] else 0,
            "purpose": row['purpose'],
            "last_synced": row['last_synced'].isoformat() if row['last_synced'] else None
        } for row in rows]
    }


@router.post("/sync/{corporation_id}")
@handle_endpoint_errors()
async def sync_wallets(
    corporation_id: int,
    token: str = Query(..., description="ESI access token with wallet scope")
):
    """
    Sync wallet data from ESI.

    Requires: esi-wallet.read_corporation_wallets.v1 scope
    """
    synced_divisions = 0
    synced_entries = 0

    # Sync balances for all 7 divisions
    balances = await fetch_esi(
        f"/corporations/{corporation_id}/wallets/",
        token
    )

    for wallet in balances:
        division = wallet['division']
        balance = wallet['balance']

        with db_cursor() as cur:
            cur.execute("""
                INSERT INTO corp_wallet_divisions (corporation_id, division, balance, last_synced)
                VALUES (%s, %s, %s, NOW())
                ON CONFLICT (corporation_id, division) DO UPDATE SET
                    balance = EXCLUDED.balance,
                    last_synced = NOW()
            """, (corporation_id, division, balance))
        synced_divisions += 1

        # Sync journal for this division
        try:
            journal = await fetch_esi(
                f"/corporations/{corporation_id}/wallets/{division}/journal/",
                token
            )

            for entry in journal:
                with db_cursor() as cur:
                    cur.execute("""
                        INSERT INTO corp_wallet_journal (
                            id, corporation_id, division, amount, balance,
                            context_id, context_id_type, date, description,
                            first_party_id, second_party_id, reason, ref_type,
                            tax, tax_receiver_id
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        )
                        ON CONFLICT (id) DO NOTHING
                    """, (
                        entry['id'],
                        corporation_id,
                        division,
                        entry['amount'],
                        entry.get('balance'),
                        entry.get('context_id'),
                        entry.get('context_id_type'),
                        entry['date'],
                        entry.get('description'),
                        entry.get('first_party_id'),
                        entry.get('second_party_id'),
                        entry.get('reason'),
                        entry['ref_type'],
                        entry.get('tax'),
                        entry.get('tax_receiver_id')
                    ))
                synced_entries += 1

        except Exception as e:
            logger.warning(f"Failed to fetch journal for division {division}: {e}")

    return {
        "message": "Sync completed",
        "corporation_id": corporation_id,
        "divisions_synced": synced_divisions,
        "journal_entries_synced": synced_entries
    }


@router.get("/journal/{corporation_id}")
def get_journal(
    corporation_id: int,
    division: Optional[int] = Query(None, ge=1, le=7),
    days: int = Query(30, ge=1, le=90),
    ref_type: Optional[str] = Query(None),
    min_amount: Optional[float] = Query(None),
    limit: int = Query(100, ge=1, le=1000)
):
    """Get wallet journal entries from cache."""
    with db_cursor() as cur:
        query = """
            SELECT id, division, amount, balance, date, description,
                   ref_type, first_party_id, second_party_id, reason
            FROM corp_wallet_journal
            WHERE corporation_id = %s
              AND date > NOW() - INTERVAL '%s days'
        """
        params = [corporation_id, days]

        if division:
            query += " AND division = %s"
            params.append(division)
        if ref_type:
            query += " AND ref_type = %s"
            params.append(ref_type)
        if min_amount:
            query += " AND ABS(amount) >= %s"
            params.append(min_amount)

        query += " ORDER BY date DESC LIMIT %s"
        params.append(limit)

        cur.execute(query, params)
        rows = cur.fetchall()

    return {
        "corporation_id": corporation_id,
        "count": len(rows),
        "entries": [{
            "id": row['id'],
            "division": row['division'],
            "amount": float(row['amount']),
            "balance": float(row['balance']) if row['balance'] else None,
            "date": row['date'].isoformat(),
            "description": row['description'],
            "ref_type": row['ref_type'],
            "category": categorize_ref_type(row['ref_type']),
            "first_party_id": row['first_party_id'],
            "second_party_id": row['second_party_id'],
            "reason": row['reason']
        } for row in rows]
    }


@router.get("/income/{corporation_id}")
def get_income_analysis(
    corporation_id: int,
    days: int = Query(30, ge=1, le=90)
):
    """Analyze income and expenses by category."""
    with db_cursor() as cur:
        # Daily totals
        cur.execute("""
            SELECT
                DATE_TRUNC('day', date) as day,
                SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as income,
                SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as expenses
            FROM corp_wallet_journal
            WHERE corporation_id = %s
              AND date > NOW() - INTERVAL '%s days'
            GROUP BY DATE_TRUNC('day', date)
            ORDER BY day DESC
        """, (corporation_id, days))
        daily = [{
            "day": row['day'].isoformat()[:10],
            "income": float(row['income']),
            "expenses": float(row['expenses']),
            "net": float(row['income'] - row['expenses'])
        } for row in cur.fetchall()]

        # By ref_type
        cur.execute("""
            SELECT
                ref_type,
                SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as income,
                SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as expenses,
                COUNT(*) as count
            FROM corp_wallet_journal
            WHERE corporation_id = %s
              AND date > NOW() - INTERVAL '%s days'
            GROUP BY ref_type
            ORDER BY income DESC, expenses DESC
        """, (corporation_id, days))
        by_type = [{
            "ref_type": row['ref_type'],
            "category": categorize_ref_type(row['ref_type']),
            "income": float(row['income']),
            "expenses": float(row['expenses']),
            "count": row['count']
        } for row in cur.fetchall()]

    total_income = sum(d['income'] for d in daily)
    total_expenses = sum(d['expenses'] for d in daily)

    return {
        "corporation_id": corporation_id,
        "period_days": days,
        "summary": {
            "total_income": total_income,
            "total_expenses": total_expenses,
            "net_change": total_income - total_expenses,
            "daily_average_income": total_income / days if days > 0 else 0,
            "daily_average_expenses": total_expenses / days if days > 0 else 0
        },
        "daily": daily,
        "by_ref_type": by_type
    }


@router.get("/tax-income/{corporation_id}")
def get_tax_income(
    corporation_id: int,
    days: int = Query(30, ge=1, le=90)
):
    """Get tax income breakdown."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT
                DATE_TRUNC('day', date) as day,
                SUM(CASE WHEN ref_type = 'corporate_reward_tax' THEN amount ELSE 0 END) as bounty_tax,
                SUM(CASE WHEN ref_type = 'industry_job_tax' THEN amount ELSE 0 END) as industry_tax,
                SUM(CASE WHEN ref_type = 'planetary_export_tax' THEN amount ELSE 0 END) as pi_tax,
                SUM(CASE WHEN ref_type = 'reprocessing_tax' THEN amount ELSE 0 END) as reprocessing_tax
            FROM corp_wallet_journal
            WHERE corporation_id = %s
              AND date > NOW() - INTERVAL '%s days'
              AND ref_type IN ('corporate_reward_tax', 'industry_job_tax', 'planetary_export_tax', 'reprocessing_tax')
            GROUP BY DATE_TRUNC('day', date)
            ORDER BY day DESC
        """, (corporation_id, days))
        daily = [{
            "day": row['day'].isoformat()[:10],
            "bounty_tax": float(row['bounty_tax']),
            "industry_tax": float(row['industry_tax']),
            "pi_tax": float(row['pi_tax']),
            "reprocessing_tax": float(row['reprocessing_tax']),
            "total": float(row['bounty_tax'] + row['industry_tax'] + row['pi_tax'] + row['reprocessing_tax'])
        } for row in cur.fetchall()]

    totals = {
        "bounty_tax": sum(d['bounty_tax'] for d in daily),
        "industry_tax": sum(d['industry_tax'] for d in daily),
        "pi_tax": sum(d['pi_tax'] for d in daily),
        "reprocessing_tax": sum(d['reprocessing_tax'] for d in daily)
    }
    totals['total'] = sum(totals.values())

    return {
        "corporation_id": corporation_id,
        "period_days": days,
        "totals": totals,
        "daily": daily
    }


@router.get("/large-transactions/{corporation_id}")
def get_large_transactions(
    corporation_id: int,
    min_amount: float = Query(100000000, description="Minimum amount (default 100M)"),
    days: int = Query(30, ge=1, le=90),
    limit: int = Query(50, ge=1, le=200)
):
    """Get large transactions."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT id, division, amount, date, ref_type, description,
                   first_party_id, second_party_id, reason
            FROM corp_wallet_journal
            WHERE corporation_id = %s
              AND ABS(amount) >= %s
              AND date > NOW() - INTERVAL '%s days'
            ORDER BY ABS(amount) DESC
            LIMIT %s
        """, (corporation_id, min_amount, days, limit))
        rows = cur.fetchall()

    return {
        "corporation_id": corporation_id,
        "min_amount": min_amount,
        "count": len(rows),
        "transactions": [{
            "id": row['id'],
            "division": row['division'],
            "amount": float(row['amount']),
            "date": row['date'].isoformat(),
            "ref_type": row['ref_type'],
            "description": row['description'],
            "first_party_id": row['first_party_id'],
            "second_party_id": row['second_party_id'],
            "reason": row['reason']
        } for row in rows]
    }


@router.get("/srp-analysis/{corporation_id}")
def get_srp_analysis(
    corporation_id: int,
    division: int = Query(1, ge=1, le=7, description="SRP wallet division"),
    days: int = Query(30, ge=1, le=90)
):
    """Analyze SRP (Ship Replacement Program) fund activity."""
    with db_cursor() as cur:
        # Get current balance
        cur.execute("""
            SELECT balance FROM corp_wallet_divisions
            WHERE corporation_id = %s AND division = %s
        """, (corporation_id, division))
        balance_row = cur.fetchone()
        current_balance = float(balance_row['balance']) if balance_row and balance_row['balance'] else 0

        # Get payouts (negative amounts, usually player_donation or corp withdrawal)
        cur.execute("""
            SELECT
                DATE_TRUNC('day', date) as day,
                SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as payouts,
                SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as deposits,
                COUNT(CASE WHEN amount < 0 THEN 1 END) as payout_count
            FROM corp_wallet_journal
            WHERE corporation_id = %s
              AND division = %s
              AND date > NOW() - INTERVAL '%s days'
            GROUP BY DATE_TRUNC('day', date)
            ORDER BY day DESC
        """, (corporation_id, division, days))
        daily = [{
            "day": row['day'].isoformat()[:10],
            "payouts": float(row['payouts']),
            "deposits": float(row['deposits']),
            "payout_count": row['payout_count']
        } for row in cur.fetchall()]

    total_payouts = sum(d['payouts'] for d in daily)
    total_deposits = sum(d['deposits'] for d in daily)
    avg_daily_payout = total_payouts / days if days > 0 else 0

    # Estimate days of runway
    days_runway = current_balance / avg_daily_payout if avg_daily_payout > 0 else float('inf')

    return {
        "corporation_id": corporation_id,
        "division": division,
        "period_days": days,
        "current_balance": current_balance,
        "total_payouts": total_payouts,
        "total_deposits": total_deposits,
        "net_change": total_deposits - total_payouts,
        "average_daily_payout": avg_daily_payout,
        "estimated_runway_days": round(days_runway, 1) if days_runway != float('inf') else None,
        "daily": daily
    }
