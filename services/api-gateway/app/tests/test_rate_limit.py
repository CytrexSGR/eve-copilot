"""Tests for Redis-based tier-aware rate limiting."""
import pytest

from app.middleware.rate_limit import (
    TIER_RATE_LIMITS,
    get_rate_limit_for_tier,
    make_rate_limit_key,
    check_rate_limit_pure,
)


class TestTierRateLimits:
    def test_public_lowest(self):
        assert get_rate_limit_for_tier("public") == 30

    def test_pilot_200(self):
        assert get_rate_limit_for_tier("pilot") == 200

    def test_corporation_500(self):
        assert get_rate_limit_for_tier("corporation") == 500

    def test_alliance_1000(self):
        assert get_rate_limit_for_tier("alliance") == 1000

    def test_unknown_tier_uses_public(self):
        assert get_rate_limit_for_tier("unknown") == 30

    def test_none_tier_uses_public(self):
        assert get_rate_limit_for_tier(None) == 30


class TestRateLimitKey:
    def test_anonymous_key(self):
        key = make_rate_limit_key(None, "1.2.3.4")
        assert key == "rl:ip:1.2.3.4"

    def test_authenticated_key(self):
        key = make_rate_limit_key(123456, "1.2.3.4")
        assert key == "rl:char:123456"

    def test_ip_fallback(self):
        key = make_rate_limit_key(None, None)
        assert key == "rl:ip:unknown"


class TestCheckRateLimitPure:
    def test_under_limit(self):
        allowed, remaining = check_rate_limit_pure(current_count=50, limit=200)
        assert allowed is True
        assert remaining == 149

    def test_at_limit(self):
        allowed, remaining = check_rate_limit_pure(current_count=200, limit=200)
        assert allowed is False
        assert remaining == 0

    def test_over_limit(self):
        allowed, remaining = check_rate_limit_pure(current_count=250, limit=200)
        assert allowed is False
        assert remaining == 0

    def test_zero_count(self):
        allowed, remaining = check_rate_limit_pure(current_count=0, limit=200)
        assert allowed is True
        assert remaining == 199
