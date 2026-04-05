"""
Fuel Tracking Router - Monitor corporation structure fuel levels.

Uses ESI corporation structures endpoint.
Requires: esi-corporations.read_structures.v1 scope
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, List
import logging

from fastapi import APIRouter, HTTPException, Query, Body
import httpx

from app.models.base import CamelModel
from app.database import db_cursor
from eve_shared.utils.error_handling import handle_endpoint_errors
logger = logging.getLogger(__name__)

router = APIRouter()

ESI_BASE = "https://esi.evetech.net/latest"


# ==============================================================================
# Models
# ==============================================================================

class FuelAlertConfig(CamelModel):
    """Fuel alert configuration."""
    critical_days: int = 3
    warning_days: int = 7
    notice_days: int = 14
    discord_webhook: Optional[str] = None
    notify_on_critical: bool = True
    notify_on_warning: bool = True
    notify_on_notice: bool = False


class StructureResponse(CamelModel):
    """Structure with fuel info."""
    structure_id: int
    name: str
    structure_type_name: Optional[str]
    system_name: Optional[str]
    region_name: Optional[str]
    fuel_expires: Optional[datetime]
    days_remaining: Optional[float]
    fuel_status: str
    state: Optional[str]


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


def calculate_days_remaining(fuel_expires: datetime) -> Optional[float]:
    """Calculate days until fuel runs out."""
    if not fuel_expires:
        return None
    now = datetime.now(timezone.utc)
    delta = fuel_expires - now
    return max(0, delta.total_seconds() / 86400)


def get_fuel_status(days: Optional[float], config: dict = None) -> str:
    """Determine fuel status based on days remaining."""
    if days is None:
        return "unknown"

    critical = config.get('critical_days', 3) if config else 3
    warning = config.get('warning_days', 7) if config else 7
    notice = config.get('notice_days', 14) if config else 14

    if days <= critical:
        return "critical"
    elif days <= warning:
        return "warning"
    elif days <= notice:
        return "notice"
    return "ok"


# ==============================================================================
# Endpoints
# ==============================================================================

@router.get("/structures/{corporation_id}")
def get_corporation_structures(
    corporation_id: int,
    status: Optional[str] = Query(None, description="Filter by status: critical, warning, notice, ok"),
    system_id: Optional[int] = Query(None, description="Filter by system")
):
    """Get all structures for a corporation with fuel status."""
    with db_cursor() as cur:
        # Get alert config for status thresholds
        cur.execute("""
            SELECT critical_days, warning_days, notice_days
            FROM fuel_alert_config
            WHERE corporation_id = %s
        """, (corporation_id,))
        config = cur.fetchone() or {'critical_days': 3, 'warning_days': 7, 'notice_days': 14}

        query = """
            SELECT
                cs.structure_id,
                cs.name,
                cs.structure_type_id,
                cs.structure_type_name,
                cs.system_id,
                cs.system_name,
                cs.region_name,
                cs.fuel_expires,
                cs.days_remaining,
                cs.state,
                cs.services,
                cs.last_synced,
                sfr.base_fuel_rate
            FROM corp_structures cs
            LEFT JOIN structure_fuel_rates sfr ON cs.structure_type_id = sfr.structure_type_id
            WHERE cs.corporation_id = %s
        """
        params = [corporation_id]

        if system_id:
            query += " AND cs.system_id = %s"
            params.append(system_id)

        query += " ORDER BY cs.days_remaining ASC NULLS FIRST"

        cur.execute(query, params)
        rows = cur.fetchall()

    structures = []
    summary = {"critical": 0, "warning": 0, "notice": 0, "ok": 0, "unknown": 0}

    for row in rows:
        days = row['days_remaining']
        fuel_status = get_fuel_status(days, config)

        if status and fuel_status != status:
            continue

        summary[fuel_status] += 1

        structures.append({
            "structure_id": row['structure_id'],
            "name": row['name'],
            "structure_type_id": row['structure_type_id'],
            "structure_type_name": row['structure_type_name'],
            "system_id": row['system_id'],
            "system_name": row['system_name'],
            "region_name": row['region_name'],
            "fuel_expires": row['fuel_expires'].isoformat() if row['fuel_expires'] else None,
            "days_remaining": round(days, 2) if days else None,
            "fuel_status": fuel_status,
            "state": row['state'],
            "fuel_rate_per_hour": row['base_fuel_rate'],
            "services": row['services'],
            "last_synced": row['last_synced'].isoformat() if row['last_synced'] else None
        })

    return {
        "corporation_id": corporation_id,
        "summary": summary,
        "total_structures": len(structures),
        "structures": structures
    }


@router.get("/low-fuel")
def get_all_low_fuel(
    days_threshold: int = Query(7, description="Alert threshold in days")
):
    """Get all structures across all corporations with low fuel."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT
                cs.structure_id,
                cs.name,
                cs.corporation_id,
                cs.structure_type_name,
                cs.system_name,
                cs.region_name,
                cs.fuel_expires,
                cs.days_remaining,
                cs.state
            FROM corp_structures cs
            WHERE cs.days_remaining IS NOT NULL
              AND cs.days_remaining <= %s
              AND (cs.state = 'online' OR cs.state IS NULL)
            ORDER BY cs.days_remaining ASC
        """, (days_threshold,))
        rows = cur.fetchall()

    return {
        "threshold_days": days_threshold,
        "count": len(rows),
        "structures": [{
            "structure_id": row['structure_id'],
            "name": row['name'],
            "corporation_id": row['corporation_id'],
            "structure_type_name": row['structure_type_name'],
            "system_name": row['system_name'],
            "region_name": row['region_name'],
            "fuel_expires": row['fuel_expires'].isoformat() if row['fuel_expires'] else None,
            "days_remaining": round(row['days_remaining'], 2),
            "fuel_status": get_fuel_status(row['days_remaining'])
        } for row in rows]
    }


@router.post("/sync/{corporation_id}")
@handle_endpoint_errors(default_status=502)
async def sync_structures(
    corporation_id: int,
    token: str = Query(..., description="ESI access token with structures scope")
):
    """
    Sync structures from ESI for a corporation.

    Requires: esi-corporations.read_structures.v1 scope
    """
    structures = await fetch_esi(
        f"/corporations/{corporation_id}/structures/",
        token
    )

    synced = 0
    for struct in structures:
        structure_id = struct['structure_id']

        # Calculate days remaining
        fuel_expires = None
        days_remaining = None
        if struct.get('fuel_expires'):
            fuel_expires = datetime.fromisoformat(struct['fuel_expires'].replace('Z', '+00:00'))
            days_remaining = calculate_days_remaining(fuel_expires)

        with db_cursor() as cur:
            # Get system info
            system_id = struct.get('system_id')
            system_name = None
            region_name = None
            region_id = None

            if system_id:
                cur.execute("""
                    SELECT solar_system_name, region_id, region_name
                    FROM system_region_map
                    WHERE solar_system_id = %s
                """, (system_id,))
                sys_row = cur.fetchone()
                if sys_row:
                    system_name = sys_row['solar_system_name']
                    region_id = sys_row['region_id']
                    region_name = sys_row['region_name']

            # Get structure type name
            type_name = None
            type_id = struct.get('type_id')
            if type_id:
                cur.execute("""
                    SELECT "typeName" FROM "invTypes" WHERE "typeID" = %s
                """, (type_id,))
                type_row = cur.fetchone()
                if type_row:
                    type_name = type_row['typeName']

            # Upsert structure
            cur.execute("""
                INSERT INTO corp_structures (
                    structure_id, corporation_id,
                    structure_type_id, structure_type_name, name,
                    system_id, system_name, region_id, region_name,
                    fuel_expires, days_remaining, state, services,
                    last_synced
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW()
                )
                ON CONFLICT (structure_id) DO UPDATE SET
                    fuel_expires = EXCLUDED.fuel_expires,
                    days_remaining = EXCLUDED.days_remaining,
                    state = EXCLUDED.state,
                    services = EXCLUDED.services,
                    last_synced = NOW(),
                    updated_at = NOW()
            """, (
                structure_id, corporation_id,
                type_id, type_name, struct.get('name', f'Structure {structure_id}'),
                system_id, system_name, region_id, region_name,
                fuel_expires, days_remaining,
                struct.get('state'), struct.get('services')
            ))

            # Record fuel history
            cur.execute("""
                INSERT INTO fuel_history (structure_id, fuel_expires, days_remaining, state)
                VALUES (%s, %s, %s, %s)
            """, (structure_id, fuel_expires, days_remaining, struct.get('state')))

        synced += 1

    return {
        "message": "Sync completed",
        "corporation_id": corporation_id,
        "structures_synced": synced
    }


@router.get("/alerts/{corporation_id}")
def get_fuel_alerts(corporation_id: int):
    """Get current fuel alerts for a corporation based on their config."""
    with db_cursor() as cur:
        # Get config
        cur.execute("""
            SELECT * FROM fuel_alert_config WHERE corporation_id = %s
        """, (corporation_id,))
        config = cur.fetchone()

        if not config:
            config = {'critical_days': 3, 'warning_days': 7, 'notice_days': 14}

        # Get structures that need alerts
        cur.execute("""
            SELECT
                cs.structure_id, cs.name, cs.structure_type_name,
                cs.system_name, cs.fuel_expires, cs.days_remaining
            FROM corp_structures cs
            WHERE cs.corporation_id = %s
              AND cs.days_remaining IS NOT NULL
              AND cs.days_remaining <= %s
              AND (cs.state = 'online' OR cs.state IS NULL)
            ORDER BY cs.days_remaining ASC
        """, (corporation_id, config['notice_days']))
        rows = cur.fetchall()

    alerts = {"critical": [], "warning": [], "notice": []}

    for row in rows:
        days = row['days_remaining']
        alert = {
            "structure_id": row['structure_id'],
            "name": row['name'],
            "type": row['structure_type_name'],
            "system": row['system_name'],
            "days_remaining": round(days, 2),
            "fuel_expires": row['fuel_expires'].isoformat() if row['fuel_expires'] else None
        }

        if days <= config['critical_days']:
            alerts['critical'].append(alert)
        elif days <= config['warning_days']:
            alerts['warning'].append(alert)
        else:
            alerts['notice'].append(alert)

    return {
        "corporation_id": corporation_id,
        "config": {
            "critical_days": config['critical_days'],
            "warning_days": config['warning_days'],
            "notice_days": config['notice_days']
        },
        "alerts": alerts,
        "total_alerts": sum(len(v) for v in alerts.values())
    }


@router.put("/alerts/{corporation_id}/config")
def update_alert_config(
    corporation_id: int,
    config: FuelAlertConfig
):
    """Update fuel alert configuration for a corporation."""
    with db_cursor() as cur:
        cur.execute("""
            INSERT INTO fuel_alert_config (
                corporation_id, critical_days, warning_days, notice_days,
                discord_webhook, notify_on_critical, notify_on_warning, notify_on_notice
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (corporation_id) DO UPDATE SET
                critical_days = EXCLUDED.critical_days,
                warning_days = EXCLUDED.warning_days,
                notice_days = EXCLUDED.notice_days,
                discord_webhook = EXCLUDED.discord_webhook,
                notify_on_critical = EXCLUDED.notify_on_critical,
                notify_on_warning = EXCLUDED.notify_on_warning,
                notify_on_notice = EXCLUDED.notify_on_notice,
                updated_at = NOW()
            RETURNING id
        """, (
            corporation_id,
            config.critical_days,
            config.warning_days,
            config.notice_days,
            config.discord_webhook,
            config.notify_on_critical,
            config.notify_on_warning,
            config.notify_on_notice
        ))

    return {"message": "Config updated", "corporation_id": corporation_id}


@router.get("/fuel-rates")
def get_fuel_rates():
    """Get fuel consumption rates for all structure types."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT structure_type_id, structure_type_name, base_fuel_rate, notes
            FROM structure_fuel_rates
            ORDER BY base_fuel_rate DESC
        """)
        rows = cur.fetchall()

    return {
        "fuel_rates": [{
            "type_id": row['structure_type_id'],
            "type_name": row['structure_type_name'],
            "fuel_per_hour": row['base_fuel_rate'],
            "fuel_per_day": row['base_fuel_rate'] * 24,
            "notes": row['notes']
        } for row in rows]
    }


@router.get("/consumption/{structure_id}")
def get_structure_consumption(
    structure_id: int,
    days: int = Query(30, ge=1, le=90)
):
    """Get fuel consumption history for a structure."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT
                cs.name,
                cs.structure_type_name,
                cs.system_name,
                cs.fuel_expires,
                cs.days_remaining as current_days,
                sfr.base_fuel_rate
            FROM corp_structures cs
            LEFT JOIN structure_fuel_rates sfr ON cs.structure_type_id = sfr.structure_type_id
            WHERE cs.structure_id = %s
        """, (structure_id,))
        struct = cur.fetchone()

        if not struct:
            raise HTTPException(status_code=404, detail="Structure not found")

        # Get history
        cur.execute("""
            SELECT recorded_at, fuel_expires, days_remaining, state
            FROM fuel_history
            WHERE structure_id = %s
              AND recorded_at > NOW() - INTERVAL '%s days'
            ORDER BY recorded_at ASC
        """, (structure_id, days))
        history = cur.fetchall()

    return {
        "structure_id": structure_id,
        "name": struct['name'],
        "type": struct['structure_type_name'],
        "system": struct['system_name'],
        "current_fuel_expires": struct['fuel_expires'].isoformat() if struct['fuel_expires'] else None,
        "current_days_remaining": round(struct['current_days'], 2) if struct['current_days'] else None,
        "fuel_rate_per_hour": struct['base_fuel_rate'],
        "history": [{
            "recorded_at": h['recorded_at'].isoformat(),
            "fuel_expires": h['fuel_expires'].isoformat() if h['fuel_expires'] else None,
            "days_remaining": round(h['days_remaining'], 2) if h['days_remaining'] else None,
            "state": h['state']
        } for h in history]
    }
