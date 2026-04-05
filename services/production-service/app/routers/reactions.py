"""
Reactions router - API endpoints for T2 manufacturing reactions.
Migrated from monolith to production-service.
"""
import logging
from decimal import Decimal
from typing import List, Optional, Dict

from fastapi import APIRouter, HTTPException, Request, Query
from pydantic import BaseModel, Field
from psycopg2.extras import RealDictCursor

from eve_shared.constants import JITA_REGION_ID

logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================================================
# Pydantic Models
# =============================================================================


class ReactionInput(BaseModel):
    """Single input material for a reaction."""
    input_type_id: int = Field(..., gt=0, description="EVE type ID of the input material")
    input_name: str = Field(..., description="Name of the input material")
    quantity: int = Field(..., gt=0, description="Quantity required per reaction run")


class ReactionFormula(BaseModel):
    """Complete reaction formula with inputs."""
    reaction_type_id: int = Field(..., gt=0, description="EVE type ID of the reaction formula")
    reaction_name: str = Field(..., description="Name of the reaction")
    product_type_id: int = Field(..., gt=0, description="EVE type ID of the product")
    product_name: str = Field(..., description="Name of the product")
    product_quantity: int = Field(..., gt=0, description="Quantity produced per run")
    reaction_time: int = Field(..., gt=0, description="Reaction time in seconds")
    reaction_category: Optional[str] = Field(None, description="Reaction category (composite, simple, etc.)")
    inputs: List[ReactionInput] = Field(default_factory=list, description="Input materials")

    @property
    def runs_per_hour(self) -> float:
        """Calculate how many runs can complete per hour."""
        if self.reaction_time <= 0:
            return 0.0
        return 3600 / self.reaction_time


class ReactionProfitability(BaseModel):
    """Profitability calculation for a reaction."""
    reaction_type_id: int = Field(..., gt=0, description="EVE type ID of the reaction")
    reaction_name: str = Field(..., description="Name of the reaction")
    product_name: str = Field(..., description="Name of the product")
    input_cost: Decimal = Field(..., description="Total cost of input materials per run")
    output_value: Decimal = Field(..., description="Value of output products per run")
    profit_per_run: Decimal = Field(..., description="Profit per single run")
    profit_per_hour: Decimal = Field(..., description="Profit per hour of production")
    roi_percent: float = Field(..., description="Return on Investment percentage")
    reaction_time: int = Field(..., gt=0, description="Reaction time in seconds")
    runs_per_hour: float = Field(..., gt=0, description="Number of runs possible per hour")


class ReactionSearchResult(BaseModel):
    """Search result for reactions (without full inputs for performance)."""
    reaction_type_id: int = Field(..., gt=0, description="EVE type ID of the reaction")
    reaction_name: str = Field(..., description="Name of the reaction")
    product_type_id: int = Field(..., gt=0, description="EVE type ID of the product")
    product_name: str = Field(..., description="Name of the product")
    product_quantity: int = Field(..., gt=0, description="Quantity produced per run")
    reaction_time: int = Field(..., gt=0, description="Reaction time in seconds")
    reaction_category: Optional[str] = Field(None, description="Reaction category")


class FacilityBonus(BaseModel):
    """Facility bonuses that affect reaction time and materials."""
    time_multiplier: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Time multiplier (0.75 = 25% faster)"
    )
    material_multiplier: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Material multiplier (0.98 = 2% less materials)"
    )


# =============================================================================
# Helper Functions
# =============================================================================


DEFAULT_REGION_ID = JITA_REGION_ID


def _get_prices(
    db,
    type_ids: List[int],
    region_id: int = DEFAULT_REGION_ID
) -> Dict[int, Dict[str, Optional[Decimal]]]:
    """
    Get market prices for a list of type IDs.
    """
    if not type_ids:
        return {}

    prices: Dict[int, Dict[str, Optional[Decimal]]] = {
        tid: {'sell': None, 'buy': None} for tid in type_ids
    }

    with db.cursor(cursor_factory=RealDictCursor) as cur:
        # Try moon_material_prices first (has Jita/Amarr prices)
        cur.execute("""
            SELECT type_id, jita_sell, jita_buy, amarr_sell, amarr_buy
            FROM moon_material_prices
            WHERE type_id = ANY(%s)
        """, (list(type_ids),))
        moon_prices = cur.fetchall()

        for p in moon_prices:
            tid = p['type_id']
            # Use Jita prices by default, or Amarr if region matches
            if region_id == 10000043:  # Domain (Amarr)
                prices[tid]['sell'] = Decimal(str(p['amarr_sell'])) if p['amarr_sell'] else None
                prices[tid]['buy'] = Decimal(str(p['amarr_buy'])) if p['amarr_buy'] else None
            else:
                prices[tid]['sell'] = Decimal(str(p['jita_sell'])) if p['jita_sell'] else None
                prices[tid]['buy'] = Decimal(str(p['jita_buy'])) if p['jita_buy'] else None

        # Check which type_ids are still missing prices
        missing_ids = [tid for tid in type_ids if prices[tid]['sell'] is None]

        if missing_ids:
            # Fall back to market_prices table
            cur.execute("""
                SELECT type_id, lowest_sell, highest_buy
                FROM market_prices
                WHERE type_id = ANY(%s) AND region_id = %s
            """, (missing_ids, region_id))
            market_prices = cur.fetchall()

            for p in market_prices:
                tid = p['type_id']
                if p['lowest_sell']:
                    prices[tid]['sell'] = Decimal(str(p['lowest_sell']))
                if p['highest_buy']:
                    prices[tid]['buy'] = Decimal(str(p['highest_buy']))

    return prices


def _get_all_reactions(db) -> List[ReactionFormula]:
    """Get all reaction formulas with their inputs."""
    with db.cursor(cursor_factory=RealDictCursor) as cur:
        # Fetch all reactions
        cur.execute("""
            SELECT
                reaction_type_id,
                reaction_name,
                product_type_id,
                product_name,
                product_quantity,
                reaction_time,
                reaction_category
            FROM reaction_formulas
            ORDER BY reaction_name
        """)
        reactions_data = cur.fetchall()

        if not reactions_data:
            return []

        # Fetch all inputs
        cur.execute("""
            SELECT
                reaction_type_id,
                input_type_id,
                input_name,
                quantity
            FROM reaction_formula_inputs
            ORDER BY reaction_type_id, input_name
        """)
        inputs_data = cur.fetchall()

    # Group inputs by reaction_type_id
    inputs_by_reaction: Dict[int, List[ReactionInput]] = {}
    for inp in inputs_data:
        reaction_id = inp['reaction_type_id']
        if reaction_id not in inputs_by_reaction:
            inputs_by_reaction[reaction_id] = []
        inputs_by_reaction[reaction_id].append(ReactionInput(
            input_type_id=inp['input_type_id'],
            input_name=inp['input_name'],
            quantity=inp['quantity']
        ))

    # Build reaction formulas
    reactions = []
    for r in reactions_data:
        reaction_id = r['reaction_type_id']
        reactions.append(ReactionFormula(
            reaction_type_id=reaction_id,
            reaction_name=r['reaction_name'],
            product_type_id=r['product_type_id'],
            product_name=r['product_name'],
            product_quantity=r['product_quantity'],
            reaction_time=r['reaction_time'],
            reaction_category=r['reaction_category'],
            inputs=inputs_by_reaction.get(reaction_id, [])
        ))

    return reactions


def _get_reaction(db, reaction_type_id: int) -> Optional[ReactionFormula]:
    """Get a single reaction formula by its type ID."""
    with db.cursor(cursor_factory=RealDictCursor) as cur:
        # Fetch reaction
        cur.execute("""
            SELECT
                reaction_type_id,
                reaction_name,
                product_type_id,
                product_name,
                product_quantity,
                reaction_time,
                reaction_category
            FROM reaction_formulas
            WHERE reaction_type_id = %s
        """, (reaction_type_id,))
        reaction_data = cur.fetchone()

        if not reaction_data:
            return None

        # Fetch inputs
        cur.execute("""
            SELECT
                input_type_id,
                input_name,
                quantity
            FROM reaction_formula_inputs
            WHERE reaction_type_id = %s
            ORDER BY input_name
        """, (reaction_type_id,))
        inputs_data = cur.fetchall()

    inputs = [
        ReactionInput(
            input_type_id=inp['input_type_id'],
            input_name=inp['input_name'],
            quantity=inp['quantity']
        )
        for inp in inputs_data
    ]

    return ReactionFormula(
        reaction_type_id=reaction_data['reaction_type_id'],
        reaction_name=reaction_data['reaction_name'],
        product_type_id=reaction_data['product_type_id'],
        product_name=reaction_data['product_name'],
        product_quantity=reaction_data['product_quantity'],
        reaction_time=reaction_data['reaction_time'],
        reaction_category=reaction_data['reaction_category'],
        inputs=inputs
    )


def _calculate_profitability(
    db,
    reaction: ReactionFormula,
    facility_bonus: Optional[FacilityBonus] = None,
    region_id: int = DEFAULT_REGION_ID
) -> ReactionProfitability:
    """Calculate profitability for a reaction."""
    # Collect all type IDs we need prices for
    input_type_ids = [inp.input_type_id for inp in reaction.inputs]
    all_type_ids = input_type_ids + [reaction.product_type_id]

    # Get prices
    prices = _get_prices(db, all_type_ids, region_id)

    # Apply facility bonus if provided
    material_mult = facility_bonus.material_multiplier if facility_bonus else 1.0
    time_mult = facility_bonus.time_multiplier if facility_bonus else 1.0

    # Calculate input cost (use sell price for inputs - we buy from sell orders)
    input_cost = Decimal('0')
    for inp in reaction.inputs:
        price_data = prices.get(inp.input_type_id, {})
        price = price_data.get('sell') or price_data.get('buy') or Decimal('0')
        adjusted_qty = int(inp.quantity * material_mult)
        input_cost += price * adjusted_qty

    # Calculate output value (use sell price for output)
    output_price_data = prices.get(reaction.product_type_id, {})
    output_price = output_price_data.get('sell') or output_price_data.get('buy') or Decimal('0')
    output_value = output_price * reaction.product_quantity

    # Calculate profits
    profit_per_run = output_value - input_cost

    # Calculate time-based metrics
    adjusted_time = int(reaction.reaction_time * time_mult)
    runs_per_hour = 3600 / adjusted_time if adjusted_time > 0 else 0

    profit_per_hour = profit_per_run * Decimal(str(runs_per_hour))

    # Calculate ROI
    if input_cost > 0:
        roi_percent = float((profit_per_run / input_cost) * 100)
    else:
        roi_percent = 0.0 if profit_per_run <= 0 else float('inf')

    return ReactionProfitability(
        reaction_type_id=reaction.reaction_type_id,
        reaction_name=reaction.reaction_name,
        product_name=reaction.product_name,
        input_cost=input_cost,
        output_value=output_value,
        profit_per_run=profit_per_run,
        profit_per_hour=profit_per_hour,
        roi_percent=round(roi_percent, 2),
        reaction_time=adjusted_time,
        runs_per_hour=round(runs_per_hour, 2)
    )


# =============================================================================
# API Endpoints
# =============================================================================


@router.get("", response_model=List[ReactionFormula])
def get_all_reactions(request: Request) -> List[ReactionFormula]:
    """
    Get all reaction formulas.

    Returns a list of all reaction formulas with their input materials.
    """
    try:
        db = request.app.state.db
        with db.cursor() as cur:
            # Need to use the db object for our helper functions
            pass
        return _get_all_reactions(db)
    except Exception as e:
        logger.error(f"Failed to get reactions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search", response_model=List[ReactionSearchResult])
def search_reactions(
    request: Request,
    q: str = Query(..., min_length=2, description="Search term")
) -> List[ReactionSearchResult]:
    """
    Search reactions by name.

    Searches both reaction names and product names.
    Returns up to 50 results.
    """
    try:
        db = request.app.state.db
        search_pattern = f"%{q}%"

        with db.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    reaction_type_id,
                    reaction_name,
                    product_type_id,
                    product_name,
                    product_quantity,
                    reaction_time,
                    reaction_category
                FROM reaction_formulas
                WHERE reaction_name ILIKE %s
                   OR product_name ILIKE %s
                ORDER BY reaction_name
                LIMIT 50
            """, (search_pattern, search_pattern))
            results = cur.fetchall()

        return [
            ReactionSearchResult(
                reaction_type_id=r['reaction_type_id'],
                reaction_name=r['reaction_name'],
                product_type_id=r['product_type_id'],
                product_name=r['product_name'],
                product_quantity=r['product_quantity'],
                reaction_time=r['reaction_time'],
                reaction_category=r['reaction_category']
            )
            for r in results
        ]
    except Exception as e:
        logger.error(f"Failed to search reactions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/profitable", response_model=List[ReactionProfitability])
def get_profitable_reactions(
    request: Request,
    min_roi: float = Query(default=0, ge=0, description="Minimum ROI percentage"),
    limit: int = Query(default=50, ge=1, le=200, description="Maximum results"),
    region_id: int = Query(
        default=JITA_REGION_ID,
        description="Region ID for market prices (default: Jita/The Forge)"
    ),
    time_bonus: float = Query(
        default=1.0,
        ge=0.5,
        le=1.0,
        description="Facility time multiplier (e.g., 0.75 for 25% faster)"
    ),
    material_bonus: float = Query(
        default=1.0,
        ge=0.5,
        le=1.0,
        description="Facility material multiplier (e.g., 0.98 for 2% savings)"
    )
) -> List[ReactionProfitability]:
    """
    Find profitable reactions.

    Returns reactions sorted by profit per hour (descending).
    Supports facility bonuses for refineries with reaction rigs.

    **Common facility bonuses:**
    - T1 Reaction Rig: time_bonus=0.8 (20% faster)
    - T2 Reaction Rig: time_bonus=0.76 (24% faster)
    - Tatara with T2 Rig: time_bonus=0.75, material_bonus=0.98
    """
    try:
        db = request.app.state.db

        facility_bonus = None
        if time_bonus != 1.0 or material_bonus != 1.0:
            facility_bonus = FacilityBonus(
                time_multiplier=time_bonus,
                material_multiplier=material_bonus
            )

        all_reactions = _get_all_reactions(db)

        profitable = []
        for reaction in all_reactions:
            try:
                profit = _calculate_profitability(
                    db,
                    reaction,
                    facility_bonus=facility_bonus,
                    region_id=region_id
                )

                # Filter by ROI
                if profit.roi_percent >= min_roi:
                    profitable.append(profit)

            except Exception:
                # Skip reactions with calculation errors
                continue

        # Sort by profit per hour descending
        profitable.sort(key=lambda p: float(p.profit_per_hour), reverse=True)

        return profitable[:limit]
    except Exception as e:
        logger.error(f"Failed to get profitable reactions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{reaction_type_id}", response_model=ReactionFormula)
def get_reaction(
    request: Request,
    reaction_type_id: int
) -> ReactionFormula:
    """
    Get a specific reaction formula by ID.

    Returns the reaction with all its input materials.
    """
    try:
        db = request.app.state.db
        reaction = _get_reaction(db, reaction_type_id)

        if not reaction:
            raise HTTPException(
                status_code=404,
                detail=f"Reaction {reaction_type_id} not found"
            )

        return reaction
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get reaction {reaction_type_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{reaction_type_id}/profit", response_model=ReactionProfitability)
def calculate_reaction_profitability(
    request: Request,
    reaction_type_id: int,
    region_id: int = Query(
        default=JITA_REGION_ID,
        description="Region ID for market prices (default: Jita/The Forge)"
    ),
    time_bonus: float = Query(
        default=1.0,
        ge=0.5,
        le=1.0,
        description="Facility time multiplier"
    ),
    material_bonus: float = Query(
        default=1.0,
        ge=0.5,
        le=1.0,
        description="Facility material multiplier"
    )
) -> ReactionProfitability:
    """
    Calculate profitability for a specific reaction.

    Returns detailed profit analysis including:
    - Input cost (materials)
    - Output value (product)
    - Profit per run and per hour
    - ROI percentage

    **Facility bonuses:**
    - time_bonus: Multiplier for reaction time (0.75 = 25% faster)
    - material_bonus: Multiplier for material usage (0.98 = 2% savings)
    """
    try:
        db = request.app.state.db
        reaction = _get_reaction(db, reaction_type_id)

        if not reaction:
            raise HTTPException(
                status_code=404,
                detail=f"Reaction {reaction_type_id} not found"
            )

        facility_bonus = None
        if time_bonus != 1.0 or material_bonus != 1.0:
            facility_bonus = FacilityBonus(
                time_multiplier=time_bonus,
                material_multiplier=material_bonus
            )

        return _calculate_profitability(
            db,
            reaction,
            facility_bonus=facility_bonus,
            region_id=region_id
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to calculate profitability for {reaction_type_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
