"""Database-backed token storage for OAuth tokens and PKCE states."""

import logging
from typing import Optional, List
from datetime import datetime, timezone

from app.database import db_cursor
from app.models.token import StoredToken, AuthState

logger = logging.getLogger(__name__)

# Lazy-loaded encryption singleton
_encryption = None


def _get_encryption():
    global _encryption
    if _encryption is None:
        try:
            from eve_shared.esi.encryption import TokenEncryption
            _encryption = TokenEncryption()
        except ImportError:
            logger.debug("TokenEncryption not available")
    return _encryption


class DatabaseTokenStore:
    """PostgreSQL-backed storage for OAuth tokens and PKCE states.

    Replaces file-based TokenStore for concurrent access safety and scalability.
    All methods are synchronous (psycopg2 with connection pooling).
    Supports optional Fernet encryption for refresh_tokens.
    """

    def save_token(self, character_id: int, token: StoredToken):
        """Save or update token for a character.

        If encryption is enabled, encrypts refresh_token before storage.
        """
        enc = _get_encryption()
        refresh_token_plain = token.refresh_token
        refresh_token_encrypted = None
        is_encrypted = False

        if enc and enc.is_enabled:
            encrypted = enc.encrypt(refresh_token_plain)
            if encrypted:
                refresh_token_encrypted = encrypted
                is_encrypted = True
                refresh_token_plain = "[encrypted]"  # Placeholder in plaintext column

        with db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO oauth_tokens
                    (character_id, character_name, access_token, refresh_token,
                     refresh_token_encrypted, is_encrypted,
                     scopes, expires_at, updated_at, character_owner_hash)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (character_id) DO UPDATE SET
                    character_name = EXCLUDED.character_name,
                    access_token = EXCLUDED.access_token,
                    refresh_token = EXCLUDED.refresh_token,
                    refresh_token_encrypted = EXCLUDED.refresh_token_encrypted,
                    is_encrypted = EXCLUDED.is_encrypted,
                    scopes = EXCLUDED.scopes,
                    expires_at = EXCLUDED.expires_at,
                    updated_at = EXCLUDED.updated_at,
                    character_owner_hash = COALESCE(EXCLUDED.character_owner_hash, oauth_tokens.character_owner_hash)
                """,
                (
                    character_id,
                    token.character_name,
                    token.access_token,
                    refresh_token_plain,
                    refresh_token_encrypted,
                    is_encrypted,
                    list(token.scopes),
                    token.expires_at,
                    token.updated_at or datetime.now(timezone.utc),
                    token.character_owner_hash,
                ),
            )

    def get_token(self, character_id: int) -> Optional[StoredToken]:
        """Get token for a character.

        If the token is encrypted, decrypts the refresh_token transparently.
        """
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT character_id, character_name, access_token, refresh_token,
                       refresh_token_encrypted, is_encrypted,
                       scopes, expires_at, updated_at, character_owner_hash
                FROM oauth_tokens
                WHERE character_id = %s
                """,
                (character_id,),
            )
            row = cur.fetchone()
            if not row:
                return None

            row = dict(row)

            # Decrypt refresh_token if encrypted
            if row.get("is_encrypted") and row.get("refresh_token_encrypted"):
                enc = _get_encryption()
                if enc and enc.is_enabled:
                    decrypted = enc.decrypt(bytes(row["refresh_token_encrypted"]))
                    if decrypted:
                        row["refresh_token"] = decrypted
                    else:
                        logger.error(f"Failed to decrypt refresh_token for character {character_id}")

            return StoredToken(**row)

    def delete_token(self, character_id: int) -> bool:
        """Delete token for a character."""
        with db_cursor() as cur:
            cur.execute(
                "DELETE FROM oauth_tokens WHERE character_id = %s",
                (character_id,),
            )
            return cur.rowcount > 0

    def list_tokens(self) -> List[StoredToken]:
        """List all stored tokens."""
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT character_id, character_name, access_token, refresh_token,
                       refresh_token_encrypted, is_encrypted,
                       scopes, expires_at, updated_at, character_owner_hash
                FROM oauth_tokens
                ORDER BY character_name
                """
            )
            tokens = []
            enc = _get_encryption()
            for row in cur.fetchall():
                row = dict(row)
                if row.get("is_encrypted") and row.get("refresh_token_encrypted"):
                    if enc and enc.is_enabled:
                        decrypted = enc.decrypt(bytes(row["refresh_token_encrypted"]))
                        if decrypted:
                            row["refresh_token"] = decrypted
                tokens.append(StoredToken(**row))
            return tokens

    def save_state(self, state: str, auth_state: AuthState):
        """Save PKCE state for OAuth flow."""
        with db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO oauth_states
                    (state, code_verifier, redirect_url, created_at, expires_at)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (state) DO UPDATE SET
                    code_verifier = EXCLUDED.code_verifier,
                    redirect_url = EXCLUDED.redirect_url,
                    created_at = EXCLUDED.created_at,
                    expires_at = EXCLUDED.expires_at
                """,
                (
                    state,
                    auth_state.code_verifier,
                    auth_state.redirect_url,
                    auth_state.created_at,
                    auth_state.expires_at,
                ),
            )

    def get_state(self, state: str) -> Optional[AuthState]:
        """Get PKCE state (only if not expired)."""
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT state, code_verifier, redirect_url, created_at, expires_at
                FROM oauth_states
                WHERE state = %s
                """,
                (state,),
            )
            row = cur.fetchone()
            if row:
                return AuthState(**row)
            return None

    def delete_state(self, state: str) -> bool:
        """Delete PKCE state after use."""
        with db_cursor() as cur:
            cur.execute(
                "DELETE FROM oauth_states WHERE state = %s",
                (state,),
            )
            return cur.rowcount > 0

    def cleanup_expired_states(self) -> int:
        """Remove expired PKCE states. Returns number of deleted rows."""
        with db_cursor() as cur:
            cur.execute(
                "DELETE FROM oauth_states WHERE expires_at < NOW()"
            )
            return cur.rowcount
