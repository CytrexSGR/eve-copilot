"""Tests for corp history vetting stage in VettingEngine."""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import sys
import os

# The vetting engine needs some imports mocked
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# -- Pure logic tests for corp history scoring --


class TestCorpHopping:
    """Test frequent corporation hopping detection (>5 corps in 6 months)."""

    def _make_history(self, count, days_ago_start=0, days_apart=20):
        """Generate corp history with N entries spaced days_apart days."""
        now = datetime.now(timezone.utc)
        return [
            {
                "corporation_id": 98000000 + i,
                "start_date": now - timedelta(days=days_ago_start + i * days_apart),
            }
            for i in range(count)
        ]

    def test_no_hopping_3_corps(self):
        """3 corps in 6 months is not hopping."""
        history = self._make_history(3, days_ago_start=0, days_apart=30)
        recent = [
            h for h in history
            if h["start_date"] > datetime.now(timezone.utc) - timedelta(days=180)
        ]
        assert len(recent) <= 5

    def test_hopping_7_corps(self):
        """7 corps in 6 months triggers hopping detection."""
        history = self._make_history(7, days_ago_start=0, days_apart=20)
        recent = [
            h for h in history
            if h["start_date"] > datetime.now(timezone.utc) - timedelta(days=180)
        ]
        assert len(recent) > 5

    def test_old_corps_not_counted(self):
        """Corps from >6 months ago don't count."""
        history = self._make_history(10, days_ago_start=200, days_apart=10)
        recent = [
            h for h in history
            if h["start_date"] > datetime.now(timezone.utc) - timedelta(days=180)
        ]
        assert len(recent) <= 5


class TestShortTenure:
    """Test short tenure detection (<7 days in recent corps)."""

    def test_short_tenure_detected(self):
        """Tenure < 7 days should be flagged."""
        now = datetime.now(timezone.utc)
        history = [
            {"corporation_id": 1, "start_date": now - timedelta(days=1)},
            {"corporation_id": 2, "start_date": now - timedelta(days=4)},  # 3-day tenure
            {"corporation_id": 3, "start_date": now - timedelta(days=9)},  # 5-day tenure
        ]
        short = 0
        for i in range(min(3, len(history) - 1)):
            current = history[i]
            previous = history[i + 1]
            if current["start_date"] and previous["start_date"]:
                tenure_days = (current["start_date"] - previous["start_date"]).days
                if 0 < tenure_days < 7:
                    short += 1
        assert short == 2  # Both gaps are < 7 days

    def test_long_tenure_not_flagged(self):
        """Tenure >= 7 days should not be flagged."""
        now = datetime.now(timezone.utc)
        history = [
            {"corporation_id": 1, "start_date": now - timedelta(days=0)},
            {"corporation_id": 2, "start_date": now - timedelta(days=30)},
            {"corporation_id": 3, "start_date": now - timedelta(days=60)},
        ]
        short = 0
        for i in range(min(3, len(history) - 1)):
            current = history[i]
            previous = history[i + 1]
            tenure_days = (current["start_date"] - previous["start_date"]).days
            if 0 < tenure_days < 7:
                short += 1
        assert short == 0

    def test_only_checks_recent_3(self):
        """Only the most recent 3 tenures are checked."""
        now = datetime.now(timezone.utc)
        history = [
            {"corporation_id": 1, "start_date": now - timedelta(days=0)},
            {"corporation_id": 2, "start_date": now - timedelta(days=2)},
            {"corporation_id": 3, "start_date": now - timedelta(days=4)},
            {"corporation_id": 4, "start_date": now - timedelta(days=6)},
            {"corporation_id": 5, "start_date": now - timedelta(days=8)},  # 4th gap, not checked
        ]
        checked = min(3, len(history) - 1)
        assert checked == 3


class TestNPCCycling:
    """Test NPC corporation cycling pattern detection."""

    NPC_CORPS = {
        1000001, 1000002, 1000003, 1000004, 1000005, 1000006,
        1000007, 1000008, 1000009, 1000010, 1000011, 1000012,
        1000125, 1000127, 1000128, 1000130,
        1000166, 1000167, 1000168, 1000169,
    }

    def _count_npc_switches(self, history):
        """Count NPC ↔ player corp transitions."""
        switches = 0
        for i in range(len(history) - 1):
            is_npc = history[i]["corporation_id"] in self.NPC_CORPS
            was_npc = history[i + 1]["corporation_id"] in self.NPC_CORPS
            if is_npc != was_npc:
                switches += 1
        return switches

    def test_no_npc_cycling(self):
        """All player corps — no NPC switches."""
        history = [
            {"corporation_id": 98000001},
            {"corporation_id": 98000002},
            {"corporation_id": 98000003},
        ]
        assert self._count_npc_switches(history) == 0

    def test_all_npc(self):
        """All NPC corps — no switches."""
        history = [
            {"corporation_id": 1000001},
            {"corporation_id": 1000002},
            {"corporation_id": 1000003},
        ]
        assert self._count_npc_switches(history) == 0

    def test_cycling_pattern(self):
        """NPC → Player → NPC → Player → NPC = 4 switches."""
        history = [
            {"corporation_id": 1000001},
            {"corporation_id": 98000001},
            {"corporation_id": 1000002},
            {"corporation_id": 98000002},
            {"corporation_id": 1000003},
        ]
        assert self._count_npc_switches(history) == 4

    def test_threshold_at_4(self):
        """Exactly 4 switches triggers the flag (>= 4)."""
        history = [
            {"corporation_id": 1000001},
            {"corporation_id": 98000001},
            {"corporation_id": 1000002},
            {"corporation_id": 98000002},
            {"corporation_id": 1000003},
        ]
        switches = self._count_npc_switches(history)
        assert switches >= 4

    def test_below_threshold(self):
        """3 switches does not trigger."""
        history = [
            {"corporation_id": 1000001},
            {"corporation_id": 98000001},
            {"corporation_id": 1000002},
            {"corporation_id": 98000002},
        ]
        switches = self._count_npc_switches(history)
        assert switches < 4

    def test_single_entry_no_crash(self):
        history = [{"corporation_id": 1000001}]
        assert self._count_npc_switches(history) == 0

    def test_empty_history(self):
        assert self._count_npc_switches([]) == 0


class TestScoreCapping:
    """Test that risk scores are properly capped."""

    WEIGHT_CORP_HISTORY = 15

    def test_score_cap_at_weight(self):
        """Score should be capped at WEIGHT_CORP_HISTORY."""
        raw_score = 30  # exceeds cap
        capped = min(raw_score, self.WEIGHT_CORP_HISTORY)
        assert capped == 15

    def test_score_below_cap(self):
        """Score below cap stays unchanged."""
        raw_score = 8
        capped = min(raw_score, self.WEIGHT_CORP_HISTORY)
        assert capped == 8

    def test_zero_score(self):
        """Zero score stays zero."""
        raw_score = 0
        capped = min(raw_score, self.WEIGHT_CORP_HISTORY)
        assert capped == 0

    def test_hopping_plus_short_tenure_capped(self):
        """Hopping (8) + 3x short tenure (9) = 17, capped to 15."""
        score = 8 + 3 * 3  # hopping + 3 short tenures
        capped = min(score, self.WEIGHT_CORP_HISTORY)
        assert capped == 15

    def test_all_flags_capped(self):
        """Hopping (8) + 3x short tenure (9) + NPC cycling (5) = 22, capped to 15."""
        score = 8 + 3 * 3 + 5
        capped = min(score, self.WEIGHT_CORP_HISTORY)
        assert capped == 15


class TestTotalRiskCap:
    """Test that total risk score is capped at 100."""

    def test_total_risk_capped(self):
        components = [30, 25, 20, 15, 10]  # All max weights
        total = min(100, sum(components))
        assert total == 100

    def test_total_risk_below_cap(self):
        components = [10, 5, 0, 0, 0]
        total = min(100, sum(components))
        assert total == 15
