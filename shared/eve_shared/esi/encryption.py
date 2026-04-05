"""Fernet-based token encryption for ESI refresh tokens.

Encrypts refresh_token before storing in the database and decrypts on read.
Supports key rotation: multiple keys can be configured, with the first key
used for encryption and all keys tried for decryption.

Usage:
    from eve_shared.esi import TokenEncryption

    enc = TokenEncryption()  # reads ESI_SECRET_KEY from env

    # Encrypt
    encrypted = enc.encrypt("refresh_token_value")
    # Store encrypted bytes in DB (BYTEA column)

    # Decrypt
    plaintext = enc.decrypt(encrypted)

Key rotation:
    ESI_SECRET_KEY="current_key,old_key_1,old_key_2"
    - First key is used for all new encryptions
    - All keys are tried for decryption (newest first)
    - Run re-key task to migrate all tokens to current key
"""

import base64
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

ENV_KEY_NAME = "ESI_SECRET_KEY"


def _derive_fernet_key(passphrase: str) -> bytes:
    """Derive a valid Fernet key from a passphrase.

    Fernet requires exactly 32 bytes, URL-safe base64 encoded.
    We use PBKDF2 from the cryptography library for key derivation.
    """
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"eve-copilot-token-encryption",  # Fixed salt (key is the secret)
        iterations=100_000,
    )
    raw_key = kdf.derive(passphrase.encode("utf-8"))
    return base64.urlsafe_b64encode(raw_key)


class TokenEncryption:
    """Fernet encryption for ESI refresh tokens with key rotation support."""

    def __init__(self, secret_key: Optional[str] = None):
        """Initialize with encryption key(s).

        Args:
            secret_key: Comma-separated list of keys. First key is current.
                       If None, reads from ESI_SECRET_KEY env var.
        """
        self._fernets: list = []
        self._initialized = False
        self._raw_key = secret_key

    def _ensure_initialized(self) -> bool:
        """Lazy initialization to avoid import-time failures."""
        if self._initialized:
            return len(self._fernets) > 0

        self._initialized = True
        raw = self._raw_key or os.environ.get(ENV_KEY_NAME, "")
        if not raw:
            logger.warning(
                f"{ENV_KEY_NAME} not set — token encryption disabled. "
                "Refresh tokens will be stored in plaintext."
            )
            return False

        try:
            from cryptography.fernet import Fernet

            keys = [k.strip() for k in raw.split(",") if k.strip()]
            for key_str in keys:
                fernet_key = _derive_fernet_key(key_str)
                self._fernets.append(Fernet(fernet_key))

            logger.info(
                f"Token encryption initialized with {len(self._fernets)} key(s)"
            )
            return True
        except ImportError:
            logger.warning(
                "cryptography package not installed — token encryption disabled"
            )
            return False
        except Exception as e:
            logger.error(f"Failed to initialize token encryption: {e}")
            return False

    @property
    def is_enabled(self) -> bool:
        """Check if encryption is available and configured."""
        return self._ensure_initialized()

    def encrypt(self, plaintext: str) -> Optional[bytes]:
        """Encrypt a token string to bytes.

        Args:
            plaintext: The refresh token to encrypt

        Returns:
            Encrypted bytes suitable for BYTEA storage, or None if encryption disabled
        """
        if not self._ensure_initialized():
            return None

        try:
            return self._fernets[0].encrypt(plaintext.encode("utf-8"))
        except Exception as e:
            logger.error(f"Token encryption failed: {e}")
            return None

    def decrypt(self, ciphertext: bytes) -> Optional[str]:
        """Decrypt token bytes back to plaintext string.

        Tries all configured keys (newest first) for key rotation support.

        Args:
            ciphertext: Encrypted bytes from database

        Returns:
            Decrypted token string, or None if decryption fails
        """
        if not self._ensure_initialized():
            return None

        from cryptography.fernet import InvalidToken

        for i, fernet in enumerate(self._fernets):
            try:
                return fernet.decrypt(ciphertext).decode("utf-8")
            except InvalidToken:
                continue
            except Exception as e:
                logger.warning(f"Decryption error with key {i}: {e}")
                continue

        logger.error("Failed to decrypt token with any configured key")
        return None

    def needs_rekey(self, ciphertext: bytes) -> bool:
        """Check if ciphertext was encrypted with an old key (needs re-encryption).

        Returns True if the token decrypts with a non-primary key.
        """
        if not self._ensure_initialized() or len(self._fernets) < 2:
            return False

        from cryptography.fernet import InvalidToken

        # Try primary key first
        try:
            self._fernets[0].decrypt(ciphertext)
            return False  # Encrypted with current key
        except InvalidToken:
            pass

        # Try old keys
        for fernet in self._fernets[1:]:
            try:
                fernet.decrypt(ciphertext)
                return True  # Encrypted with old key — needs rekey
            except InvalidToken:
                continue

        return False  # Can't decrypt at all

    def rekey(self, ciphertext: bytes) -> Optional[bytes]:
        """Decrypt with any key and re-encrypt with the current key.

        Args:
            ciphertext: Token encrypted with possibly old key

        Returns:
            Token re-encrypted with current key, or None on failure
        """
        plaintext = self.decrypt(ciphertext)
        if plaintext is None:
            return None
        return self.encrypt(plaintext)
