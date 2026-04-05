#!/usr/bin/env python3
"""Wallet journal polling job for payment detection.

Polls the service wallet for ISK donations and automatically
processes payments to activate subscriptions.

Runs every 5 minutes via scheduler-service.
"""

import logging
import os
import re
import sys
from datetime import datetime, timezone, timedelta
from typing import Optional

import psycopg2
from psycopg2.extras import RealDictCursor
import httpx
import redis

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database connection
_pg_host = os.environ.get('POSTGRES_HOST', 'eve_db')
_pg_port = os.environ.get('POSTGRES_PORT', '5432')
_pg_user = os.environ.get('POSTGRES_USER', 'eve')
_pg_pass = os.environ.get('POSTGRES_PASSWORD', '')
_pg_db = os.environ.get('POSTGRES_DB', 'eve_sde')
DATABASE_URL = os.environ.get(
    'DATABASE_URL',
    f'postgresql://{_pg_user}:{_pg_pass}@{_pg_host}:{_pg_port}/{_pg_db}'
)

# Redis connection
REDIS_URL = os.environ.get('REDIS_URL', 'redis://redis:6379/0')

# Service URLs
ESI_BASE = "https://esi.evetech.net/latest"
AUTH_SERVICE_URL = os.environ.get('AUTH_SERVICE_URL', 'http://auth-service:8000')


def get_db_connection():
    """Get database connection."""
    return psycopg2.connect(DATABASE_URL)


def get_redis_client():
    """Get Redis client."""
    return redis.from_url(REDIS_URL)


def get_auth_token(character_id: int) -> Optional[str]:
    """Get valid ESI token from auth-service."""
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(f"{AUTH_SERVICE_URL}/api/auth/token/{character_id}")
            if resp.status_code == 200:
                return resp.json().get("access_token")
            logger.warning(f"Auth service returned {resp.status_code} for character {character_id}")
    except Exception as e:
        logger.error(f"Failed to get auth token: {e}")
    return None


def get_wallet_journal(character_id: int, token: str) -> list:
    """Fetch wallet journal from ESI."""
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(
                f"{ESI_BASE}/characters/{character_id}/wallet/journal/",
                headers={"Authorization": f"Bearer {token}"},
                params={"datasource": "tranquility"}
            )
            if resp.status_code == 200:
                return resp.json()
            logger.error(f"ESI wallet journal failed: {resp.status_code}")
    except Exception as e:
        logger.error(f"Failed to fetch wallet journal: {e}")
    return []


def get_character_name(character_id: int) -> str:
    """Get character name from ESI."""
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(f"{ESI_BASE}/characters/{character_id}/")
            if resp.status_code == 200:
                return resp.json().get("name", f"Character {character_id}")
    except Exception:
        pass
    return f"Character {character_id}"


def activate_subscription(conn, payment_id: int, character_id: int, product_id: int, payment_code: Optional[str] = None):
    """Activate subscription for a payment."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # Get product details
        cur.execute("SELECT duration_days FROM products WHERE id = %s", (product_id,))
        product = cur.fetchone()
        if not product:
            logger.error(f"Product {product_id} not found")
            return

        # Create subscription
        now = datetime.now(timezone.utc)
        expires = now + timedelta(days=product["duration_days"])

        cur.execute("""
            INSERT INTO subscriptions (character_id, product_id, starts_at, expires_at, payment_id)
            VALUES (%s, %s, %s, %s, %s)
        """, (character_id, product_id, now, expires, payment_id))

        # Update payment
        cur.execute("""
            UPDATE payments
            SET status = 'processed',
                matched_customer_id = %s,
                payment_code = %s,
                processed_at = NOW()
            WHERE id = %s
        """, (character_id, payment_code, payment_id))

        conn.commit()
        logger.info(f"Subscription activated for character {character_id}, product {product_id}, expires {expires}")


def process_payment_entry(conn, entry: dict):
    """Process a single wallet journal entry."""
    ref_id = entry["id"]
    from_id = entry.get("first_party_id")
    amount = int(entry.get("amount", 0))
    reason = entry.get("reason", "")
    received_at = entry.get("date")

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # Skip if already processed
        cur.execute("SELECT id FROM payments WHERE journal_ref_id = %s", (ref_id,))
        if cur.fetchone():
            return

        # Get sender name
        from_name = get_character_name(from_id)

        # Create payment record
        cur.execute("""
            INSERT INTO payments (
                journal_ref_id, from_character_id, from_character_name,
                amount, reason, received_at, status
            )
            VALUES (%s, %s, %s, %s, %s, %s, 'pending')
            RETURNING id
        """, (ref_id, from_id, from_name, amount, reason, received_at))
        payment_row = cur.fetchone()
        payment_id = payment_row["id"]

        # Auto-create customer
        cur.execute("""
            INSERT INTO customers (character_id, character_name)
            VALUES (%s, %s)
            ON CONFLICT (character_id) DO UPDATE SET character_name = EXCLUDED.character_name
        """, (from_id, from_name))

        conn.commit()

    # Try to match payment

    # Attempt 1: Payment code in reason
    code_match = re.search(r"PAY-[A-Z0-9]{5}", reason.upper())
    if code_match:
        code_str = code_match.group()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT code, character_id, product_id
                FROM payment_codes
                WHERE code = %s AND used_at IS NULL AND expires_at > NOW()
            """, (code_str,))
            code = cur.fetchone()

            if code:
                activate_subscription(conn, payment_id, code["character_id"], code["product_id"], code_str)
                cur.execute("UPDATE payment_codes SET used_at = NOW() WHERE code = %s", (code_str,))
                conn.commit()
                logger.info(f"Payment {payment_id} matched via code {code_str}")
                return

    # Attempt 2: Match by exact price
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT id, price_isk FROM products WHERE price_isk = %s AND is_active = true", (amount,))
        products = cur.fetchall()

        if len(products) == 1:
            activate_subscription(conn, payment_id, from_id, products[0]["id"])
            logger.info(f"Payment {payment_id} auto-matched by price to product {products[0]['id']}")
            return
        elif len(products) > 1:
            cur.execute(
                "UPDATE payments SET notes = %s WHERE id = %s",
                ("Multiple products match price - manual review needed", payment_id)
            )
        else:
            cur.execute(
                "UPDATE payments SET notes = %s WHERE id = %s",
                (f"No product matches {amount} ISK", payment_id)
            )
        conn.commit()

    logger.info(f"Payment {payment_id} requires manual review: {amount} ISK from {from_name}")


def poll_wallet_journal():
    """Poll wallet journal for new payments."""
    conn = get_db_connection()
    redis_client = get_redis_client()

    try:
        # Check kill-switch
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT value FROM system_config WHERE key = 'wallet_poll_enabled'")
            config_row = cur.fetchone()
            if not config_row or config_row["value"] != "true":
                logger.debug("Wallet polling disabled")
                return True

        # Acquire lock
        lock_key = "wallet_poll_lock"
        if not redis_client.set(lock_key, "1", nx=True, ex=300):
            logger.info("Wallet poll already running, skipping")
            return True

        try:
            # Get active service wallet
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT id, character_id, character_name, last_journal_ref_id
                    FROM service_wallets
                    WHERE is_active = true
                    LIMIT 1
                """)
                wallet = cur.fetchone()

            if not wallet:
                logger.warning("No active service wallet configured")
                return True

            # Get auth token
            token = get_auth_token(wallet["character_id"])
            if not token:
                logger.error(f"Could not get token for wallet character {wallet['character_id']}")
                return False

            # Fetch journal
            journal = get_wallet_journal(wallet["character_id"], token)
            if not journal:
                logger.debug("No journal entries returned")
                return True

            last_ref_id = wallet["last_journal_ref_id"] or 0
            max_ref_id = last_ref_id
            processed_count = 0

            for entry in journal:
                ref_id = entry.get("id", 0)

                # Skip already processed
                if ref_id <= last_ref_id:
                    continue

                # Only process player donations
                if entry.get("ref_type") != "player_donation":
                    continue

                max_ref_id = max(max_ref_id, ref_id)
                process_payment_entry(conn, entry)
                processed_count += 1

            # Update last processed ref ID
            if max_ref_id > last_ref_id:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE service_wallets SET last_journal_ref_id = %s WHERE id = %s",
                        (max_ref_id, wallet["id"])
                    )
                    conn.commit()
                logger.info(f"Processed {processed_count} payments, journal up to ref_id {max_ref_id}")
            else:
                logger.debug("No new payments to process")

            return True

        finally:
            redis_client.delete(lock_key)

    except Exception as e:
        logger.exception(f"Wallet poll failed: {e}")
        return False
    finally:
        conn.close()


def main():
    """Main job execution."""
    logger.info("Starting wallet poll job")
    start_time = datetime.now(timezone.utc)

    try:
        success = poll_wallet_journal()
        elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
        logger.info(f"Wallet poll completed in {elapsed:.1f}s")
        return success
    except Exception as e:
        logger.exception(f"Wallet poll failed: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
