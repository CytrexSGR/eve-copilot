"""PI multi-character summary and detail endpoints."""

from typing import List
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, Query

from ._helpers import get_pi_repository

router = APIRouter()


# ==================== Multi-Character Aggregation ====================

@router.get("/multi-character/summary")
def get_multi_character_summary(
    request: Request,
    character_ids: str = Query(..., description="Comma-separated character IDs")
) -> dict:
    """Get aggregated PI summary across multiple characters."""
    repo = get_pi_repository(request)

    ids = [int(cid.strip()) for cid in character_ids.split(",") if cid.strip().isdigit()]
    if not ids:
        raise HTTPException(status_code=400, detail="No valid character IDs provided")

    characters = []
    total_colonies = 0
    total_extractors = 0
    total_factories = 0
    total_max_planets = 0
    total_used_planets = 0
    product_output = {}

    for char_id in ids:
        skills = repo.get_character_skills(char_id)
        max_planets = skills.get("max_planets", 1) if skills else 1

        colonies = repo.get_colonies(char_id)
        used_planets = len(colonies)

        total_max_planets += max_planets
        total_used_planets += used_planets
        total_colonies += len(colonies)

        char_extractors = 0
        char_factories = 0

        for colony in colonies:
            detail = repo.get_colony_detail(colony.id)
            if detail:
                for pin in detail.pins:
                    if pin.product_type_id:
                        char_extractors += 1
                        if pin.qty_per_cycle and pin.cycle_time and pin.cycle_time > 0:
                            output_per_hour = (pin.qty_per_cycle * 3600) / pin.cycle_time
                            type_id = pin.product_type_id
                            if type_id not in product_output:
                                product_output[type_id] = {
                                    'type_name': pin.product_name or f"Type {type_id}",
                                    'output_per_hour': 0,
                                    'characters': []
                                }
                            product_output[type_id]['output_per_hour'] += output_per_hour
                            if char_id not in product_output[type_id]['characters']:
                                product_output[type_id]['characters'].append(char_id)
                    elif pin.schematic_id:
                        char_factories += 1

        total_extractors += char_extractors
        total_factories += char_factories

        # Get character name
        with request.app.state.db.cursor() as cur:
            cur.execute(
                "SELECT character_name FROM characters WHERE character_id = %s",
                (char_id,)
            )
            result = cur.fetchone()
            char_name = result['character_name'] if result else f"Character {char_id}"

        characters.append({
            'character_id': char_id,
            'character_name': char_name,
            'colonies': len(colonies),
            'extractors': char_extractors,
            'factories': char_factories,
            'max_planets': max_planets,
            'used_planets': used_planets,
        })

    return {
        'total_characters': len(ids),
        'total_colonies': total_colonies,
        'total_extractors': total_extractors,
        'total_factories': total_factories,
        'total_max_planets': total_max_planets,
        'total_used_planets': total_used_planets,
        'total_free_planets': total_max_planets - total_used_planets,
        'products': [
            {
                'type_id': type_id,
                'type_name': data['type_name'],
                'output_per_hour': round(data['output_per_hour'], 2),
                'character_count': len(data['characters'])
            }
            for type_id, data in sorted(
                product_output.items(),
                key=lambda x: x[1]['output_per_hour'],
                reverse=True
            )
        ],
        'characters': characters,
    }


@router.get("/multi-character/detail")
def get_multi_character_detail(
    request: Request,
    character_ids: str = Query(..., description="Comma-separated character IDs"),
):
    """
    Get detailed PI overview for multiple characters.

    Includes extractor status with expiry times and alerts.
    """
    repo = get_pi_repository(request)

    # Parse character IDs
    ids = [int(x.strip()) for x in character_ids.split(",") if x.strip().isdigit()]
    if not ids:
        raise HTTPException(status_code=400, detail="No character IDs provided")

    # Build summary and extract details
    characters = []
    total_colonies = 0
    total_extractors = 0
    total_factories = 0
    extractors = []
    alerts = []

    now = datetime.now(timezone.utc)

    for char_id in ids:
        # Get character name
        with request.app.state.db.cursor() as cur:
            cur.execute(
                "SELECT character_name FROM characters WHERE character_id = %s",
                (char_id,)
            )
            result = cur.fetchone()
            char_name = result['character_name'] if result else f"Character {char_id}"

        # Get all colonies
        colonies = repo.get_colonies(char_id)
        char_extractors = 0
        char_factories = 0

        for colony in colonies:
            detail = repo.get_colony_detail(colony.id)
            if not detail:
                continue

            planet_name = colony.solar_system_name or f"Planet {colony.planet_id}"
            if hasattr(colony, 'planet_name') and colony.planet_name:
                planet_name = colony.planet_name

            for pin in detail.pins:
                # Extractor pins
                if pin.product_type_id and pin.qty_per_cycle:
                    char_extractors += 1

                    expiry = pin.expiry_time
                    hours_remaining = None
                    status = 'stopped'

                    if expiry:
                        # Handle timezone-aware comparison
                        if expiry.tzinfo is None:
                            expiry = expiry.replace(tzinfo=timezone.utc)
                        remaining = expiry - now
                        hours_remaining = max(0, remaining.total_seconds() / 3600)

                        if hours_remaining > 12:
                            status = 'active'
                        elif hours_remaining > 0:
                            status = 'expiring'
                        else:
                            status = 'stopped'

                    extractors.append({
                        'character_id': char_id,
                        'character_name': char_name,
                        'planet_id': colony.planet_id,
                        'planet_name': planet_name,
                        'planet_type': colony.planet_type,
                        'product_type_id': pin.product_type_id,
                        'product_name': pin.product_name or f"Type {pin.product_type_id}",
                        'qty_per_cycle': pin.qty_per_cycle,
                        'cycle_time': pin.cycle_time or 3600,
                        'expiry_time': expiry.isoformat() if expiry else None,
                        'hours_remaining': round(hours_remaining, 1) if hours_remaining is not None else None,
                        'status': status,
                    })

                    # Generate alerts
                    if status == 'expiring':
                        alerts.append({
                            'type': 'extractor_depleting',
                            'severity': 'warning',
                            'character_id': char_id,
                            'character_name': char_name,
                            'planet_name': planet_name,
                            'message': f"{pin.product_name or 'Extractor'} depletes in {hours_remaining:.1f}h",
                            'expiry_time': expiry.isoformat() if expiry else None,
                        })
                    elif status == 'stopped':
                        alerts.append({
                            'type': 'extractor_stopped',
                            'severity': 'critical',
                            'character_id': char_id,
                            'character_name': char_name,
                            'planet_name': planet_name,
                            'message': f"{pin.product_name or 'Extractor'} has stopped",
                            'expiry_time': None,
                        })

                # Factory pins
                elif pin.schematic_id:
                    char_factories += 1

        characters.append({
            'character_id': char_id,
            'character_name': char_name,
            'colonies': len(colonies),
            'extractors': char_extractors,
            'factories': char_factories,
        })
        total_colonies += len(colonies)
        total_extractors += char_extractors
        total_factories += char_factories

    # Sort alerts by severity (critical first) then by expiry
    alerts.sort(key=lambda a: (0 if a['severity'] == 'critical' else 1, a.get('expiry_time') or 'z'))

    # Sort extractors by hours remaining (most urgent first, None values last)
    extractors.sort(key=lambda e: e['hours_remaining'] if e['hours_remaining'] is not None else 9999)

    return {
        'summary': {
            'total_characters': len(ids),
            'total_colonies': total_colonies,
            'total_extractors': total_extractors,
            'total_factories': total_factories,
            'characters': characters,
        },
        'extractors': extractors,
        'alerts': alerts,
    }
