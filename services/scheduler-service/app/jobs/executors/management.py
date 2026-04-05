"""Management suite executor functions."""

import logging
import os

logger = logging.getLogger(__name__)

__all__ = [
    "run_notification_sync",
    "run_contract_sync",
    "run_timer_expiry_check",
    "run_sov_asset_snapshot",
    "run_token_rekey",
    "run_pi_monitor",
    "run_portfolio_snapshotter",
    "run_corp_wallet_sync",
    "run_mining_observer_sync",
]


def run_notification_sync():
    """Sync ESI notifications for all authenticated characters."""
    import httpx

    auth_url = os.environ.get("AUTH_SERVICE_URL", "http://auth-service:8000")
    wi_url = os.environ.get("WAR_INTEL_SERVICE_URL", "http://war-intel-service:8000")

    logger.info("Starting notification_sync job")
    try:
        resp = httpx.get(f"{auth_url}/api/auth/characters", timeout=10)
        resp.raise_for_status()
        characters = resp.json().get("characters", [])

        if not characters:
            logger.warning("notification_sync: No authenticated characters found")
            return True

        success_count = 0
        for char in characters:
            char_id = char.get("character_id")
            token = char.get("access_token")
            if not char_id or not token:
                continue

            try:
                esi_resp = httpx.get(
                    f"https://esi.evetech.net/latest/characters/{char_id}/notifications/",
                    headers={"Authorization": f"Bearer {token}"},
                    params={"datasource": "tranquility"},
                    timeout=30,
                )
                esi_resp.raise_for_status()
                notifications = esi_resp.json()

                store_resp = httpx.post(
                    f"{wi_url}/api/notifications/sync",
                    json={"character_id": char_id, "notifications": notifications},
                    timeout=30,
                )
                store_resp.raise_for_status()
                result = store_resp.json()
                logger.info(f"notification_sync: char {char_id} — {result.get('stored', 0)} stored, {result.get('timers_created', 0)} timers")
                success_count += 1
            except Exception as e:
                logger.error(f"notification_sync: Failed for character {char_id}: {e}")

        logger.info(f"notification_sync: {success_count}/{len(characters)} characters synced")
        return success_count > 0
    except Exception as e:
        logger.error(f"notification_sync: {e}")
        return False


def run_contract_sync():
    """Sync corporation contracts via existing war-intel endpoint."""
    import httpx

    auth_url = os.environ.get("AUTH_SERVICE_URL", "http://auth-service:8000")
    wi_url = os.environ.get("WAR_INTEL_SERVICE_URL", "http://war-intel-service:8000")

    logger.info("Starting contract_sync job")
    try:
        resp = httpx.get(f"{auth_url}/api/auth/characters", timeout=10)
        resp.raise_for_status()
        characters = resp.json().get("characters", [])

        seen_corps = set()
        success_count = 0

        for char in characters:
            corp_id = char.get("corporation_id")
            token = char.get("access_token")
            if not corp_id or not token or corp_id in seen_corps:
                continue
            seen_corps.add(corp_id)

            try:
                sync_resp = httpx.post(
                    f"{wi_url}/api/corp-contracts/sync/{corp_id}",
                    params={"token": token},
                    timeout=60,
                )
                sync_resp.raise_for_status()
                success_count += 1
                logger.info(f"contract_sync: Corp {corp_id} synced")
            except Exception as e:
                logger.error(f"contract_sync: Failed for corp {corp_id}: {e}")

        logger.info(f"contract_sync: {success_count}/{len(seen_corps)} corps synced")
        return success_count > 0
    except Exception as e:
        logger.error(f"contract_sync: {e}")
        return False


def run_timer_expiry_check():
    """Expire old timers and check for soon-expiring timers."""
    import httpx

    wi_url = os.environ.get("WAR_INTEL_SERVICE_URL", "http://war-intel-service:8000")

    logger.info("Starting timer_expiry_check job")
    try:
        resp = httpx.post(f"{wi_url}/api/timers/expire-old", timeout=10)
        resp.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"timer_expiry_check: {e}")
        return False


def run_sov_asset_snapshot():
    """Create sovereignty asset snapshots for delta analysis."""
    import httpx

    wi_url = os.environ.get("WAR_INTEL_SERVICE_URL", "http://war-intel-service:8000")

    logger.info("Starting sov_asset_snapshot job")
    try:
        resp = httpx.post(f"{wi_url}/api/sov/assets/snapshot", timeout=30)
        resp.raise_for_status()
        result = resp.json()
        logger.info(f"sov_asset_snapshot: {result.get('snapshots_created', 0)} snapshots")
        return True
    except Exception as e:
        logger.error(f"sov_asset_snapshot: {e}")
        return False


def run_token_rekey():
    """Re-encrypt tokens with current key if needed after key rotation."""
    import httpx

    auth_url = os.environ.get("AUTH_SERVICE_URL", "http://auth-service:8000")

    logger.info("Starting token_rekey job")
    try:
        resp = httpx.post(f"{auth_url}/api/auth/rekey-tokens", timeout=30)
        resp.raise_for_status()
        result = resp.json()
        rekeyed = result.get("rekeyed", 0)
        if rekeyed > 0:
            logger.info(f"token_rekey: Re-keyed {rekeyed} tokens")
        return True
    except Exception as e:
        logger.error(f"token_rekey: {e}")
        return False


def run_pi_monitor():
    """Execute PI colony monitor via production-service API."""
    logger.info("Starting pi_monitor job")
    try:
        import httpx
        api_url = os.environ.get('API_GATEWAY_URL', 'http://api-gateway:8000')
        response = httpx.post(f"{api_url}/api/pi/monitor", timeout=180)
        if response.status_code == 200:
            logger.info("PI monitor completed successfully")
            return True
        else:
            logger.error(f"PI monitor failed: HTTP {response.status_code} - {response.text[:500]}")
            return False
    except Exception as e:
        logger.exception(f"PI monitor execution failed: {e}")
        return False


def run_portfolio_snapshotter():
    """Execute portfolio snapshotter via API gateway."""
    import httpx

    api_url = os.environ.get("API_GATEWAY_URL", "http://api-gateway:8000")
    logger.info("Starting portfolio_snapshotter job")
    try:
        response = httpx.post(f"{api_url}/api/portfolio/snapshot", timeout=120)
        if response.status_code == 200:
            result = response.json()
            created = result.get("created", 0)
            errors = result.get("errors", [])
            logger.info(f"portfolio_snapshotter: Created {created} snapshots")
            if errors:
                for err in errors:
                    logger.error(f"portfolio_snapshotter: Error for {err.get('character_id')}: {err.get('error')}")
            return True
        else:
            logger.error(f"portfolio_snapshotter: HTTP {response.status_code} - {response.text[:500]}")
            return False
    except Exception as e:
        logger.error(f"portfolio_snapshotter failed: {e}")
        return False


def run_corp_wallet_sync():
    """Sync corporation wallet journals via finance-service.

    Queries platform_accounts + account_characters to find corporations
    with authenticated characters, then calls finance-service wallet/sync
    for each unique corporation (all 7 divisions).
    """
    import httpx
    from eve_shared import get_db

    finance_url = os.environ.get("FINANCE_SERVICE_URL", "http://finance-service:8000")

    logger.info("Starting corp_wallet_sync job")
    try:
        db = get_db()
        with db.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT ON (pa.corporation_id)
                    pa.corporation_id, ac.character_id
                FROM platform_accounts pa
                JOIN account_characters ac ON ac.account_id = pa.id
                WHERE pa.corporation_id IS NOT NULL
            """)
            corps = cur.fetchall()

        if not corps:
            logger.warning("corp_wallet_sync: No corporations with authenticated characters found")
            return True

        success_count = 0
        for row in corps:
            corp_id = row["corporation_id"]
            char_id = row["character_id"]
            try:
                resp = httpx.post(
                    f"{finance_url}/api/finance/wallet/sync",
                    json={
                        "corporation_id": corp_id,
                        "character_id": char_id,
                        "all_divisions": True,
                    },
                    timeout=120,
                )
                resp.raise_for_status()
                result = resp.json()
                logger.info(
                    f"corp_wallet_sync: Corp {corp_id} — "
                    f"{result.get('new_entries', 0)} new entries, "
                    f"{result.get('pages_fetched', 0)} pages"
                )
                success_count += 1
            except Exception as e:
                logger.error(f"corp_wallet_sync: Failed for corp {corp_id}: {e}")

        logger.info(f"corp_wallet_sync: {success_count}/{len(corps)} corps synced")
        return success_count > 0 or len(corps) == 0
    except Exception as e:
        logger.error(f"corp_wallet_sync: {e}")
        return False


def run_mining_observer_sync():
    """Sync mining observers, ledgers, extractions, and ore prices.

    Queries platform_accounts + account_characters for distinct
    (corporation_id, character_id) pairs, then calls finance-service
    mining sync endpoints for each corporation.
    """
    import httpx
    from eve_shared import get_db

    finance_url = os.environ.get("FINANCE_SERVICE_URL", "http://finance-service:8000")

    logger.info("Starting mining_observer_sync job")
    try:
        db = get_db()
        with db.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT ON (pa.corporation_id)
                    pa.corporation_id, ac.character_id
                FROM platform_accounts pa
                JOIN account_characters ac ON ac.account_id = pa.id
                WHERE pa.corporation_id IS NOT NULL
            """)
            corps = cur.fetchall()

        if not corps:
            logger.warning("mining_observer_sync: No corporations found")
            return True

        success_count = 0
        for row in corps:
            corp_id = row["corporation_id"]
            char_id = row["character_id"]

            # 1. Sync observers + ledgers
            try:
                resp = httpx.post(
                    f"{finance_url}/api/finance/mining/sync/{corp_id}",
                    params={"character_id": char_id},
                    timeout=120,
                )
                resp.raise_for_status()
                sync_result = resp.json()
                logger.info(
                    f"mining_observer_sync: Corp {corp_id} — "
                    f"{sync_result.get('observers', 0)} observers, "
                    f"{sync_result.get('entries_synced', 0)} entries"
                )
            except Exception as e:
                logger.error(f"mining_observer_sync: Sync failed for corp {corp_id}: {e}")

            # 2. Sync extractions
            try:
                resp = httpx.post(
                    f"{finance_url}/api/finance/mining/sync-extractions/{corp_id}",
                    params={"character_id": char_id},
                    timeout=60,
                )
                resp.raise_for_status()
                ext_result = resp.json()
                logger.info(
                    f"mining_observer_sync: Corp {corp_id} — "
                    f"{ext_result.get('extractions_synced', 0)} extractions"
                )
                success_count += 1
            except Exception as e:
                logger.error(f"mining_observer_sync: Extractions failed for corp {corp_id}: {e}")

        # 3. Sync ore prices (once globally)
        try:
            resp = httpx.post(
                f"{finance_url}/api/finance/mining/sync-prices",
                timeout=30,
            )
            resp.raise_for_status()
            logger.info(f"mining_observer_sync: Prices synced — {resp.json().get('prices_updated', 0)} updated")
        except Exception as e:
            logger.error(f"mining_observer_sync: Price sync failed: {e}")

        logger.info(f"mining_observer_sync: {success_count}/{len(corps)} corps synced")
        return success_count > 0 or len(corps) == 0
    except Exception as e:
        logger.error(f"mining_observer_sync: {e}")
        return False
