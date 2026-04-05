"""PI colony endpoints — list, sync, detail, graph, health, summary."""

from typing import List
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, Query

from app.services.pi.models import PIColony, PIColonyDetail, PICharacterSummary
from app.services.pi.esi_service import PIESIService
from app.services.auth_client import AuthClient
from ._helpers import get_pi_repository

router = APIRouter()


# ==================== Colony Endpoints ====================

@router.get("/characters/{character_id}/colonies")
def get_colonies(
    request: Request,
    character_id: int
) -> List[PIColony]:
    """Get all PI colonies for a character."""
    repo = get_pi_repository(request)
    return repo.get_colonies(character_id)


@router.post("/characters/{character_id}/colonies/sync")
async def sync_colonies(
    request: Request,
    character_id: int
):
    """
    Sync PI colonies from ESI.

    Fetches current colony data from EVE ESI and updates the local cache.
    This includes colony list, pins, routes, and extractor status.

    Required scope: esi-planets.manage_planets.v1
    """
    repo = get_pi_repository(request)
    auth_client = AuthClient()
    esi_service = PIESIService(repo, auth_client)
    result = await esi_service.sync_colonies(character_id)
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["message"])
    return result


@router.get("/characters/{character_id}/colonies/{planet_id}")
def get_colony_detail(
    request: Request,
    character_id: int,
    planet_id: int
) -> PIColonyDetail:
    """Get colony details including pins and routes."""
    repo = get_pi_repository(request)

    colonies = repo.get_colonies(character_id)
    colony = next((c for c in colonies if c.planet_id == planet_id), None)

    if not colony:
        raise HTTPException(status_code=404, detail="Colony not found")

    detail = repo.get_colony_detail(colony.id)
    if not detail:
        raise HTTPException(status_code=404, detail="Colony detail not found")

    return detail


@router.get("/characters/{character_id}/summary")
def get_character_summary(
    request: Request,
    character_id: int
) -> PICharacterSummary:
    """Get aggregated PI summary for a character."""
    repo = get_pi_repository(request)

    # Get character name
    with request.app.state.db.cursor() as cur:
        cur.execute(
            "SELECT character_name FROM characters WHERE character_id = %s",
            (character_id,)
        )
        result = cur.fetchone()
        character_name = result[0] if result else f"Character {character_id}"

    colonies = repo.get_colonies(character_id)
    if not colonies:
        return PICharacterSummary(
            character_id=character_id,
            character_name=character_name,
            total_colonies=0,
            active_extractors=0,
            active_factories=0,
            products=[],
            expiring_soon=[],
        )

    total_colonies = len(colonies)
    active_extractors = 0
    active_factories = 0
    products = {}
    expiring_soon = []

    now = datetime.now(timezone.utc)

    for colony in colonies:
        detail = repo.get_colony_detail(colony.id)
        if not detail:
            continue

        for pin in detail.pins:
            if pin.expiry_time and pin.product_type_id:
                active_extractors += 1

                if pin.qty_per_cycle and pin.cycle_time and pin.cycle_time > 0:
                    qty_per_day = (pin.qty_per_cycle * 86400) / pin.cycle_time
                else:
                    qty_per_day = 0

                if pin.product_type_id in products:
                    products[pin.product_type_id]["quantity_per_day"] += qty_per_day
                else:
                    products[pin.product_type_id] = {
                        "type_id": pin.product_type_id,
                        "type_name": pin.product_name or "Unknown",
                        "quantity_per_day": qty_per_day,
                    }

                expiry_time = pin.expiry_time
                if expiry_time.tzinfo is None:
                    expiry_time = expiry_time.replace(tzinfo=timezone.utc)

                hours_remaining = (expiry_time - now).total_seconds() / 3600
                if 0 < hours_remaining <= 24:
                    expiring_soon.append({
                        "colony_id": colony.id,
                        "planet_id": colony.planet_id,
                        "planet_type": colony.planet_type,
                        "solar_system_name": colony.solar_system_name,
                        "product_type_id": pin.product_type_id,
                        "product_name": pin.product_name,
                        "expiry_time": pin.expiry_time.isoformat(),
                        "hours_remaining": round(hours_remaining, 1),
                    })

            elif pin.schematic_id:
                active_factories += 1

    expiring_soon.sort(key=lambda x: x["hours_remaining"])

    return PICharacterSummary(
        character_id=character_id,
        character_name=character_name,
        total_colonies=total_colonies,
        active_extractors=active_extractors,
        active_factories=active_factories,
        products=list(products.values()),
        expiring_soon=expiring_soon,
    )


# ==================== Colony Graph & Health Check ====================

@router.get("/characters/{character_id}/colonies/{planet_id}/graph")
def get_colony_graph(
    request: Request,
    character_id: int,
    planet_id: int,
):
    """Get colony data as a graph (nodes + edges) for visualization.

    Nodes = pins (extractors, factories, storage, launchpad, command center)
    Edges = routes between pins with material type and quantity
    Includes health annotations (bottlenecks, idle pins, expiring extractors).
    """
    repo = get_pi_repository(request)

    colonies = repo.get_colonies(character_id)
    colony = next((c for c in colonies if c.planet_id == planet_id), None)
    if not colony:
        raise HTTPException(status_code=404, detail="Colony not found")

    detail = repo.get_colony_detail(colony.id)
    if not detail:
        raise HTTPException(status_code=404, detail="Colony detail not found")

    now = datetime.now(timezone.utc)

    # Build nodes from pins
    nodes = []
    pin_map = {}
    for pin in detail.pins:
        # Classify pin type
        if pin.product_type_id and pin.qty_per_cycle:
            pin_type = "extractor"
        elif pin.schematic_id:
            pin_type = "factory"
        else:
            # Heuristic: check type name for classification
            type_name = (pin.type_name or "").lower()
            if "launch" in type_name:
                pin_type = "launchpad"
            elif "storage" in type_name:
                pin_type = "storage"
            elif "command" in type_name:
                pin_type = "command_center"
            else:
                pin_type = "other"

        # Health status
        health = "ok"
        health_detail = None
        if pin_type == "extractor":
            if pin.expiry_time:
                expiry = pin.expiry_time
                if expiry.tzinfo is None:
                    expiry = expiry.replace(tzinfo=timezone.utc)
                hours = (expiry - now).total_seconds() / 3600
                if hours <= 0:
                    health = "stopped"
                    health_detail = "Extractor has stopped"
                elif hours <= 4:
                    health = "critical"
                    health_detail = f"Depletes in {hours:.1f}h"
                elif hours <= 12:
                    health = "warning"
                    health_detail = f"Depletes in {hours:.1f}h"
            else:
                health = "stopped"
                health_detail = "No expiry set"
        elif pin_type == "factory" and not pin.schematic_id:
            health = "idle"
            health_detail = "No schematic set"

        node = {
            "pin_id": pin.pin_id,
            "type_id": pin.type_id,
            "type_name": pin.type_name,
            "pin_type": pin_type,
            "latitude": pin.latitude,
            "longitude": pin.longitude,
            "health": health,
            "health_detail": health_detail,
        }
        if pin_type == "extractor":
            node["product_type_id"] = pin.product_type_id
            node["product_name"] = pin.product_name
            node["qty_per_cycle"] = pin.qty_per_cycle
            node["cycle_time"] = pin.cycle_time
            node["expiry_time"] = pin.expiry_time.isoformat() if pin.expiry_time else None
        elif pin_type == "factory":
            node["schematic_id"] = pin.schematic_id
            node["schematic_name"] = pin.schematic_name

        nodes.append(node)
        pin_map[pin.pin_id] = node

    # Build edges from routes
    edges = []
    # Track incoming volume per pin for bottleneck detection
    incoming_volume = {}
    for route in detail.routes:
        edges.append({
            "route_id": route.route_id,
            "source_pin_id": route.source_pin_id,
            "destination_pin_id": route.destination_pin_id,
            "content_type_id": route.content_type_id,
            "content_name": route.content_name,
            "quantity": route.quantity,
        })
        incoming_volume.setdefault(route.destination_pin_id, 0)
        incoming_volume[route.destination_pin_id] += route.quantity

    # Detect pins with no incoming/outgoing routes (disconnected)
    routed_pins = set()
    for route in detail.routes:
        routed_pins.add(route.source_pin_id)
        routed_pins.add(route.destination_pin_id)

    for node in nodes:
        if node["pin_type"] in ("factory", "extractor") and node["pin_id"] not in routed_pins:
            node["health"] = "warning"
            node["health_detail"] = "No routes connected"

    # Summary health
    health_counts = {"ok": 0, "warning": 0, "critical": 0, "stopped": 0, "idle": 0}
    for node in nodes:
        h = node.get("health", "ok")
        health_counts[h] = health_counts.get(h, 0) + 1

    overall = "ok"
    if health_counts.get("stopped", 0) > 0 or health_counts.get("critical", 0) > 0:
        overall = "critical"
    elif health_counts.get("warning", 0) > 0 or health_counts.get("idle", 0) > 0:
        overall = "warning"

    return {
        "colony": {
            "planet_id": colony.planet_id,
            "planet_type": colony.planet_type,
            "solar_system_name": colony.solar_system_name,
        },
        "nodes": nodes,
        "edges": edges,
        "health_summary": {
            "overall": overall,
            "counts": health_counts,
        },
    }


@router.get("/health")
def pi_health_check(
    request: Request,
    character_ids: str = Query(..., description="Comma-separated character IDs"),
):
    """Quick health check across all PI colonies for given characters.

    Returns per-colony health status with actionable alerts.
    """
    repo = get_pi_repository(request)

    ids = [int(x.strip()) for x in character_ids.split(",") if x.strip().isdigit()]
    if not ids:
        raise HTTPException(status_code=400, detail="No character IDs provided")

    now = datetime.now(timezone.utc)
    colonies_health = []
    total_extractors = 0
    stopped_extractors = 0
    expiring_extractors = 0

    for char_id in ids:
        with request.app.state.db.cursor() as cur:
            cur.execute(
                "SELECT character_name FROM characters WHERE character_id = %s",
                (char_id,)
            )
            result = cur.fetchone()
            char_name = result['character_name'] if result else f"Character {char_id}"

        colonies = repo.get_colonies(char_id)
        for colony in colonies:
            detail = repo.get_colony_detail(colony.id)
            if not detail:
                continue

            colony_issues = []
            ext_count = 0
            factory_count = 0

            for pin in detail.pins:
                if pin.product_type_id and pin.qty_per_cycle:
                    ext_count += 1
                    total_extractors += 1
                    if pin.expiry_time:
                        expiry = pin.expiry_time
                        if expiry.tzinfo is None:
                            expiry = expiry.replace(tzinfo=timezone.utc)
                        hours = (expiry - now).total_seconds() / 3600
                        if hours <= 0:
                            stopped_extractors += 1
                            colony_issues.append({
                                "type": "extractor_stopped",
                                "severity": "critical",
                                "product": pin.product_name,
                            })
                        elif hours <= 4:
                            expiring_extractors += 1
                            colony_issues.append({
                                "type": "extractor_critical",
                                "severity": "critical",
                                "product": pin.product_name,
                                "hours_remaining": round(hours, 1),
                            })
                        elif hours <= 12:
                            expiring_extractors += 1
                            colony_issues.append({
                                "type": "extractor_expiring",
                                "severity": "warning",
                                "product": pin.product_name,
                                "hours_remaining": round(hours, 1),
                            })
                    else:
                        stopped_extractors += 1
                        colony_issues.append({
                            "type": "extractor_no_program",
                            "severity": "critical",
                            "product": pin.product_name,
                        })
                elif pin.schematic_id:
                    factory_count += 1

            # Check for unrouted pins
            routed_pins = set()
            for route in detail.routes:
                routed_pins.add(route.source_pin_id)
                routed_pins.add(route.destination_pin_id)

            for pin in detail.pins:
                if (pin.product_type_id or pin.schematic_id) and pin.pin_id not in routed_pins:
                    colony_issues.append({
                        "type": "unrouted_pin",
                        "severity": "warning",
                        "pin_type": pin.type_name,
                    })

            status = "ok"
            if any(i["severity"] == "critical" for i in colony_issues):
                status = "critical"
            elif colony_issues:
                status = "warning"

            colonies_health.append({
                "character_id": char_id,
                "character_name": char_name,
                "planet_id": colony.planet_id,
                "planet_type": colony.planet_type,
                "solar_system_name": colony.solar_system_name,
                "extractors": ext_count,
                "factories": factory_count,
                "status": status,
                "issues": colony_issues,
            })

    colonies_health.sort(key=lambda c: (
        0 if c["status"] == "critical" else 1 if c["status"] == "warning" else 2
    ))

    overall = "ok"
    if stopped_extractors > 0:
        overall = "critical"
    elif expiring_extractors > 0:
        overall = "warning"

    return {
        "overall_health": overall,
        "total_extractors": total_extractors,
        "stopped_extractors": stopped_extractors,
        "expiring_extractors": expiring_extractors,
        "colonies": colonies_health,
    }
