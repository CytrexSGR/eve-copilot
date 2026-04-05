"""PI advisor endpoint — skill-based opportunity analysis for a character."""

from typing import Optional, List
from datetime import datetime, timezone
import logging

from fastapi import APIRouter, Request, Query

from eve_shared.constants import JITA_REGION_ID
from eve_shared.utils.error_handling import handle_endpoint_errors

from ._helpers import (
    get_pi_repository,
    PISchematicService,
    MarketPriceAdapter,
    PIProfitabilityService,
    P0_PLANET_MAP,
    PLANET_P0_RESOURCES,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# PI skill IDs
SKILL_INTERPLANETARY_CONSOLIDATION = 2495
SKILL_COMMAND_CENTER_UPGRADES = 2505
SKILL_PLANETOLOGY = 2406
SKILL_ADVANCED_PLANETOLOGY = 2403

PI_SKILL_IDS = (
    SKILL_INTERPLANETARY_CONSOLIDATION,
    SKILL_COMMAND_CENTER_UPGRADES,
    SKILL_PLANETOLOGY,
    SKILL_ADVANCED_PLANETOLOGY,
)


def _optimal_planet_combination(needed_p0: list[str]) -> list[dict]:
    """Find minimal set of planet types covering all needed P0 materials.

    Uses greedy set-cover: repeatedly pick the planet type that covers
    the most uncovered P0 materials until all are covered.

    Returns list of dicts: [{"planet_type": "gas", "provides": ["Reactive Gas", "Ionic Solutions"]}]
    """
    uncovered = set(needed_p0)
    result = []

    while uncovered:
        best_planet = None
        best_covers: set = set()

        for planet_type, p0_list in PLANET_P0_RESOURCES.items():
            covers = uncovered & set(p0_list)
            if len(covers) > len(best_covers):
                best_covers = covers
                best_planet = planet_type

        if not best_planet:
            break  # No planet can cover remaining P0s (shouldn't happen)

        result.append({
            "planet_type": best_planet,
            "provides": sorted(best_covers),
        })
        uncovered -= best_covers

    # Sort by number of P0s provided (descending), then alphabetically
    result.sort(key=lambda x: (-len(x["provides"]), x["planet_type"]))
    return result


def _production_layout(tier: int, optimal_planets: list[dict], max_planets: int) -> dict:
    """Determine production layout recommendation based on tier and planet count.

    Returns a dict with:
      - strategy: "all_in_one" | "extract_and_factory" | "factory_buy"
      - summary: Human-readable recommendation text
      - planets: Enhanced optimal_planets with 'role' per planet
    """
    num_extract = len(optimal_planets)

    if tier == 1:
        # P1: extract P0 and process to P1 on same planet
        planets = [
            {**p, "role": "extract+process", "processing": f"P0 -> P1"}
            for p in optimal_planets
        ]
        return {
            "strategy": "all_in_one",
            "summary": f"Extract and process P1 on {num_extract} planet(s). No hauling needed.",
            "planets": planets,
        }

    if tier == 2:
        if num_extract == 1:
            # Single planet can provide all P0, do everything there
            planets = [
                {**optimal_planets[0], "role": "extract+process", "processing": "P0 -> P1 -> P2"}
            ]
            return {
                "strategy": "all_in_one",
                "summary": "All-in-one: extract P0, process P1 and P2 on same planet.",
                "planets": planets,
            }
        else:
            # Multiple extraction planets -> P1 locally, ship to factory for P2
            planets = [
                {**p, "role": "extract", "processing": "P0 -> P1"}
                for p in optimal_planets
            ]
            needs_factory = num_extract + 1 <= max_planets
            if needs_factory:
                planets.append({
                    "planet_type": "any",
                    "provides": [],
                    "role": "factory",
                    "processing": "P1 -> P2",
                })
                summary = f"Extract P0 on {num_extract} planets, process P1 locally, ship P1 to factory planet for P2."
            else:
                # No room for factory planet — try P2 on busiest extraction planet
                planets[0]["role"] = "extract+process"
                planets[0]["processing"] = "P0 -> P1 -> P2"
                summary = f"Extract P0 on {num_extract} planets, combine P2 on primary extraction planet (no room for factory)."
            return {
                "strategy": "extract_and_factory",
                "summary": summary,
                "planets": planets,
            }

    # P3 and P4
    if num_extract + 1 <= max_planets:
        # Self-sufficient: extraction planets + 1 factory planet
        planets = [
            {**p, "role": "extract", "processing": "P0 -> P1"}
            for p in optimal_planets
        ]
        processing_label = f"P1 -> P2 -> P3" if tier == 3 else "P1 -> P2 -> P3 -> P4"
        planets.append({
            "planet_type": "any",
            "provides": [],
            "role": "factory",
            "processing": processing_label,
        })
        summary = f"Extract P0 on {num_extract} planets, ship P1 to factory planet for {processing_label}."
    else:
        # Not enough planets — market buy recommended
        planets = [{
            "planet_type": "any",
            "provides": [],
            "role": "factory",
            "processing": f"Buy P2 inputs -> P3" if tier == 3 else "Buy P2/P3 inputs -> P4",
        }]
        summary = f"Buy intermediate inputs from market, process on 1 factory planet."

    return {
        "strategy": "factory_buy" if num_extract + 1 > max_planets else "extract_and_factory",
        "summary": summary,
        "planets": planets,
    }


def _build_chain_data(node) -> dict:
    """Extract P0→P1 mapping, P2+ recipes, and all type_ids from chain tree.

    Walks the chain tree recursively to build:
      - p0_to_p1: {p0_name: p1_name} — which P0 becomes which P1
      - recipes: [{tier, output, inputs}] — factory recipes for P2+
      - type_ids: {type_name: type_id} — all items in the chain

    Returns {"p0_to_p1": {...}, "recipes": [...], "type_ids": {...}}
    """
    p0_to_p1: dict[str, str] = {}
    recipes: list[dict] = []
    seen_outputs: set[str] = set()
    type_ids: dict[str, int] = {}

    def walk(n):
        type_ids[n.type_name] = n.type_id
        if not n.children:
            return
        for child in n.children:
            walk(child)
        # P1 node with P0 children → record P0→P1 mapping
        if n.tier == 1:
            for child in n.children:
                if child.tier == 0:
                    p0_to_p1[child.type_name] = n.type_name
        # P2+ node → record recipe (inputs → output)
        if n.tier >= 2 and n.type_name not in seen_outputs:
            seen_outputs.add(n.type_name)
            inputs = [c.type_name for c in n.children]
            recipes.append({
                "tier": n.tier,
                "output": n.type_name,
                "inputs": sorted(inputs),
            })

    walk(node)
    recipes.sort(key=lambda r: (r["tier"], r["output"]))
    return {"p0_to_p1": p0_to_p1, "recipes": recipes, "type_ids": type_ids}


@router.get("/advisor/{character_id}")
@handle_endpoint_errors()
def get_pi_advisor(
    request: Request,
    character_id: int,
    tier: Optional[int] = Query(None, ge=1, le=4),
    limit: int = Query(20, ge=1, le=50),
    region_id: int = Query(JITA_REGION_ID),
):
    """Get PI advisor recommendations based on character skills.

    Combines character PI skills with market profitability data to
    recommend feasible PI production chains. Each opportunity is
    enriched with required planet types, feasibility based on the
    character's max planet count, and full production step chains.
    """
    db = request.app.state.db
    repo = get_pi_repository(request)

    # ------------------------------------------------------------------
    # 1. Get PI skills — prefer character_skills table, fall back to
    #    pi_character_skills, default to 0 if nothing found.
    # ------------------------------------------------------------------
    ic_level = 0
    ccu_level = 0
    planetology_level = 0
    adv_planetology_level = 0

    with db.cursor() as cur:
        cur.execute(
            "SELECT skill_id, trained_skill_level FROM character_skills "
            "WHERE character_id = %s AND skill_id IN %s",
            (character_id, PI_SKILL_IDS),
        )
        rows = cur.fetchall()

    if rows:
        for row in rows:
            sid = row["skill_id"]
            lvl = row["trained_skill_level"] or 0
            if sid == SKILL_INTERPLANETARY_CONSOLIDATION:
                ic_level = lvl
            elif sid == SKILL_COMMAND_CENTER_UPGRADES:
                ccu_level = lvl
            elif sid == SKILL_PLANETOLOGY:
                planetology_level = lvl
            elif sid == SKILL_ADVANCED_PLANETOLOGY:
                adv_planetology_level = lvl
    else:
        # Fallback: pi_character_skills table
        pi_skills = repo.get_character_skills(character_id)
        if pi_skills:
            ic_level = pi_skills.get("interplanetary_consolidation", 0)
            ccu_level = pi_skills.get("command_center_upgrades", 0)

    max_planets = 1 + ic_level

    # ------------------------------------------------------------------
    # 2. Get character name
    # ------------------------------------------------------------------
    with db.cursor() as cur:
        cur.execute(
            "SELECT character_name FROM characters WHERE character_id = %s",
            (character_id,),
        )
        result = cur.fetchone()
    character_name = result["character_name"] if result else f"Character {character_id}"

    # ------------------------------------------------------------------
    # 3. Get profitable opportunities
    # ------------------------------------------------------------------
    market = MarketPriceAdapter(db)
    service = PIProfitabilityService(repo, market)
    schematic_service = PISchematicService(repo)
    opportunities = service.get_opportunities(
        tier=tier, limit=limit, min_roi=0, region_id=region_id,
    )

    # ------------------------------------------------------------------
    # 4. Enrich each opportunity
    # ------------------------------------------------------------------
    enriched_opportunities: List[dict] = []
    for opp in opportunities:
        # P0 materials needed (full chain, informational)
        p0_materials = schematic_service.get_flat_inputs(opp.type_id)

        # Enrich each P0 material with planet sources + build required set
        required_planet_types: set = set()
        for mat in p0_materials:
            mat_name = mat.get("type_name", "")
            planet_types = P0_PLANET_MAP.get(mat_name, [])
            mat["planet_sources"] = sorted(planet_types)
            required_planet_types.update(planet_types)

        # Production chain data (P0→P1 mapping + P2+ recipes + type_ids)
        chain = schematic_service.get_production_chain(opp.type_id)
        chain_data = _build_chain_data(chain) if chain else {"p0_to_p1": {}, "recipes": [], "type_ids": {}}

        # Batch-fetch market prices + SDE volumes for all chain items
        chain_type_ids = chain_data.get("type_ids", {})
        if chain_type_ids:
            tid_list = list(chain_type_ids.values())
            with db.cursor() as cur:
                cur.execute("""
                    SELECT it."typeID", it."typeName", it.volume AS volume_m3,
                           mp.lowest_sell, mp.avg_daily_volume
                    FROM "invTypes" it
                    LEFT JOIN market_prices mp ON mp.type_id = it."typeID" AND mp.region_id = %s
                    WHERE it."typeID" = ANY(%s)
                """, (region_id, tid_list))
                rows = cur.fetchall()
            chain_data["prices"] = {
                row["typeName"]: {
                    "price": float(row["lowest_sell"]) if row["lowest_sell"] else None,
                    "volume_m3": float(row["volume_m3"]) if row["volume_m3"] else None,
                    "daily_volume": int(row["avg_daily_volume"]) if row["avg_daily_volume"] else 0,
                }
                for row in rows
            }
        else:
            chain_data["prices"] = {}

        # Optimal planet combination (greedy set cover) — must be before feasibility
        needed_p0_names = [m["type_name"] for m in p0_materials]
        optimal_planets = _optimal_planet_combination(needed_p0_names)

        # Two feasibility perspectives:
        # Self-Sufficient: extract all P0 yourself (optimal extraction + factory planet)
        num_extract = len(optimal_planets)
        if opp.tier == 1:
            self_sufficient_planets = num_extract
        elif opp.tier == 2 and num_extract == 1:
            self_sufficient_planets = 1  # all-in-one
        else:
            self_sufficient_planets = num_extract + 1  # extraction + factory
        self_sufficient_feasible = self_sufficient_planets <= max_planets

        # Market Buy: buy intermediate inputs, just need factory planet(s)
        if opp.tier <= 2:
            market_buy_planets = self_sufficient_planets
        else:
            market_buy_planets = 1
        market_buy_feasible = market_buy_planets <= max_planets

        # Production layout recommendation
        layout = _production_layout(opp.tier, optimal_planets, max_planets)

        enriched_opportunities.append({
            "type_id": opp.type_id,
            "type_name": opp.type_name,
            "tier": opp.tier,
            "schematic_id": opp.schematic_id,
            "profit_per_hour": opp.profit_per_hour,
            "roi_percent": opp.roi_percent,
            "input_cost": opp.input_cost,
            "output_value": opp.output_value,
            "cycle_time": opp.cycle_time,
            "p0_materials": p0_materials,
            "required_planet_types": sorted(required_planet_types),
            "market_buy_planets": market_buy_planets,
            "market_buy_feasible": market_buy_feasible,
            "self_sufficient_planets": self_sufficient_planets,
            "self_sufficient_feasible": self_sufficient_feasible,
            "optimal_planets": optimal_planets,
            "production_layout": layout,
            "production_chain": chain_data,
        })

    # ------------------------------------------------------------------
    # 5. Get existing colonies
    # ------------------------------------------------------------------
    colonies = repo.get_colonies(character_id)

    # ------------------------------------------------------------------
    # 6. Get expiring alerts (same logic as colonies.py:get_character_summary)
    # ------------------------------------------------------------------
    expiring_list: List[dict] = []
    now = datetime.now(timezone.utc)

    for colony in colonies:
        detail = repo.get_colony_detail(colony.id)
        if not detail:
            continue

        for pin in detail.pins:
            if pin.expiry_time and pin.product_type_id:
                expiry_time = pin.expiry_time
                if expiry_time.tzinfo is None:
                    expiry_time = expiry_time.replace(tzinfo=timezone.utc)

                hours_remaining = (expiry_time - now).total_seconds() / 3600
                if 0 < hours_remaining <= 24:
                    expiring_list.append({
                        "colony_id": colony.id,
                        "planet_id": colony.planet_id,
                        "planet_type": colony.planet_type,
                        "solar_system_name": colony.solar_system_name,
                        "product_type_id": pin.product_type_id,
                        "product_name": pin.product_name,
                        "expiry_time": pin.expiry_time.isoformat(),
                        "hours_remaining": round(hours_remaining, 1),
                    })

    expiring_list.sort(key=lambda x: x["hours_remaining"])

    # ------------------------------------------------------------------
    # 7. Build response
    # ------------------------------------------------------------------
    return {
        "character_id": character_id,
        "character_name": character_name,
        "skills": {
            "interplanetary_consolidation": ic_level,
            "command_center_upgrades": ccu_level,
            "max_planets": max_planets,
            "planetology": planetology_level,
            "advanced_planetology": adv_planetology_level,
        },
        "existing_colonies": len(colonies),
        "opportunities": enriched_opportunities,
        "expiring_soon": expiring_list,
    }
