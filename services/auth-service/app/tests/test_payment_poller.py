"""Tests for wallet journal payment matching — pure function tests."""
import pytest
from app.services.payment_poller import (
    extract_reference_code,
    is_player_donation,
    match_payment,
)


class TestExtractReferenceCode:
    def test_standard_format(self):
        assert extract_reference_code("PAY-A1B2C") == "PAY-A1B2C"

    def test_in_longer_text(self):
        assert extract_reference_code("Payment for EVE Copilot PAY-X9Y8Z") == "PAY-X9Y8Z"

    def test_case_insensitive(self):
        assert extract_reference_code("pay-abc12") == "PAY-ABC12"

    def test_no_code(self):
        assert extract_reference_code("random ISK transfer") is None

    def test_empty_string(self):
        assert extract_reference_code("") is None

    def test_none_input(self):
        assert extract_reference_code(None) is None

    def test_code_at_start(self):
        assert extract_reference_code("PAY-12345 subscription") == "PAY-12345"

    def test_code_at_end(self):
        assert extract_reference_code("subscription PAY-ABCDE") == "PAY-ABCDE"

    def test_multiple_codes_returns_first(self):
        assert extract_reference_code("PAY-11111 and PAY-22222") == "PAY-11111"


class TestIsPlayerDonation:
    def test_player_donation(self):
        assert is_player_donation({"ref_type": "player_donation", "amount": 500000000}) is True

    def test_negative_amount_ignored(self):
        assert is_player_donation({"ref_type": "player_donation", "amount": -500000000}) is False

    def test_other_ref_type(self):
        assert is_player_donation({"ref_type": "market_transaction", "amount": 500000000}) is False

    def test_zero_amount(self):
        assert is_player_donation({"ref_type": "player_donation", "amount": 0}) is False

    def test_missing_ref_type(self):
        assert is_player_donation({"amount": 500000000}) is False

    def test_missing_amount(self):
        assert is_player_donation({"ref_type": "player_donation"}) is False


class TestMatchPayment:
    def _pending(self, code="PAY-ABC12", amount=500000000, char_id=12345):
        return {"reference_code": code, "amount": amount, "character_id": char_id}

    def _entry(self, amount=500000000, reason="PAY-ABC12", journal_id=9999, sender=12345):
        return {"id": journal_id, "amount": amount, "reason": reason, "first_party_id": sender}

    def test_match_found(self):
        match = match_payment(self._entry(), [self._pending()])
        assert match is not None
        assert match["reference_code"] == "PAY-ABC12"

    def test_no_match_wrong_code(self):
        entry = self._entry(reason="PAY-WRONG")
        assert match_payment(entry, [self._pending()]) is None

    def test_overpayment_accepted(self):
        entry = self._entry(amount=600000000)
        match = match_payment(entry, [self._pending()])
        assert match is not None

    def test_underpayment_rejected(self):
        entry = self._entry(amount=400000000)
        assert match_payment(entry, [self._pending()]) is None

    def test_code_in_reason_text(self):
        entry = self._entry(reason="Sub payment PAY-ABC12 for corp")
        match = match_payment(entry, [self._pending()])
        assert match is not None

    def test_no_reason(self):
        entry = self._entry(reason=None)
        assert match_payment(entry, [self._pending()]) is None

    def test_empty_pending_list(self):
        assert match_payment(self._entry(), []) is None

    def test_multiple_pending_first_match(self):
        pending = [
            self._pending(code="PAY-OTHER", amount=1000000000),
            self._pending(code="PAY-ABC12", amount=500000000),
        ]
        match = match_payment(self._entry(), pending)
        assert match is not None
        assert match["reference_code"] == "PAY-ABC12"

    def test_exact_amount_matches(self):
        entry = self._entry(amount=500000000)
        match = match_payment(entry, [self._pending(amount=500000000)])
        assert match is not None
