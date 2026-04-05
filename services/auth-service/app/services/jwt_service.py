"""JWT service for public frontend sessions."""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

import jwt

from app.config import settings

logger = logging.getLogger(__name__)

# JWT settings
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_DAYS = 30


class JWTService:
    """Service for creating and validating JWT tokens."""

    def __init__(self, secret_key: Optional[str] = None):
        self.secret_key = secret_key or settings.jwt_secret_key
        if not self.secret_key:
            raise ValueError("JWT secret key not configured")

    def create_token(
        self,
        character_id: int,
        character_name: str,
        expires_days: int = JWT_EXPIRY_DAYS
    ) -> str:
        """Create JWT token for public session."""
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(character_id),
            "name": character_name,
            "iat": now,
            "exp": now + timedelta(days=expires_days),
            "type": "public_session"
        }
        return jwt.encode(payload, self.secret_key, algorithm=JWT_ALGORITHM)

    def create_enriched_token(
        self,
        account_id: int,
        character_id: int,
        character_name: str,
        tier: str,
        corporation_id: Optional[int] = None,
        alliance_id: Optional[int] = None,
        active_modules: Optional[list] = None,
        org_plan: Optional[dict] = None,
        character_ids: Optional[list] = None,
        expires_days: int = JWT_EXPIRY_DAYS,
    ) -> str:
        """Create enriched JWT with account_id + tier + modules for SaaS."""
        from app.repository.account_store import build_jwt_claims
        claims = build_jwt_claims(
            account_id=account_id,
            character_id=character_id,
            character_name=character_name,
            tier=tier,
            corporation_id=corporation_id,
            alliance_id=alliance_id,
            active_modules=active_modules,
            org_plan=org_plan,
            character_ids=character_ids,
        )
        return jwt.encode(claims, self.secret_key, algorithm=JWT_ALGORITHM)

    def validate_token(self, token: str) -> Optional[dict]:
        """Validate JWT token and return payload."""
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[JWT_ALGORITHM]
            )
            if payload.get("type") != "public_session":
                logger.warning("Invalid token type")
                return None
            result = {
                "character_id": int(payload["sub"]),
                "character_name": payload["name"],
                "expires_at": datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
            }
            # Enriched fields (present in new tokens, absent in old)
            if "account_id" in payload:
                result["account_id"] = payload["account_id"]
            if "tier" in payload:
                result["tier"] = payload["tier"]
            if "active_modules" in payload:
                result["active_modules"] = payload["active_modules"]
            if "org_plan" in payload:
                result["org_plan"] = payload["org_plan"]
            if "character_ids" in payload:
                result["character_ids"] = payload["character_ids"]
            return result
        except jwt.ExpiredSignatureError:
            logger.debug("Token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None

    def get_character_id(self, token: str) -> Optional[int]:
        """Extract character ID from token."""
        payload = self.validate_token(token)
        return payload["character_id"] if payload else None

    def get_account_id(self, token: str) -> Optional[int]:
        """Extract account ID from token (None for old tokens)."""
        payload = self.validate_token(token)
        return payload.get("account_id") if payload else None

    def get_tier(self, token: str) -> Optional[str]:
        """Extract tier from token (None for old tokens)."""
        payload = self.validate_token(token)
        return payload.get("tier") if payload else None
