"""Tests for wallet journal ESI data transformation — pure functions only."""
import pytest
from app.services.wallet_journal import (
    filter_donations_since,
    build_journal_url,
)


class TestFilterDonationsSince:
    """Filter wallet journal entries to player donations after a ref ID."""

    def test_filters_donations_only(self):
        entries = [
            {"id": 100, "ref_type": "player_donation", "amount": 500000000, "reason": "PAY-ABC12"},
            {"id": 101, "ref_type": "market_transaction", "amount": 1000, "reason": ""},
            {"id": 102, "ref_type": "player_donation", "amount": -500000000, "reason": "PAY-XYZ99"},
        ]
        result = filter_donations_since(entries, last_ref_id=0)
        assert len(result) == 1
        assert result[0]["id"] == 100

    def test_filters_after_ref_id(self):
        entries = [
            {"id": 98, "ref_type": "player_donation", "amount": 500000000, "reason": "PAY-OLD01"},
            {"id": 100, "ref_type": "player_donation", "amount": 500000000, "reason": "PAY-NEW01"},
        ]
        result = filter_donations_since(entries, last_ref_id=99)
        assert len(result) == 1
        assert result[0]["id"] == 100

    def test_empty_journal(self):
        assert filter_donations_since([], last_ref_id=0) == []

    def test_no_donations(self):
        entries = [
            {"id": 100, "ref_type": "bounty_prizes", "amount": 50000, "reason": ""},
        ]
        assert filter_donations_since(entries, last_ref_id=0) == []

    def test_zero_amount_excluded(self):
        entries = [
            {"id": 100, "ref_type": "player_donation", "amount": 0, "reason": "PAY-ABC12"},
        ]
        assert filter_donations_since(entries, last_ref_id=0) == []


class TestBuildJournalUrl:
    def test_default_url(self):
        url = build_journal_url(2124063958)
        assert url == "https://esi.evetech.net/latest/characters/2124063958/wallet/journal/"

    def test_with_page(self):
        url = build_journal_url(2124063958, page=2)
        assert "page=2" in url
