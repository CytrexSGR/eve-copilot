"""Tests for subscription grace period lifecycle."""
import pytest
from datetime import datetime, timedelta, timezone

from app.repository.tier_store import (
    compute_subscription_status_detail,
    ACTIVE_STATUSES,
    TIER_HIERARCHY,
)


def _make_sub(status, expires_at, tier="pilot"):
    return {
        "id": 1, "tier": tier, "status": status,
        "expires_at": expires_at, "auto_renew": True,
        "paid_by": 123, "corporation_id": None, "alliance_id": None,
    }


class TestComputeSubscriptionStatusDetail:
    """Test the pure function that computes detailed status info."""

    def test_active_far_from_expiry(self):
        sub = _make_sub("active", datetime.now(timezone.utc) + timedelta(days=20))
        detail = compute_subscription_status_detail(sub)
        assert detail["phase"] == "active"
        assert detail["days_remaining"] >= 19
        assert detail["warning"] is None

    def test_active_within_7_days(self):
        sub = _make_sub("active", datetime.now(timezone.utc) + timedelta(days=5))
        detail = compute_subscription_status_detail(sub)
        assert detail["phase"] == "expiring_soon"
        assert detail["days_remaining"] <= 5
        assert detail["warning"] == "subscription_expiring"

    def test_active_within_1_day(self):
        sub = _make_sub("active", datetime.now(timezone.utc) + timedelta(hours=12))
        detail = compute_subscription_status_detail(sub)
        assert detail["phase"] == "expiring_soon"
        assert detail["days_remaining"] == 0
        assert detail["warning"] == "subscription_expiring"

    def test_grace_period(self):
        sub = _make_sub("grace", datetime.now(timezone.utc) - timedelta(days=1))
        detail = compute_subscription_status_detail(sub)
        assert detail["phase"] == "grace"
        assert detail["grace_days_remaining"] == 2  # 3 - 1 = 2
        assert detail["warning"] == "subscription_grace"
        assert detail["access_until"] is not None

    def test_grace_last_day(self):
        # 2d20h since expiry → floor(2.83) = 2 full days → 3 - 2 = 1 partial day remaining
        sub = _make_sub("grace", datetime.now(timezone.utc) - timedelta(days=2, hours=20))
        detail = compute_subscription_status_detail(sub)
        assert detail["phase"] == "grace"
        assert detail["grace_days_remaining"] == 1  # partial day still counts

    def test_expired(self):
        sub = _make_sub("expired", datetime.now(timezone.utc) - timedelta(days=10))
        detail = compute_subscription_status_detail(sub)
        assert detail["phase"] == "expired"
        assert detail["days_remaining"] == 0
        assert detail["warning"] == "subscription_expired"

    def test_none_subscription(self):
        detail = compute_subscription_status_detail(None)
        assert detail["phase"] == "none"
        assert detail["tier"] == "free"

    def test_cancelled(self):
        sub = _make_sub("cancelled", datetime.now(timezone.utc) + timedelta(days=10))
        detail = compute_subscription_status_detail(sub)
        assert detail["phase"] == "cancelled"


class TestGracePeriodConstants:
    def test_grace_is_active(self):
        assert "grace" in ACTIVE_STATUSES

    def test_expired_not_active(self):
        assert "expired" not in ACTIVE_STATUSES

    def test_cancelled_not_active(self):
        assert "cancelled" not in ACTIVE_STATUSES

    def test_tier_hierarchy_complete(self):
        assert set(TIER_HIERARCHY.keys()) == {"free", "pilot", "corporation", "alliance", "coalition"}
