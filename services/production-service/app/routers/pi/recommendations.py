"""PI planet recommendation endpoints."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Query

from app.services.pi.models import (
    PlanetRecommendationItem,
    PlanetRecommendationResponse,
)
from ._helpers import (
    get_pi_repository,
    PISchematicService,
    PLANET_P0_RESOURCES,
    P0_PLANET_MAP,
)

router = APIRouter()


# ==================== Planet Recommendations ====================

@router.get("/recommendations/planets/{target_type_id}")
def get_planet_recommendations(
    request: Request,
    target_type_id: int,
    current_types: str = Query("", description="Comma-separated current planet types")
) -> dict:
    """Recommend planet types needed for a target product."""
    repo = get_pi_repository(request)
    service = PISchematicService(repo)

    current_planet_types = [t.strip() for t in current_types.split(",") if t.strip()]

    p0_materials = service.get_flat_inputs(target_type_id, quantity=1.0)

    if not p0_materials:
        chain = service.get_production_chain(target_type_id)
        return {
            'target_type_id': target_type_id,
            'target_name': chain.type_name if chain else '',
            'p0_requirements': [],
            'current_planet_types': current_planet_types,
            'covered_materials': [],
            'missing_materials': [],
            'recommendations': []
        }

    current_types_lower = [t.lower() for t in current_planet_types]

    requirements = []
    covered_materials = []
    missing_materials = []

    for material in p0_materials:
        material_name = material.get('type_name', '')
        available_planets = P0_PLANET_MAP.get(material_name, [])

        is_covered = any(
            planet.lower() in current_types_lower
            for planet in available_planets
        )

        requirement = {
            'material_type_id': material.get('type_id', 0),
            'material_name': material_name,
            'quantity_needed': material.get('quantity', 0),
            'available_planet_types': available_planets,
            'is_covered': is_covered
        }
        requirements.append(requirement)

        if is_covered:
            covered_materials.append(material_name)
        else:
            missing_materials.append({
                'material_name': material_name,
                'planet_options': available_planets
            })

    planet_coverage = {}
    for missing in missing_materials:
        for planet in missing['planet_options']:
            planet_lower = planet.lower()
            if planet_lower not in planet_coverage:
                planet_coverage[planet_lower] = []
            planet_coverage[planet_lower].append(missing['material_name'])

    recommendations = [
        {
            'planet_type': planet,
            'covers_materials': materials,
            'coverage_count': len(materials),
            'priority': 'high' if len(materials) >= 2 else 'medium' if len(materials) == 1 else 'low'
        }
        for planet, materials in sorted(
            planet_coverage.items(),
            key=lambda x: len(x[1]),
            reverse=True
        )
    ]

    chain = service.get_production_chain(target_type_id)
    return {
        'target_type_id': target_type_id,
        'target_name': chain.type_name if chain else '',
        'p0_requirements': requirements,
        'current_planet_types': current_planet_types,
        'covered_materials': covered_materials,
        'missing_materials': [m['material_name'] for m in missing_materials],
        'recommendations': recommendations
    }


# ==================== Planet Recommendation Endpoint ====================

@router.get("/planets/recommend", response_model=PlanetRecommendationResponse)
def recommend_planets(
    request: Request,
    system_name: str = Query(..., description="Center system name"),
    jump_range: int = Query(5, ge=1, le=15, description="Max jumps from center"),
    planet_type: Optional[str] = Query(None, description="Filter by type: barren, gas, lava, etc."),
    required_resources: Optional[str] = Query(None, description="Comma-separated P0 names to filter"),
    min_security: float = Query(-1.0, ge=-1.0, le=1.0, description="Minimum security status"),
):
    """
    Find planets for PI within jump range of a system.

    Returns planets sorted by recommendation score based on:
    - Distance (closer = better)
    - Security (higher = safer)
    - Resource availability (based on planet type)
    """
    repo = get_pi_repository(request)

    # Find center system
    center = repo.get_system_by_name(system_name)
    if not center:
        raise HTTPException(status_code=404, detail=f"System '{system_name}' not found")

    # Find nearby systems
    nearby_systems = repo.get_systems_within_jumps(center['system_id'], jump_range)

    # Apply security filter
    if min_security > -1.0:
        nearby_systems = [s for s in nearby_systems if s['security'] >= min_security]

    if not nearby_systems:
        return PlanetRecommendationResponse(
            search_center=system_name,
            search_radius=jump_range,
            systems_searched=0,
            planets_found=0,
            recommendations=[],
            by_planet_type={},
            by_resource={}
        )

    # Get planets
    system_ids = [s['system_id'] for s in nearby_systems]
    system_jumps = {s['system_id']: s['jumps'] for s in nearby_systems}

    planets = repo.get_planets_in_systems(system_ids, planet_type)

    # Parse required resources filter
    required_p0 = []
    if required_resources:
        required_p0 = [r.strip() for r in required_resources.split(',')]

    # Score and filter planets
    recommendations = []
    by_type = {}
    by_resource = {}

    for planet in planets:
        ptype = planet['planet_type']
        jumps = system_jumps.get(planet['system_id'], 0)

        # Get resources for this planet type
        resources = PLANET_P0_RESOURCES.get(ptype, [])

        # Filter by required resources
        if required_p0:
            matching = [r for r in resources if any(req.lower() in r.lower() for req in required_p0)]
            if not matching:
                continue
            resources = matching

        # Calculate score (0-10)
        # - Distance: 5 points max (0 jumps = 5, max_jumps = 0)
        distance_score = 5 * (1 - jumps / max(jump_range, 1))
        # - Security: 3 points max (1.0 = 3, 0.0 = 1.5, -1.0 = 0)
        security_score = 1.5 * (planet['security'] + 1)
        # - Resource count: 2 points max
        resource_score = min(len(resources) / 3, 1) * 2

        total_score = round(distance_score + security_score + resource_score, 1)

        # Generate reason
        reasons = []
        if jumps == 0:
            reasons.append("Home system")
        elif jumps <= 2:
            reasons.append(f"Close ({jumps} jumps)")
        if planet['security'] >= 0.5:
            reasons.append("High-sec")
        elif planet['security'] >= 0.0:
            reasons.append("Low-sec")
        if len(resources) >= 4:
            reasons.append("Resource-rich")

        reason = ", ".join(reasons) if reasons else "Standard planet"

        recommendations.append(PlanetRecommendationItem(
            planet_id=planet['planet_id'],
            planet_name=planet['planet_name'],
            planet_type=ptype,
            system_id=planet['system_id'],
            system_name=planet['system_name'],
            security=planet['security'],
            jumps_from_home=jumps,
            resources=resources,
            recommendation_score=total_score,
            reason=reason
        ))

        # Aggregate stats
        by_type[ptype] = by_type.get(ptype, 0) + 1
        for res in resources:
            if res not in by_resource:
                by_resource[res] = []
            if planet['planet_name'] not in by_resource[res]:
                by_resource[res].append(planet['planet_name'])

    # Sort by score descending
    recommendations.sort(key=lambda x: x.recommendation_score, reverse=True)

    return PlanetRecommendationResponse(
        search_center=system_name,
        search_radius=jump_range,
        systems_searched=len(nearby_systems),
        planets_found=len(recommendations),
        recommendations=recommendations,
        by_planet_type=by_type,
        by_resource=by_resource
    )
