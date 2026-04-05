"""Skyhook Telemetry & Metenox Drill Management.

Provides endpoints for:
- Skyhook status, cargo monitoring, vulnerability windows
- Metenox drill fuel tracking, yield prediction, time-to-dark alerts
- Manual sync endpoints for structure data
"""

import logging
from typing import Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Body, Query, Path, HTTPException
from pydantic import Field

from app.models.base import CamelModel
from app.database import db_cursor
from eve_shared.utils.error_handling import handle_endpoint_errors

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Skyhook Models
# =============================================================================

class SkyhookUpsertRequest(CamelModel):
    structure_id: int
    system_id: int
    planet_id: Optional[int] = None
    planet_type: Optional[str] = None
    type_id: Optional[int] = None
    structure_name: Optional[str] = None
    power_output: int = 0
    workforce_output: int = 0
    reagent_type: Optional[str] = None
    reagent_rate: int = 0
    reagent_stock: dict = Field(default_factory=dict)
    vulnerability_start: Optional[datetime] = None
    vulnerability_end: Optional[datetime] = None
    state: str = "online"


class MetenoxUpsertRequest(CamelModel):
    structure_id: int
    system_id: int
    moon_id: Optional[int] = None
    structure_name: Optional[str] = None
    moon_composition: dict = Field(default_factory=dict)
    fuel_blocks_qty: int = 0
    magmatic_gas_qty: int = 0
    fuel_expires: Optional[datetime] = None
    daily_yield_m3: float = 0
    accumulated_ore: dict = Field(default_factory=dict)
    output_bay_used_m3: float = 0
    output_bay_capacity_m3: float = 500000
    state: str = "online"


# =============================================================================
# Skyhook Endpoints
# =============================================================================

@router.get("/skyhooks")
@handle_endpoint_errors()
def list_skyhooks(
    system_id: Optional[int] = Query(None, description="Filter by system"),
    state: Optional[str] = Query(None, description="Filter by state (online, reinforced, etc.)"),
    planet_type: Optional[str] = Query(None, description="Filter by planet type"),
):
    """List all tracked skyhooks with status."""
    with db_cursor() as cur:
        where_clauses = []
        params = []

        if system_id is not None:
            where_clauses.append("sk.system_id = %s")
            params.append(system_id)
        if state:
            where_clauses.append("sk.state = %s")
            params.append(state)
        if planet_type:
            where_clauses.append("sk.planet_type = %s")
            params.append(planet_type)

        where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        cur.execute(f"""
            SELECT
                sk.structure_id, sk.system_id, sk.planet_id, sk.planet_type,
                sk.type_id, sk.structure_name,
                sk.power_output, sk.workforce_output,
                sk.reagent_type, sk.reagent_rate, sk.reagent_stock,
                sk.vulnerability_start, sk.vulnerability_end,
                sk.last_siphon_alert, sk.state, sk.last_updated,
                st.system_name, st.region_id,
                r."regionName" AS region_name
            FROM skyhook_status sk
            LEFT JOIN system_topology st ON sk.system_id = st.system_id
            LEFT JOIN "mapRegions" r ON st.region_id = r."regionID"
            {where_sql}
            ORDER BY st.system_name, sk.planet_type
        """, params)
        return [dict(r) for r in cur.fetchall()]


@router.get("/skyhooks/{structure_id}")
@handle_endpoint_errors()
def get_skyhook_detail(structure_id: int = Path(...)):
    """Get detailed telemetry for a specific skyhook."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT
                sk.structure_id, sk.system_id, sk.planet_id, sk.planet_type,
                sk.type_id, sk.structure_name,
                sk.power_output, sk.workforce_output,
                sk.reagent_type, sk.reagent_rate, sk.reagent_stock,
                sk.vulnerability_start, sk.vulnerability_end,
                sk.last_siphon_alert, sk.state, sk.last_updated,
                st.system_name, st.region_id,
                st.max_potential_power, st.max_potential_workforce,
                r."regionName" AS region_name,
                prv.power_output AS expected_power,
                prv.workforce_output AS expected_workforce,
                prv.reagent_output AS expected_reagent_rate
            FROM skyhook_status sk
            LEFT JOIN system_topology st ON sk.system_id = st.system_id
            LEFT JOIN "mapRegions" r ON st.region_id = r."regionID"
            LEFT JOIN planet_resource_values prv ON sk.planet_type = prv.planet_type
            WHERE sk.structure_id = %s
        """, (structure_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Skyhook not found")

        result = dict(row)

        # Calculate vulnerability window info
        if row['vulnerability_start'] and row['vulnerability_end']:
            now = datetime.now(timezone.utc)
            vuln_start = row['vulnerability_start']
            vuln_end = row['vulnerability_end']
            result['is_vulnerable'] = vuln_start <= now <= vuln_end
            if now < vuln_start:
                result['time_until_vulnerable'] = (vuln_start - now).total_seconds()
            else:
                result['time_until_vulnerable'] = None
        else:
            result['is_vulnerable'] = None
            result['time_until_vulnerable'] = None

        return result


@router.post("/skyhooks/sync")
@handle_endpoint_errors()
def sync_skyhooks(skyhooks: list[SkyhookUpsertRequest] = Body(...)):
    """Bulk upsert skyhook data (from ESI structure sync or manual import)."""
    import json

    with db_cursor() as cur:
        count = 0
        for sk in skyhooks:
            cur.execute("""
                INSERT INTO skyhook_status
                    (structure_id, system_id, planet_id, planet_type, type_id,
                     structure_name, power_output, workforce_output,
                     reagent_type, reagent_rate, reagent_stock,
                     vulnerability_start, vulnerability_end, state, last_updated)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, NOW())
                ON CONFLICT (structure_id) DO UPDATE SET
                    system_id = EXCLUDED.system_id,
                    planet_id = COALESCE(EXCLUDED.planet_id, skyhook_status.planet_id),
                    planet_type = COALESCE(EXCLUDED.planet_type, skyhook_status.planet_type),
                    type_id = COALESCE(EXCLUDED.type_id, skyhook_status.type_id),
                    structure_name = COALESCE(EXCLUDED.structure_name, skyhook_status.structure_name),
                    power_output = EXCLUDED.power_output,
                    workforce_output = EXCLUDED.workforce_output,
                    reagent_type = COALESCE(EXCLUDED.reagent_type, skyhook_status.reagent_type),
                    reagent_rate = EXCLUDED.reagent_rate,
                    reagent_stock = EXCLUDED.reagent_stock,
                    vulnerability_start = COALESCE(EXCLUDED.vulnerability_start, skyhook_status.vulnerability_start),
                    vulnerability_end = COALESCE(EXCLUDED.vulnerability_end, skyhook_status.vulnerability_end),
                    state = EXCLUDED.state,
                    last_updated = NOW()
            """, (
                sk.structure_id, sk.system_id, sk.planet_id, sk.planet_type,
                sk.type_id, sk.structure_name,
                sk.power_output, sk.workforce_output,
                sk.reagent_type, sk.reagent_rate,
                json.dumps(sk.reagent_stock),
                sk.vulnerability_start, sk.vulnerability_end,
                sk.state,
            ))
            count += 1

    logger.info(f"Synced {count} skyhooks")
    return {"synced": count, "message": f"Synced {count} skyhooks"}


@router.post("/skyhooks/{structure_id}/siphon-alert")
@handle_endpoint_errors()
def report_siphon_alert(
    structure_id: int = Path(...),
    aggressor_id: Optional[int] = Query(None),
):
    """Record a siphon alert for a skyhook (from ESI notification parsing)."""
    with db_cursor() as cur:
        cur.execute("""
            UPDATE skyhook_status
            SET last_siphon_alert = NOW(), last_updated = NOW()
            WHERE structure_id = %s
            RETURNING structure_id, system_id, structure_name
        """, (structure_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Skyhook not found")

    logger.warning(
        f"Siphon alert: Skyhook {row['structure_name']} "
        f"(system {row['system_id']}) — aggressor {aggressor_id}"
    )
    return {
        "alert": "siphon_detected",
        "structure_id": row['structure_id'],
        "system_id": row['system_id'],
        "structure_name": row['structure_name'],
        "aggressor_id": aggressor_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# =============================================================================
# Metenox Drill Endpoints
# =============================================================================

@router.get("/metenox/alerts")
@handle_endpoint_errors()
def metenox_fuel_alerts(
    ttd_threshold: int = Query(72, description="Alert threshold in hours"),
):
    """Get Metenox drills approaching fuel depletion (Time-to-Dark < threshold)."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT
                md.structure_id, md.system_id, md.structure_name,
                md.fuel_blocks_qty, md.magmatic_gas_qty,
                md.state, md.last_updated,
                st.system_name, r."regionName" AS region_name,
                CASE
                    WHEN md.fuel_blocks_qty > 0 AND md.magmatic_gas_qty > 0
                    THEN LEAST(md.fuel_blocks_qty / 5.0, md.magmatic_gas_qty / 55.0)
                    WHEN md.fuel_blocks_qty > 0 THEN md.fuel_blocks_qty / 5.0
                    WHEN md.magmatic_gas_qty > 0 THEN md.magmatic_gas_qty / 55.0
                    ELSE 0
                END AS time_to_dark_hours,
                CASE
                    WHEN md.fuel_blocks_qty / 5.0 < md.magmatic_gas_qty / 55.0
                    THEN 'fuel_blocks'
                    ELSE 'magmatic_gas'
                END AS limiting_fuel
            FROM metenox_drills md
            LEFT JOIN system_topology st ON md.system_id = st.system_id
            LEFT JOIN "mapRegions" r ON st.region_id = r."regionID"
            WHERE md.state = 'online'
              AND CASE
                WHEN md.fuel_blocks_qty > 0 AND md.magmatic_gas_qty > 0
                THEN LEAST(md.fuel_blocks_qty / 5.0, md.magmatic_gas_qty / 55.0)
                WHEN md.fuel_blocks_qty > 0 THEN md.fuel_blocks_qty / 5.0
                WHEN md.magmatic_gas_qty > 0 THEN md.magmatic_gas_qty / 55.0
                ELSE 0
              END <= %s
            ORDER BY time_to_dark_hours ASC
        """, (ttd_threshold,))
        return [dict(r) for r in cur.fetchall()]


@router.get("/metenox")
@handle_endpoint_errors()
def list_metenox_drills(
    system_id: Optional[int] = Query(None, description="Filter by system"),
    state: Optional[str] = Query(None, description="Filter by state"),
    ttd_max_hours: Optional[int] = Query(None, description="Filter: max hours until dark"),
):
    """List all tracked Metenox drills with fuel and yield status."""
    with db_cursor() as cur:
        where_clauses = []
        params = []

        if system_id is not None:
            where_clauses.append("md.system_id = %s")
            params.append(system_id)
        if state:
            where_clauses.append("md.state = %s")
            params.append(state)

        where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        cur.execute(f"""
            SELECT
                md.structure_id, md.system_id, md.moon_id, md.structure_name,
                md.moon_composition, md.fuel_blocks_qty, md.magmatic_gas_qty,
                md.fuel_expires, md.daily_yield_m3,
                md.accumulated_ore, md.output_bay_used_m3, md.output_bay_capacity_m3,
                md.state, md.last_asset_sync, md.last_updated,
                st.system_name, st.region_id,
                r."regionName" AS region_name,
                -- Time-to-Dark calculation: MIN(fuel_blocks/5, magmatic_gas/55) hours
                CASE
                    WHEN md.fuel_blocks_qty > 0 AND md.magmatic_gas_qty > 0
                    THEN LEAST(md.fuel_blocks_qty / 5.0, md.magmatic_gas_qty / 55.0)
                    WHEN md.fuel_blocks_qty > 0
                    THEN md.fuel_blocks_qty / 5.0
                    WHEN md.magmatic_gas_qty > 0
                    THEN md.magmatic_gas_qty / 55.0
                    ELSE 0
                END AS time_to_dark_hours
            FROM metenox_drills md
            LEFT JOIN system_topology st ON md.system_id = st.system_id
            LEFT JOIN "mapRegions" r ON st.region_id = r."regionID"
            {where_sql}
            ORDER BY
                CASE
                    WHEN md.fuel_blocks_qty > 0 AND md.magmatic_gas_qty > 0
                    THEN LEAST(md.fuel_blocks_qty / 5.0, md.magmatic_gas_qty / 55.0)
                    WHEN md.fuel_blocks_qty > 0
                    THEN md.fuel_blocks_qty / 5.0
                    WHEN md.magmatic_gas_qty > 0
                    THEN md.magmatic_gas_qty / 55.0
                    ELSE 0
                END ASC
        """, params)
        rows = [dict(r) for r in cur.fetchall()]

        # Post-filter by TTD if requested
        if ttd_max_hours is not None:
            rows = [r for r in rows if (r.get('time_to_dark_hours') or 0) <= ttd_max_hours]

    return rows


@router.get("/metenox/{structure_id}")
@handle_endpoint_errors()
def get_metenox_detail(structure_id: int = Path(...)):
    """Get detailed Metenox drill data with fuel predictions."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT
                md.structure_id, md.system_id, md.moon_id, md.structure_name,
                md.moon_composition, md.fuel_blocks_qty, md.magmatic_gas_qty,
                md.fuel_expires, md.daily_yield_m3,
                md.accumulated_ore, md.output_bay_used_m3, md.output_bay_capacity_m3,
                md.state, md.last_asset_sync, md.last_updated,
                st.system_name, st.region_id,
                r."regionName" AS region_name
            FROM metenox_drills md
            LEFT JOIN system_topology st ON md.system_id = st.system_id
            LEFT JOIN "mapRegions" r ON st.region_id = r."regionID"
            WHERE md.structure_id = %s
        """, (structure_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Metenox drill not found")

        result = dict(row)

        # Time-to-Dark calculation
        fuel_hours = row['fuel_blocks_qty'] / 5.0 if row['fuel_blocks_qty'] > 0 else 0
        gas_hours = row['magmatic_gas_qty'] / 55.0 if row['magmatic_gas_qty'] > 0 else 0
        if fuel_hours > 0 and gas_hours > 0:
            ttd = min(fuel_hours, gas_hours)
            result['limiting_fuel'] = 'fuel_blocks' if fuel_hours < gas_hours else 'magmatic_gas'
        elif fuel_hours > 0:
            ttd = fuel_hours
            result['limiting_fuel'] = 'fuel_blocks'
        elif gas_hours > 0:
            ttd = gas_hours
            result['limiting_fuel'] = 'magmatic_gas'
        else:
            ttd = 0
            result['limiting_fuel'] = 'both_empty'

        result['time_to_dark_hours'] = round(ttd, 1)
        result['fuel_blocks_hours'] = round(fuel_hours, 1)
        result['magmatic_gas_hours'] = round(gas_hours, 1)

        # Refuel quantities needed for 7-day supply
        target_hours = 168  # 7 days
        result['refuel_blocks_needed'] = max(0, int((target_hours - fuel_hours) * 5))
        result['refuel_gas_needed'] = max(0, int((target_hours - gas_hours) * 55))

        # Output bay utilization
        if row['output_bay_capacity_m3'] > 0:
            result['output_bay_pct'] = round(
                (row['output_bay_used_m3'] / row['output_bay_capacity_m3']) * 100, 1
            )
            if row['daily_yield_m3'] > 0:
                remaining_m3 = row['output_bay_capacity_m3'] - row['output_bay_used_m3']
                result['time_to_full_hours'] = round(remaining_m3 / (row['daily_yield_m3'] / 24), 1)
            else:
                result['time_to_full_hours'] = None
        else:
            result['output_bay_pct'] = 0
            result['time_to_full_hours'] = None

        # Alert level
        if ttd <= 24:
            result['alert_level'] = 'critical'
        elif ttd <= 72:
            result['alert_level'] = 'warning'
        elif ttd <= 168:
            result['alert_level'] = 'info'
        else:
            result['alert_level'] = 'ok'

        return result


@router.post("/metenox/sync")
@handle_endpoint_errors()
def sync_metenox_drills(drills: list[MetenoxUpsertRequest] = Body(...)):
    """Bulk upsert Metenox drill data (from ESI asset sync or manual import)."""
    import json

    with db_cursor() as cur:
        count = 0
        for d in drills:
            cur.execute("""
                INSERT INTO metenox_drills
                    (structure_id, system_id, moon_id, structure_name,
                     moon_composition, fuel_blocks_qty, magmatic_gas_qty,
                     fuel_expires, daily_yield_m3,
                     accumulated_ore, output_bay_used_m3, output_bay_capacity_m3,
                     state, last_updated)
                VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, NOW())
                ON CONFLICT (structure_id) DO UPDATE SET
                    system_id = EXCLUDED.system_id,
                    moon_id = COALESCE(EXCLUDED.moon_id, metenox_drills.moon_id),
                    structure_name = COALESCE(EXCLUDED.structure_name, metenox_drills.structure_name),
                    moon_composition = CASE
                        WHEN EXCLUDED.moon_composition != '{}'::jsonb
                        THEN EXCLUDED.moon_composition
                        ELSE metenox_drills.moon_composition
                    END,
                    fuel_blocks_qty = EXCLUDED.fuel_blocks_qty,
                    magmatic_gas_qty = EXCLUDED.magmatic_gas_qty,
                    fuel_expires = COALESCE(EXCLUDED.fuel_expires, metenox_drills.fuel_expires),
                    daily_yield_m3 = EXCLUDED.daily_yield_m3,
                    accumulated_ore = CASE
                        WHEN EXCLUDED.accumulated_ore != '{}'::jsonb
                        THEN EXCLUDED.accumulated_ore
                        ELSE metenox_drills.accumulated_ore
                    END,
                    output_bay_used_m3 = EXCLUDED.output_bay_used_m3,
                    output_bay_capacity_m3 = EXCLUDED.output_bay_capacity_m3,
                    state = EXCLUDED.state,
                    last_asset_sync = NOW(),
                    last_updated = NOW()
            """, (
                d.structure_id, d.system_id, d.moon_id, d.structure_name,
                json.dumps(d.moon_composition),
                d.fuel_blocks_qty, d.magmatic_gas_qty,
                d.fuel_expires, d.daily_yield_m3,
                json.dumps(d.accumulated_ore),
                d.output_bay_used_m3, d.output_bay_capacity_m3,
                d.state,
            ))
            count += 1

    logger.info(f"Synced {count} Metenox drills")
    return {"synced": count, "message": f"Synced {count} Metenox drills"}


