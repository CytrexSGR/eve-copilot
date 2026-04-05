"""
Listener Module for zkillboard Streams.

Provides RedisQ and WebSocket listener implementations for real-time killmail processing.
"""

import asyncio
import json
from typing import TYPE_CHECKING

import aiohttp

from .models import (
    ZKILL_REDISQ_URL,
    ZKILL_QUEUE_ID,
    ZKILL_WEBSOCKET_URL,
    ZKILL_USER_AGENT,
    ZKILL_POLL_INTERVAL,
    ZKILL_WS_RECONNECT_DELAY,
    HOTSPOT_THRESHOLD_KILLS,
    HOTSPOT_WINDOW_SECONDS,
)

# Avoid circular import
if TYPE_CHECKING:
    import websockets


class ListenerMixin:
    """Mixin providing listener methods for ZKillboardLiveService."""

    async def finalize_hotspots_loop(self, verbose: bool = False):
        """
        Background task that periodically checks for inactive battles/hotspots.

        Runs every 5 minutes.
        """
        if verbose:
            print("Starting hotspot finalizer background task...")

        while self.running:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                if verbose:
                    print("[Finalizer] Checking for inactive battles...")

                # Finalize inactive battles (30 minutes without activity)
                self.finalize_inactive_battles()

                # Finalize dormant alliance wars
                self.finalize_dormant_wars()

            except Exception as e:
                print(f"Error in finalizer loop: {e}")

    async def listen_zkillboard(self, verbose: bool = False):
        """
        Main loop: continuously poll zkillboard API and process new kills.

        This is a fallback method - prefer listen_redisq() for production.
        """
        self.running = True

        if verbose:
            print("Starting zKillboard API poller...")
            print(f"Poll interval: {ZKILL_POLL_INTERVAL}s")
            print(f"Hotspot detection: {HOTSPOT_THRESHOLD_KILLS} kills in {HOTSPOT_WINDOW_SECONDS}s")

        kill_count = 0
        poll_count = 0

        # Start background finalizer task
        finalizer_task = asyncio.create_task(self.finalize_hotspots_loop(verbose))

        try:
            while self.running:
                # Fetch recent kills
                kills = await self.fetch_recent_kills()
                poll_count += 1

                for zkb_entry in kills:
                    await self.process_live_kill(zkb_entry)
                    kill_count += 1

                if verbose and poll_count % 100 == 0:
                    print(f"[Poller] Poll #{poll_count}: processed {kill_count} kills total")

                # Wait before next poll
                await asyncio.sleep(ZKILL_POLL_INTERVAL)

        finally:
            if verbose:
                print(f"\n[Poller] Stopped. Processed {kill_count} kills in {poll_count} polls.")
            finalizer_task.cancel()
            if self.session and not self.session.closed:
                await self.session.close()

    def stop(self):
        """Stop the listener"""
        self.running = False

    async def listen_websocket(self, verbose: bool = False):
        """
        Main loop: WebSocket connection to zkillboard for real-time kills.

        NOTE: zkillboard WebSocket is currently disabled. Use listen_redisq() instead.

        zkillboard WebSocket protocol:
        1. Connect to wss://zkillboard.com/websocket/
        2. Subscribe with: {"action":"sub","channel":"killstream"}
        3. Receive kills as JSON messages
        """
        import websockets

        self.running = True

        if verbose:
            print("Starting zKillboard WebSocket listener...")
            print(f"WebSocket URL: {ZKILL_WEBSOCKET_URL}")
            print(f"Hotspot detection: {HOTSPOT_THRESHOLD_KILLS} kills in {HOTSPOT_WINDOW_SECONDS}s")

        kill_count = 0
        reconnect_count = 0

        # Start background finalizer task
        finalizer_task = asyncio.create_task(self.finalize_hotspots_loop(verbose))

        while self.running:
            try:
                if verbose:
                    print(f"\n[WebSocket] Connecting... (attempt {reconnect_count + 1})")

                async with websockets.connect(
                    ZKILL_WEBSOCKET_URL,
                    additional_headers={
                        'User-Agent': ZKILL_USER_AGENT,
                        'Origin': 'https://zkillboard.com'
                    },
                    ping_interval=30,
                    ping_timeout=10,
                    close_timeout=5
                ) as ws:
                    # Subscribe to killstream
                    subscribe_msg = json.dumps({
                        "action": "sub",
                        "channel": "killstream"
                    })
                    await ws.send(subscribe_msg)

                    if verbose:
                        print("[WebSocket] Connected! Subscribed to killstream")
                        reconnect_count = 0

                    # Process incoming kills
                    async for message in ws:
                        try:
                            kill_data = json.loads(message)

                            if "killmail_id" in kill_data:
                                await self.process_live_kill(kill_data)
                                kill_count += 1

                                if verbose and kill_count % 100 == 0:
                                    print(f"[WebSocket] Processed {kill_count} kills")

                        except json.JSONDecodeError as e:
                            if verbose:
                                print(f"[WebSocket] Invalid JSON: {e}")
                        except Exception as e:
                            if verbose:
                                print(f"[WebSocket] Error processing kill: {e}")

            except Exception as e:
                reconnect_count += 1
                if verbose:
                    print(f"[WebSocket] Error: {e}. Reconnecting in {ZKILL_WS_RECONNECT_DELAY}s...")
                await asyncio.sleep(ZKILL_WS_RECONNECT_DELAY)

        if verbose:
            print(f"\n[WebSocket] Stopped. Processed {kill_count} kills total.")

        finalizer_task.cancel()
        if self.session and not self.session.closed:
            await self.session.close()

    async def listen_redisq(self, verbose: bool = False):
        """
        Main loop: RedisQ long-polling for real-time kills.

        RedisQ provides a reliable message queue where each client gets
        their own queue. No data loss on short disconnects.

        Endpoint: https://zkillredisq.stream/listen.php
        Protocol: Long-poll HTTP - returns when kill available or timeout
        """
        self.running = True

        if verbose:
            print("Starting zKillboard RedisQ listener...")
            print(f"RedisQ URL: {ZKILL_REDISQ_URL}")
            print(f"Queue ID: {ZKILL_QUEUE_ID}")
            print(f"Hotspot detection: {HOTSPOT_THRESHOLD_KILLS} kills in {HOTSPOT_WINDOW_SECONDS}s")

        kill_count = 0
        error_count = 0
        empty_count = 0
        rate_limit_count = 0  # Track consecutive rate limits

        # Conservative polling: don't hammer the server
        MIN_POLL_INTERVAL = 0.5  # Minimum 0.5s between requests (2 req/s max)
        BACKOFF_BASE = 60  # Base backoff for rate limits
        MAX_BACKOFF = 300  # Max 5 minutes between retries

        # Start background finalizer task
        finalizer_task = asyncio.create_task(self.finalize_hotspots_loop(verbose))

        session = await self._get_session()

        if verbose:
            print(f"[RedisQ] Conservative mode: {MIN_POLL_INTERVAL}s min interval, exponential backoff on 429")

        while self.running:
            try:
                url = f"{ZKILL_REDISQ_URL}?queueID={ZKILL_QUEUE_ID}&ttw=10"

                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        package = data.get("package")

                        # Success - reset rate limit counter
                        rate_limit_count = 0

                        if package:
                            # RedisQ uses 'killID', API uses 'killmail_id'
                            if "killID" in package and "killmail_id" not in package:
                                package["killmail_id"] = package["killID"]

                            # Process the kill
                            await self.process_live_kill(package)
                            kill_count += 1
                            error_count = 0
                            empty_count = 0

                            if verbose and kill_count % 50 == 0:
                                print(f"[RedisQ] Processed {kill_count} kills")

                            # Small delay to be nice to the server
                            await asyncio.sleep(MIN_POLL_INTERVAL)

                        else:
                            # Empty package - no new kills
                            empty_count += 1
                            if verbose and empty_count % 100 == 0:
                                print(f"[RedisQ] {empty_count} empty responses (queue quiet)")

                    elif response.status == 429:
                        # Rate limited - exponential backoff
                        rate_limit_count += 1
                        retry_after = int(response.headers.get("Retry-After", BACKOFF_BASE))

                        # Exponential backoff: double the wait time for each consecutive 429
                        backoff_time = min(retry_after * (2 ** (rate_limit_count - 1)), MAX_BACKOFF)

                        if verbose:
                            print(f"[RedisQ] Rate limited (429 #{rate_limit_count}), waiting {backoff_time}s...")
                        await asyncio.sleep(backoff_time)
                        error_count += 1

                    else:
                        if verbose:
                            print(f"[RedisQ] HTTP {response.status}, retrying in 10s...")
                        error_count += 1
                        await asyncio.sleep(10)

            except asyncio.TimeoutError:
                # Normal timeout - RedisQ returns empty after timeout
                continue

            except Exception as e:
                error_count += 1
                if verbose:
                    print(f"[RedisQ] Error: {e}")
                if error_count >= 10:
                    if verbose:
                        print("[RedisQ] Too many errors, waiting 60s...")
                    await asyncio.sleep(60)
                    error_count = 0
                else:
                    await asyncio.sleep(5)

        if verbose:
            print(f"\n[RedisQ] Stopped. Processed {kill_count} kills total.")

        finalizer_task.cancel()
        if self.session and not self.session.closed:
            await self.session.close()
