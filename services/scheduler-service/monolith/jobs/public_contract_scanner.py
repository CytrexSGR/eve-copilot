#!/usr/bin/env python3
"""
Public Contract Scanner Cron Job

Scans major trade hub regions for profitable contracts.
Run every 30 minutes: */30 * * * * /path/to/public_contract_scanner.py

Note: ESI caches public contracts for ~30 minutes.
"""

import asyncio
import logging
import time
from datetime import datetime
import httpx

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Service URL
import os
WAR_INTEL_SERVICE = os.environ.get("WAR_INTEL_SERVICE_URL", "http://war-intel-service:8000")

# Major trade hub regions
TRADE_HUB_REGIONS = [
    10000002,  # The Forge (Jita)
    10000043,  # Domain (Amarr)
    10000032,  # Sinq Laison (Dodixie)
    10000042,  # Metropolis (Hek)
    10000030,  # Heimatar (Rens)
]


async def scan_region(client: httpx.AsyncClient, region_id: int) -> dict:
    """Scan a single region for contracts."""
    try:
        response = await client.post(
            f"{WAR_INTEL_SERVICE}/api/contracts/scan/{region_id}",
            timeout=120.0  # Long timeout for full scan
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as e:
        logger.error(f"Failed to scan region {region_id}: {e}")
        return None


async def main():
    """Main scanner function."""
    start_time = time.time()
    logger.info("Starting public contract scan...")

    total_contracts = 0
    total_profitable = 0

    async with httpx.AsyncClient() as client:
        for region_id in TRADE_HUB_REGIONS:
            result = await scan_region(client, region_id)
            if result:
                logger.info(
                    f"Region {result['region_name']}: "
                    f"{result['total_contracts']} contracts "
                    f"({result['item_exchange']} item_exchange, "
                    f"{result['courier']} courier, "
                    f"{result['auction']} auction), "
                    f"{result['profitable_opportunities']} profitable"
                )
                total_contracts += result['total_contracts']
                total_profitable += result['profitable_opportunities']

            # Small delay between regions to be nice to ESI
            await asyncio.sleep(2)

    elapsed = time.time() - start_time
    logger.info(
        f"Scan complete in {elapsed:.1f}s: "
        f"{total_contracts} contracts scanned, "
        f"{total_profitable} profitable opportunities"
    )


if __name__ == "__main__":
    asyncio.run(main())
