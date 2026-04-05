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
    R2Z2_POLL_INTERVAL_DATA,
    R2Z2_POLL_INTERVAL_EMPTY,
)
from services.zkillboard.r2z2_client import R2Z2Client, R2Z2RateLimited, R2Z2Blocked

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

    async def listen_r2z2(self, verbose: bool = False):
        """
        Main loop: R2Z2 sequence-based polling for real-time kills.

        Replaces listen_redisq(). R2Z2 uses Cloudflare R2 buckets with
        monotonically increasing sequence numbers. Each response includes
        the complete killmail (no separate ESI fetch needed).

        Sequence state is persisted in Redis via self.state_manager.
        On restart, resumes from the last processed sequence.

        API: https://github.com/zKillboard/zKillboard/wiki/API-(R2Z2)
        """
        self.running = True
        client = R2Z2Client()
        kill_count = 0
        error_count = 0
        last_success_time = asyncio.get_event_loop().time()
        STALE_SEQUENCE_TIMEOUT = 300  # 5 min of 404s -> re-fetch sequence.json

        if verbose:
            print("Starting zKillboard R2Z2 listener...")
            print(f"Hotspot detection: {HOTSPOT_THRESHOLD_KILLS} kills in {HOTSPOT_WINDOW_SECONDS}s")

        # Determine starting sequence
        saved_seq = self.state_manager.get_r2z2_sequence()
        if saved_seq is not None:
            sequence = saved_seq + 1  # Resume from next unprocessed
            if verbose:
                print(f"[R2Z2] Resuming from saved sequence {saved_seq}, starting at {sequence}")
        else:
            sequence = await client.fetch_current_sequence()
            if sequence is None:
                print("[R2Z2] FATAL: Cannot fetch initial sequence from R2Z2. Retrying in 30s...")
                await asyncio.sleep(30)
                sequence = await client.fetch_current_sequence()
                if sequence is None:
                    print("[R2Z2] FATAL: Still cannot reach R2Z2. Aborting.")
                    return
            if verbose:
                print(f"[R2Z2] Starting from current sequence: {sequence}")

        # Start background finalizer task
        finalizer_task = asyncio.create_task(self.finalize_hotspots_loop(verbose))

        try:
            while self.running:
                try:
                    package = await client.fetch_killmail(sequence)

                    if package is not None:
                        # Got a killmail - process it
                        entry = client.to_process_format(package)
                        await self.process_live_kill(entry)
                        kill_count += 1
                        error_count = 0
                        last_success_time = asyncio.get_event_loop().time()

                        # Persist sequence AFTER successful handoff
                        self.state_manager.save_r2z2_sequence(sequence)

                        if verbose and kill_count % 50 == 0:
                            print(f"[R2Z2] Processed {kill_count} kills (seq={sequence})")

                        # Next sequence, short delay
                        sequence += 1
                        await asyncio.sleep(R2Z2_POLL_INTERVAL_DATA)

                    else:
                        # 404 or parse error - no data at this sequence yet
                        # Detect stale sequence (gap in sequence numbers)
                        now = asyncio.get_event_loop().time()
                        if now - last_success_time > STALE_SEQUENCE_TIMEOUT:
                            print(f"[R2Z2] No data for {STALE_SEQUENCE_TIMEOUT}s - re-fetching sequence.json")
                            new_seq = await client.fetch_current_sequence()
                            if new_seq is not None and new_seq > sequence:
                                print(f"[R2Z2] Jumping from {sequence} to {new_seq}")
                                sequence = new_seq
                            last_success_time = now  # Reset to avoid spam

                        await asyncio.sleep(R2Z2_POLL_INTERVAL_EMPTY)

                except R2Z2RateLimited as e:
                    print(f"[R2Z2] Rate limited, waiting {e.retry_after}s...")
                    await asyncio.sleep(e.retry_after)

                except R2Z2Blocked:
                    print("[R2Z2] BLOCKED by R2Z2 (403). Waiting 5 minutes...")
                    await asyncio.sleep(300)

                except asyncio.CancelledError:
                    print("[R2Z2] Listener cancelled")
                    break

                except Exception as e:
                    error_count += 1
                    print(f"[R2Z2] Error: {e}")
                    if error_count >= 10:
                        print("[R2Z2] Too many errors, waiting 60s...")
                        await asyncio.sleep(60)
                        error_count = 0
                    else:
                        await asyncio.sleep(5)

        finally:
            if verbose:
                print(f"\n[R2Z2] Stopped. Processed {kill_count} kills. Last sequence: {sequence}")
            finalizer_task.cancel()
            await client.close()
            if self.session and not self.session.closed:
                await self.session.close()
