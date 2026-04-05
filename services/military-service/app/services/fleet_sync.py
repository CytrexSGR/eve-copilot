"""Fleet Sync Service -- Background ESI polling for live fleet member data.

Polls ESI /fleets/{fleet_id}/members/ every 60 seconds per active operation,
creates fleet snapshots, and upserts fleet_participation records.

Supports up to 10 concurrent sync tasks. After 3 consecutive errors,
sync stops automatically for that operation.
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from typing import Dict, Optional

import httpx

from app.database import db_cursor

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8000")
ESI_BASE_URL = "https://esi.evetech.net/latest"
POLL_INTERVAL = 60          # seconds between ESI polls
MAX_CONCURRENT_SYNCS = 10
MAX_CONSECUTIVE_ERRORS = 3

# ---------------------------------------------------------------------------
# In-memory state for active sync tasks
# ---------------------------------------------------------------------------
_active_syncs: Dict[int, dict] = {}
# Structure: { operation_id: { "task": asyncio.Task, "esi_fleet_id": int,
#   "fc_character_id": int, "started_at": str, "last_sync": str|None,
#   "error_count": int, "last_error": str|None, "snapshot_count": int } }


# ---------------------------------------------------------------------------
# ESI Token retrieval (via auth-service)
# ---------------------------------------------------------------------------
async def _get_esi_token(character_id: int) -> str:
    """Fetch a valid ESI access_token from auth-service for the given character."""
    url = f"{AUTH_SERVICE_URL}/api/auth/token/{character_id}"
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(url)

    if r.status_code != 200:
        raise RuntimeError(
            f"Failed to get ESI token for character {character_id}: "
            f"{r.status_code} {r.text[:200]}"
        )

    data = r.json()
    token = data.get("access_token")
    if not token:
        raise RuntimeError(f"No access_token in auth-service response for character {character_id}")
    return token


# ---------------------------------------------------------------------------
# ESI Fleet Members fetch
# ---------------------------------------------------------------------------
async def _fetch_fleet_members(esi_fleet_id: int, token: str) -> list[dict]:
    """Call ESI GET /fleets/{fleet_id}/members/ and return the member list."""
    url = f"{ESI_BASE_URL}/fleets/{esi_fleet_id}/members/"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(url, headers=headers)

    if r.status_code == 404:
        raise RuntimeError(f"Fleet {esi_fleet_id} not found (404) -- fleet may have ended")
    if r.status_code == 403:
        raise RuntimeError(f"No access to fleet {esi_fleet_id} (403) -- FC may have changed")
    if r.status_code != 200:
        raise RuntimeError(
            f"ESI fleet members error: {r.status_code} {r.text[:200]}"
        )

    return r.json()


# ---------------------------------------------------------------------------
# Snapshot creation + participation upsert
# ---------------------------------------------------------------------------
def _create_snapshot(operation_id: int, members: list[dict]) -> int:
    """Store a fleet snapshot and upsert fleet_participation records.

    Returns the snapshot id.
    """
    now = datetime.now(timezone.utc)

    with db_cursor() as cur:
        # Insert snapshot
        cur.execute(
            """INSERT INTO fleet_snapshots (operation_id, snapshot_time, member_count, raw_data)
               VALUES (%s, %s, %s, %s)
               RETURNING id""",
            (operation_id, now, len(members), json.dumps(members)),
        )
        snapshot_id = cur.fetchone()["id"]

        # Upsert each member into fleet_participation
        for m in members:
            character_id = m.get("character_id")
            if not character_id:
                continue

            cur.execute(
                """INSERT INTO fleet_participation
                       (operation_id, character_id, character_name, ship_type_id,
                        solar_system_id, first_seen, last_seen, snapshot_count)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, 1)
                   ON CONFLICT (operation_id, character_id)
                   DO UPDATE SET
                       ship_type_id    = EXCLUDED.ship_type_id,
                       solar_system_id = EXCLUDED.solar_system_id,
                       last_seen       = EXCLUDED.last_seen,
                       snapshot_count   = fleet_participation.snapshot_count + 1
                """,
                (
                    operation_id,
                    character_id,
                    m.get("character_name") or f"Character #{character_id}",
                    m.get("ship_type_id"),
                    m.get("solar_system_id"),
                    now,
                    now,
                ),
            )

        # Update fleet_operations sync metadata
        cur.execute(
            """UPDATE fleet_operations
               SET last_sync_at = %s, sync_error = NULL
               WHERE id = %s""",
            (now, operation_id),
        )

    return snapshot_id


# ---------------------------------------------------------------------------
# Background sync loop (one per operation)
# ---------------------------------------------------------------------------
async def _sync_loop(operation_id: int, esi_fleet_id: int, fc_character_id: int):
    """Background polling loop for a single fleet operation.

    Runs until cancelled or MAX_CONSECUTIVE_ERRORS is reached.
    """
    state = _active_syncs.get(operation_id)
    if not state:
        return

    logger.info(
        f"Fleet sync started: op={operation_id} fleet={esi_fleet_id} fc={fc_character_id}"
    )

    while True:
        try:
            # 1. Get fresh ESI token
            token = await _get_esi_token(fc_character_id)

            # 2. Fetch fleet members
            members = await _fetch_fleet_members(esi_fleet_id, token)

            # 3. Create snapshot (synchronous DB work, run in executor)
            loop = asyncio.get_running_loop()
            snapshot_id = await loop.run_in_executor(
                None, _create_snapshot, operation_id, members
            )

            # 4. Update in-memory state
            state["last_sync"] = datetime.now(timezone.utc).isoformat()
            state["error_count"] = 0
            state["last_error"] = None
            state["snapshot_count"] += 1

            logger.debug(
                f"Fleet sync snapshot #{snapshot_id}: op={operation_id} "
                f"members={len(members)} total_snapshots={state['snapshot_count']}"
            )

        except asyncio.CancelledError:
            logger.info(f"Fleet sync cancelled: op={operation_id}")
            raise
        except Exception as exc:
            state["error_count"] += 1
            state["last_error"] = str(exc)

            logger.warning(
                f"Fleet sync error ({state['error_count']}/{MAX_CONSECUTIVE_ERRORS}): "
                f"op={operation_id} -- {exc}"
            )

            # Persist error to DB
            try:
                with db_cursor() as cur:
                    cur.execute(
                        """UPDATE fleet_operations
                           SET sync_error = %s
                           WHERE id = %s""",
                        (str(exc)[:500], operation_id),
                    )
            except Exception:
                logger.error("Failed to persist sync error to DB", exc_info=True)

            # Stop after too many consecutive errors
            if state["error_count"] >= MAX_CONSECUTIVE_ERRORS:
                logger.error(
                    f"Fleet sync stopped after {MAX_CONSECUTIVE_ERRORS} consecutive errors: "
                    f"op={operation_id}"
                )
                # Mark sync inactive in DB
                try:
                    with db_cursor() as cur:
                        cur.execute(
                            """UPDATE fleet_operations
                               SET sync_active = FALSE, sync_error = %s
                               WHERE id = %s""",
                            (f"Stopped: {MAX_CONSECUTIVE_ERRORS} consecutive errors -- {exc}", operation_id),
                        )
                except Exception:
                    pass
                # Clean up in-memory state
                _active_syncs.pop(operation_id, None)
                return

        # Wait before next poll
        await asyncio.sleep(POLL_INTERVAL)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
async def start_sync(operation_id: int, esi_fleet_id: int, fc_character_id: int) -> bool:
    """Start background ESI sync for a fleet operation.

    Returns True if sync was started, False if already active.
    Raises RuntimeError if max concurrent syncs reached.
    """
    # Already syncing?
    if operation_id in _active_syncs:
        return False

    # Check concurrency limit
    if len(_active_syncs) >= MAX_CONCURRENT_SYNCS:
        raise RuntimeError(
            f"Maximum concurrent syncs ({MAX_CONCURRENT_SYNCS}) reached. "
            "Stop another sync first."
        )

    # Verify operation exists
    with db_cursor() as cur:
        cur.execute("SELECT id, is_active FROM fleet_operations WHERE id = %s", (operation_id,))
        op = cur.fetchone()
        if not op:
            raise RuntimeError(f"Operation {operation_id} not found")
        if not op["is_active"]:
            raise RuntimeError(f"Operation {operation_id} is closed")

    # Mark sync active in DB
    with db_cursor() as cur:
        cur.execute(
            """UPDATE fleet_operations
               SET sync_active = TRUE, esi_fleet_id = %s, sync_error = NULL
               WHERE id = %s""",
            (esi_fleet_id, operation_id),
        )

    # Create state + launch background task
    state = {
        "esi_fleet_id": esi_fleet_id,
        "fc_character_id": fc_character_id,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "last_sync": None,
        "error_count": 0,
        "last_error": None,
        "snapshot_count": 0,
    }
    _active_syncs[operation_id] = state

    task = asyncio.create_task(
        _sync_loop(operation_id, esi_fleet_id, fc_character_id),
        name=f"fleet_sync_{operation_id}",
    )
    state["task"] = task

    # Clean up on task completion (normal or error)
    def _on_done(t: asyncio.Task):
        _active_syncs.pop(operation_id, None)
        if t.cancelled():
            logger.info(f"Fleet sync task cleaned up (cancelled): op={operation_id}")
        elif t.exception():
            logger.error(
                f"Fleet sync task ended with error: op={operation_id}",
                exc_info=t.exception(),
            )

    task.add_done_callback(_on_done)

    logger.info(f"Fleet sync started: op={operation_id} esi_fleet={esi_fleet_id}")
    return True


async def stop_sync(operation_id: int) -> None:
    """Stop background ESI sync for a fleet operation."""
    state = _active_syncs.pop(operation_id, None)
    if state and "task" in state:
        state["task"].cancel()
        try:
            await state["task"]
        except asyncio.CancelledError:
            pass

    # Mark sync inactive in DB
    try:
        with db_cursor() as cur:
            cur.execute(
                """UPDATE fleet_operations
                   SET sync_active = FALSE
                   WHERE id = %s""",
                (operation_id,),
            )
    except Exception:
        logger.error(f"Failed to update sync_active=FALSE for op={operation_id}", exc_info=True)

    logger.info(f"Fleet sync stopped: op={operation_id}")


def get_sync_status(operation_id: int) -> dict:
    """Return current sync state for an operation."""
    state = _active_syncs.get(operation_id)

    if not state:
        # Check DB for historical state
        try:
            with db_cursor() as cur:
                cur.execute(
                    """SELECT sync_active, last_sync_at, sync_error
                       FROM fleet_operations WHERE id = %s""",
                    (operation_id,),
                )
                row = cur.fetchone()
                if row:
                    return {
                        "operation_id": operation_id,
                        "syncing": bool(row["sync_active"]),
                        "last_sync": row["last_sync_at"].isoformat() if row["last_sync_at"] else None,
                        "error": row["sync_error"],
                        "snapshot_count": 0,
                    }
        except Exception:
            pass

        return {
            "operation_id": operation_id,
            "syncing": False,
            "last_sync": None,
            "error": None,
            "snapshot_count": 0,
        }

    return {
        "operation_id": operation_id,
        "syncing": True,
        "esi_fleet_id": state["esi_fleet_id"],
        "fc_character_id": state["fc_character_id"],
        "started_at": state["started_at"],
        "last_sync": state["last_sync"],
        "error_count": state["error_count"],
        "last_error": state["last_error"],
        "snapshot_count": state["snapshot_count"],
    }
