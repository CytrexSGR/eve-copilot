"""SaaS-related executor functions (payments, subscriptions)."""

import logging
import os

logger = logging.getLogger(__name__)

__all__ = [
    "run_payment_poll",
    "run_subscription_expiry",
]


def run_payment_poll():
    """Poll wallet journal for ISK payments. Every 60 seconds."""
    import httpx

    auth_url = os.environ.get("AUTH_SERVICE_URL", "http://auth-service:8000")

    try:
        resp = httpx.post(f"{auth_url}/api/tier/internal/poll-payments", timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            verified = data.get("verified", 0)
            if verified > 0:
                logger.info(f"payment_poll: {verified} payments verified")
            return True
        logger.warning(f"payment_poll: HTTP {resp.status_code}")
        return False
    except Exception as e:
        logger.error(f"payment_poll: {e}")
        return False


def run_subscription_expiry():
    """Check and expire stale subscriptions. Every hour."""
    import httpx

    auth_url = os.environ.get("AUTH_SERVICE_URL", "http://auth-service:8000")

    try:
        resp = httpx.post(f"{auth_url}/api/tier/internal/expire-subscriptions", timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            expired = data.get("expired", 0)
            if expired > 0:
                logger.info(f"subscription_expiry: {expired} subscriptions expired")
            return True
        return False
    except Exception as e:
        logger.error(f"subscription_expiry: {e}")
        return False
