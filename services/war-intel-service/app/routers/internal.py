"""Internal endpoints for scheduler-triggered jobs.

These endpoints are called by the scheduler-service to execute
background tasks that were previously run as subprocess scripts.
Not exposed via api-gateway.
"""

import asyncio
import logging
from datetime import datetime, timedelta

import httpx
from fastapi import APIRouter
from psycopg2.extras import RealDictCursor, execute_values

from app.database import db_cursor
from eve_shared.utils.error_handling import handle_endpoint_errors

logger = logging.getLogger(__name__)

router = APIRouter()

# ESI constants
ESI_BASE_URL = "https://esi.evetech.net/latest"
ESI_USER_AGENT = "EVE-CoPilot/1.0"

# Faction ID to name mapping
FACTIONS = {
    500001: "Caldari State",
    500002: "Minmatar Republic",
    500003: "Amarr Empire",
    500004: "Gallente Federation",
}


# ---------------------------------------------------------------------------
# Sovereignty Campaign Tracker
# ---------------------------------------------------------------------------

def _fetch_esi_campaigns() -> list | None:
    """Fetch sovereignty campaigns from ESI."""
    try:
        resp = httpx.get(
            f"{ESI_BASE_URL}/sovereignty/campaigns/",
            params={"datasource": "tranquility"},
            headers={"User-Agent": ESI_USER_AGENT},
            timeout=30,
        )
        if resp.status_code == 200:
            return resp.json()
        logger.error(f"ESI sov campaigns failed: HTTP {resp.status_code}")
        return None
    except Exception as e:
        logger.error(f"ESI sov campaigns error: {e}")
        return None


def _get_alliance_name(alliance_id: int) -> str:
    """Get alliance name from ESI."""
    try:
        resp = httpx.get(
            f"{ESI_BASE_URL}/alliances/{alliance_id}/",
            params={"datasource": "tranquility"},
            headers={"User-Agent": ESI_USER_AGENT},
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.json().get("name", f"Alliance {alliance_id}")
    except Exception:
        pass
    return f"Alliance {alliance_id}"


def refresh_sov_campaigns() -> dict:
    """Fetch sovereignty campaigns from ESI and sync to DB.

    Returns dict with new/updated/deleted counts.
    """
    campaigns = _fetch_esi_campaigns()
    if campaigns is None:
        return {"error": "Failed to fetch campaigns from ESI"}

    # Resolve alliance names
    alliance_cache = {}
    for campaign in campaigns:
        defender_id = campaign.get("defender_id")
        if defender_id:
            if defender_id not in alliance_cache:
                alliance_cache[defender_id] = _get_alliance_name(defender_id)
            campaign["defender_name"] = alliance_cache[defender_id]
        else:
            campaign["defender_name"] = None

    new = 0
    updated = 0

    with db_cursor(cursor_factory=RealDictCursor) as cur:
        for campaign in campaigns:
            start_time_str = campaign.get("start_time")
            start_time = None
            if start_time_str:
                start_time = datetime.fromisoformat(
                    start_time_str.replace("Z", "+00:00")
                )

            cur.execute(
                "SELECT id FROM sovereignty_campaigns WHERE campaign_id = %s",
                (campaign.get("campaign_id"),),
            )
            exists = cur.fetchone()

            if exists:
                cur.execute(
                    """UPDATE sovereignty_campaigns
                       SET event_type = %s, solar_system_id = %s,
                           constellation_id = %s, defender_id = %s,
                           defender_name = %s, attacker_score = %s,
                           defender_score = %s, start_time = %s,
                           structure_id = %s, last_updated_at = NOW()
                       WHERE campaign_id = %s""",
                    (
                        campaign.get("event_type"),
                        campaign.get("solar_system_id"),
                        campaign.get("constellation_id"),
                        campaign.get("defender_id"),
                        campaign.get("defender_name"),
                        campaign.get("attackers_score"),
                        campaign.get("defender_score"),
                        start_time,
                        campaign.get("structure_id"),
                        campaign.get("campaign_id"),
                    ),
                )
                updated += 1
            else:
                cur.execute(
                    """INSERT INTO sovereignty_campaigns (
                           campaign_id, event_type, solar_system_id, constellation_id,
                           defender_id, defender_name, attacker_score, defender_score,
                           start_time, structure_id, first_seen_at, last_updated_at
                       ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW(),NOW())""",
                    (
                        campaign.get("campaign_id"),
                        campaign.get("event_type"),
                        campaign.get("solar_system_id"),
                        campaign.get("constellation_id"),
                        campaign.get("defender_id"),
                        campaign.get("defender_name"),
                        campaign.get("attackers_score"),
                        campaign.get("defender_score"),
                        start_time,
                        campaign.get("structure_id"),
                    ),
                )
                new += 1

        # Cleanup old campaigns (>24h past start_time)
        cur.execute(
            "DELETE FROM sovereignty_campaigns WHERE start_time < NOW() - INTERVAL '24 hours'"
        )
        deleted = cur.rowcount

    return {
        "total_campaigns": len(campaigns),
        "new": new,
        "updated": updated,
        "deleted": deleted,
    }


@router.post("/internal/refresh-sov-campaigns")
@handle_endpoint_errors("refresh-sov-campaigns")
async def api_refresh_sov_campaigns():
    """Refresh sovereignty campaigns from ESI."""
    result = await asyncio.to_thread(refresh_sov_campaigns)
    if "error" in result:
        return {"status": "failed", "job": "sov-campaigns", "details": result}
    return {"status": "completed", "job": "sov-campaigns", "details": result}


# ---------------------------------------------------------------------------
# Faction Warfare Tracker
# ---------------------------------------------------------------------------

def _fetch_fw_systems() -> list | None:
    """Fetch FW system status from ESI."""
    try:
        resp = httpx.get(
            f"{ESI_BASE_URL}/fw/systems/",
            params={"datasource": "tranquility"},
            headers={"User-Agent": ESI_USER_AGENT},
            timeout=30,
        )
        if resp.status_code == 200:
            return resp.json()
        logger.error(f"ESI FW systems failed: HTTP {resp.status_code}")
        return None
    except Exception as e:
        logger.error(f"ESI FW systems error: {e}")
        return None


def refresh_fw_status() -> dict:
    """Fetch FW system status from ESI, snapshot to DB, cleanup old data.

    Returns dict with systems_updated, hotspots, deleted counts.
    """
    systems = _fetch_fw_systems()
    if not systems:
        return {"error": "Failed to fetch FW systems from ESI"}

    now = datetime.now()
    values = []
    for system in systems:
        solar_system_id = system.get("solar_system_id")
        owner_faction_id = system.get("owner_faction_id")
        occupier_faction_id = system.get("occupier_faction_id")
        contested = system.get("contested", "uncontested")
        victory_points = system.get("victory_points", 0)
        victory_points_threshold = system.get("victory_points_threshold", 3000)

        if solar_system_id and owner_faction_id and occupier_faction_id:
            values.append((
                solar_system_id,
                owner_faction_id,
                occupier_faction_id,
                contested,
                victory_points,
                victory_points_threshold,
                now,
            ))

    with db_cursor() as cur:
        if values:
            execute_values(
                cur,
                """INSERT INTO fw_system_status
                   (solar_system_id, owner_faction_id, occupier_faction_id,
                    contested, victory_points, victory_points_threshold, snapshot_time)
                   VALUES %s""",
                values,
                page_size=1000,
            )

        # Count hotspots (>70% contested) from this snapshot
        cur.execute(
            """SELECT COUNT(*) FROM fw_system_status
               WHERE snapshot_time = %s
                 AND (victory_points::numeric / victory_points_threshold * 100) >= 70""",
            (now,),
        )
        row = cur.fetchone()
        hotspot_count = row["count"] if isinstance(row, dict) else row[0]

        # Cleanup old snapshots (>7 days)
        cutoff = now - timedelta(days=7)
        cur.execute(
            "DELETE FROM fw_system_status WHERE snapshot_time < %s", (cutoff,)
        )
        deleted = cur.rowcount

    return {
        "systems_updated": len(values),
        "hotspots": hotspot_count,
        "snapshots_deleted": deleted,
    }


@router.post("/internal/refresh-fw-status")
@handle_endpoint_errors("refresh-fw-status")
async def api_refresh_fw_status():
    """Refresh faction warfare system status from ESI."""
    result = await asyncio.to_thread(refresh_fw_status)
    if "error" in result:
        return {"status": "failed", "job": "fw-status", "details": result}
    return {"status": "completed", "job": "fw-status", "details": result}


# ---------------------------------------------------------------------------
# Killmail Fetcher (daily archive import from EVE Ref)
# ---------------------------------------------------------------------------

def fetch_killmails_from_everef(target_date: datetime | None = None) -> dict:
    """Download and import killmail archive for a specific date.

    Args:
        target_date: Date to import (default: yesterday)

    Returns:
        Dict with imported/skipped/items counts.
    """
    import json
    import tarfile
    import tempfile
    from pathlib import Path

    if target_date is None:
        target_date = datetime.now() - timedelta(days=1)

    year = target_date.strftime("%Y")
    date_str = target_date.strftime("%Y-%m-%d")
    filename = f"killmails-{date_str}.tar.bz2"
    url = f"https://data.everef.net/killmails/{year}/{filename}"

    logger.info(f"Downloading killmail archive: {url}")

    try:
        resp = httpx.get(
            url,
            headers={"User-Agent": "EVE-Copilot/1.0 (Killmail Backfill)"},
            timeout=60,
            follow_redirects=True,
        )
        if resp.status_code == 404:
            return {"imported": 0, "skipped": 0, "items": 0, "note": f"No dump for {date_str}"}
        resp.raise_for_status()
    except Exception as e:
        return {"error": str(e)}

    # Save to temp file
    temp_path = Path(tempfile.gettempdir()) / filename
    temp_path.write_bytes(resp.content)
    size_mb = len(resp.content) / 1024 / 1024
    logger.info(f"Downloaded {size_mb:.2f} MB")

    imported = 0
    skipped = 0
    items_imported = 0

    try:
        from app.database import get_db_connection, release_db_connection
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            with tarfile.open(str(temp_path), "r:bz2") as tar:
                members = tar.getmembers()
                total = len(members)
                logger.info(f"Processing {total} killmails...")

                for i, member in enumerate(members):
                    if not member.name.endswith(".json"):
                        continue
                    try:
                        f = tar.extractfile(member)
                        if f is None:
                            continue
                        data = json.loads(f.read().decode("utf-8"))
                        killmail_id = data.get("killmail_id")
                        if not killmail_id:
                            skipped += 1
                            continue

                        # Check existence
                        cur.execute("SELECT 1 FROM killmails WHERE killmail_id = %s", (killmail_id,))
                        if cur.fetchone():
                            skipped += 1
                            continue

                        killmail_time = data.get("killmail_time")
                        solar_system_id = data.get("solar_system_id")
                        victim = data.get("victim", {})
                        zkb = data.get("zkb", {})
                        attackers = data.get("attackers", [])
                        final_blow = next(
                            (a for a in attackers if a.get("final_blow")),
                            attackers[0] if attackers else {},
                        )

                        # Get region
                        cur.execute(
                            "SELECT region_id FROM system_region_map WHERE solar_system_id = %s",
                            (solar_system_id,),
                        )
                        row = cur.fetchone()
                        region_id = row[0] if row else None

                        cur.execute(
                            """INSERT INTO killmails (
                                   killmail_id, killmail_time, solar_system_id, region_id,
                                   ship_type_id, ship_value,
                                   victim_character_id, victim_corporation_id, victim_alliance_id,
                                   final_blow_character_id, final_blow_corporation_id, final_blow_alliance_id,
                                   attacker_count
                               ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                               ON CONFLICT (killmail_id) DO NOTHING""",
                            (
                                killmail_id, killmail_time, solar_system_id, region_id,
                                victim.get("ship_type_id"), zkb.get("totalValue", 0),
                                victim.get("character_id"), victim.get("corporation_id"), victim.get("alliance_id"),
                                final_blow.get("character_id"), final_blow.get("corporation_id"),
                                final_blow.get("alliance_id"),
                                len(attackers),
                            ),
                        )

                        # Import items
                        for item in victim.get("items", []):
                            item_type_id = item.get("item_type_id")
                            if not item_type_id:
                                continue
                            qty_destroyed = item.get("quantity_destroyed", 0)
                            qty_dropped = item.get("quantity_dropped", 0)
                            flag = item.get("flag")
                            singleton = item.get("singleton")
                            if qty_destroyed > 0:
                                cur.execute(
                                    """INSERT INTO killmail_items
                                       (killmail_id, item_type_id, quantity, was_destroyed, flag, singleton)
                                       VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
                                    (killmail_id, item_type_id, qty_destroyed, True, flag, singleton),
                                )
                                items_imported += 1
                            if qty_dropped > 0:
                                cur.execute(
                                    """INSERT INTO killmail_items
                                       (killmail_id, item_type_id, quantity, was_destroyed, flag, singleton)
                                       VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
                                    (killmail_id, item_type_id, qty_dropped, False, flag, singleton),
                                )
                                items_imported += 1

                        imported += 1

                        if (i + 1) % 1000 == 0:
                            conn.commit()
                            logger.info(f"Progress: {i+1}/{total} ({imported} imported, {skipped} skipped)")

                    except Exception as e:
                        skipped += 1
                        if skipped <= 5:
                            logger.warning(f"Error processing {member.name}: {e}")

                conn.commit()
            cur.close()
        finally:
            release_db_connection(conn)
    finally:
        if temp_path.exists():
            temp_path.unlink()

    return {"imported": imported, "skipped": skipped, "items": items_imported, "date": date_str}


@router.post("/internal/fetch-killmails")
@handle_endpoint_errors("fetch-killmails")
async def api_fetch_killmails():
    """Fetch yesterday's killmails from EVE Ref archive."""
    result = await asyncio.to_thread(fetch_killmails_from_everef)
    if "error" in result:
        return {"status": "failed", "job": "killmail-fetcher", "details": result}
    return {"status": "completed", "job": "killmail-fetcher", "details": result}


# ---------------------------------------------------------------------------
# Everef Killmail Importer (alias -- same logic as fetch-killmails)
# ---------------------------------------------------------------------------

@router.post("/internal/import-everef")
@handle_endpoint_errors("import-everef")
async def api_import_everef():
    """Import killmails from EVE Ref daily dump (yesterday)."""
    result = await asyncio.to_thread(fetch_killmails_from_everef)
    if "error" in result:
        return {"status": "failed", "job": "everef-importer", "details": result}
    return {"status": "completed", "job": "everef-importer", "details": result}
