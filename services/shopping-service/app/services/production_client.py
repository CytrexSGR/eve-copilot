"""Production service client for material calculations."""
import logging
from typing import Optional, List, Dict

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class ProductionClient:
    """Client for production-service material calculations."""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or settings.production_service_url
        self.timeout = 30.0

    async def get_materials(
        self,
        type_id: int,
        runs: int = 1,
        me_level: int = 0
    ) -> Optional[dict]:
        """Get materials list for production."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/api/chains/{type_id}/materials",
                    params={"me": me_level, "runs": runs}
                )
                if response.status_code == 200:
                    return response.json()
                return None
        except Exception as e:
            logger.warning(f"Production service unavailable for {type_id}: {e}")
            return None

    async def get_chain(
        self,
        type_id: int,
        quantity: int = 1,
        format: str = "tree"
    ) -> Optional[dict]:
        """Get full production chain."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/api/chains/{type_id}",
                    params={"quantity": quantity, "format": format}
                )
                if response.status_code == 200:
                    return response.json()
                return None
        except Exception as e:
            logger.warning(f"Production service chain unavailable: {e}")
            return None

    async def get_economics(
        self,
        type_id: int,
        region_id: int = 10000002,
        me: int = 0,
        te: int = 0
    ) -> Optional[dict]:
        """Get production economics."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/api/economics/{type_id}",
                    params={"region_id": region_id, "me": me, "te": te}
                )
                if response.status_code == 200:
                    return response.json()
                return None
        except Exception as e:
            logger.warning(f"Production economics unavailable: {e}")
            return None

    async def simulate_build(
        self,
        type_id: int,
        runs: int = 1,
        me: int = 0,
        te: int = 0,
        region_id: int = 10000002
    ) -> Optional[dict]:
        """Simulate a production build."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/api/simulate/{type_id}",
                    params={
                        "runs": runs,
                        "me": me,
                        "te": te,
                        "region_id": region_id
                    }
                )
                if response.status_code == 200:
                    return response.json()
                return None
        except Exception as e:
            logger.warning(f"Production simulation unavailable: {e}")
            return None


class LocalProductionClient(ProductionClient):
    """Production client with database fallback for materials."""

    def __init__(self, db):
        super().__init__()
        self.db = db

    async def get_materials(
        self,
        type_id: int,
        runs: int = 1,
        me_level: int = 0
    ) -> Optional[dict]:
        """Get materials, falling back to database."""
        # Try service first
        result = await super().get_materials(type_id, runs, me_level)
        if result:
            return result

        # Fallback to database
        return await self._get_materials_from_db(type_id, runs, me_level)

    async def _get_materials_from_db(
        self,
        type_id: int,
        runs: int,
        me_level: int
    ) -> Optional[dict]:
        """Get materials directly from database."""
        # Get blueprint
        bp_query = """
            SELECT ib."typeID" as blueprint_id, t."typeName" as product_name,
                   ib."productionTime"
            FROM "industryBlueprints" ib
            JOIN "invTypes" t ON ib."productTypeID" = t."typeID"
            WHERE ib."productTypeID" = $1
        """
        bp_row = await self.db.fetchrow(bp_query, type_id)
        if not bp_row:
            return None

        # Get materials
        mat_query = """
            SELECT iam."materialTypeID" as type_id, t."typeName" as type_name,
                   iam.quantity as quantity_base
            FROM "industryActivityMaterials" iam
            JOIN "invTypes" t ON iam."materialTypeID" = t."typeID"
            WHERE iam."typeID" = $1 AND iam."activityID" = 1
        """
        mat_rows = await self.db.fetch(mat_query, bp_row["blueprint_id"])

        # Calculate ME adjustment
        me_factor = 1.0 - (me_level * 0.01)
        materials = []

        for row in mat_rows:
            base_qty = row["quantity_base"] * runs
            adjusted_qty = max(runs, int(base_qty * me_factor))
            materials.append({
                "type_id": row["type_id"],
                "type_name": row["type_name"],
                "quantity_base": base_qty,
                "quantity_adjusted": adjusted_qty
            })

        return {
            "type_id": type_id,
            "type_name": bp_row["product_name"],
            "runs": runs,
            "me_level": me_level,
            "materials": materials
        }
