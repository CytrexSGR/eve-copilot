"""Sovereignty Resource Topology — Equinox power/workforce/reagent balance.

Provides endpoints for:
- System topology with power/workforce capacity (from SDE)
- Dynamic resource balance per system (from ESI sync)
- Skyhook status and cargo monitoring
- Metenox drill fuel and yield tracking
- Sov upgrade reference data
- Workforce connectivity graph (BFS over alliance-owned systems)
"""

import logging
from collections import defaultdict, deque
from typing import Optional, Literal

from fastapi import APIRouter, Body, Query, Path, HTTPException
from pydantic import Field

from app.models.base import CamelModel
from app.database import db_cursor
from eve_shared.utils.error_handling import handle_endpoint_errors

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/systems")
@handle_endpoint_errors()
def list_systems(
    region_id: Optional[int] = Query(None, description="Filter by region ID"),
    alliance_id: Optional[int] = Query(None, description="Filter by owning alliance"),
    min_power: Optional[int] = Query(None, description="Minimum max potential power"),
    min_workforce: Optional[int] = Query(None, description="Minimum max potential workforce"),
    limit: int = Query(200, ge=1, le=2000),
    offset: int = Query(0, ge=0),
):
    """List systems with resource topology and current balance."""
    with db_cursor() as cur:
        where_clauses = []
        params = []

        if region_id is not None:
            where_clauses.append("st.region_id = %s")
            params.append(region_id)
        if alliance_id is not None:
            where_clauses.append("rb.owner_alliance_id = %s")
            params.append(alliance_id)
        if min_power is not None:
            where_clauses.append("st.max_potential_power >= %s")
            params.append(min_power)
        if min_workforce is not None:
            where_clauses.append("st.max_potential_workforce >= %s")
            params.append(min_workforce)

        where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        cur.execute(f"""
            SELECT
                st.system_id, st.system_name, st.constellation_id, st.region_id,
                st.security, st.sun_type_id, st.base_power,
                st.cnt_plasma, st.cnt_storm, st.cnt_gas,
                st.cnt_lava, st.cnt_ice,
                st.cnt_temperate, st.cnt_oceanic, st.cnt_barren,
                st.max_potential_power, st.max_potential_workforce,
                spv.sun_name, spv.category AS sun_category,
                rb.owner_alliance_id, rb.owner_alliance_name,
                rb.generated_power, rb.generated_workforce,
                rb.load_power, rb.load_workforce,
                rb.net_power, rb.net_workforce,
                rb.workforce_import, rb.workforce_export,
                rb.is_power_compliant, rb.installed_upgrades,
                rb.last_updated AS balance_updated,
                r."regionName" AS region_name
            FROM system_topology st
            LEFT JOIN system_resource_balance rb ON st.system_id = rb.system_id
            LEFT JOIN sun_power_values spv ON st.sun_type_id = spv.sun_type_id
            LEFT JOIN "mapRegions" r ON st.region_id = r."regionID"
            {where_sql}
            ORDER BY r."regionName", st.system_name
            LIMIT %s OFFSET %s
        """, params + [limit, offset])
        rows = cur.fetchall()

        # Get total count
        cur.execute(f"""
            SELECT COUNT(*) AS total
            FROM system_topology st
            LEFT JOIN system_resource_balance rb ON st.system_id = rb.system_id
            {where_sql}
        """, params)
        total = cur.fetchone()['total']

    return {
        "systems": [dict(r) for r in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/system/{system_id}")
@handle_endpoint_errors()
def get_system_detail(system_id: int = Path(..., description="Solar system ID")):
    """Get detailed resource topology for a single system."""
    with db_cursor() as cur:
        # System topology
        cur.execute("""
            SELECT
                st.system_id, st.system_name, st.constellation_id, st.region_id,
                st.security, st.sun_type_id, st.base_power,
                st.cnt_plasma, st.cnt_storm, st.cnt_gas,
                st.cnt_lava, st.cnt_ice,
                st.cnt_temperate, st.cnt_oceanic, st.cnt_barren,
                st.max_potential_power, st.max_potential_workforce,
                spv.sun_name, spv.category AS sun_category,
                r."regionName" AS region_name,
                c."constellationName" AS constellation_name
            FROM system_topology st
            LEFT JOIN sun_power_values spv ON st.sun_type_id = spv.sun_type_id
            LEFT JOIN "mapRegions" r ON st.region_id = r."regionID"
            LEFT JOIN "mapConstellations" c ON st.constellation_id = c."constellationID"
            WHERE st.system_id = %s
        """, (system_id,))
        topology = cur.fetchone()
        if not topology:
            raise HTTPException(status_code=404, detail="System not found")

        # Resource balance
        cur.execute("""
            SELECT
                owner_alliance_id, owner_alliance_name,
                generated_power, generated_workforce,
                load_power, load_workforce,
                net_power, net_workforce,
                workforce_import, workforce_export,
                is_power_compliant, installed_upgrades, last_updated
            FROM system_resource_balance
            WHERE system_id = %s
        """, (system_id,))
        balance = cur.fetchone()

        # Skyhooks in this system
        cur.execute("""
            SELECT
                structure_id, planet_id, planet_type, type_id, structure_name,
                power_output, workforce_output,
                reagent_type, reagent_rate, reagent_stock,
                vulnerability_start, vulnerability_end,
                last_siphon_alert, state, last_updated
            FROM skyhook_status
            WHERE system_id = %s
            ORDER BY planet_type
        """, (system_id,))
        skyhooks = [dict(r) for r in cur.fetchall()]

        # Metenox drills in this system
        cur.execute("""
            SELECT
                structure_id, moon_id, structure_name,
                moon_composition, fuel_blocks_qty, magmatic_gas_qty,
                fuel_expires, daily_yield_m3,
                accumulated_ore, output_bay_used_m3, output_bay_capacity_m3,
                state, last_asset_sync, last_updated
            FROM metenox_drills
            WHERE system_id = %s
        """, (system_id,))
        metenox = [dict(r) for r in cur.fetchall()]

        # Connected systems (gates) — deduplicate bidirectional entries
        cur.execute("""
            SELECT DISTINCT ON (neighbor_id)
                neighbor_id,
                st2.system_name AS neighbor_name,
                st2.max_potential_power AS neighbor_power,
                st2.max_potential_workforce AS neighbor_workforce,
                rb2.owner_alliance_id AS neighbor_alliance_id,
                rb2.owner_alliance_name AS neighbor_alliance_name
            FROM (
                SELECT "toSolarSystemID" AS neighbor_id
                FROM "mapSolarSystemJumps"
                WHERE "fromSolarSystemID" = %s
                UNION
                SELECT "fromSolarSystemID" AS neighbor_id
                FROM "mapSolarSystemJumps"
                WHERE "toSolarSystemID" = %s
            ) gates
            LEFT JOIN system_topology st2 ON st2.system_id = gates.neighbor_id
            LEFT JOIN system_resource_balance rb2 ON rb2.system_id = st2.system_id
            ORDER BY neighbor_id
        """, (system_id, system_id))
        neighbors = [dict(r) for r in cur.fetchall()]

    return {
        "topology": dict(topology),
        "balance": dict(balance) if balance else None,
        "skyhooks": skyhooks,
        "metenox_drills": metenox,
        "neighbors": neighbors,
    }


@router.get("/upgrades")
@handle_endpoint_errors()
def list_upgrade_types(
    category: Optional[str] = Query(None, description="Filter: strategic, military, industrial"),
):
    """List sovereignty hub upgrade types with resource costs."""
    with db_cursor() as cur:
        if category:
            cur.execute("""
                SELECT type_id, name, category, power_cost, workforce_cost,
                       reagent_type, reagent_rate, description
                FROM sov_upgrade_types
                WHERE category = %s
                ORDER BY power_cost
            """, (category,))
        else:
            cur.execute("""
                SELECT type_id, name, category, power_cost, workforce_cost,
                       reagent_type, reagent_rate, description
                FROM sov_upgrade_types
                ORDER BY category, power_cost
            """)
        return [dict(r) for r in cur.fetchall()]


@router.get("/summary")
@handle_endpoint_errors()
def resource_summary(
    alliance_id: Optional[int] = Query(None, description="Filter by owning alliance"),
):
    """Get aggregate resource summary across all owned systems."""
    with db_cursor() as cur:
        where = ""
        params = []
        if alliance_id:
            where = "WHERE rb.owner_alliance_id = %s"
            params.append(alliance_id)

        cur.execute(f"""
            SELECT
                COUNT(*) AS total_systems,
                SUM(st.max_potential_power) AS total_potential_power,
                SUM(st.max_potential_workforce) AS total_potential_workforce,
                SUM(rb.generated_power) AS total_generated_power,
                SUM(rb.generated_workforce) AS total_generated_workforce,
                SUM(rb.load_power) AS total_load_power,
                SUM(rb.load_workforce) AS total_load_workforce,
                SUM(rb.net_power) AS total_net_power,
                SUM(rb.net_workforce) AS total_net_workforce,
                COUNT(*) FILTER (WHERE rb.is_power_compliant = FALSE) AS power_deficit_systems,
                COUNT(*) FILTER (WHERE rb.net_workforce < 0) AS workforce_deficit_systems,
                rb.owner_alliance_id,
                rb.owner_alliance_name
            FROM system_resource_balance rb
            JOIN system_topology st ON rb.system_id = st.system_id
            {where}
            GROUP BY rb.owner_alliance_id, rb.owner_alliance_name
            ORDER BY COUNT(*) DESC
        """, params)
        rows = cur.fetchall()

    return [dict(r) for r in rows]


@router.get("/planet-values")
@handle_endpoint_errors()
def get_planet_values():
    """Get reference data for planet resource outputs."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT planet_type, power_output, workforce_output,
                   reagent_type, reagent_output, description
            FROM planet_resource_values
            ORDER BY power_output DESC, workforce_output DESC
        """)
        return [dict(r) for r in cur.fetchall()]


@router.get("/sun-values")
@handle_endpoint_errors()
def get_sun_values():
    """Get reference data for sun power outputs."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT sun_type_id, sun_name, base_power, category
            FROM sun_power_values
            ORDER BY base_power DESC
        """)
        return [dict(r) for r in cur.fetchall()]


# =============================================================================
# Workforce Graph (BFS Connectivity)
# =============================================================================

def _build_workforce_graph(cur, alliance_id: int):
    """Build graph of alliance-owned systems and their gate connections.

    Returns (owned_set, adjacency_dict, system_info_dict).
    """
    # Get systems owned by this alliance (IHUB holder = sovereignty)
    cur.execute("""
        SELECT ss.solar_system_id
        FROM sovereignty_structures ss
        WHERE ss.alliance_id = %s AND ss.structure_type_id = 32458
    """, (alliance_id,))
    owned_ids = {row['solar_system_id'] for row in cur.fetchall()}

    if not owned_ids:
        return set(), {}, {}

    # Get topology info for owned systems
    placeholders = ','.join(['%s'] * len(owned_ids))
    cur.execute(f"""
        SELECT st.system_id, st.system_name, st.region_id,
               st.max_potential_power, st.max_potential_workforce,
               st.cnt_temperate, st.cnt_oceanic, st.cnt_barren,
               st.cnt_lava, st.cnt_ice,
               rb.generated_workforce, rb.load_workforce,
               rb.net_workforce, rb.workforce_import, rb.workforce_export
        FROM system_topology st
        LEFT JOIN system_resource_balance rb ON st.system_id = rb.system_id
        WHERE st.system_id IN ({placeholders})
    """, list(owned_ids))
    system_info = {row['system_id']: dict(row) for row in cur.fetchall()}

    # Build adjacency among owned systems only
    cur.execute(f"""
        SELECT DISTINCT "fromSolarSystemID" AS from_id, "toSolarSystemID" AS to_id
        FROM "mapSolarSystemJumps"
        WHERE "fromSolarSystemID" IN ({placeholders})
          AND "toSolarSystemID" IN ({placeholders})
    """, list(owned_ids) + list(owned_ids))

    adjacency = defaultdict(set)
    for row in cur.fetchall():
        adjacency[row['from_id']].add(row['to_id'])
        adjacency[row['to_id']].add(row['from_id'])

    return owned_ids, adjacency, system_info


def _bfs_components(owned_ids: set, adjacency: dict) -> list[set]:
    """Find connected components via BFS."""
    visited = set()
    components = []

    for start in owned_ids:
        if start in visited:
            continue
        component = set()
        queue = deque([start])
        while queue:
            node = queue.popleft()
            if node in visited:
                continue
            visited.add(node)
            component.add(node)
            for neighbor in adjacency.get(node, set()):
                if neighbor not in visited and neighbor in owned_ids:
                    queue.append(neighbor)
        components.append(component)

    return sorted(components, key=len, reverse=True)


@router.get("/workforce-graph")
@handle_endpoint_errors()
def workforce_graph(
    alliance_id: int = Query(..., description="Alliance ID to analyze"),
):
    """Get workforce connectivity graph for an alliance's territory.

    Returns connected components of owned systems with workforce
    surplus/deficit per component. Useful for identifying isolated
    systems that cannot receive workforce imports.
    """
    with db_cursor() as cur:
        owned_ids, adjacency, system_info = _build_workforce_graph(cur, alliance_id)

        if not owned_ids:
            return {
                "alliance_id": alliance_id,
                "total_systems": 0,
                "components": [],
                "edges": [],
            }

        # Find connected components
        components = _bfs_components(owned_ids, adjacency)

        # Build component summaries
        component_data = []
        for i, comp in enumerate(components):
            systems = []
            total_potential_wf = 0
            total_potential_pw = 0
            total_generated_wf = 0
            total_load_wf = 0
            wf_surplus_systems = 0
            wf_deficit_systems = 0

            for sid in sorted(comp):
                info = system_info.get(sid, {})
                pot_wf = info.get('max_potential_workforce', 0) or 0
                pot_pw = info.get('max_potential_power', 0) or 0
                gen_wf = info.get('generated_workforce', 0) or 0
                load_wf = info.get('load_workforce', 0) or 0
                net_wf = info.get('net_workforce') or (gen_wf - load_wf)

                if net_wf > 0:
                    wf_surplus_systems += 1
                elif net_wf < 0:
                    wf_deficit_systems += 1

                total_potential_wf += pot_wf
                total_potential_pw += pot_pw
                total_generated_wf += gen_wf
                total_load_wf += load_wf

                systems.append({
                    "system_id": sid,
                    "system_name": info.get('system_name', 'Unknown'),
                    "max_potential_workforce": pot_wf,
                    "max_potential_power": pot_pw,
                    "generated_workforce": gen_wf,
                    "load_workforce": load_wf,
                    "net_workforce": net_wf,
                    "has_workforce_planets": (
                        (info.get('cnt_temperate', 0) or 0) +
                        (info.get('cnt_oceanic', 0) or 0) +
                        (info.get('cnt_barren', 0) or 0)
                    ) > 0,
                })

            component_data.append({
                "component_id": i,
                "system_count": len(comp),
                "total_potential_workforce": total_potential_wf,
                "total_potential_power": total_potential_pw,
                "total_generated_workforce": total_generated_wf,
                "total_load_workforce": total_load_wf,
                "net_workforce": total_generated_wf - total_load_wf,
                "surplus_systems": wf_surplus_systems,
                "deficit_systems": wf_deficit_systems,
                "is_self_sufficient": total_generated_wf >= total_load_wf,
                "systems": systems,
            })

        # Build edge list for visualization
        edges = []
        seen_edges = set()
        for sid in owned_ids:
            for neighbor in adjacency.get(sid, set()):
                edge_key = (min(sid, neighbor), max(sid, neighbor))
                if edge_key not in seen_edges:
                    seen_edges.add(edge_key)
                    edges.append({
                        "from": edge_key[0],
                        "to": edge_key[1],
                    })

    return {
        "alliance_id": alliance_id,
        "total_systems": len(owned_ids),
        "total_components": len(components),
        "components": component_data,
        "edges": edges,
    }


@router.get("/workforce-graph/vulnerability")
@handle_endpoint_errors()
def workforce_vulnerability(
    alliance_id: int = Query(..., description="Alliance ID to analyze"),
):
    """Identify critical systems whose loss would fragment the workforce network.

    For each system, simulates its removal and checks if it creates
    new disconnected components (bridge/cut-vertex detection).
    """
    with db_cursor() as cur:
        owned_ids, adjacency, system_info = _build_workforce_graph(cur, alliance_id)

        if len(owned_ids) < 2:
            return {
                "alliance_id": alliance_id,
                "critical_systems": [],
                "total_systems": len(owned_ids),
            }

        # Baseline: count components
        baseline_components = _bfs_components(owned_ids, adjacency)
        baseline_count = len(baseline_components)

        # Test each system removal
        critical_systems = []
        for test_id in owned_ids:
            reduced = owned_ids - {test_id}
            new_components = _bfs_components(reduced, adjacency)

            if len(new_components) > baseline_count:
                # This system is a bridge — its removal fragments the network
                info = system_info.get(test_id, {})
                fragments = []
                for comp in new_components:
                    frag_wf = sum(
                        (system_info.get(s, {}).get('max_potential_workforce', 0) or 0)
                        for s in comp
                    )
                    fragments.append({
                        "system_count": len(comp),
                        "total_workforce": frag_wf,
                    })

                critical_systems.append({
                    "system_id": test_id,
                    "system_name": info.get('system_name', 'Unknown'),
                    "new_component_count": len(new_components),
                    "fragments_created": len(new_components) - baseline_count,
                    "fragments": sorted(fragments, key=lambda f: f['system_count'], reverse=True),
                })

        critical_systems.sort(key=lambda c: c['fragments_created'], reverse=True)

    return {
        "alliance_id": alliance_id,
        "total_systems": len(owned_ids),
        "baseline_components": baseline_count,
        "critical_systems": critical_systems,
        "critical_count": len(critical_systems),
    }


# =============================================================================
# Sov Hub What-If Simulator
# =============================================================================

class SimulateRequest(CamelModel):
    action: Literal["remove_skyhook", "lose_system", "add_upgrade", "remove_upgrade"]
    alliance_id: int
    system_id: int
    structure_id: Optional[int] = None
    upgrade_type_id: Optional[int] = None


def _load_simulation_context(
    cur, system_id: int
) -> tuple[dict, list[dict], dict[int, dict]]:
    """Load system topology, online skyhooks, and upgrade reference data.

    Returns:
        (system_row, skyhooks_list, upgrades_ref_by_type_id)

    Raises:
        HTTPException 404 if system not found.
    """
    cur.execute("""
        SELECT st.system_id, st.system_name, st.base_power,
               st.max_potential_power, st.max_potential_workforce,
               st.cnt_plasma, st.cnt_storm, st.cnt_gas,
               st.cnt_temperate, st.cnt_oceanic, st.cnt_barren,
               st.cnt_lava, st.cnt_ice,
               rb.generated_power, rb.generated_workforce,
               rb.load_power, rb.load_workforce,
               rb.net_power, rb.net_workforce,
               rb.installed_upgrades
        FROM system_topology st
        LEFT JOIN system_resource_balance rb ON st.system_id = rb.system_id
        WHERE st.system_id = %s
    """, (system_id,))
    system = cur.fetchone()
    if not system:
        raise HTTPException(status_code=404, detail="System not found")

    cur.execute("""
        SELECT structure_id, planet_type, power_output, workforce_output,
               reagent_type, reagent_rate, structure_name
        FROM skyhook_status
        WHERE system_id = %s AND state = 'online'
    """, (system_id,))
    skyhooks = [dict(r) for r in cur.fetchall()]

    cur.execute("SELECT * FROM sov_upgrade_types")
    upgrades_ref = {row['type_id']: dict(row) for row in cur.fetchall()}

    return dict(system), skyhooks, upgrades_ref


def _build_resource_snapshot(
    system: dict, skyhooks: list[dict]
) -> tuple[int, int, int, int, list, dict]:
    """Extract current resource values and build the 'before' snapshot.

    Returns:
        (gen_power, gen_wf, load_power, load_wf, installed_upgrades, before_dict)
    """
    gen_power = system.get('generated_power') or 0
    gen_wf = system.get('generated_workforce') or 0
    load_power = system.get('load_power') or 0
    load_wf = system.get('load_workforce') or 0
    installed = system.get('installed_upgrades') or []

    before = {
        "generated_power": gen_power,
        "generated_workforce": gen_wf,
        "load_power": load_power,
        "load_workforce": load_wf,
        "net_power": gen_power - load_power,
        "net_workforce": gen_wf - load_wf,
        "power_compliant": gen_power >= load_power,
        "skyhook_count": len(skyhooks),
    }

    return gen_power, gen_wf, load_power, load_wf, installed, before


def _simulate_remove_skyhook(
    structure_id: Optional[int],
    skyhooks: list[dict],
    gen_power: int,
    gen_wf: int,
    load_power: int,
    load_wf: int,
    installed: list,
    upgrades_ref: dict[int, dict],
) -> dict:
    """Simulate removing a skyhook and return impact details.

    Raises:
        HTTPException 400 if structure_id missing.
        HTTPException 404 if skyhook not found.
    """
    if not structure_id:
        raise HTTPException(status_code=400, detail="structure_id required for remove_skyhook")

    removed = None
    for sk in skyhooks:
        if sk['structure_id'] == structure_id:
            removed = sk
            break

    if not removed:
        raise HTTPException(status_code=404, detail="Skyhook not found in this system")

    new_gen_power = gen_power - (removed.get('power_output') or 0)
    new_gen_wf = gen_wf - (removed.get('workforce_output') or 0)

    # Check which upgrades would go offline
    offline_upgrades = []
    if new_gen_power < load_power:
        for upg in installed:
            upg_id = upg.get('type_id') if isinstance(upg, dict) else upg
            ref = upgrades_ref.get(upg_id, {})
            if ref:
                offline_upgrades.append({
                    "type_id": upg_id,
                    "name": ref.get('name', 'Unknown'),
                    "power_cost": ref.get('power_cost', 0),
                    "workforce_cost": ref.get('workforce_cost', 0),
                })

    severity = (
        "critical" if offline_upgrades else
        "warning" if new_gen_power - load_power < 100 else
        "ok"
    )

    return {
        "removed_skyhook": {
            "structure_id": removed['structure_id'],
            "structure_name": removed.get('structure_name'),
            "planet_type": removed.get('planet_type'),
            "power_lost": removed.get('power_output', 0),
            "workforce_lost": removed.get('workforce_output', 0),
        },
        "after": {
            "generated_power": new_gen_power,
            "generated_workforce": new_gen_wf,
            "load_power": load_power,
            "load_workforce": load_wf,
            "net_power": new_gen_power - load_power,
            "net_workforce": new_gen_wf - load_wf,
            "power_compliant": new_gen_power >= load_power,
            "skyhook_count": len(skyhooks) - 1,
        },
        "offline_upgrades": offline_upgrades,
        "severity": severity,
    }


def _simulate_lose_system(
    cur,
    alliance_id: int,
    system_id: int,
    system: dict,
    before: dict,
) -> tuple[dict, bool]:
    """Simulate losing a system and return network fragmentation analysis.

    Returns:
        (partial_result_dict, should_return_early)
        When should_return_early is True, the caller should return immediately.
    """
    owned_ids, adjacency, sys_info = _build_workforce_graph(cur, alliance_id)

    if system_id not in owned_ids:
        return {
            "after": before,
            "network_impact": "System not owned by this alliance",
        }, True

    baseline_components = _bfs_components(owned_ids, adjacency)
    reduced = owned_ids - {system_id}
    new_components = _bfs_components(reduced, adjacency)

    fragments = []
    for comp in new_components:
        frag_wf = sum(
            (sys_info.get(s, {}).get('max_potential_workforce', 0) or 0)
            for s in comp
        )
        frag_pw = sum(
            (sys_info.get(s, {}).get('max_potential_power', 0) or 0)
            for s in comp
        )
        fragments.append({
            "system_count": len(comp),
            "total_workforce": frag_wf,
            "total_power": frag_pw,
        })

    is_bridge = len(new_components) > len(baseline_components)
    severity = (
        "critical" if is_bridge else
        "warning" if system['max_potential_workforce'] > 10000 else
        "ok"
    )

    return {
        "after": {
            "total_systems": len(reduced),
            "components_before": len(baseline_components),
            "components_after": len(new_components),
            "is_bridge_system": is_bridge,
            "fragments": sorted(fragments, key=lambda f: f['system_count'], reverse=True),
        },
        "lost_resources": {
            "max_potential_power": system['max_potential_power'],
            "max_potential_workforce": system['max_potential_workforce'],
        },
        "severity": severity,
    }, False


def _simulate_add_upgrade(
    upgrade_type_id: Optional[int],
    upgrades_ref: dict[int, dict],
    gen_power: int,
    gen_wf: int,
    load_power: int,
    load_wf: int,
) -> dict:
    """Simulate adding an upgrade and return resource impact.

    Raises:
        HTTPException 400 if upgrade_type_id missing.
        HTTPException 404 if upgrade type unknown.
    """
    if not upgrade_type_id:
        raise HTTPException(status_code=400, detail="upgrade_type_id required")
    ref = upgrades_ref.get(upgrade_type_id)
    if not ref:
        raise HTTPException(status_code=404, detail="Unknown upgrade type")

    new_load_power = load_power + ref['power_cost']
    new_load_wf = load_wf + ref['workforce_cost']
    can_install = gen_power >= new_load_power and gen_wf >= new_load_wf

    return {
        "upgrade": {
            "type_id": ref['type_id'],
            "name": ref['name'],
            "category": ref['category'],
            "power_cost": ref['power_cost'],
            "workforce_cost": ref['workforce_cost'],
            "reagent_type": ref.get('reagent_type'),
            "reagent_rate": ref.get('reagent_rate', 0),
        },
        "after": {
            "generated_power": gen_power,
            "generated_workforce": gen_wf,
            "load_power": new_load_power,
            "load_workforce": new_load_wf,
            "net_power": gen_power - new_load_power,
            "net_workforce": gen_wf - new_load_wf,
            "power_compliant": gen_power >= new_load_power,
        },
        "can_install": can_install,
        "severity": "ok" if can_install else "critical",
    }


def _simulate_remove_upgrade(
    upgrade_type_id: Optional[int],
    upgrades_ref: dict[int, dict],
    gen_power: int,
    gen_wf: int,
    load_power: int,
    load_wf: int,
) -> dict:
    """Simulate removing an upgrade and return freed resources.

    Raises:
        HTTPException 400 if upgrade_type_id missing.
        HTTPException 404 if upgrade type unknown.
    """
    if not upgrade_type_id:
        raise HTTPException(status_code=400, detail="upgrade_type_id required")
    ref = upgrades_ref.get(upgrade_type_id)
    if not ref:
        raise HTTPException(status_code=404, detail="Unknown upgrade type")

    new_load_power = max(0, load_power - ref['power_cost'])
    new_load_wf = max(0, load_wf - ref['workforce_cost'])

    return {
        "upgrade": {
            "type_id": ref['type_id'],
            "name": ref['name'],
            "power_freed": ref['power_cost'],
            "workforce_freed": ref['workforce_cost'],
        },
        "after": {
            "generated_power": gen_power,
            "generated_workforce": gen_wf,
            "load_power": new_load_power,
            "load_workforce": new_load_wf,
            "net_power": gen_power - new_load_power,
            "net_workforce": gen_wf - new_load_wf,
            "power_compliant": gen_power >= new_load_power,
        },
        "severity": "ok",
    }


@router.post("/simulate")
@handle_endpoint_errors()
def simulate_change(req: SimulateRequest = Body(...)):
    """What-if simulator: predict impact of losing a skyhook/system or changing upgrades.

    Actions:
    - remove_skyhook: Remove a skyhook, recalculate power/workforce for its system
    - lose_system: Remove a system entirely, check network fragmentation
    - add_upgrade: Add an upgrade to a system, check if resources suffice
    - remove_upgrade: Remove an upgrade, show freed resources
    """
    with db_cursor() as cur:
        system, skyhooks, upgrades_ref = _load_simulation_context(cur, req.system_id)
        gen_power, gen_wf, load_power, load_wf, installed, before = (
            _build_resource_snapshot(system, skyhooks)
        )

        result = {
            "system_id": req.system_id,
            "system_name": system['system_name'],
            "action": req.action,
            "before": before,
        }

        if req.action == "remove_skyhook":
            result.update(_simulate_remove_skyhook(
                req.structure_id, skyhooks,
                gen_power, gen_wf, load_power, load_wf,
                installed, upgrades_ref,
            ))

        elif req.action == "lose_system":
            partial, early_return = _simulate_lose_system(
                cur, req.alliance_id, req.system_id, system, before,
            )
            result.update(partial)
            if early_return:
                return result

        elif req.action == "add_upgrade":
            result.update(_simulate_add_upgrade(
                req.upgrade_type_id, upgrades_ref,
                gen_power, gen_wf, load_power, load_wf,
            ))

        elif req.action == "remove_upgrade":
            result.update(_simulate_remove_upgrade(
                req.upgrade_type_id, upgrades_ref,
                gen_power, gen_wf, load_power, load_wf,
            ))

    return result
