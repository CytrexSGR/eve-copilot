"""Tests for payment processing pipeline — pure function tests."""
import pytest
from app.services.payment_processor import (
    determine_subscription_params,
    build_activation_summary,
)


class TestDetermineSubscriptionParams:
    """Map tier + payment to subscription INSERT params."""

    def test_pilot_tier(self):
        payment = {
            "id": 1, "character_id": 12345, "amount": 500000000,
            "reference_code": "PAY-ABC12",
        }
        params = determine_subscription_params(payment, tier="pilot", duration_days=30)
        assert params["tier"] == "pilot"
        assert params["paid_by"] == 12345
        assert params["duration_days"] == 30
        assert params["corporation_id"] is None
        assert params["alliance_id"] is None

    def test_corporation_tier(self):
        payment = {
            "id": 2, "character_id": 12345, "amount": 5000000000,
            "reference_code": "PAY-XYZ99",
        }
        params = determine_subscription_params(
            payment, tier="corporation", duration_days=30,
            corporation_id=98378388,
        )
        assert params["corporation_id"] == 98378388

    def test_alliance_tier(self):
        payment = {
            "id": 3, "character_id": 12345, "amount": 10000000000,
            "reference_code": "PAY-QWE42",
        }
        params = determine_subscription_params(
            payment, tier="alliance", duration_days=30,
            alliance_id=99003581,
        )
        assert params["alliance_id"] == 99003581


class TestBuildActivationSummary:
    def test_summary(self):
        summary = build_activation_summary(
            reference_code="PAY-ABC12",
            tier="pilot",
            character_id=12345,
            journal_id=9999,
        )
        assert summary["reference_code"] == "PAY-ABC12"
        assert summary["tier"] == "pilot"
        assert summary["character_id"] == 12345
        assert summary["esi_journal_id"] == 9999
        assert summary["status"] == "activated"
