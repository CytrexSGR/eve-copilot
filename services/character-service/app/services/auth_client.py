"""Auth service client for token management."""
import logging
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class AuthClient:
    """Client for auth-service token management."""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or settings.auth_service_url
        self.timeout = 10.0
        self._token_cache: dict = {}

    def get_valid_token(self, character_id: int) -> Optional[str]:
        """Get a valid access token for a character.

        Args:
            character_id: EVE character ID

        Returns:
            Access token string or None if not available
        """
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(
                    f"{self.base_url}/api/auth/token/{character_id}"
                )
                if response.status_code == 200:
                    data = response.json()
                    return data.get("access_token")
                return None
        except Exception as e:
            logger.warning(f"Auth service unavailable for {character_id}: {e}")
            return None

    def refresh_token(self, character_id: int) -> bool:
        """Refresh token for a character.

        Args:
            character_id: EVE character ID

        Returns:
            True if refresh successful
        """
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.base_url}/api/auth/refresh/{character_id}"
                )
                return response.status_code == 200
        except Exception as e:
            logger.warning(f"Token refresh failed for {character_id}: {e}")
            return False

    def get_characters(self) -> list:
        """Get list of authenticated characters.

        Returns:
            List of character dicts with id and name
        """
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(
                    f"{self.base_url}/api/auth/characters"
                )
                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, dict):
                        return data.get("characters", [])
                    return data
                return []
        except Exception as e:
            logger.warning(f"Failed to get characters: {e}")
            return []


class LocalAuthClient(AuthClient):
    """Auth client with local token file fallback."""

    def __init__(self, db):
        super().__init__()
        self.db = db

    def get_valid_token(self, character_id: int) -> Optional[str]:
        """Get token, falling back to database."""
        # Try service first
        token = super().get_valid_token(character_id)
        if token:
            return token

        # Fallback to database
        query = """
            SELECT access_token, expires_at
            FROM character_tokens
            WHERE character_id = $1
        """
        row = self.db.fetchrow(query, character_id)
        if row and row["access_token"]:
            return row["access_token"]
        return None
