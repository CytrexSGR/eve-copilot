#!/usr/bin/env python3
# jobs/portfolio_snapshotter.py
"""
Daily portfolio snapshot job.
Creates portfolio snapshots for all authenticated characters.

Runs: 0 0 * * * (midnight UTC)
"""

import sys
import os
import logging
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Create portfolio snapshots for all characters."""
    import requests

    logger.info("Starting portfolio snapshot job")

    try:
        api_url = os.environ.get("API_GATEWAY_URL", "http://api-gateway:8000")
        response = requests.post(
            f"{api_url}/api/portfolio/snapshot",
            timeout=120
        )

        if response.status_code == 200:
            result = response.json()
            logger.info(f"Created {result['created']} snapshots")
            if result.get('errors'):
                for err in result['errors']:
                    logger.error(f"Error for {err['character_id']}: {err['error']}")
        else:
            logger.error(f"API error: {response.status_code} - {response.text}")

    except Exception as e:
        logger.error(f"Job failed: {e}")
        sys.exit(1)

    logger.info("Portfolio snapshot job complete")


if __name__ == "__main__":
    main()
