"""Tests for enriched JWT tokens with account_id + tier."""

import pytest
import jwt as pyjwt
from app.services.jwt_service import JWTService, JWT_ALGORITHM

SECRET = "test-secret-key-32-bytes-minimum!"


class TestCreateEnrichedToken:
    """Enriched JWT includes account_id and tier."""

    def setup_method(self):
        self.svc = JWTService(secret_key=SECRET)

    def test_enriched_token_has_account_id(self):
        token = self.svc.create_enriched_token(
            account_id=42,
            character_id=12345,
            character_name="Cytrex",
            tier="pilot",
        )
        payload = pyjwt.decode(token, SECRET, algorithms=[JWT_ALGORITHM])
        assert payload["account_id"] == 42

    def test_enriched_token_has_tier(self):
        token = self.svc.create_enriched_token(
            account_id=1,
            character_id=12345,
            character_name="Cytrex",
            tier="corporation",
        )
        payload = pyjwt.decode(token, SECRET, algorithms=[JWT_ALGORITHM])
        assert payload["tier"] == "corporation"

    def test_enriched_token_has_corp_id(self):
        token = self.svc.create_enriched_token(
            account_id=1,
            character_id=12345,
            character_name="Cytrex",
            tier="corporation",
            corporation_id=98378388,
        )
        payload = pyjwt.decode(token, SECRET, algorithms=[JWT_ALGORITHM])
        assert payload["corp_id"] == 98378388

    def test_enriched_token_compatible_with_validate(self):
        """validate_token must still work with enriched tokens."""
        token = self.svc.create_enriched_token(
            account_id=1,
            character_id=12345,
            character_name="Cytrex",
            tier="pilot",
        )
        result = self.svc.validate_token(token)
        assert result is not None
        assert result["character_id"] == 12345
        assert result["character_name"] == "Cytrex"

    def test_validate_returns_account_id_and_tier(self):
        token = self.svc.create_enriched_token(
            account_id=42,
            character_id=12345,
            character_name="Cytrex",
            tier="alliance",
        )
        result = self.svc.validate_token(token)
        assert result["account_id"] == 42
        assert result["tier"] == "alliance"

    def test_old_token_without_account_id_still_validates(self):
        """Backward compatibility: old tokens without account_id."""
        token = self.svc.create_token(
            character_id=12345,
            character_name="Cytrex",
        )
        result = self.svc.validate_token(token)
        assert result is not None
        assert result["character_id"] == 12345
        assert result.get("account_id") is None
        assert result.get("tier") is None


class TestGetAccountId:
    """Extract account_id from token."""

    def setup_method(self):
        self.svc = JWTService(secret_key=SECRET)

    def test_get_account_id_enriched(self):
        token = self.svc.create_enriched_token(
            account_id=42,
            character_id=12345,
            character_name="Test",
            tier="pilot",
        )
        assert self.svc.get_account_id(token) == 42

    def test_get_account_id_old_token_returns_none(self):
        token = self.svc.create_token(
            character_id=12345,
            character_name="Test",
        )
        assert self.svc.get_account_id(token) is None

    def test_get_tier_enriched(self):
        token = self.svc.create_enriched_token(
            account_id=1,
            character_id=12345,
            character_name="Test",
            tier="corporation",
        )
        assert self.svc.get_tier(token) == "corporation"

    def test_get_tier_old_token_returns_none(self):
        token = self.svc.create_token(
            character_id=12345,
            character_name="Test",
        )
        assert self.svc.get_tier(token) is None


class TestCharacterIdsClaim:
    """JWT must include character_ids for gateway ownership validation."""

    def test_jwt_contains_character_ids(self):
        """JWT must include all linked character IDs for gateway ownership validation."""
        from app.repository.account_store import build_jwt_claims
        claims = build_jwt_claims(
            account_id=2,
            character_id=1117367444,
            character_name="Cytrex",
            tier="pilot",
            character_ids=[1117367444, 110592475],
        )
        assert claims["character_ids"] == [1117367444, 110592475]

    def test_jwt_character_ids_defaults_to_single(self):
        """When character_ids not provided, fallback to [character_id]."""
        from app.repository.account_store import build_jwt_claims
        claims = build_jwt_claims(
            account_id=2,
            character_id=1117367444,
            character_name="Cytrex",
            tier="pilot",
        )
        assert claims["character_ids"] == [1117367444]

    def test_enriched_token_contains_character_ids(self):
        """Enriched JWT token roundtrip preserves character_ids."""
        svc = JWTService(secret_key=SECRET)
        token = svc.create_enriched_token(
            account_id=2,
            character_id=1117367444,
            character_name="Cytrex",
            tier="pilot",
            character_ids=[1117367444, 110592475],
        )
        payload = pyjwt.decode(token, SECRET, algorithms=[JWT_ALGORITHM])
        assert payload["character_ids"] == [1117367444, 110592475]
