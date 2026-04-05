"""Integration tests for feature gate decision flows.

Tests end-to-end scenarios for SaaS access control:
- Free user: which endpoints are accessible vs blocked
- Pilot user: character access granted, finance blocked
- Rate limit key isolation between users
- Tier-map YAML correctness for key endpoints
"""
import pytest

from app.middleware.feature_gate import (
    get_required_tier,
    load_tier_map,
    _matches_pattern,
    TIER_HIERARCHY,
)
from app.middleware.rate_limit import (
    get_rate_limit_for_tier,
    check_rate_limit_pure,
    make_rate_limit_key,
)


@pytest.fixture
def tier_map():
    return load_tier_map()


# ---------------------------------------------------------------------------
# Free User Flow
# ---------------------------------------------------------------------------

class TestFreeUserFlow:
    """Simulate a free-tier user navigating endpoints."""

    def test_free_can_access_battles(self, tier_map):
        """Battles are free-tier (public kill data)."""
        tier = get_required_tier("/api/war/battles", tier_map)
        assert TIER_HIERARCHY.get(tier, 0) <= TIER_HIERARCHY["free"]

    def test_free_can_access_battle_detail(self, tier_map):
        """Battle detail pages are free-tier."""
        tier = get_required_tier("/api/war/battles/12345", tier_map)
        assert TIER_HIERARCHY.get(tier, 0) <= TIER_HIERARCHY["free"]

    def test_free_can_access_killmails(self, tier_map):
        """Killmails are free-tier."""
        tier = get_required_tier("/api/war/killmails", tier_map)
        assert TIER_HIERARCHY.get(tier, 0) <= TIER_HIERARCHY["free"]

    def test_free_can_access_market_prices(self, tier_map):
        """Single market price lookup is free."""
        tier = get_required_tier("/api/market/prices/34", tier_map)
        assert TIER_HIERARCHY.get(tier, 0) <= TIER_HIERARCHY["free"]

    def test_free_blocked_from_character(self, tier_map):
        """Character data requires pilot tier."""
        tier = get_required_tier("/api/character/123/skills", tier_map)
        assert TIER_HIERARCHY.get(tier, 0) > TIER_HIERARCHY["free"]

    def test_free_blocked_from_finance(self, tier_map):
        """Finance endpoints require corporation tier."""
        tier = get_required_tier("/api/finance/wallet", tier_map)
        assert TIER_HIERARCHY.get(tier, 0) > TIER_HIERARCHY["free"]

    def test_free_rate_limit(self):
        """Free users get 60 requests per minute."""
        limit = get_rate_limit_for_tier("free")
        assert limit == 60


# ---------------------------------------------------------------------------
# Pilot User Flow
# ---------------------------------------------------------------------------

class TestPilotUserFlow:
    """Simulate a pilot-tier user navigating endpoints."""

    def test_pilot_can_access_character(self, tier_map):
        """Pilot tier grants access to character endpoints."""
        tier = get_required_tier("/api/character/123/skills", tier_map)
        assert TIER_HIERARCHY.get("pilot", 0) >= TIER_HIERARCHY.get(tier, 0)

    def test_pilot_can_access_fittings(self, tier_map):
        """Pilot tier grants access to fittings."""
        tier = get_required_tier("/api/fittings/custom/123", tier_map)
        assert TIER_HIERARCHY.get("pilot", 0) >= TIER_HIERARCHY.get(tier, 0)

    def test_pilot_can_access_production(self, tier_map):
        """Pilot tier grants access to production."""
        tier = get_required_tier("/api/production/blueprints", tier_map)
        assert TIER_HIERARCHY.get("pilot", 0) >= TIER_HIERARCHY.get(tier, 0)

    def test_pilot_blocked_from_finance(self, tier_map):
        """Finance requires corporation tier, pilot is insufficient."""
        tier = get_required_tier("/api/finance/wallet", tier_map)
        assert TIER_HIERARCHY.get("pilot", 0) < TIER_HIERARCHY.get(tier, 0)

    def test_pilot_blocked_from_hr(self, tier_map):
        """HR requires corporation tier."""
        tier = get_required_tier("/api/hr/vetting", tier_map)
        assert TIER_HIERARCHY.get("pilot", 0) < TIER_HIERARCHY.get(tier, 0)

    def test_pilot_blocked_from_sov(self, tier_map):
        """Sovereignty monitoring requires alliance tier."""
        tier = get_required_tier("/api/sov/status", tier_map)
        assert TIER_HIERARCHY.get("pilot", 0) < TIER_HIERARCHY.get(tier, 0)

    def test_pilot_rate_limit_allows_200(self):
        """Pilot rate limit is 200; 150 requests should pass."""
        allowed, remaining = check_rate_limit_pure(current_count=150, limit=200)
        assert allowed is True
        assert remaining == 49

    def test_pilot_rate_limit_blocks_at_200(self):
        """At exactly 200 requests, pilot is rate-limited."""
        allowed, remaining = check_rate_limit_pure(current_count=200, limit=200)
        assert allowed is False
        assert remaining == 0


# ---------------------------------------------------------------------------
# Corporation User Flow
# ---------------------------------------------------------------------------

class TestCorporationUserFlow:
    """Simulate a corporation-tier user navigating endpoints."""

    def test_corp_can_access_finance(self, tier_map):
        """Corporation tier grants finance access."""
        tier = get_required_tier("/api/finance/wallet", tier_map)
        assert TIER_HIERARCHY.get("corporation", 0) >= TIER_HIERARCHY.get(tier, 0)

    def test_corp_can_access_hr(self, tier_map):
        """Corporation tier grants HR access."""
        tier = get_required_tier("/api/hr/vetting", tier_map)
        assert TIER_HIERARCHY.get("corporation", 0) >= TIER_HIERARCHY.get(tier, 0)

    def test_corp_can_access_character(self, tier_map):
        """Corporation tier includes pilot-level access."""
        tier = get_required_tier("/api/character/123/skills", tier_map)
        assert TIER_HIERARCHY.get("corporation", 0) >= TIER_HIERARCHY.get(tier, 0)

    def test_corp_blocked_from_sov(self, tier_map):
        """Sovereignty requires alliance tier."""
        tier = get_required_tier("/api/sov/status", tier_map)
        assert TIER_HIERARCHY.get("corporation", 0) < TIER_HIERARCHY.get(tier, 0)

    def test_corp_rate_limit(self):
        """Corporation tier gets 500 requests per minute."""
        limit = get_rate_limit_for_tier("corporation")
        assert limit == 500


# ---------------------------------------------------------------------------
# Public Endpoints Flow
# ---------------------------------------------------------------------------

class TestPublicEndpoints:
    """Verify that public endpoints require no authentication."""

    def test_auth_endpoints_are_public(self, tier_map):
        tier = get_required_tier("/api/auth/callback", tier_map)
        assert tier == "public"

    def test_health_is_public(self, tier_map):
        tier = get_required_tier("/health", tier_map)
        assert tier == "public"

    def test_tier_pricing_is_public(self, tier_map):
        tier = get_required_tier("/api/tier/pricing", tier_map)
        assert tier == "public"

    def test_unlisted_defaults_to_pilot(self, tier_map):
        """Endpoints not in tier_map default to pilot tier."""
        tier = get_required_tier("/api/unknown/endpoint", tier_map)
        assert tier == "pilot"


# ---------------------------------------------------------------------------
# Rate Limit Key Isolation
# ---------------------------------------------------------------------------

class TestRateLimitKeyIsolation:
    """Rate limit keys must be unique per user and per IP."""

    def test_different_chars_different_keys(self):
        k1 = make_rate_limit_key(123, "1.1.1.1")
        k2 = make_rate_limit_key(456, "1.1.1.1")
        assert k1 != k2

    def test_same_char_same_key(self):
        k1 = make_rate_limit_key(123, "1.1.1.1")
        k2 = make_rate_limit_key(123, "2.2.2.2")
        assert k1 == k2  # auth users keyed by character, not IP

    def test_same_ip_different_anon_key(self):
        """Anonymous users from different IPs get different keys."""
        k1 = make_rate_limit_key(None, "1.1.1.1")
        k2 = make_rate_limit_key(None, "2.2.2.2")
        assert k1 != k2

    def test_anon_key_format(self):
        key = make_rate_limit_key(None, "10.0.0.1")
        assert key == "rl:ip:10.0.0.1"

    def test_auth_key_format(self):
        key = make_rate_limit_key(12345, "10.0.0.1")
        assert key == "rl:char:12345"


# ---------------------------------------------------------------------------
# Tier Escalation Ladder
# ---------------------------------------------------------------------------

class TestTierEscalationLadder:
    """Verify the full tier hierarchy matches expectations."""

    def test_full_hierarchy_values(self):
        assert TIER_HIERARCHY["public"] == -1
        assert TIER_HIERARCHY["free"] == 0
        assert TIER_HIERARCHY["pilot"] == 1
        assert TIER_HIERARCHY["corporation"] == 2
        assert TIER_HIERARCHY["alliance"] == 3
        assert TIER_HIERARCHY["coalition"] == 4

    def test_each_tier_includes_lower(self):
        """Each tier rank is strictly greater than the one below."""
        tiers = ["public", "free", "pilot", "corporation", "alliance", "coalition"]
        for i in range(1, len(tiers)):
            assert TIER_HIERARCHY[tiers[i]] > TIER_HIERARCHY[tiers[i - 1]]

    def test_rate_limits_increase_with_tier(self):
        """Higher tiers get more generous rate limits."""
        tiers = ["public", "free", "pilot", "corporation", "alliance", "coalition"]
        limits = [get_rate_limit_for_tier(t) for t in tiers]
        for i in range(1, len(limits)):
            assert limits[i] > limits[i - 1], (
                f"{tiers[i]} limit ({limits[i]}) should exceed "
                f"{tiers[i-1]} limit ({limits[i-1]})"
            )
