"""ESI sync executor functions."""

import logging
import os

from ._helpers import _call_service

logger = logging.getLogger(__name__)

__all__ = [
    "run_character_sync",
    "run_corporation_sync",
    "run_capability_sync",
    "run_skill_snapshot",
    "run_killmail_fetcher",
    "run_token_refresh",
    "run_wallet_poll",
    "run_everef_importer",
]


def run_character_sync():
    """Execute character data sync via character-service API.

    Fetches authenticated characters from auth-service, then triggers
    sync for each character via character-service POST endpoint.
    """
    import httpx

    auth_url = os.environ.get("AUTH_SERVICE_URL", "http://auth-service:8000")
    char_url = os.environ.get("CHARACTER_SERVICE_URL", "http://character-service:8000")

    logger.info("Starting character_sync job")

    # Get authenticated characters
    try:
        resp = httpx.get(f"{auth_url}/api/auth/characters", timeout=10)
        resp.raise_for_status()
        characters = resp.json().get("characters", [])
    except Exception as e:
        logger.error(f"Failed to get characters from auth-service: {e}")
        return False

    if not characters:
        logger.warning("No authenticated characters found")
        return True

    success_count = 0
    for char in characters:
        char_id = char["character_id"]
        char_name = char.get("character_name", str(char_id))
        try:
            resp = httpx.post(f"{char_url}/api/character/{char_id}/sync", timeout=60)
            resp.raise_for_status()
            result = resp.json()
            synced = result.get("synced", {})
            ok = sum(1 for v in synced.values() if v)
            total = len(synced)
            logger.info(f"Synced {char_name} ({char_id}): {ok}/{total} successful")
            success_count += 1
        except Exception as e:
            logger.error(f"Failed to sync {char_name} ({char_id}): {e}")

    logger.info(f"Character sync complete: {success_count}/{len(characters)} characters")
    return success_count == len(characters)


def run_corporation_sync():
    """Sync corporation data from ESI for all active alliances.

    This is "Truth #1" (structural membership) for coalition detection.
    Fetches corporation IDs and details for all alliances with activity.
    """
    logger.info("Starting corporation_sync job")
    try:
        from app.jobs.corporation_sync import run_sync
        result = run_sync()
        logger.info(f"Corporation sync: {result['corporations_saved']} corps saved")
        return result["errors"] == 0
    except Exception as e:
        logger.exception(f"Corporation sync error: {e}")
        return False


def run_capability_sync():
    """Sync ship capabilities via character-service internal endpoint."""
    char_url = os.environ.get("CHARACTER_SERVICE_URL", "http://character-service:8000")
    logger.info("Starting capability_sync job")
    try:
        result = _call_service(f"{char_url}/api/internal/sync-capabilities", timeout=300)
        details = result.get("details", {})
        logger.info(
            f"Capability sync: {details.get('characters', 0)} characters, "
            f"{details.get('total_synced', 0)} ships synced, "
            f"{details.get('errors', 0)} errors"
        )
        return result.get("status") == "completed"
    except Exception as e:
        logger.error(f"Capability sync failed: {e}")
        return False


def run_skill_snapshot():
    """Character skill snapshot -- superseded by run_character_sync().

    The character_sync job already persists skills to the DB via
    character-service POST /api/character/{id}/sync. This job is
    kept for backward compatibility but just delegates to character_sync.
    """
    logger.info("Skill snapshot: delegating to character_sync (superseded)")
    return run_character_sync()


def run_killmail_fetcher():
    """Fetch daily killmails from EVE Ref archive via war-intel-service."""
    war_intel_url = os.environ.get("WAR_INTEL_SERVICE_URL", "http://war-intel-service:8000")
    logger.info("Starting killmail_fetcher job")
    try:
        result = _call_service(f"{war_intel_url}/api/internal/fetch-killmails", timeout=600)
        details = result.get("details", {})
        logger.info(
            f"Killmail fetcher: {details.get('imported', 0)} imported, "
            f"{details.get('skipped', 0)} skipped, "
            f"{details.get('items', 0)} items"
        )
        return result.get("status") == "completed"
    except Exception as e:
        logger.error(f"Killmail fetcher failed: {e}")
        return False


def run_token_refresh():
    """Refresh OAuth tokens for all authenticated characters.

    Calls auth-service to refresh tokens that are expired or near expiry.
    Runs every 15 minutes to keep tokens alive (EVE tokens expire after 20 min).
    """
    logger.info("Starting token_refresh job")
    import httpx

    auth_url = os.environ.get('AUTH_SERVICE_URL', 'http://auth-service:8000')

    # Get all characters from auth-service
    try:
        with httpx.Client(timeout=30) as client:
            resp = client.get(f"{auth_url}/api/auth/characters")
            if resp.status_code != 200:
                logger.error(f"Failed to list characters: HTTP {resp.status_code}")
                return False
            characters = resp.json().get("characters", [])
    except Exception as e:
        logger.exception(f"Failed to connect to auth-service: {e}")
        return False

    if not characters:
        logger.info("No authenticated characters found")
        return True

    refreshed = 0
    failed = 0

    with httpx.Client(timeout=30) as client:
        for char in characters:
            char_id = char["character_id"]
            char_name = char["character_name"]
            needs_refresh = char.get("needs_refresh", False)
            is_valid = char.get("is_valid", True)

            if is_valid and not needs_refresh:
                logger.debug(f"Token still valid for {char_name}, skipping")
                continue

            try:
                resp = client.post(f"{auth_url}/api/auth/refresh/{char_id}")
                if resp.status_code == 200:
                    refreshed += 1
                    logger.info(f"Refreshed token for {char_name} ({char_id})")
                else:
                    failed += 1
                    logger.warning(
                        f"Failed to refresh {char_name} ({char_id}): HTTP {resp.status_code}"
                    )
            except Exception as e:
                failed += 1
                logger.warning(f"Error refreshing {char_name} ({char_id}): {e}")

    logger.info(
        f"Token refresh complete: {refreshed} refreshed, {failed} failed, "
        f"{len(characters) - refreshed - failed} still valid"
    )
    return failed == 0


def run_wallet_poll():
    """Wallet journal polling -- superseded by auth-service payment_poller.

    The auth-service already has a complete payment processing pipeline
    (payment_processor.py + wallet_journal.py) that handles ISK payments,
    reference code matching, and subscription activation. The scheduler's
    run_payment_poll job (in saas.py) already calls the auth-service endpoint.

    This legacy job is kept for backward compatibility but logs a deprecation
    warning and returns True (no-op).
    """
    logger.warning(
        "wallet_poll is deprecated -- use run_payment_poll (saas executor) instead. "
        "Auth-service handles payment processing via its own pipeline."
    )
    return True


def run_everef_importer():
    """Import killmails from EVE Ref daily dump via war-intel-service."""
    war_intel_url = os.environ.get("WAR_INTEL_SERVICE_URL", "http://war-intel-service:8000")
    logger.info("Starting everef_importer job")
    try:
        result = _call_service(f"{war_intel_url}/api/internal/import-everef", timeout=900)
        details = result.get("details", {})
        logger.info(
            f"Everef importer: {details.get('imported', 0)} imported, "
            f"{details.get('skipped', 0)} skipped, "
            f"{details.get('items', 0)} items"
        )
        return result.get("status") == "completed"
    except Exception as e:
        logger.error(f"Everef importer failed: {e}")
        return False
