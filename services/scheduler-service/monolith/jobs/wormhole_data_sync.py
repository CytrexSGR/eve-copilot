"""Sync wormhole static data from Pathfinder."""
import asyncio
import logging
import sys

sys.path.insert(0, '/home/cytrex/eve_copilot/services/wormhole-service')
from app.services.importer import WormholeImporter
from app.services.repository import WormholeRepository

logger = logging.getLogger(__name__)


async def sync_wormhole_data() -> dict:
    """Sync Pathfinder CSV data with checksum-based change detection."""
    importer = WormholeImporter()
    repo = WormholeRepository()
    result = {'statics': 0, 'wormholes': 0, 'skipped': []}

    # Sync statics
    try:
        last = repo.get_last_import('pathfinder', 'statics')
        checksum, data = await importer.fetch_statics()

        if checksum is None:
            result['statics_error'] = 'Failed to fetch statics'
        elif last and last['checksum'] == checksum:
            result['skipped'].append('statics')
        else:
            count = repo.upsert_statics(data)
            repo.record_import('pathfinder', 'statics', count, checksum)
            result['statics'] = count
            logger.info(f"Imported {count} system statics")
    except Exception as e:
        logger.error(f"Statics sync failed: {e}")
        result['statics_error'] = str(e)

    # Sync wormhole extended
    try:
        last = repo.get_last_import('pathfinder', 'wormholes')
        checksum, data = await importer.fetch_wormholes()

        if checksum is None:
            result['wormholes_error'] = 'Failed to fetch wormholes'
        elif last and last['checksum'] == checksum:
            result['skipped'].append('wormholes')
        else:
            count = repo.upsert_wormhole_extended(data)
            repo.record_import('pathfinder', 'wormholes', count, checksum)
            result['wormholes'] = count
            logger.info(f"Imported {count} wormhole types")
    except Exception as e:
        logger.error(f"Wormholes sync failed: {e}")
        result['wormholes_error'] = str(e)

    return result


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    print(asyncio.run(sync_wormhole_data()))
