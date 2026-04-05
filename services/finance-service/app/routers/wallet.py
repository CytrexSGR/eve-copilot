"""Corp Wallet Journal - Sync, gap-filling, and query endpoints."""

from typing import List, Optional

from fastapi import APIRouter, Request, Query

from eve_shared import get_db
from eve_shared.utils.error_handling import handle_endpoint_errors

from app.models import (
    WalletJournalEntry,
    WalletSyncRequest,
    WalletSyncResult,
    WalletDivision,
)
from app.services.wallet_sync import WalletSyncService

router = APIRouter(prefix="/wallet", tags=["Wallet"])


@router.get("/journal/{corporation_id}", response_model=List[WalletJournalEntry])
@handle_endpoint_errors()
def get_wallet_journal(
    request: Request,
    corporation_id: int,
    division_id: int = Query(1, ge=1, le=7),
    ref_type: Optional[str] = None,
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
):
    """Get corporation wallet journal entries from local database."""
    db = get_db()
    with db.cursor() as cur:
        if ref_type:
            cur.execute(
                """SELECT transaction_id, corporation_id, division_id, date,
                          ref_type, first_party_id, second_party_id,
                          amount, balance, reason, extra_info
                   FROM corp_wallet_journal
                   WHERE corporation_id = %s AND division_id = %s AND ref_type = %s
                   ORDER BY date DESC
                   LIMIT %s OFFSET %s""",
                (corporation_id, division_id, ref_type, limit, offset),
            )
        else:
            cur.execute(
                """SELECT transaction_id, corporation_id, division_id, date,
                          ref_type, first_party_id, second_party_id,
                          amount, balance, reason, extra_info
                   FROM corp_wallet_journal
                   WHERE corporation_id = %s AND division_id = %s
                   ORDER BY date DESC
                   LIMIT %s OFFSET %s""",
                (corporation_id, division_id, limit, offset),
            )
        rows = cur.fetchall()

    # Resolve ref_type labels from ref_types table
    ref_type_labels = _get_ref_type_labels()

    result = []
    for row in rows:
        entry = WalletJournalEntry(
            transaction_id=row["transaction_id"],
            corporation_id=row["corporation_id"],
            division_id=row["division_id"],
            date=row["date"],
            ref_type=row["ref_type"],
            ref_type_label=ref_type_labels.get(row["ref_type"]),
            first_party_id=row["first_party_id"],
            second_party_id=row["second_party_id"],
            amount=row["amount"],
            balance=row["balance"],
            reason=row["reason"],
            extra_info=row["extra_info"] or {},
        )
        result.append(entry)

    return result


@router.post("/sync", response_model=WalletSyncResult)
@handle_endpoint_errors()
async def sync_wallet(request: Request, sync_req: WalletSyncRequest):
    """Trigger wallet journal sync with gap-filling algorithm."""
    service = WalletSyncService()

    if sync_req.all_divisions:
        results = await service.sync_all_divisions(
            sync_req.corporation_id, sync_req.character_id
        )
        # Aggregate results
        total_new = sum(r["new_entries"] for r in results)
        total_gaps = sum(r.get("gaps_filled", 0) for r in results)
        total_pages = sum(r["pages_fetched"] for r in results)
        return WalletSyncResult(
            corporation_id=sync_req.corporation_id,
            division_id=0,  # 0 = all divisions
            new_entries=total_new,
            gaps_filled=total_gaps,
            pages_fetched=total_pages,
        )

    result = await service.sync_journal(
        sync_req.corporation_id, sync_req.division_id, sync_req.character_id
    )
    return WalletSyncResult(
        corporation_id=result["corporation_id"],
        division_id=result["division_id"],
        new_entries=result["new_entries"],
        gaps_filled=result.get("gaps_filled", 0),
        pages_fetched=result["pages_fetched"],
    )


@router.get("/divisions/{corporation_id}", response_model=List[WalletDivision])
@handle_endpoint_errors()
def get_divisions(request: Request, corporation_id: int):
    """Get wallet division names for a corporation."""
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            "SELECT corporation_id, division_id, name FROM wallet_divisions "
            "WHERE corporation_id = %s ORDER BY division_id",
            (corporation_id,),
        )
        rows = cur.fetchall()

    if not rows:
        # Return default divisions if none cached
        return [
            WalletDivision(
                corporation_id=corporation_id, division_id=i, name=f"Division {i}"
            )
            for i in range(1, 8)
        ]

    return [
        WalletDivision(
            corporation_id=row["corporation_id"],
            division_id=row["division_id"],
            name=row["name"],
        )
        for row in rows
    ]


@router.get("/balance/{corporation_id}")
@handle_endpoint_errors()
def get_balance(
    request: Request,
    corporation_id: int,
    division_id: int = Query(1, ge=1, le=7),
):
    """Get latest balance for a wallet division from stored journal."""
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            """SELECT balance, date FROM corp_wallet_journal
               WHERE corporation_id = %s AND division_id = %s
               ORDER BY date DESC, transaction_id DESC
               LIMIT 1""",
            (corporation_id, division_id),
        )
        row = cur.fetchone()

    if not row:
        return {
            "corporation_id": corporation_id,
            "division_id": division_id,
            "balance": 0,
            "as_of": None,
        }

    return {
        "corporation_id": corporation_id,
        "division_id": division_id,
        "balance": float(row["balance"]),
        "as_of": row["date"].isoformat() if row["date"] else None,
    }


@router.get("/sync-state/{corporation_id}")
@handle_endpoint_errors()
def get_sync_state(request: Request, corporation_id: int):
    """Get sync state for all divisions of a corporation."""
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            """SELECT division_id, high_water_mark, last_sync_at,
                      pages_fetched, entries_added
               FROM wallet_sync_state
               WHERE corporation_id = %s
               ORDER BY division_id""",
            (corporation_id,),
        )
        rows = cur.fetchall()

    return [
        {
            "division_id": row["division_id"],
            "high_water_mark": row["high_water_mark"],
            "last_sync_at": row["last_sync_at"].isoformat() if row["last_sync_at"] else None,
            "pages_fetched": row["pages_fetched"],
            "entries_added": row["entries_added"],
        }
        for row in rows
    ]


# --- Helpers ---

_ref_labels_cache: dict = {}


def _get_ref_type_labels() -> dict:
    """Cache ref_type name→label_de mapping."""
    global _ref_labels_cache
    if _ref_labels_cache:
        return _ref_labels_cache
    try:
        db = get_db()
        with db.cursor() as cur:
            cur.execute("SELECT name, label_de FROM ref_types")
            rows = cur.fetchall()
        _ref_labels_cache = {row["name"]: row["label_de"] for row in rows}
    except Exception:
        pass
    return _ref_labels_cache
