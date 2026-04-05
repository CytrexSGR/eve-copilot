"""Production comparison router — compare costs across facilities."""
import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Request, Query
from pydantic import BaseModel

from app.services.production import ProductionService
from app.services.structure_bonus import StructureBonusCalculator
from app.services.invention import InventionService
from eve_shared.constants import JITA_REGION_ID

logger = logging.getLogger(__name__)
router = APIRouter()


class CompareRequest(BaseModel):
    """Request model for facility comparison."""
    type_id: int
    facility_ids: List[int]
    me: int = 10
    te: int = 20
    runs: int = 1
    region_id: int = JITA_REGION_ID


@router.post("/compare")
def compare_facilities(
    request: Request,
    body: CompareRequest,
) -> dict:
    """Compare production costs across multiple facilities.

    Calculates material cost, time, and total cost per facility
    to identify the cheapest production location.
    """
    try:
        db = request.app.state.db
        prod = ProductionService(db, body.region_id)
        calc = StructureBonusCalculator(db)

        results = []
        for fid in body.facility_ids:
            facility = calc.get_facility(fid)
            facility_name = facility.get("name", f"Facility {fid}") if facility else f"Facility {fid}"

            bom = prod.get_bom(body.type_id, body.runs, body.me, facility_id=fid)
            if not bom:
                continue

            bom_items = prod.get_bom_with_prices(
                body.type_id, body.runs, body.me, body.region_id
            )

            # Recalculate with facility bonus
            mat_modifier = calc.get_material_modifier(fid)
            time_modifier = calc.get_time_modifier(fid)
            facility_tax = calc.get_facility_tax(fid)

            # Material cost from BOM with facility modifier
            from app.services.market_client import LocalMarketClient
            market = LocalMarketClient(db)
            prices = market.get_prices_bulk(list(bom.keys()), body.region_id)
            material_cost = sum(
                prices.get(mid, 0.0) * qty for mid, qty in bom.items()
            )

            # Base production time
            bp_id = prod.repository.get_blueprint_for_product(body.type_id)
            base_time = 0
            if bp_id:
                base_time = prod.repository.get_base_production_time(bp_id)
            te_factor = 1 - (body.te / 100)
            actual_time = int(base_time * body.runs * te_factor * time_modifier)

            # Job installation cost = EIV * system_cost_index * structure_cost_modifier
            # EIV = estimated_item_value (sum of adjusted prices of inputs)
            cost_modifier = calc.get_cost_modifier(fid)
            install_cost = material_cost * 0.01 * cost_modifier  # simplified

            total_cost = material_cost + install_cost

            results.append({
                "facility_id": fid,
                "facility_name": facility_name,
                "material_cost": round(material_cost, 2),
                "install_cost": round(install_cost, 2),
                "total_cost": round(total_cost, 2),
                "production_time_seconds": actual_time,
                "production_time_formatted": f"{actual_time // 3600}h {(actual_time % 3600) // 60}m",
                "material_modifier": round(mat_modifier, 6),
                "time_modifier": round(time_modifier, 6),
                "facility_tax": round(facility_tax, 4),
            })

        results.sort(key=lambda x: x["total_cost"])

        product_name = prod.repository.get_item_name(body.type_id) or "Unknown"

        return {
            "type_id": body.type_id,
            "product_name": product_name,
            "runs": body.runs,
            "me": body.me,
            "te": body.te,
            "facilities": results,
            "recommendation": results[0]["facility_name"] if results else None,
        }
    except Exception as e:
        logger.error(f"Facility comparison failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


