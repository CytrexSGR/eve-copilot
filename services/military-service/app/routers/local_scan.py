"""Local Scan Analysis — Cross-reference pilot names with intel databases.

Accepts a list of pilot names (from local chat copy-paste) and checks them
against red_list_entities, killmail history, and character data to identify
threats, known hostiles, and fleet composition.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Body, Query
from pydantic import Field

from app.models.base import CamelModel
from app.database import sde_cursor
from eve_shared.utils.error_handling import handle_endpoint_errors

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Models
# =============================================================================

class LocalScanRequest(CamelModel):
    raw_text: str = Field(..., description="Pilot names from local chat, one per line")
    system_id: Optional[int] = Field(None, description="Current system ID for context")


class PilotIntel(CamelModel):
    character_name: str
    character_id: Optional[int] = None
    corporation_id: Optional[int] = None
    corporation_name: Optional[str] = None
    alliance_id: Optional[int] = None
    alliance_name: Optional[str] = None
    is_red_listed: bool = False
    red_list_severity: Optional[int] = None
    red_list_reason: Optional[str] = None
    recent_kills: int = 0
    recent_losses: int = 0
    last_ship_type: Optional[str] = None
    threat_level: str = "unknown"


class LocalScanResult(CamelModel):
    total_pilots: int
    identified: int
    unidentified: int
    red_listed: int
    hostiles: int
    threat_breakdown: dict
    pilots: list[PilotIntel]
    alliance_breakdown: list[dict]
    corporation_breakdown: list[dict]


# =============================================================================
# Helpers
# =============================================================================

def _parse_local_names(raw_text: str) -> list[str]:
    """Extract unique pilot names from local chat paste."""
    names = []
    seen = set()
    for line in raw_text.strip().splitlines():
        name = line.strip()
        if not name:
            continue
        lower = name.lower()
        if lower not in seen:
            seen.add(lower)
            names.append(name)
    return names


def _resolve_characters(names: list[str]) -> dict[str, dict]:
    """Resolve pilot names to character IDs and corp/alliance via killmail data."""
    if not names:
        return {}

    result: dict[str, dict] = {}
    # Batch resolve from killmail_attackers (most complete pilot data we have)
    with sde_cursor() as cur:
        for i in range(0, len(names), 200):
            chunk = names[i:i + 200]
            placeholders = ",".join(["%s"] * len(chunk))
            # Use the most recent killmail per character for current corp/alliance
            cur.execute(f"""
                SELECT DISTINCT ON (ka.character_name)
                    ka.character_name,
                    ka.character_id,
                    ka.corporation_id,
                    ka.alliance_id,
                    k.killmail_time,
                    st."typeName" AS last_ship
                FROM killmail_attackers ka
                JOIN killmails k ON ka.killmail_id = k.killmail_id
                LEFT JOIN "invTypes" st ON ka.ship_type_id = st."typeID"
                WHERE LOWER(ka.character_name) IN ({placeholders})
                  AND ka.character_id IS NOT NULL
                ORDER BY ka.character_name, k.killmail_time DESC
            """, [n.lower() for n in chunk])

            for row in cur.fetchall():
                cname = row["character_name"]
                result[cname.lower()] = {
                    "character_name": cname,
                    "character_id": row["character_id"],
                    "corporation_id": row["corporation_id"],
                    "alliance_id": row["alliance_id"],
                    "last_ship_type": row["last_ship"],
                }

    return result


def _check_red_list(character_ids: list[int], corp_ids: list[int], alliance_ids: list[int]) -> dict[int, dict]:
    """Check entities against red_list_entities. Returns entity_id -> red list info."""
    if not character_ids and not corp_ids and not alliance_ids:
        return {}

    red_map: dict[int, dict] = {}
    with sde_cursor() as cur:
        all_ids = character_ids + corp_ids + alliance_ids
        if not all_ids:
            return red_map
        placeholders = ",".join(["%s"] * len(all_ids))
        cur.execute(f"""
            SELECT entity_id, severity, reason, category
            FROM red_list_entities
            WHERE active = TRUE
              AND entity_id IN ({placeholders})
        """, all_ids)
        for row in cur.fetchall():
            red_map[row["entity_id"]] = {
                "severity": row["severity"],
                "reason": row["reason"],
                "category": row["category"],
            }
    return red_map


def _get_recent_activity(character_ids: list[int], days: int = 7) -> dict[int, dict]:
    """Get recent kill/loss counts for characters."""
    if not character_ids:
        return {}

    activity: dict[int, dict] = {}
    with sde_cursor() as cur:
        placeholders = ",".join(["%s"] * len(character_ids))

        # Kills (as attacker)
        cur.execute(f"""
            SELECT ka.character_id, COUNT(DISTINCT ka.killmail_id) AS kills
            FROM killmail_attackers ka
            JOIN killmails k ON ka.killmail_id = k.killmail_id
            WHERE ka.character_id IN ({placeholders})
              AND k.killmail_time > NOW() - INTERVAL {days} days
            GROUP BY ka.character_id
        """, character_ids)
        for row in cur.fetchall():
            cid = row["character_id"]
            activity[cid] = {"kills": row["kills"], "losses": 0}

        # Losses (as victim)
        cur.execute(f"""
            SELECT k.victim_character_id AS character_id,
                   COUNT(*) AS losses
            FROM killmails k
            WHERE k.victim_character_id IN ({placeholders})
              AND k.killmail_time > NOW() - INTERVAL {days} days
            GROUP BY k.victim_character_id
        """, character_ids)
        for row in cur.fetchall():
            cid = row["character_id"]
            if cid in activity:
                activity[cid]["losses"] = row["losses"]
            else:
                activity[cid] = {"kills": 0, "losses": row["losses"]}

    return activity


def _resolve_names(corp_ids: list[int], alliance_ids: list[int]) -> tuple[dict, dict]:
    """Resolve corporation and alliance names from reference tables."""
    corp_names: dict[int, str] = {}
    alliance_names: dict[int, str] = {}

    with sde_cursor() as cur:
        if corp_ids:
            placeholders = ",".join(["%s"] * len(corp_ids))
            cur.execute(f"""
                SELECT corporation_id, corporation_name
                FROM corporations
                WHERE corporation_id IN ({placeholders})
            """, corp_ids)
            for row in cur.fetchall():
                corp_names[row["corporation_id"]] = row["corporation_name"]

        if alliance_ids:
            placeholders = ",".join(["%s"] * len(alliance_ids))
            cur.execute(f"""
                SELECT alliance_id, alliance_name
                FROM alliance_name_cache
                WHERE alliance_id IN ({placeholders})
            """, alliance_ids)
            for row in cur.fetchall():
                alliance_names[row["alliance_id"]] = row["alliance_name"]

    return corp_names, alliance_names


def _assess_pilot_threat(pilot: PilotIntel) -> str:
    """Assess individual pilot threat level."""
    if pilot.is_red_listed and pilot.red_list_severity and pilot.red_list_severity >= 4:
        return "critical"
    if pilot.is_red_listed:
        return "high"
    if pilot.recent_kills >= 20:
        return "high"
    if pilot.recent_kills >= 5:
        return "medium"
    if pilot.recent_kills >= 1:
        return "low"
    return "unknown"


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/local/analyze", response_model=LocalScanResult)
@handle_endpoint_errors()
def analyze_local_scan(
    req: LocalScanRequest = Body(...),
    days: int = Query(7, ge=1, le=90, description="Days of history to check"),
):
    """Analyze local chat pilot names against intel databases."""
    names = _parse_local_names(req.raw_text)
    if not names:
        return LocalScanResult(
            total_pilots=0, identified=0, unidentified=0,
            red_listed=0, hostiles=0, threat_breakdown={},
            pilots=[], alliance_breakdown=[], corporation_breakdown=[],
        )

    # Step 1: Resolve character names -> IDs + corp/alliance
    char_data = _resolve_characters(names)

    # Step 2: Collect entity IDs for red list check
    char_ids = [d["character_id"] for d in char_data.values() if d.get("character_id")]
    corp_ids = list({d["corporation_id"] for d in char_data.values() if d.get("corporation_id")})
    alliance_ids = list({d["alliance_id"] for d in char_data.values() if d.get("alliance_id")})

    # Step 3: Red list + activity lookups
    red_map = _check_red_list(char_ids, corp_ids, alliance_ids)
    activity = _get_recent_activity(char_ids, days=days)
    corp_names, alliance_names_map = _resolve_names(corp_ids, alliance_ids)

    # Step 4: Build pilot intel objects
    pilots: list[PilotIntel] = []
    red_count = 0
    hostile_count = 0
    threat_counts: dict[str, int] = {}

    # Alliance/corp aggregation
    alliance_counts: dict[int, dict] = {}
    corp_counts: dict[int, dict] = {}

    for name in names:
        data = char_data.get(name.lower())
        if data:
            cid = data.get("character_id")
            corp_id = data.get("corporation_id")
            aid = data.get("alliance_id")

            # Check red list for char, corp, alliance
            is_red = False
            red_severity = None
            red_reason = None
            for eid in [cid, corp_id, aid]:
                if eid and eid in red_map:
                    is_red = True
                    red_info = red_map[eid]
                    if red_severity is None or red_info["severity"] > red_severity:
                        red_severity = red_info["severity"]
                        red_reason = red_info["reason"]

            act = activity.get(cid, {})

            pilot = PilotIntel(
                character_name=data["character_name"],
                character_id=cid,
                corporation_id=corp_id,
                corporation_name=corp_names.get(corp_id) if corp_id else None,
                alliance_id=aid,
                alliance_name=alliance_names_map.get(aid) if aid else None,
                is_red_listed=is_red,
                red_list_severity=red_severity,
                red_list_reason=red_reason,
                recent_kills=act.get("kills", 0),
                recent_losses=act.get("losses", 0),
                last_ship_type=data.get("last_ship_type"),
            )
            pilot.threat_level = _assess_pilot_threat(pilot)

            if is_red:
                red_count += 1
            if pilot.threat_level in ("high", "critical"):
                hostile_count += 1

            threat_counts[pilot.threat_level] = threat_counts.get(pilot.threat_level, 0) + 1

            # Alliance aggregation
            if aid:
                if aid not in alliance_counts:
                    alliance_counts[aid] = {
                        "alliance_id": aid,
                        "alliance_name": alliance_names_map.get(aid, f"Alliance {aid}"),
                        "count": 0,
                    }
                alliance_counts[aid]["count"] += 1

            # Corp aggregation
            if corp_id:
                if corp_id not in corp_counts:
                    corp_counts[corp_id] = {
                        "corporation_id": corp_id,
                        "corporation_name": corp_names.get(corp_id, f"Corp {corp_id}"),
                        "count": 0,
                    }
                corp_counts[corp_id]["count"] += 1

        else:
            pilot = PilotIntel(
                character_name=name,
                threat_level="unknown",
            )
            threat_counts["unknown"] = threat_counts.get("unknown", 0) + 1

        pilots.append(pilot)

    # Sort: red-listed first, then by threat level
    threat_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "unknown": 4}
    pilots.sort(key=lambda p: (threat_order.get(p.threat_level, 5), not p.is_red_listed))

    identified = sum(1 for p in pilots if p.character_id)
    alliance_breakdown = sorted(alliance_counts.values(), key=lambda a: -a["count"])
    corporation_breakdown = sorted(corp_counts.values(), key=lambda c: -c["count"])

    return LocalScanResult(
        total_pilots=len(pilots),
        identified=identified,
        unidentified=len(pilots) - identified,
        red_listed=red_count,
        hostiles=hostile_count,
        threat_breakdown=threat_counts,
        pilots=pilots,
        alliance_breakdown=alliance_breakdown,
        corporation_breakdown=corporation_breakdown,
    )
