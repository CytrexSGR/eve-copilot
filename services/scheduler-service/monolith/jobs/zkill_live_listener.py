#!/usr/bin/env python3
"""
zKillboard Live Listener - Background Worker (v2.0)

Uses official zKillboard RedisQ API for reliable killmail streaming.
https://github.com/zKillboard/RedisQ

Key Features:
- queueID persistence: zKillboard remembers position for 3 hours
- Survives restarts without missing kills
- Redis-based deduplication (no more in-memory state loss)
- Atomic battle tracking (no more 18.5x inflation)

This should run as a long-running background process (systemd service or screen).

Usage:
    python3 -m jobs.zkill_live_listener                    # Start listener
    python3 -m jobs.zkill_live_listener --verbose          # Verbose output
"""

import sys
import os
import asyncio
import argparse
import signal
from typing import List

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.zkillboard.redisq_client import ZKillRedisQClient, RedisQPackage, create_redisq_client
from services.zkillboard.live_service import ZKillboardLiveService
from services.zkillboard.state_manager import RedisStateManager
from services.war_economy.doctrine.snapshot_collector import get_collector
from config import ZKILL_QUEUE_ID, ZKILL_TTW, ZKILL_MAX_CONCURRENT_ESI

# Global service instance
live_service: ZKillboardLiveService = None
redisq_client: ZKillRedisQClient = None
state_manager: RedisStateManager = None
doctrine_collector = None  # Fleet snapshot collector for doctrine detection
verbose_mode: bool = False


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    print("\nShutdown signal received. Stopping listener...")
    if redisq_client:
        redisq_client.stop()
    if live_service:
        live_service.stop()
    sys.exit(0)


async def process_kill_batch(packages: List[RedisQPackage]):
    """
    Process a batch of killmails from RedisQ.

    Args:
        packages: List of RedisQPackage from RedisQ
    """
    global live_service, doctrine_collector, verbose_mode

    for package in packages:
        try:
            if not package.killmail_id or not package.hash:
                continue

            if verbose_mode:
                print(f"[RedisQ] Processing killmail {package.killmail_id}")

            # Create zkb_entry format expected by process_live_kill
            zkb_entry = {
                "killmail_id": package.killmail_id,
                "zkb": {
                    "hash": package.hash,
                    **package.zkb
                }
            }

            # If killmail data was pre-fetched by RedisQ client
            if package.killmail:
                zkb_entry["killmail"] = package.killmail

            # Process the kill (battle tracking, hotspots, alerts)
            await live_service.process_live_kill(zkb_entry)

            # Feed to doctrine detection (fleet snapshot collection)
            if doctrine_collector:
                if package.killmail:
                    try:
                        # Flatten killmail for snapshot collector (expects solar_system_id, killmail_time at top level)
                        flattened_kill = {
                            "killmail_id": package.killmail_id,
                            **package.killmail  # Contains solar_system_id, killmail_time, victim, attackers
                        }
                        await doctrine_collector.receive_kill(flattened_kill)
                        if verbose_mode:
                            print(f"[DOCTRINE] Kill {package.killmail_id} sent to collector")
                    except Exception as dc_error:
                        print(f"[DOCTRINE] Error collecting snapshot: {dc_error}")
                elif verbose_mode:
                    print(f"[DOCTRINE] Skip {package.killmail_id}: no killmail data")

        except Exception as e:
            print(f"[ERROR] Failed to process killmail {package.killmail_id}: {e}")


async def main():
    global live_service, redisq_client, state_manager, doctrine_collector, verbose_mode

    parser = argparse.ArgumentParser(
        description='zKillboard Live Listener - Real-time killmail processing (v2.0 RedisQ)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output'
    )
    parser.add_argument(
        '--queue-id',
        default=ZKILL_QUEUE_ID,
        help=f'RedisQ queue ID (default: {ZKILL_QUEUE_ID})'
    )
    parser.add_argument(
        '--ttw',
        type=int,
        default=ZKILL_TTW,
        help=f'Time to wait for new kills in seconds (default: {ZKILL_TTW})'
    )

    args = parser.parse_args()
    verbose_mode = args.verbose

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Initialize services
    print("=" * 70)
    print("zKillboard Live Listener v2.0 - EVE Co-Pilot")
    print("Using official RedisQ API: https://github.com/zKillboard/RedisQ")
    print("=" * 70)

    print("\nInitializing services...")

    # State Manager (Redis-based, survives restarts)
    state_manager = RedisStateManager()
    print(f"  ✓ Redis State Manager: Connected ({state_manager.health_check()})")
    print(f"    - Processed kills today: {state_manager.get_processed_count()}")

    # Live Service
    live_service = ZKillboardLiveService()
    print(f"  ✓ Live Service: Initialized")
    print(f"    - Hotspot threshold: 5 kills in 5 minutes")
    print(f"    - Battle timeout: 30 minutes")

    # Doctrine Detection - Fleet Snapshot Collector
    doctrine_collector = get_collector()
    print(f"  ✓ Doctrine Collector: Initialized")
    print(f"    - Buffer window: 5 minutes")
    print(f"    - Min fleet size: 5 pilots")

    # RedisQ Client
    redisq_client = create_redisq_client(
        queue_id=args.queue_id,
        ttw=args.ttw
    )
    print(f"  ✓ RedisQ Client: Initialized")
    print(f"    - Queue ID: {args.queue_id}")
    print(f"    - TTW: {args.ttw}s")
    print(f"    - zKillboard remembers position for 3 hours!")

    print("\n" + "=" * 70)
    print("STATUS: Starting listener...")
    print("Press Ctrl+C to stop")
    print("=" * 70 + "\n")

    try:
        # Start listening with callback
        await redisq_client.listen(
            callback=process_kill_batch,
            batch_size=1  # Process kills immediately
        )
    except KeyboardInterrupt:
        print("\nStopped by user")
    except Exception as e:
        print(f"\nError: {e}")
        raise
    finally:
        # Cleanup
        if redisq_client:
            await redisq_client.close()
        print("\nListener stopped.")

        # Print stats
        if state_manager:
            stats = state_manager.get_stats()
            print(f"\nSession Statistics:")
            print(f"  - Kills processed today: {stats.get('processed_today', 0)}")
            print(f"  - Active systems: {stats.get('active_systems', 0)}")


if __name__ == "__main__":
    asyncio.run(main())
