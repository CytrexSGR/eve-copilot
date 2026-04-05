"""EVE SSO OAuth2 service with PKCE, distributed locking, and owner hash tracking."""

import secrets
import hashlib
import base64
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from urllib.parse import urlencode
import httpx

logger = logging.getLogger(__name__)

# HTTP client timeout in seconds
HTTP_TIMEOUT = 30.0

from app.config import AuthConfig
from app.models.token import OAuthTokenResponse, CharacterInfo, StoredToken, AuthState
from app.repository.db_token_store import DatabaseTokenStore

# Lazy-loaded token lock singleton
_token_lock = None


def _get_token_lock():
    global _token_lock
    if _token_lock is None:
        try:
            from eve_shared.esi.token_lock import TokenLock
            _token_lock = TokenLock()
        except ImportError:
            logger.debug("TokenLock not available, distributed locking disabled")
    return _token_lock


# All 66 ESI scopes
ESI_SCOPES = [
    "esi-alliances.read_contacts.v1",
    "esi-assets.read_assets.v1",
    "esi-assets.read_corporation_assets.v1",
    "esi-calendar.read_calendar_events.v1",
    "esi-calendar.respond_calendar_events.v1",
    "esi-characters.read_agents_research.v1",
    "esi-characters.read_blueprints.v1",
    "esi-characters.read_contacts.v1",
    "esi-characters.read_corporation_roles.v1",
    "esi-characters.read_fatigue.v1",
    "esi-characters.read_fw_stats.v1",
    "esi-characters.read_loyalty.v1",
    "esi-characters.read_medals.v1",
    "esi-characters.read_notifications.v1",
    "esi-characters.read_standings.v1",
    "esi-characters.read_titles.v1",
    "esi-characters.write_contacts.v1",
    "esi-clones.read_clones.v1",
    "esi-clones.read_implants.v1",
    "esi-contracts.read_character_contracts.v1",
    "esi-contracts.read_corporation_contracts.v1",
    "esi-corporations.read_blueprints.v1",
    "esi-corporations.read_contacts.v1",
    "esi-corporations.read_container_logs.v1",
    "esi-corporations.read_corporation_membership.v1",
    "esi-corporations.read_divisions.v1",
    "esi-corporations.read_facilities.v1",
    "esi-corporations.read_fw_stats.v1",
    "esi-corporations.read_medals.v1",
    "esi-corporations.read_standings.v1",
    "esi-corporations.read_starbases.v1",
    "esi-corporations.read_structures.v1",
    "esi-corporations.read_titles.v1",
    "esi-corporations.track_members.v1",
    "esi-fittings.read_fittings.v1",
    "esi-fittings.write_fittings.v1",
    "esi-fleets.read_fleet.v1",
    "esi-fleets.write_fleet.v1",
    "esi-industry.read_character_jobs.v1",
    "esi-industry.read_character_mining.v1",
    "esi-industry.read_corporation_jobs.v1",
    "esi-industry.read_corporation_mining.v1",
    "esi-killmails.read_corporation_killmails.v1",
    "esi-killmails.read_killmails.v1",
    "esi-location.read_location.v1",
    "esi-location.read_online.v1",
    "esi-location.read_ship_type.v1",
    "esi-mail.organize_mail.v1",
    "esi-mail.read_mail.v1",
    "esi-mail.send_mail.v1",
    "esi-markets.read_character_orders.v1",
    "esi-markets.read_corporation_orders.v1",
    "esi-markets.structure_markets.v1",
    "esi-planets.manage_planets.v1",
    "esi-planets.read_customs_offices.v1",
    "esi-search.search_structures.v1",
    "esi-skills.read_skillqueue.v1",
    "esi-skills.read_skills.v1",
    "esi-ui.open_window.v1",
    "esi-ui.write_waypoint.v1",
    "esi-universe.read_structures.v1",
    "esi-wallet.read_character_wallet.v1",
    "esi-wallet.read_corporation_wallets.v1",
]


class EVESSOService:
    """EVE SSO OAuth2 service with PKCE support."""

    def __init__(self, token_store: DatabaseTokenStore, config: AuthConfig):
        self.token_store = token_store
        self.config = config

    def _generate_code_verifier(self) -> str:
        """Generate PKCE code verifier (86 chars)."""
        return secrets.token_urlsafe(64)[:86]

    def _generate_code_challenge(self, verifier: str) -> str:
        """Generate PKCE code challenge from verifier."""
        digest = hashlib.sha256(verifier.encode()).digest()
        return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()

    def _generate_state(self) -> str:
        """Generate state parameter for CSRF protection."""
        return secrets.token_urlsafe(32)

    async def get_auth_url(self, redirect_url: Optional[str] = None) -> str:
        """Generate OAuth2 authorization URL with PKCE."""
        state = self._generate_state()
        code_verifier = self._generate_code_verifier()
        code_challenge = self._generate_code_challenge(code_verifier)

        # Store state for validation
        auth_state = AuthState(
            state=state,
            code_verifier=code_verifier,
            redirect_url=redirect_url,
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
        )
        self.token_store.save_state(state, auth_state)

        # Build auth URL with proper URL encoding
        scopes = " ".join(ESI_SCOPES)
        params = {
            "response_type": "code",
            "redirect_uri": self.config.esi_callback_url,
            "client_id": self.config.esi_client_id,
            "scope": scopes,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        return f"{self.config.esi_auth_url}?{urlencode(params)}"

    async def handle_callback(self, code: str, state: str) -> OAuthTokenResponse:
        """Handle OAuth2 callback and exchange code for tokens."""
        # Validate state
        auth_state = self.token_store.get_state(state)
        if not auth_state:
            raise ValueError("Invalid or expired state parameter")

        if datetime.now(timezone.utc) > auth_state.expires_at:
            self.token_store.delete_state(state)
            raise ValueError("State parameter expired")

        # Exchange code for tokens
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            response = await client.post(
                self.config.esi_token_url,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "client_id": self.config.esi_client_id,
                    "code_verifier": auth_state.code_verifier,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if response.status_code != 200:
                logger.error(f"Token exchange failed: {response.text}")
                raise ValueError("Token exchange failed")

            token_data = response.json()

            # Verify token and get character info
            verify_response = await client.get(
                self.config.esi_verify_url,
                headers={"Authorization": f"Bearer {token_data['access_token']}"},
            )

            if verify_response.status_code != 200:
                logger.error(f"Token verification failed: {verify_response.text}")
                raise ValueError("Token verification failed")

            char_info = verify_response.json()

        # Calculate expiration
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=token_data["expires_in"])

        # Extract CharacterOwnerHash for account transfer detection
        owner_hash = char_info.get("CharacterOwnerHash")
        if owner_hash:
            logger.info(f"CharacterOwnerHash for {char_info['CharacterName']}: {owner_hash[:12]}...")

        # Store token
        stored_token = StoredToken(
            access_token=token_data["access_token"],
            refresh_token=token_data["refresh_token"],
            expires_at=expires_at,
            character_id=char_info["CharacterID"],
            character_name=char_info["CharacterName"],
            scopes=ESI_SCOPES,
            updated_at=datetime.now(timezone.utc),
            character_owner_hash=owner_hash,
        )
        self.token_store.save_token(char_info["CharacterID"], stored_token)

        # Clean up state
        self.token_store.delete_state(state)

        return OAuthTokenResponse(
            access_token=token_data["access_token"],
            token_type="Bearer",
            expires_in=token_data["expires_in"],
            refresh_token=token_data["refresh_token"],
            character_id=char_info["CharacterID"],
            character_name=char_info["CharacterName"],
        )

    async def refresh_token(self, character_id: int) -> OAuthTokenResponse:
        """Refresh access token for a character.

        Uses distributed locking to prevent concurrent refresh attempts
        across multiple services. Implements double-check locking:
        1. Acquire lock
        2. Re-read token from DB (another service may have refreshed it)
        3. If still expired, perform the refresh
        4. Release lock
        """
        stored = self.token_store.get_token(character_id)
        if not stored:
            raise ValueError(f"No token found for character {character_id}")

        # Try to acquire distributed lock
        lock = _get_token_lock()
        lock_acquired = lock.acquire(character_id) if lock else True

        if not lock_acquired:
            # Another service is refreshing — wait briefly and re-read
            import asyncio
            await asyncio.sleep(2)
            stored = self.token_store.get_token(character_id)
            if stored and (stored.expires_at - datetime.now(timezone.utc)).total_seconds() > 10:
                logger.info(f"Token for {character_id} refreshed by another service")
                return OAuthTokenResponse(
                    access_token=stored.access_token,
                    token_type="Bearer",
                    expires_in=int((stored.expires_at - datetime.now(timezone.utc)).total_seconds()),
                    refresh_token=stored.refresh_token,
                    character_id=character_id,
                    character_name=stored.character_name,
                )
            # Lock contention but token still expired — proceed without lock
            logger.warning(f"Lock contention for {character_id}, proceeding with refresh")

        try:
            # Double-check: re-read token after acquiring lock
            if lock_acquired and lock:
                stored = self.token_store.get_token(character_id)
                if not stored:
                    raise ValueError(f"No token found for character {character_id}")
                if (stored.expires_at - datetime.now(timezone.utc)).total_seconds() > self.config.token_refresh_buffer_seconds:
                    logger.info(f"Token for {character_id} already refreshed (double-check)")
                    return OAuthTokenResponse(
                        access_token=stored.access_token,
                        token_type="Bearer",
                        expires_in=int((stored.expires_at - datetime.now(timezone.utc)).total_seconds()),
                        refresh_token=stored.refresh_token,
                        character_id=character_id,
                        character_name=stored.character_name,
                    )

            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
                # Use Basic Auth for token refresh
                auth = (self.config.esi_client_id, self.config.esi_client_secret)
                response = await client.post(
                    self.config.esi_token_url,
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": stored.refresh_token,
                    },
                    auth=auth,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )

                if response.status_code != 200:
                    logger.error(f"Token refresh failed for character {character_id}: {response.text}")
                    raise ValueError("Token refresh failed")

                token_data = response.json()

            expires_at = datetime.now(timezone.utc) + timedelta(seconds=token_data["expires_in"])

            # Update stored token
            stored.access_token = token_data["access_token"]
            stored.refresh_token = token_data.get("refresh_token", stored.refresh_token)
            stored.expires_at = expires_at
            stored.updated_at = datetime.now(timezone.utc)
            self.token_store.save_token(character_id, stored)

            return OAuthTokenResponse(
                access_token=token_data["access_token"],
                token_type="Bearer",
                expires_in=token_data["expires_in"],
                refresh_token=stored.refresh_token,
                character_id=character_id,
                character_name=stored.character_name,
            )
        finally:
            if lock_acquired and lock:
                lock.release(character_id)

    async def get_authenticated_characters(self) -> List[CharacterInfo]:
        """Get list of authenticated characters."""
        tokens = self.token_store.list_tokens()
        characters = []
        for token in tokens:
            is_valid = datetime.now(timezone.utc) < token.expires_at
            needs_refresh = (token.expires_at - datetime.now(timezone.utc)).total_seconds() < self.config.token_refresh_buffer_seconds
            characters.append(CharacterInfo(
                character_id=token.character_id,
                character_name=token.character_name,
                is_valid=is_valid,
                needs_refresh=needs_refresh,
                expires_at=token.expires_at.isoformat(),
            ))
        return characters

    async def logout_character(self, character_id: int) -> bool:
        """Remove character authentication."""
        return self.token_store.delete_token(character_id)

    async def get_valid_token(self, character_id: int) -> str:
        """Get valid access token, refreshing if needed."""
        stored = self.token_store.get_token(character_id)
        if not stored:
            raise ValueError(f"No token found for character {character_id}")

        # Check if refresh needed
        seconds_until_expiry = (stored.expires_at - datetime.now(timezone.utc)).total_seconds()
        if seconds_until_expiry < self.config.token_refresh_buffer_seconds:
            token_response = await self.refresh_token(character_id)
            return token_response.access_token

        return stored.access_token
