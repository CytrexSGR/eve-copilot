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
                logger.warning(
                    f"Failed to get token for {character_id}: "
                    f"status={response.status_code}"
                )
                return None
        except Exception as e:
            logger.warning(f"Auth service unavailable for {character_id}: {e}")
            return None

    async def get_valid_token_async(self, character_id: int) -> Optional[str]:
        """Get a valid access token for a character (async version).

        Args:
            character_id: EVE character ID

        Returns:
            Access token string or None if not available
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/api/auth/token/{character_id}"
                )
                if response.status_code == 200:
                    data = response.json()
                    return data.get("access_token")
                logger.warning(
                    f"Failed to get token for {character_id}: "
                    f"status={response.status_code}"
                )
                return None
        except Exception as e:
            logger.warning(f"Auth service unavailable for {character_id}: {e}")
            return None

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
                    return response.json()
                return []
        except Exception as e:
            logger.warning(f"Failed to get characters: {e}")
            return []
