"""Shopping wizard router."""
import logging

from fastapi import APIRouter, HTTPException, Request
from eve_shared.utils.error_handling import handle_endpoint_errors

from app.models import (
    WizardMaterialsRequest, WizardMaterialsResponse,
    WizardRegionRequest, WizardRegionResponse
)
from app.services import ShoppingService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/calculate-materials")
@handle_endpoint_errors()
def wizard_calculate_materials(
    request: Request,
    data: WizardMaterialsRequest
) -> WizardMaterialsResponse:
    """Wizard: Calculate materials for production."""
    try:
        db = request.app.state.db
        service = ShoppingService(db)
        return service.wizard_calculate_materials(data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Wizard materials calculation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/compare-regions")
@handle_endpoint_errors()
def wizard_compare_regions(
    request: Request,
    data: WizardRegionRequest
) -> WizardRegionResponse:
    """Wizard: Compare prices across regions."""
    try:
        if len(data.type_ids) != len(data.quantities):
            raise HTTPException(
                status_code=400,
                detail="type_ids and quantities must have same length"
            )

        db = request.app.state.db
        service = ShoppingService(db)
        return service.wizard_compare_regions(data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Wizard region comparison failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
