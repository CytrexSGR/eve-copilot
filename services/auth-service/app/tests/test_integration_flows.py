"""Integration tests for SaaS subscription lifecycle flows (pure functions only).

Simulates full end-to-end scenarios:
- Free -> Pilot purchase -> Active -> Expiry -> Grace -> Expired
- Corp subscription stacking (corp sub gives all members pilot+ access)
- Payment -> subscription param determination
"""
import pytest
from datetime import datetime, timedelta, timezone

from app.repository.tier_store import (
    resolve_effective_tier,
    tier_includes,
    compute_subscription_status_detail,
    TIER_HIERARCHY,
    ACTIVE_STATUSES,
)
from app.services.payment_processor import (
    determine_subscription_params,
    build_activation_summary,
)


def _sub(tier, status="active", days_left=25):
    """Build a mock subscription dict."""
    return {
        "id": 1,
        "tier": tier,
        "status": status,
        "expires_at": datetime.now(timezone.utc) + timedelta(days=days_left),
        "auto_renew": False,
    }


# ---------------------------------------------------------------------------
# Full Upgrade Flow: Free -> Pilot -> Active -> Expiring -> Grace -> Expired
# ---------------------------------------------------------------------------

class TestFullUpgradeFlow:
    """Simulate a user upgrading from free to pilot and the subscription lifecycle."""

    def test_free_user_has_no_access(self):
        """A user with no subscriptions is free tier."""
        tier = resolve_effective_tier([], [], [])
        assert tier == "free"
        assert not tier_includes(tier, "pilot")

    def test_pilot_purchase_grants_access(self):
        """After purchasing pilot, user gains pilot access but not corporation."""
        tier = resolve_effective_tier([_sub("pilot")], [], [])
        assert tier == "pilot"
        assert tier_includes(tier, "pilot")
        assert tier_includes(tier, "free")
        assert not tier_includes(tier, "corporation")

    def test_active_subscription_detail(self):
        """Active subscription with 20 days remaining shows active phase, no warning."""
        detail = compute_subscription_status_detail(_sub("pilot", days_left=20))
        assert detail["phase"] == "active"
        assert detail["warning"] is None
        assert detail["days_remaining"] >= 19
        assert detail["tier"] == "pilot"

    def test_expiring_soon_warning(self):
        """Subscription within 7-day warning window shows expiring_soon phase."""
        detail = compute_subscription_status_detail(_sub("pilot", days_left=3))
        assert detail["phase"] == "expiring_soon"
        assert detail["warning"] == "subscription_expiring"
        assert detail["days_remaining"] >= 2

    def test_grace_period_still_has_access(self):
        """Grace period subscription still grants tier access."""
        sub = _sub("pilot", status="grace", days_left=-1)
        tier = resolve_effective_tier([sub], [], [])
        assert tier == "pilot"

    def test_grace_period_detail(self):
        """Grace period shows correct phase and warning."""
        detail = compute_subscription_status_detail(
            _sub("pilot", status="grace", days_left=-1)
        )
        assert detail["phase"] == "grace"
        assert detail["warning"] == "subscription_grace"
        assert detail["grace_days_remaining"] >= 0

    def test_expired_loses_access(self):
        """Expired subscription reverts to free tier."""
        sub = _sub("pilot", status="expired", days_left=-10)
        tier = resolve_effective_tier([sub], [], [])
        assert tier == "free"

    def test_expired_detail(self):
        """Expired subscription shows correct phase and warning."""
        detail = compute_subscription_status_detail(
            _sub("pilot", status="expired", days_left=-10)
        )
        assert detail["phase"] == "expired"
        assert detail["warning"] == "subscription_expired"
        assert detail["days_remaining"] == 0

    def test_cancelled_loses_access(self):
        """Cancelled subscription reverts to free tier."""
        sub = _sub("pilot", status="cancelled", days_left=10)
        tier = resolve_effective_tier([sub], [], [])
        assert tier == "free"

    def test_none_subscription_detail(self):
        """No subscription at all returns the 'none' phase."""
        detail = compute_subscription_status_detail(None)
        assert detail["phase"] == "none"
        assert detail["tier"] == "free"
        assert detail["days_remaining"] == 0


# ---------------------------------------------------------------------------
# Corp Stacking Flow: Corp subscription benefits all members
# ---------------------------------------------------------------------------

class TestCorpStackingFlow:
    """Corp/alliance subscriptions stack; highest tier wins."""

    def test_corp_sub_grants_corporation_tier(self):
        """A corp subscription alone grants corporation tier."""
        corp_sub = _sub("corporation")
        tier = resolve_effective_tier([], [corp_sub], [])
        assert tier == "corporation"
        assert tier_includes(tier, "pilot")
        assert tier_includes(tier, "corporation")

    def test_personal_pilot_plus_corp(self):
        """Corp subscription overrides personal pilot subscription."""
        own = _sub("pilot")
        corp = _sub("corporation")
        tier = resolve_effective_tier([own], [corp], [])
        assert tier == "corporation"

    def test_alliance_sub_overrides_all(self):
        """Alliance subscription is highest and overrides corp + personal."""
        own = _sub("pilot")
        corp = _sub("corporation")
        alliance = _sub("alliance")
        tier = resolve_effective_tier([own], [corp], [alliance])
        assert tier == "alliance"
        assert tier_includes(tier, "corporation")
        assert tier_includes(tier, "pilot")

    def test_expired_corp_sub_does_not_stack(self):
        """Expired corp subscription should not count."""
        own = _sub("pilot")
        expired_corp = _sub("corporation", status="expired")
        tier = resolve_effective_tier([own], [expired_corp], [])
        assert tier == "pilot"

    def test_grace_corp_sub_still_stacks(self):
        """Grace-period corp subscription still counts."""
        grace_corp = _sub("corporation", status="grace")
        tier = resolve_effective_tier([], [grace_corp], [])
        assert tier == "corporation"

    def test_multiple_corp_subs_highest_wins(self):
        """If multiple corp subs exist, the highest tier wins."""
        corp_pilot = _sub("pilot")
        corp_corp = _sub("corporation")
        tier = resolve_effective_tier([], [corp_pilot, corp_corp], [])
        assert tier == "corporation"


# ---------------------------------------------------------------------------
# Payment Params Flow: Payment -> subscription creation parameters
# ---------------------------------------------------------------------------

class TestPaymentParamsFlow:
    """Verify payment -> subscription parameter mapping."""

    def test_pilot_subscription_params(self):
        payment = {
            "id": 1, "character_id": 12345,
            "amount": 500_000_000, "reference_code": "PAY-ABC12",
        }
        params = determine_subscription_params(payment, "pilot", 30)
        assert params["tier"] == "pilot"
        assert params["paid_by"] == 12345
        assert params["duration_days"] == 30
        assert params["corporation_id"] is None
        assert params["alliance_id"] is None

    def test_corp_subscription_params(self):
        payment = {
            "id": 2, "character_id": 12345,
            "amount": 5_000_000_000, "reference_code": "PAY-XYZ99",
        }
        params = determine_subscription_params(
            payment, "corporation", 30, corporation_id=98378388,
        )
        assert params["tier"] == "corporation"
        assert params["corporation_id"] == 98378388
        assert params["alliance_id"] is None

    def test_alliance_subscription_params(self):
        payment = {
            "id": 3, "character_id": 12345,
            "amount": 10_000_000_000, "reference_code": "PAY-QWE42",
        }
        params = determine_subscription_params(
            payment, "alliance", 30, alliance_id=99003581,
        )
        assert params["tier"] == "alliance"
        assert params["alliance_id"] == 99003581

    def test_activation_summary_has_correct_status(self):
        summary = build_activation_summary(
            reference_code="PAY-ABC12",
            tier="pilot",
            character_id=12345,
            journal_id=9999,
        )
        assert summary["status"] == "activated"
        assert summary["reference_code"] == "PAY-ABC12"
        assert summary["tier"] == "pilot"
        assert summary["esi_journal_id"] == 9999


# ---------------------------------------------------------------------------
# Active statuses constant verification
# ---------------------------------------------------------------------------

class TestActiveStatuses:
    """Verify which statuses count as active for tier resolution."""

    def test_active_is_active(self):
        assert "active" in ACTIVE_STATUSES

    def test_grace_is_active(self):
        assert "grace" in ACTIVE_STATUSES

    def test_expired_is_not_active(self):
        assert "expired" not in ACTIVE_STATUSES

    def test_cancelled_is_not_active(self):
        assert "cancelled" not in ACTIVE_STATUSES

    def test_pending_is_not_active(self):
        assert "pending" not in ACTIVE_STATUSES
