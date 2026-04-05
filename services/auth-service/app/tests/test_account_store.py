"""Tests for platform account logic — pure functions only."""

import pytest
from app.repository.account_store import (
    build_jwt_claims,
    should_update_corp_info,
)


class TestBuildJwtClaims:
    """JWT claims builder for enriched tokens."""

    def test_basic_claims(self):
        claims = build_jwt_claims(
            account_id=1,
            character_id=12345,
            character_name="Cytrex",
            tier="pilot",
        )
        assert claims["sub"] == "12345"
        assert claims["name"] == "Cytrex"
        assert claims["account_id"] == 1
        assert claims["tier"] == "pilot"
        assert claims["type"] == "public_session"
        assert "iat" in claims
        assert "exp" in claims

    def test_free_tier_default(self):
        claims = build_jwt_claims(
            account_id=1,
            character_id=12345,
            character_name="Test",
            tier="free",
        )
        assert claims["tier"] == "free"

    def test_corporation_id_included(self):
        claims = build_jwt_claims(
            account_id=1,
            character_id=12345,
            character_name="Test",
            tier="corporation",
            corporation_id=98378388,
        )
        assert claims["corp_id"] == 98378388

    def test_alliance_id_included(self):
        claims = build_jwt_claims(
            account_id=1,
            character_id=12345,
            character_name="Test",
            tier="alliance",
            alliance_id=99003581,
        )
        assert claims["alliance_id"] == 99003581

    def test_no_corp_no_alliance_omitted(self):
        claims = build_jwt_claims(
            account_id=1,
            character_id=12345,
            character_name="Test",
            tier="free",
        )
        assert "corp_id" not in claims
        assert "alliance_id" not in claims

    def test_expiry_default_30_days(self):
        claims = build_jwt_claims(
            account_id=1,
            character_id=12345,
            character_name="Test",
            tier="free",
        )
        delta = claims["exp"] - claims["iat"]
        assert delta.days == 30


class TestShouldUpdateCorpInfo:
    """Decides whether corp/alliance info should be refreshed from ESI."""

    def test_no_existing_data_should_update(self):
        assert should_update_corp_info(None, None) is True

    def test_existing_data_no_update(self):
        assert should_update_corp_info(98378388, 99003581) is False

    def test_corp_but_no_alliance_should_update(self):
        # alliance could have changed
        assert should_update_corp_info(98378388, None) is True

    def test_zero_corp_should_update(self):
        assert should_update_corp_info(0, None) is True
