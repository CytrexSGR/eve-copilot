"""
Public Contracts Router - Scanning for profitable opportunities

Provides endpoints for:
- Scanning public contracts by region
- Finding profitable item_exchange contracts
- Analyzing courier contracts
- Contract item details
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List
import httpx
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel

from app.database import db_cursor
from eve_shared.utils.error_handling import handle_endpoint_errors

logger = logging.getLogger(__name__)

router = APIRouter()

# ESI endpoints
ESI_PUBLIC_CONTRACTS = "https://esi.evetech.net/latest/contracts/public/{region_id}/"
ESI_CONTRACT_ITEMS = "https://esi.evetech.net/latest/contracts/public/items/{contract_id}/"
ESI_MARKET_PRICES = "https://esi.evetech.net/latest/markets/prices/"

# Major trade hub regions
TRADE_HUB_REGIONS = {
    10000002: "The Forge",       # Jita
    10000043: "Domain",          # Amarr
    10000032: "Sinq Laison",     # Dodixie
    10000042: "Metropolis",      # Hek
    10000030: "Heimatar",        # Rens
}


# ==============================================================================
# Models
# ==============================================================================

class Contract(BaseModel):
    """Public contract data."""
    contract_id: int
    region_id: int
    region_name: Optional[str] = None
    type: str
    title: Optional[str] = None
    price: Optional[float] = None
    reward: Optional[float] = None
    collateral: Optional[float] = None
    buyout: Optional[float] = None
    volume: Optional[float] = None
    estimated_value: Optional[float] = None
    profit_potential: Optional[float] = None
    profit_margin: Optional[float] = None
    date_expired: Optional[datetime] = None
    hours_remaining: Optional[float] = None


class ContractItem(BaseModel):
    """Item in a contract."""
    type_id: int
    type_name: Optional[str] = None
    quantity: int
    is_included: bool
    unit_price: Optional[float] = None
    total_price: Optional[float] = None


class ContractDetailResponse(BaseModel):
    """Full contract details with items."""
    contract: Contract
    items: List[ContractItem]


class ContractsResponse(BaseModel):
    """Response for contract list."""
    contracts: List[Contract]
    count: int
    region_id: Optional[int] = None


class ScanResult(BaseModel):
    """Result of contract scan."""
    region_id: int
    region_name: str
    total_contracts: int
    item_exchange: int
    courier: int
    auction: int
    profitable_opportunities: int
    scan_time: datetime


class CourierContract(BaseModel):
    """Courier contract with analysis."""
    contract_id: int
    region_id: int
    region_name: Optional[str] = None
    title: Optional[str] = None
    reward: float
    collateral: float
    volume: float
    days_to_complete: int
    isk_per_m3: float
    reward_collateral_pct: float
    hours_remaining: Optional[float] = None
    start_location_name: Optional[str] = None
    end_location_name: Optional[str] = None


class CourierContractsResponse(BaseModel):
    """Response for courier contracts."""
    contracts: List[CourierContract]
    count: int


# ==============================================================================
# ESI Fetch
# ==============================================================================

async def fetch_public_contracts(region_id: int) -> List[dict]:
    """Fetch all public contracts from a region (handles pagination)."""
    all_contracts = []
    page = 1

    async with httpx.AsyncClient() as client:
        while True:
            response = await client.get(
                ESI_PUBLIC_CONTRACTS.format(region_id=region_id),
                params={"page": page},
                headers={"User-Agent": "EVE-Copilot/1.0"},
                timeout=30.0
            )
            response.raise_for_status()

            contracts = response.json()
            if not contracts:
                break

            all_contracts.extend(contracts)

            # Check for more pages
            total_pages = int(response.headers.get("X-Pages", 1))
            if page >= total_pages:
                break
            page += 1

    return all_contracts


async def fetch_contract_items(contract_id: int) -> List[dict]:
    """Fetch items for a specific contract."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            ESI_CONTRACT_ITEMS.format(contract_id=contract_id),
            headers={"User-Agent": "EVE-Copilot/1.0"},
            timeout=30.0
        )
        if response.status_code == 404:
            return []
        response.raise_for_status()
        return response.json()


async def fetch_market_prices() -> dict:
    """Fetch current market prices from ESI."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            ESI_MARKET_PRICES,
            headers={"User-Agent": "EVE-Copilot/1.0"},
            timeout=30.0
        )
        response.raise_for_status()
        prices = {}
        for item in response.json():
            prices[item["type_id"]] = {
                "adjusted_price": item.get("adjusted_price", 0),
                "average_price": item.get("average_price", 0)
            }
        return prices


# ==============================================================================
# Endpoints
# ==============================================================================

@router.post("/scan/{region_id}", response_model=ScanResult)
@handle_endpoint_errors()
async def scan_region_contracts(region_id: int, background_tasks: BackgroundTasks):
    """
    Scan a region for public contracts and store in database.

    This fetches all public contracts and calculates profit opportunities
    for item_exchange contracts.
    """
    region_name = TRADE_HUB_REGIONS.get(region_id, f"Region {region_id}")

    try:
        # Fetch contracts from ESI
        contracts = await fetch_public_contracts(region_id)

        # Fetch market prices for value estimation
        market_prices = await fetch_market_prices()

        # Counters
        item_exchange = 0
        courier = 0
        auction = 0
        profitable = 0

        with db_cursor() as cur:
            # Clear old contracts for this region
            cur.execute(
                "DELETE FROM public_contracts WHERE region_id = %s",
                (region_id,)
            )

            for contract in contracts:
                contract_type = contract.get("type", "unknown")
                if contract_type == "item_exchange":
                    item_exchange += 1
                elif contract_type == "courier":
                    courier += 1
                elif contract_type == "auction":
                    auction += 1

                # Insert contract
                cur.execute("""
                    INSERT INTO public_contracts (
                        contract_id, region_id, type, issuer_id, issuer_corporation_id,
                        assignee_id, title, start_location_id, end_location_id,
                        price, reward, collateral, buyout, volume,
                        date_issued, date_expired, days_to_complete, for_corporation,
                        last_updated
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW()
                    )
                    ON CONFLICT (contract_id) DO UPDATE SET
                        price = EXCLUDED.price,
                        reward = EXCLUDED.reward,
                        collateral = EXCLUDED.collateral,
                        volume = EXCLUDED.volume,
                        date_expired = EXCLUDED.date_expired,
                        last_updated = NOW()
                """, (
                    contract["contract_id"],
                    region_id,
                    contract_type,
                    contract.get("issuer_id"),
                    contract.get("issuer_corporation_id"),
                    contract.get("assignee_id"),
                    contract.get("title"),
                    contract.get("start_location_id"),
                    contract.get("end_location_id"),
                    contract.get("price"),
                    contract.get("reward"),
                    contract.get("collateral"),
                    contract.get("buyout"),
                    contract.get("volume"),
                    contract.get("date_issued"),
                    contract.get("date_expired"),
                    contract.get("days_to_complete"),
                    contract.get("for_corporation", False),
                ))

            # Schedule background task to analyze item_exchange contracts
            background_tasks.add_task(
                analyze_item_exchange_contracts,
                region_id,
                market_prices
            )

            # Count profitable (after analysis runs, this will be updated)
            cur.execute("""
                SELECT COUNT(*) FROM public_contracts
                WHERE region_id = %s AND profit_potential > 0
            """, (region_id,))
            profitable = cur.fetchone()['count']

        return ScanResult(
            region_id=region_id,
            region_name=region_name,
            total_contracts=len(contracts),
            item_exchange=item_exchange,
            courier=courier,
            auction=auction,
            profitable_opportunities=profitable,
            scan_time=datetime.now(timezone.utc)
        )

    except httpx.HTTPError as e:
        logger.error(f"ESI request failed: {e}")
        raise HTTPException(status_code=502, detail=f"ESI request failed: {e}")


async def analyze_item_exchange_contracts(region_id: int, market_prices: dict):
    """Background task to analyze item_exchange contracts for profit."""
    try:
        with db_cursor() as cur:
            # Get all item_exchange contracts
            cur.execute("""
                SELECT contract_id, price
                FROM public_contracts
                WHERE region_id = %s AND type = 'item_exchange'
            """, (region_id,))
            contracts = cur.fetchall()

            for contract in contracts:
                contract_id = contract['contract_id']
                price = contract['price'] or 0

                try:
                    # Fetch items for this contract
                    items = await fetch_contract_items(contract_id)

                    if not items:
                        continue

                    # Calculate estimated value
                    estimated_value = 0
                    for item in items:
                        if item.get("is_included", True):  # Items being offered
                            type_id = item["type_id"]
                            quantity = item.get("quantity", 1)

                            # Get price from market data
                            price_data = market_prices.get(type_id, {})
                            unit_price = price_data.get("average_price") or price_data.get("adjusted_price", 0)
                            estimated_value += unit_price * quantity

                            # Store item
                            cur.execute("""
                                INSERT INTO public_contract_items (
                                    contract_id, type_id, quantity, is_included,
                                    is_blueprint_copy, material_efficiency, time_efficiency, runs,
                                    unit_price, total_price
                                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (contract_id, type_id, is_included) DO UPDATE SET
                                    quantity = EXCLUDED.quantity,
                                    unit_price = EXCLUDED.unit_price,
                                    total_price = EXCLUDED.total_price
                            """, (
                                contract_id,
                                type_id,
                                quantity,
                                item.get("is_included", True),
                                item.get("is_blueprint_copy", False),
                                item.get("material_efficiency"),
                                item.get("time_efficiency"),
                                item.get("runs"),
                                unit_price,
                                unit_price * quantity
                            ))

                    # Calculate profit
                    if estimated_value > 0 and price > 0:
                        profit_potential = estimated_value - price
                        profit_margin = (profit_potential / price) * 100

                        cur.execute("""
                            UPDATE public_contracts
                            SET estimated_value = %s,
                                profit_potential = %s,
                                profit_margin = %s
                            WHERE contract_id = %s
                        """, (estimated_value, profit_potential, profit_margin, contract_id))

                except Exception as e:
                    logger.warning(f"Failed to analyze contract {contract_id}: {e}")
                    continue

        logger.info(f"Analyzed {len(contracts)} item_exchange contracts for region {region_id}")

    except Exception as e:
        logger.error(f"Failed to analyze contracts: {e}")


@router.get("/profitable", response_model=ContractsResponse)
def get_profitable_contracts(
    region_id: Optional[int] = Query(None, description="Filter by region"),
    min_profit: float = Query(1000000, description="Minimum profit in ISK"),
    limit: int = Query(100, description="Maximum results")
):
    """Get profitable item_exchange contracts."""
    with db_cursor() as cur:
        query = """
            SELECT contract_id, region_id, region_name, type, title,
                   price, estimated_value, profit_potential, profit_margin,
                   volume, date_expired, hours_remaining
            FROM v_profitable_contracts
            WHERE profit_potential >= %s
        """
        params = [min_profit]

        if region_id:
            query += " AND region_id = %s"
            params.append(region_id)

        query += " LIMIT %s"
        params.append(limit)

        cur.execute(query, params)
        rows = cur.fetchall()

        contracts = [
            Contract(
                contract_id=row['contract_id'],
                region_id=row['region_id'],
                region_name=row['region_name'],
                type=row['type'],
                title=row['title'],
                price=float(row['price']) if row['price'] else None,
                estimated_value=float(row['estimated_value']) if row['estimated_value'] else None,
                profit_potential=float(row['profit_potential']) if row['profit_potential'] else None,
                profit_margin=float(row['profit_margin']) if row['profit_margin'] else None,
                volume=row['volume'],
                date_expired=row['date_expired'],
                hours_remaining=float(row['hours_remaining']) if row['hours_remaining'] else None
            )
            for row in rows
        ]

    return ContractsResponse(contracts=contracts, count=len(contracts), region_id=region_id)


@router.get("/courier", response_model=CourierContractsResponse)
def get_courier_contracts(
    region_id: Optional[int] = Query(None, description="Filter by region"),
    min_isk_per_m3: float = Query(500, description="Minimum ISK/m3"),
    max_collateral: float = Query(None, description="Maximum collateral"),
    limit: int = Query(100, description="Maximum results")
):
    """Get courier contracts sorted by ISK/m3."""
    with db_cursor() as cur:
        query = """
            SELECT contract_id, region_id, region_name, title,
                   reward, collateral, volume, days_to_complete,
                   isk_per_m3, reward_collateral_pct, hours_remaining
            FROM v_courier_contracts
            WHERE isk_per_m3 >= %s
        """
        params = [min_isk_per_m3]

        if region_id:
            query += " AND region_id = %s"
            params.append(region_id)

        if max_collateral:
            query += " AND collateral <= %s"
            params.append(max_collateral)

        query += " LIMIT %s"
        params.append(limit)

        cur.execute(query, params)
        rows = cur.fetchall()

        contracts = [
            CourierContract(
                contract_id=row['contract_id'],
                region_id=row['region_id'],
                region_name=row['region_name'],
                title=row['title'],
                reward=float(row['reward']) if row['reward'] else 0,
                collateral=float(row['collateral']) if row['collateral'] else 0,
                volume=float(row['volume']) if row['volume'] else 0,
                days_to_complete=row['days_to_complete'] or 0,
                isk_per_m3=float(row['isk_per_m3']) if row['isk_per_m3'] else 0,
                reward_collateral_pct=float(row['reward_collateral_pct']) if row['reward_collateral_pct'] else 0,
                hours_remaining=float(row['hours_remaining']) if row['hours_remaining'] else None
            )
            for row in rows
        ]

    return CourierContractsResponse(contracts=contracts, count=len(contracts))


@router.get("/{contract_id}", response_model=ContractDetailResponse)
def get_contract_detail(contract_id: int):
    """Get full contract details including items."""
    with db_cursor() as cur:
        # Get contract
        cur.execute("""
            SELECT pc.contract_id, pc.region_id, pc.type, pc.title,
                   pc.price, pc.reward, pc.collateral, pc.volume,
                   pc.estimated_value, pc.profit_potential, pc.profit_margin,
                   pc.date_expired,
                   rm.region_name
            FROM public_contracts pc
            LEFT JOIN region_name_cache rm ON pc.region_id = rm.region_id
            WHERE pc.contract_id = %s
        """, (contract_id,))
        row = cur.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Contract not found")

        contract = Contract(
            contract_id=row['contract_id'],
            region_id=row['region_id'],
            region_name=row['region_name'],
            type=row['type'],
            title=row['title'],
            price=float(row['price']) if row['price'] else None,
            reward=float(row['reward']) if row['reward'] else None,
            collateral=float(row['collateral']) if row['collateral'] else None,
            volume=row['volume'],
            estimated_value=float(row['estimated_value']) if row['estimated_value'] else None,
            profit_potential=float(row['profit_potential']) if row['profit_potential'] else None,
            profit_margin=float(row['profit_margin']) if row['profit_margin'] else None,
            date_expired=row['date_expired']
        )

        # Get items
        cur.execute("""
            SELECT pci.type_id, pci.quantity, pci.is_included,
                   pci.unit_price, pci.total_price,
                   it.type_name
            FROM public_contract_items pci
            LEFT JOIN inv_types it ON pci.type_id = it.type_id
            WHERE pci.contract_id = %s
        """, (contract_id,))
        item_rows = cur.fetchall()

        items = [
            ContractItem(
                type_id=item['type_id'],
                type_name=item['type_name'],
                quantity=item['quantity'],
                is_included=item['is_included'],
                unit_price=float(item['unit_price']) if item['unit_price'] else None,
                total_price=float(item['total_price']) if item['total_price'] else None
            )
            for item in item_rows
        ]

    return ContractDetailResponse(contract=contract, items=items)


@router.get("/regions/tradehubs")
def get_trade_hub_regions():
    """Get list of major trade hub regions for scanning."""
    return {
        "regions": [
            {"region_id": rid, "region_name": name}
            for rid, name in TRADE_HUB_REGIONS.items()
        ]
    }
