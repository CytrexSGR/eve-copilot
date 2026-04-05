#!/usr/bin/env python3
"""
Character Sync Job

Syncs all character data for authenticated characters:
- Wallet balance
- Skills
- Assets
- Market orders
- Industry jobs
- Blueprints

Reads authenticated character IDs from tokens.json and calls
character_sync_service.sync_all() for each character.

Should run every 30 minutes via cron.
"""

import sys
import os
import json
import logging
import random
import time
from datetime import datetime

# Add parent directory to sys.path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.character_sync_service import character_sync_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

AUTH_SERVICE_URL = os.environ.get("AUTH_SERVICE_URL", "http://auth-service:8000")

STAGGER_THRESHOLD = 10  # Only stagger if more than this many characters
SYNC_WINDOW_SECONDS = 1500  # 25 min of 30 min window


def calculate_stagger_delay(index: int, total: int, window_seconds: int = SYNC_WINDOW_SECONDS) -> float:
    """Calculate stagger delay to distribute syncs across window.

    Args:
        index: Character position in the sync order (0-based).
        total: Total number of characters to sync.
        window_seconds: Window to spread syncs over.

    Returns:
        Delay in seconds before syncing this character.
    """
    if total <= STAGGER_THRESHOLD or index == 0:
        return 0
    interval = window_seconds / total
    base_delay = index * interval
    jitter = random.uniform(0, interval * 0.25)
    return min(base_delay + jitter, window_seconds)


def get_authenticated_character_ids():
    """
    Get authenticated character IDs from auth-service API.

    Falls back to reading tokens.json if auth-service is unavailable.

    Returns:
        List of character IDs (as integers)
    """
    # Primary: query auth-service API (works in Docker and locally)
    try:
        import httpx
        resp = httpx.get(f"{AUTH_SERVICE_URL}/api/auth/characters", timeout=10)
        if resp.status_code == 200:
            characters = resp.json().get("characters", [])
            character_ids = [c["character_id"] for c in characters]
            logger.info(f"Found {len(character_ids)} authenticated characters (from auth-service)")
            return character_ids
    except Exception as e:
        logger.warning(f"Auth-service unavailable ({e}), trying fallback...")

    # Fallback: read tokens.json (for local/legacy runs)
    tokens_file = os.environ.get("TOKEN_FILE", "/home/cytrex/eve_copilot/data/tokens.json")
    try:
        if not os.path.exists(tokens_file):
            logger.warning(f"Tokens file not found: {tokens_file}")
            return []

        with open(tokens_file, 'r') as f:
            tokens = json.load(f)

        character_ids = [int(char_id) for char_id in tokens.keys()]
        logger.info(f"Found {len(character_ids)} authenticated characters (from {tokens_file})")
        return character_ids

    except Exception as e:
        logger.error(f"Error reading tokens file: {e}")
        return []


def main():
    """Main sync job function"""
    logger.info("=" * 60)
    logger.info("Starting character sync job")

    # Get authenticated character IDs
    character_ids = get_authenticated_character_ids()

    if not character_ids:
        logger.warning("No authenticated characters found. Exiting.")
        return

    # Shuffle to avoid always hitting the same characters first
    random.shuffle(character_ids)
    total = len(character_ids)

    # Track results
    success_count = 0
    failure_count = 0

    # Sync each character with staggering
    for index, character_id in enumerate(character_ids):
        delay = calculate_stagger_delay(index, total)
        if delay > 0:
            logger.info(f"Stagger: char {character_id} waiting {delay:.0f}s ({index+1}/{total})")
            time.sleep(delay)

        logger.info(f"Syncing character {character_id} ({index+1}/{total})...")

        try:
            result = character_sync_service.sync_all(character_id)

            if result.get("success"):
                summary = result.get("summary", {})
                successful_syncs = summary.get("successful_syncs", 0)
                failed_syncs = summary.get("failed_syncs", 0)

                logger.info(
                    f"Character {character_id} sync completed: "
                    f"{successful_syncs}/7 successful, {failed_syncs}/7 failed"
                )
                success_count += 1
            else:
                logger.error(f"Character {character_id} sync failed")
                failure_count += 1

        except Exception as e:
            logger.error(f"Exception syncing character {character_id}: {e}")
            failure_count += 1

    # Log summary
    logger.info("-" * 60)
    logger.info(
        f"Character sync job complete: "
        f"{success_count} succeeded, {failure_count} failed "
        f"(total: {total} characters)"
    )
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
