"""PI empire plan CRUD and profitability endpoints."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Query

from app.services.pi.models import (
    EmpireProfitabilityResponse,
    EmpirePlanCreate,
    EmpirePlanAssignmentCreate,
)
from eve_shared.constants import JITA_REGION_ID
from ._helpers import (
    get_pi_repository,
    PISchematicService,
    MarketPriceAdapter,
    PIEmpireService,
    PIProfitabilityService,
)

router = APIRouter()


# ==================== Empire Profitability ====================

@router.get("/profitability/empire", response_model=EmpireProfitabilityResponse)
def get_empire_profitability(
    request: Request,
    total_planets: int = Query(18, ge=6, le=36, description="Total planets in empire"),
    extraction_planets: int = Query(12, ge=0, le=30, description="Planets for extraction"),
    factory_planets: int = Query(6, ge=0, le=18, description="Planets for factories"),
    region_id: int = Query(JITA_REGION_ID, description="Region ID for market prices"),
    poco_tax: float = Query(0.10, ge=0.0, le=1.0, description="POCO tax rate (0-1)"),
) -> EmpireProfitabilityResponse:
    """
    Calculate profitability of all P4 products for a PI empire.

    Analyzes each P4 product assuming the specified planet configuration:
    - Monthly output based on extraction/factory split
    - Production costs including POCO taxes
    - Complexity rating (number of P0 materials)
    - Logistics score (transfer requirements)

    **Configuration Example:**
    - 3 characters x 6 planets = 18 total
    - 12 extraction planets (P0->P1)
    - 6 factory planets (P2->P4)
    - 10% POCO tax
    """
    if extraction_planets + factory_planets > total_planets:
        raise HTTPException(
            status_code=400,
            detail="extraction_planets + factory_planets cannot exceed total_planets"
        )

    repo = get_pi_repository(request)
    market = MarketPriceAdapter(request.app.state.db)
    schematic_service = PISchematicService(repo)
    empire_service = PIEmpireService(repo, schematic_service, market)

    return empire_service.calculate_empire_profitability(
        total_planets=total_planets,
        extraction_planets=extraction_planets,
        factory_planets=factory_planets,
        region_id=region_id,
        poco_tax=poco_tax,
    )


# ==================== Empire Plan CRUD Endpoints ====================

@router.post("/empire/plans")
def create_empire_plan(request: Request, plan: EmpirePlanCreate):
    """
    Create a new PI empire plan.

    An empire plan organizes multi-character PI production for a target P4 product.
    """
    repo = get_pi_repository(request)

    # Get product name from schematic if not provided
    target_product_name = plan.target_product_name
    if not target_product_name:
        schematic = repo.get_schematic_for_output(plan.target_product_id)
        if not schematic:
            raise HTTPException(
                status_code=400,
                detail=f"Product {plan.target_product_id} is not a valid PI schematic output"
            )
        target_product_name = schematic.output_name

    plan_id = repo.create_empire_plan(
        name=plan.name,
        target_product_id=plan.target_product_id,
        target_product_name=target_product_name,
        home_system_id=plan.home_system_id,
        home_system_name=plan.home_system_name,
        total_planets=plan.total_planets,
        extraction_planets=plan.extraction_planets,
        factory_planets=plan.factory_planets,
        poco_tax_rate=plan.poco_tax_rate,
    )

    return {"plan_id": plan_id, "status": "created"}


@router.get("/empire/plans")
def list_empire_plans(
    request: Request,
    status: Optional[str] = Query(None, description="Filter by status: planning, active, paused, completed")
):
    """
    List all PI empire plans.

    Optionally filter by status.
    """
    repo = get_pi_repository(request)
    plans = repo.list_empire_plans(status=status)

    # Build response with assignment counts
    result = []
    for plan in plans:
        assignments = repo.get_plan_assignments(plan["id"])
        result.append({
            **plan,
            "assignment_count": len(assignments),
            "poco_tax_rate": float(plan["poco_tax_rate"]) if plan.get("poco_tax_rate") else 0.10,
        })

    return result


@router.get("/empire/plans/{plan_id}")
def get_empire_plan(request: Request, plan_id: int):
    """
    Get a specific empire plan with its assignments.
    """
    repo = get_pi_repository(request)

    plan = repo.get_empire_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    assignments = repo.get_plan_assignments(plan_id)

    return {
        "plan_id": plan["id"],
        "name": plan["name"],
        "target_product": {
            "id": plan["target_product_id"],
            "name": plan["target_product_name"],
        },
        "home_system": {
            "id": plan["home_system_id"],
            "name": plan["home_system_name"],
        } if plan["home_system_id"] else None,
        "configuration": {
            "total_planets": plan["total_planets"],
            "extraction_planets": plan["extraction_planets"],
            "factory_planets": plan["factory_planets"],
            "poco_tax_rate": float(plan["poco_tax_rate"]) if plan.get("poco_tax_rate") else 0.10,
        },
        "status": plan["status"],
        "estimated_monthly_output": plan["estimated_monthly_output"],
        "estimated_monthly_profit": float(plan["estimated_monthly_profit"]) if plan.get("estimated_monthly_profit") else None,
        "assignments": assignments,
        "created_at": plan["created_at"],
        "updated_at": plan["updated_at"],
    }


@router.post("/empire/plans/{plan_id}/assignments")
def add_empire_plan_assignment(
    request: Request,
    plan_id: int,
    assignment: EmpirePlanAssignmentCreate
):
    """
    Add a character assignment to an empire plan.
    """
    repo = get_pi_repository(request)

    # Verify plan exists
    plan = repo.get_empire_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    # Validate role
    valid_roles = {"extractor", "factory", "hybrid"}
    if assignment.role not in valid_roles:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role '{assignment.role}'. Must be one of: {', '.join(sorted(valid_roles))}"
        )

    assignment_id = repo.add_plan_assignment(
        plan_id=plan_id,
        character_id=assignment.character_id,
        character_name=assignment.character_name,
        role=assignment.role,
        planets=assignment.planets,
    )

    return {"assignment_id": assignment_id, "status": "created"}


@router.patch("/empire/plans/{plan_id}/status")
def update_empire_plan_status(
    request: Request,
    plan_id: int,
    status: str = Query(..., description="New status: planning, active, paused, completed")
):
    """
    Update an empire plan's status.
    """
    repo = get_pi_repository(request)

    valid_statuses = {"planning", "active", "paused", "completed"}
    if status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {', '.join(sorted(valid_statuses))}"
        )

    success = repo.update_plan_status(plan_id, status)
    if not success:
        raise HTTPException(status_code=404, detail="Plan not found")

    return {"status": "updated", "new_status": status}


@router.delete("/empire/plans/{plan_id}")
def delete_empire_plan(request: Request, plan_id: int):
    """
    Delete an empire plan and all its assignments.
    """
    repo = get_pi_repository(request)

    success = repo.delete_empire_plan(plan_id)
    if not success:
        raise HTTPException(status_code=404, detail="Plan not found")

    return {"status": "deleted"}


@router.get("/empire/plans/{plan_id}/logistics")
def get_empire_logistics(
    request: Request,
    plan_id: int,
    frequency_hours: int = Query(48, description="Pickup frequency in hours"),
):
    """
    Calculate optimal logistics plan for a PI empire.

    Returns pickup schedule, cross-character transfers, and hub station recommendation.
    """
    repo = get_pi_repository(request)

    # Verify plan exists
    with repo.db.cursor() as cur:
        cur.execute("SELECT * FROM pi_empire_plans WHERE id = %s", (plan_id,))
        plan = cur.fetchone()

    if not plan:
        raise HTTPException(status_code=404, detail="Empire plan not found")

    # Get all colonies with system info
    colonies = repo.get_plan_colonies_with_systems(plan_id)
    if not colonies:
        raise HTTPException(status_code=400, detail="No colonies assigned to this plan")

    # Group colonies by character and system
    char_systems = {}
    for colony in colonies:
        char_id = colony['character_id']
        if char_id not in char_systems:
            char_systems[char_id] = {
                'character_name': colony['character_name'],
                'role': colony['role'],
                'systems': {}
            }
        sys_id = colony['solar_system_id']
        if sys_id not in char_systems[char_id]['systems']:
            char_systems[char_id]['systems'][sys_id] = {
                'system_name': colony['system_name'],
                'security': float(colony['security']),
                'planets': 0
            }
        char_systems[char_id]['systems'][sys_id]['planets'] += 1

    # Build pickup route (simple: group by character, then by system)
    route = []
    total_jumps = 0
    prev_system = None

    for char_id, char_data in char_systems.items():
        for sys_id, sys_data in char_data['systems'].items():
            # Estimate time: 5 min per planet + jump time
            est_time = sys_data['planets'] * 5

            # Add jump time from previous system
            if prev_system and prev_system != sys_id:
                jumps = repo.get_system_jump_distance(prev_system, sys_id)
                total_jumps += jumps
                est_time += jumps * 1  # 1 min per jump

            # Estimate cargo: ~500 m3 per planet per pickup
            cargo_volume = sys_data['planets'] * 500.0

            route.append({
                'character_id': char_id,
                'character_name': char_data['character_name'],
                'system_id': sys_id,
                'system_name': sys_data['system_name'],
                'planets': sys_data['planets'],
                'estimated_time_minutes': est_time,
                'materials_volume_m3': cargo_volume
            })
            prev_system = sys_id

    # Calculate totals
    total_time = sum(stop['estimated_time_minutes'] for stop in route)
    total_cargo = sum(stop['materials_volume_m3'] for stop in route)

    pickup_schedule = {
        'optimal_frequency_hours': frequency_hours,
        'next_pickup': None,  # Could calculate based on extractor expiry
        'route': route,
        'total_time_minutes': total_time,
        'total_jumps': total_jumps,
        'total_cargo_volume_m3': total_cargo
    }

    # Determine transfers (extractors -> factories)
    transfers = []
    transfer_id = 1

    extractors = [(cid, cdata) for cid, cdata in char_systems.items() if cdata['role'] in ('extractor', 'hybrid')]
    factories = [(cid, cdata) for cid, cdata in char_systems.items() if cdata['role'] in ('factory', 'hybrid')]

    # If we have both extractors and factories, create transfer records
    if extractors and factories:
        factory_char = factories[0]  # Primary factory character
        for ext_char_id, ext_data in extractors:
            if ext_char_id != factory_char[0]:  # Don't transfer to self
                transfers.append({
                    'id': transfer_id,
                    'from_character_id': ext_char_id,
                    'from_character_name': ext_data['character_name'],
                    'to_character_id': factory_char[0],
                    'to_character_name': factory_char[1]['character_name'],
                    'materials': [{'type_name': 'P1 Materials', 'quantity': 3000, 'volume_m3': 300}],
                    'total_volume_m3': 300.0,
                    'method': 'contract',
                    'station_id': None,
                    'station_name': None,
                    'frequency_hours': frequency_hours
                })
                transfer_id += 1

    # Find hub station (use home system from plan or most common system)
    hub_system_id = plan['home_system_id']
    hub_system_name = plan['home_system_name'] or 'Unknown'

    if not hub_system_id and colonies:
        # Use most common system
        system_counts = {}
        for colony in colonies:
            sid = colony['solar_system_id']
            system_counts[sid] = system_counts.get(sid, 0) + 1
        hub_system_id = max(system_counts, key=system_counts.get)
        for colony in colonies:
            if colony['solar_system_id'] == hub_system_id:
                hub_system_name = colony['system_name']
                break

    # Get station in hub system
    stations = repo.get_stations_in_system(hub_system_id) if hub_system_id else []
    hub_station = {
        'station_id': stations[0]['station_id'] if stations else 0,
        'station_name': stations[0]['station_name'] if stations else f'{hub_system_name} - Station',
        'system_id': hub_system_id or 0,
        'system_name': hub_system_name,
        'security': 0.5,
        'avg_jumps_to_colonies': total_jumps / max(len(route), 1),
        'reason': 'Central location with minimal jumps to all colonies'
    }

    # Update transfer station info
    for transfer in transfers:
        transfer['station_id'] = hub_station['station_id']
        transfer['station_name'] = hub_station['station_name']

    # Calculate weekly estimates
    pickups_per_week = 168 / frequency_hours  # hours in a week
    weekly_time = (total_time / 60) * pickups_per_week

    return {
        'plan_id': plan_id,
        'pickup_schedule': pickup_schedule,
        'transfers': transfers,
        'hub_station': hub_station,
        'estimated_weekly_trips': int(pickups_per_week),
        'estimated_weekly_time_hours': round(weekly_time, 1)
    }


# ==================== Empire Analysis (Bottom-Up) ====================

@router.get("/empire/analysis")
def get_empire_analysis(
    request: Request,
    character_ids: str = Query(..., description="Comma-separated character IDs"),
    region_id: int = Query(JITA_REGION_ID, description="Region for market prices"),
):
    """
    Bottom-up analysis of PI empire across multiple characters.

    Returns what is being produced, what could be built, and what is missing.
    Aggregates extractor output (P0) and factory output (P1+) across all characters,
    then evaluates feasibility of each P4 product.
    """
    repo = get_pi_repository(request)
    market = MarketPriceAdapter(request.app.state.db)
    schematic_service = PISchematicService(repo)

    ids = [int(x.strip()) for x in character_ids.split(",") if x.strip().isdigit()]
    if not ids:
        raise HTTPException(status_code=400, detail="No valid character IDs")

    # ── Gather per-character data ──

    characters = []
    production_map = {}   # type_id -> { type_name, qty_per_hour, characters[] }
    factory_output = {}   # type_id -> { type_name, qty_per_hour, tier, characters[] }

    for char_id in ids:
        # Character name
        with request.app.state.db.cursor() as cur:
            cur.execute(
                "SELECT character_name FROM characters WHERE character_id = %s",
                (char_id,)
            )
            row = cur.fetchone()
            char_name = (row["character_name"] if isinstance(row, dict) else row[0]) if row else f"Char {char_id}"

        colonies = repo.get_colonies(char_id)
        char_extractors = 0
        char_factories = 0

        for colony in colonies:
            detail = repo.get_colony_detail(colony.id)
            if not detail:
                continue

            for pin in detail.pins:
                # Extractor pins -> P0 production
                if pin.product_type_id and pin.qty_per_cycle and pin.cycle_time and pin.cycle_time > 0:
                    char_extractors += 1
                    qty_per_hour = (pin.qty_per_cycle * 3600) / pin.cycle_time
                    tid = pin.product_type_id
                    tname = pin.product_name or f"Type {tid}"

                    if tid not in production_map:
                        production_map[tid] = {
                            "type_id": tid,
                            "type_name": tname,
                            "qty_per_hour": 0,
                            "characters": [],
                        }
                    production_map[tid]["qty_per_hour"] += qty_per_hour
                    if char_id not in production_map[tid]["characters"]:
                        production_map[tid]["characters"].append(char_id)

                # Factory pins -> P1+ production
                elif pin.schematic_id:
                    char_factories += 1
                    schematic = repo.get_schematic(pin.schematic_id)
                    if schematic:
                        out_id = schematic.output_type_id
                        out_name = schematic.output_name
                        cycles_per_hour = 3600 / schematic.cycle_time if schematic.cycle_time > 0 else 0
                        qty_h = schematic.output_quantity * cycles_per_hour

                        if out_id not in factory_output:
                            factory_output[out_id] = {
                                "type_id": out_id,
                                "type_name": out_name,
                                "qty_per_hour": 0,
                                "tier": schematic.tier,
                                "characters": [],
                            }
                        factory_output[out_id]["qty_per_hour"] += qty_h
                        if char_id not in factory_output[out_id]["characters"]:
                            factory_output[out_id]["characters"].append(char_id)

        characters.append({
            "character_id": char_id,
            "character_name": char_name,
            "colonies": len(colonies),
            "extractors": char_extractors,
            "factories": char_factories,
        })

    # ── Build combined available set (P0 from extractors + P1+ from factories) ──

    available = {}  # type_id -> qty_per_hour
    for tid, data in production_map.items():
        available[tid] = data["qty_per_hour"]
    for tid, data in factory_output.items():
        available[tid] = data["qty_per_hour"]

    # ── Get all schematics and profitability ──

    all_schematics = repo.get_all_schematics()
    p4_schematics = [s for s in all_schematics if s.tier == 4]

    # Build output_type_id -> schematic lookup
    schematic_by_output = {}
    for s in all_schematics:
        schematic_by_output[s.output_type_id] = s

    # ── Evaluate P4 feasibility ──

    p4_feasibility = []

    for p4 in p4_schematics:
        # Get all unique type_ids in the full chain
        all_chain_nodes = _collect_all_chain_inputs(p4.output_type_id, schematic_by_output)
        inputs_total = len(all_chain_nodes)

        available_inputs = []
        missing_inputs = []

        for node_tid, node_info in all_chain_nodes.items():
            if node_tid in available:
                available_inputs.append({
                    "type_id": node_tid,
                    "type_name": node_info["type_name"],
                    "tier": node_info["tier"],
                    "qty_per_hour": round(available[node_tid], 2),
                    "from_production": True,
                })
            else:
                price = market.get_price(node_tid, region_id)
                missing_inputs.append({
                    "type_id": node_tid,
                    "type_name": node_info["type_name"],
                    "tier": node_info["tier"],
                    "market_price": round(price, 2) if price else None,
                })

        inputs_available = len(available_inputs)
        feasibility_pct = round(inputs_available / inputs_total * 100, 1) if inputs_total > 0 else 0

        # Profit estimate
        profit_service = PIProfitabilityService(repo, market)
        profit = profit_service.calculate_profitability(p4.output_type_id, region_id)

        # Jita prices
        sell_price = market.get_price(p4.output_type_id, region_id)
        input_cost_total = profit.input_cost if profit else None
        missing_buy_cost = sum(
            m["market_price"] for m in missing_inputs if m.get("market_price")
        )

        p4_feasibility.append({
            "type_id": p4.output_type_id,
            "type_name": p4.output_name,
            "inputs_available": inputs_available,
            "inputs_total": inputs_total,
            "feasibility_pct": feasibility_pct,
            "available_inputs": available_inputs,
            "missing_inputs": missing_inputs,
            "profit_per_hour": round(profit.profit_per_hour, 2) if profit else None,
            "roi_percent": round(profit.roi_percent, 2) if profit else None,
            "sell_price": round(sell_price, 2) if sell_price else None,
            "input_cost": round(input_cost_total, 2) if input_cost_total else None,
            "missing_buy_cost": round(missing_buy_cost, 2),
        })

    # Sort by feasibility descending, then profit
    p4_feasibility.sort(
        key=lambda x: (x["feasibility_pct"], x["profit_per_hour"] or 0),
        reverse=True,
    )

    # Round production_map quantities
    for tid in production_map:
        production_map[tid]["qty_per_hour"] = round(production_map[tid]["qty_per_hour"], 2)
    for tid in factory_output:
        factory_output[tid]["qty_per_hour"] = round(factory_output[tid]["qty_per_hour"], 2)

    return {
        "characters": characters,
        "production_map": production_map,
        "factory_output": factory_output,
        "p4_feasibility": p4_feasibility,
    }


def _collect_all_chain_inputs(
    target_type_id: int,
    schematic_by_output: dict,
    _visited: set = None,
) -> dict:
    """Recursively collect all unique inputs (P0 through P3) for a target product.

    Returns dict of type_id -> { type_name, tier }.
    Excludes the target product itself.
    """
    if _visited is None:
        _visited = set()

    result = {}
    schematic = schematic_by_output.get(target_type_id)
    if not schematic:
        return result

    for inp in schematic.inputs:
        if inp.type_id in _visited:
            continue
        _visited.add(inp.type_id)

        # Determine tier
        child_schematic = schematic_by_output.get(inp.type_id)
        tier = child_schematic.tier if child_schematic else 0

        result[inp.type_id] = {
            "type_name": inp.type_name,
            "tier": tier,
        }

        # Recurse into inputs
        sub = _collect_all_chain_inputs(inp.type_id, schematic_by_output, _visited)
        result.update(sub)

    return result
