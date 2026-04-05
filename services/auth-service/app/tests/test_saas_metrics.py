"""Tests for SaaS Prometheus metric definitions."""
import pytest


class TestMetricDefinitions:
    def test_saas_subscriptions_active_exists(self):
        from eve_shared.metrics import saas_subscriptions_active
        assert saas_subscriptions_active is not None

    def test_saas_transitions_counter(self):
        from eve_shared.metrics import saas_subscriptions_transitions
        saas_subscriptions_transitions.labels(from_status="active", to_status="grace").inc()
        # No exception = metric works

    def test_saas_payments_counter(self):
        from eve_shared.metrics import saas_payments_total
        saas_payments_total.labels(status="verified").inc()

    def test_saas_payments_isk_counter(self):
        from eve_shared.metrics import saas_payments_isk
        saas_payments_isk.labels(tier="pilot").inc(500_000_000)

    def test_feature_gate_decisions_counter(self):
        from eve_shared.metrics import saas_feature_gate_decisions
        saas_feature_gate_decisions.labels(decision="allow", required_tier="pilot").inc()

    def test_tier_resolutions_counter(self):
        from eve_shared.metrics import saas_tier_resolutions
        saas_tier_resolutions.labels(source="jwt_claim").inc()

    def test_subscription_status_labels(self):
        from eve_shared.metrics import saas_subscriptions_transitions
        # Verify all expected transitions can be labeled
        for from_s, to_s in [("active", "grace"), ("grace", "expired"), ("expired", "active")]:
            saas_subscriptions_transitions.labels(from_status=from_s, to_status=to_s).inc(0)

    def test_all_tiers_labeled(self):
        from eve_shared.metrics import saas_subscriptions_active
        for tier in ["pilot", "corporation", "alliance", "coalition"]:
            saas_subscriptions_active.labels(tier=tier).set(0)
