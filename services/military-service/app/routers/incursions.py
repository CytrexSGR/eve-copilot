"""Incursions tracker: ESI public endpoint with name resolution."""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
import httpx

from app.database import get_sde_db

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Incursions"])

ESI_BASE = "https://esi.evetech.net/latest"


def _resolve_system_names(system_ids: list[int]) -> dict[int, dict]:
    """Resolve solar system IDs to names + security status from SDE."""
    if not system_ids:
        return {}
    conn = get_sde_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT "solarSystemID", "solarSystemName", security, "constellationID"
                FROM "mapSolarSystems"
                WHERE "solarSystemID" = ANY(%s)
            """, (system_ids,))
            return {
                r["solarSystemID"]: {
                    "name": r["solarSystemName"],
                    "security": round(float(r["security"]), 2) if r["security"] else 0.0,
                    "constellation_id": r["constellationID"],
                }
                for r in cur.fetchall()
            }
    finally:
        conn.close()


def _resolve_constellation_names(constellation_ids: list[int]) -> dict[int, dict]:
    """Resolve constellation IDs to names + region info from SDE."""
    if not constellation_ids:
        return {}
    conn = get_sde_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT c."constellationID", c."constellationName", c."regionID", r."regionName"
                FROM "mapConstellations" c
                JOIN "mapRegions" r ON r."regionID" = c."regionID"
                WHERE c."constellationID" = ANY(%s)
            """, (constellation_ids,))
            return {
                r["constellationID"]: {
                    "name": r["constellationName"],
                    "region_id": r["regionID"],
                    "region_name": r["regionName"],
                }
                for r in cur.fetchall()
            }
    finally:
        conn.close()


def _security_class(sec: float) -> str:
    """Return security classification for incursion sites."""
    if sec >= 0.5:
        return "highsec"
    elif sec > 0.0:
        return "lowsec"
    return "nullsec"


@router.get("/incursions")
async def get_incursions():
    """Get active incursions with resolved names."""
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(f"{ESI_BASE}/incursions/")
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail="ESI incursions request failed")
        incursions = resp.json()

    if not incursions:
        return {"incursions": [], "count": 0}

    # Collect all system and constellation IDs
    all_system_ids = []
    constellation_ids = []
    for inc in incursions:
        all_system_ids.extend(inc.get("infested_solar_systems", []))
        if inc.get("staging_solar_system_id"):
            all_system_ids.append(inc["staging_solar_system_id"])
        constellation_ids.append(inc["constellation_id"])

    # Resolve names
    systems = _resolve_system_names(list(set(all_system_ids)))
    constellations = _resolve_constellation_names(list(set(constellation_ids)))

    results = []
    for inc in incursions:
        con_id = inc["constellation_id"]
        con_info = constellations.get(con_id, {})
        staging_id = inc.get("staging_solar_system_id")
        staging_info = systems.get(staging_id, {})

        # Resolve infested systems
        infested = []
        for sid in inc.get("infested_solar_systems", []):
            sys_info = systems.get(sid, {})
            sec = sys_info.get("security", 0.0)
            infested.append({
                "system_id": sid,
                "system_name": sys_info.get("name", f"J{sid}"),
                "security": sec,
                "security_class": _security_class(sec),
            })

        # Sort by security descending
        infested.sort(key=lambda s: s["security"], reverse=True)

        # Determine overall security class from staging system
        staging_sec = staging_info.get("security", 0.0)

        results.append({
            "constellation_id": con_id,
            "constellation_name": con_info.get("name", f"Constellation {con_id}"),
            "region_id": con_info.get("region_id"),
            "region_name": con_info.get("region_name", "Unknown"),
            "state": inc.get("state", "unknown"),
            "influence": round(float(inc.get("influence", 0)), 4),
            "has_boss": inc.get("has_boss", False),
            "staging_system_id": staging_id,
            "staging_system_name": staging_info.get("name", f"System {staging_id}"),
            "staging_security": staging_sec,
            "security_class": _security_class(staging_sec),
            "infested_systems": infested,
            "system_count": len(infested),
            "type": inc.get("type", ""),
        })

    return {"incursions": results, "count": len(results)}


@router.get("/incursions/{constellation_id}")
async def get_incursion_detail(constellation_id: int):
    """Get detail for a specific incursion by constellation ID."""
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(f"{ESI_BASE}/incursions/")
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail="ESI incursions request failed")
        incursions = resp.json()

    target = None
    for inc in incursions:
        if inc["constellation_id"] == constellation_id:
            target = inc
            break

    if not target:
        raise HTTPException(status_code=404, detail="Incursion not found in this constellation")

    # Resolve names
    all_system_ids = target.get("infested_solar_systems", [])
    if target.get("staging_solar_system_id"):
        all_system_ids.append(target["staging_solar_system_id"])

    systems = _resolve_system_names(list(set(all_system_ids)))
    constellations = _resolve_constellation_names([constellation_id])
    con_info = constellations.get(constellation_id, {})

    staging_id = target.get("staging_solar_system_id")
    staging_info = systems.get(staging_id, {})

    infested = []
    for sid in target.get("infested_solar_systems", []):
        sys_info = systems.get(sid, {})
        sec = sys_info.get("security", 0.0)
        infested.append({
            "system_id": sid,
            "system_name": sys_info.get("name", f"J{sid}"),
            "security": sec,
            "security_class": _security_class(sec),
        })
    infested.sort(key=lambda s: s["security"], reverse=True)

    return {
        "constellation_id": constellation_id,
        "constellation_name": con_info.get("name", f"Constellation {constellation_id}"),
        "region_id": con_info.get("region_id"),
        "region_name": con_info.get("region_name", "Unknown"),
        "state": target.get("state", "unknown"),
        "influence": round(float(target.get("influence", 0)), 4),
        "has_boss": target.get("has_boss", False),
        "staging_system_id": staging_id,
        "staging_system_name": staging_info.get("name", f"System {staging_id}"),
        "staging_security": staging_info.get("security", 0.0),
        "type": target.get("type", ""),
        "infested_systems": infested,
        "system_count": len(infested),
    }
