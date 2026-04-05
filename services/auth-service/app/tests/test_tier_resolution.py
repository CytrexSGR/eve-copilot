"""Tests for tier resolution logic — pure function tests, no DB."""
import pytest
from datetime import datetime, timezone, timedelta

from app.repository.tier_store import (
    resolve_effective_tier,
    TIER_HIERARCHY,
    tier_includes,
)


class TestTierHierarchy:
    def test_hierarchy_order(self):
        assert TIER_HIERARCHY == {
            "free": 0, "pilot": 1, "corporation": 2,
            "alliance": 3, "coalition": 4,
        }

    def test_tier_includes_same(self):
        assert tier_includes("pilot", "pilot") is True

    def test_tier_includes_higher_grants_lower(self):
        assert tier_includes("corporation", "pilot") is True
        assert tier_includes("alliance", "corporation") is True
        assert tier_includes("alliance", "pilot") is True
        assert tier_includes("coalition", "free") is True

    def test_tier_includes_lower_denies_higher(self):
        assert tier_includes("pilot", "corporation") is False
        assert tier_includes("free", "pilot") is False
        assert tier_includes("corporation", "alliance") is False

    def test_tier_includes_free(self):
        assert tier_includes("free", "free") is True
        assert tier_includes("free", "pilot") is False

    def test_tier_includes_unknown(self):
        assert tier_includes("unknown", "pilot") is False
        assert tier_includes("pilot", "unknown") is True  # unknown = 0


class TestResolveEffectiveTier:
    """Test the pure resolve logic with mock subscription data."""

    def _make_sub(self, tier, status="active"):
        future = datetime.now(timezone.utc) + timedelta(days=15)
        return {"tier": tier, "status": status, "expires_at": future}

    def test_no_subscriptions_returns_free(self):
        result = resolve_effective_tier(
            own_subs=[], corp_subs=[], alliance_subs=[]
        )
        assert result == "free"

    def test_own_pilot_sub(self):
        result = resolve_effective_tier(
            own_subs=[self._make_sub("pilot")],
            corp_subs=[], alliance_subs=[],
        )
        assert result == "pilot"

    def test_corp_sub_overrides_pilot(self):
        result = resolve_effective_tier(
            own_subs=[self._make_sub("pilot")],
            corp_subs=[self._make_sub("corporation")],
            alliance_subs=[],
        )
        assert result == "corporation"

    def test_alliance_sub_overrides_all(self):
        result = resolve_effective_tier(
            own_subs=[self._make_sub("pilot")],
            corp_subs=[self._make_sub("corporation")],
            alliance_subs=[self._make_sub("alliance")],
        )
        assert result == "alliance"

    def test_expired_sub_ignored(self):
        expired = self._make_sub("alliance")
        expired["status"] = "expired"
        result = resolve_effective_tier(
            own_subs=[expired], corp_subs=[], alliance_subs=[]
        )
        assert result == "free"

    def test_grace_period_still_active(self):
        grace = self._make_sub("corporation")
        grace["status"] = "grace"
        result = resolve_effective_tier(
            own_subs=[], corp_subs=[grace], alliance_subs=[]
        )
        assert result == "corporation"

    def test_cancelled_sub_ignored(self):
        cancelled = self._make_sub("alliance")
        cancelled["status"] = "cancelled"
        result = resolve_effective_tier(
            own_subs=[], corp_subs=[], alliance_subs=[cancelled]
        )
        assert result == "free"

    def test_multiple_own_subs_highest_wins(self):
        result = resolve_effective_tier(
            own_subs=[
                self._make_sub("pilot"),
                self._make_sub("corporation"),
            ],
            corp_subs=[], alliance_subs=[],
        )
        assert result == "corporation"

    def test_only_corp_sub_no_own(self):
        """Corp subscription alone grants corporation tier."""
        result = resolve_effective_tier(
            own_subs=[],
            corp_subs=[self._make_sub("corporation")],
            alliance_subs=[],
        )
        assert result == "corporation"

    def test_only_alliance_sub_no_own(self):
        """Alliance subscription alone grants alliance tier."""
        result = resolve_effective_tier(
            own_subs=[],
            corp_subs=[],
            alliance_subs=[self._make_sub("alliance")],
        )
        assert result == "alliance"

    def test_coalition_tier(self):
        result = resolve_effective_tier(
            own_subs=[],
            corp_subs=[],
            alliance_subs=[self._make_sub("coalition")],
        )
        assert result == "coalition"

    def test_mixed_statuses(self):
        """Only active/grace count, others ignored."""
        result = resolve_effective_tier(
            own_subs=[
                self._make_sub("pilot", status="cancelled"),
                self._make_sub("corporation", status="expired"),
            ],
            corp_subs=[self._make_sub("corporation", status="active")],
            alliance_subs=[],
        )
        assert result == "corporation"
