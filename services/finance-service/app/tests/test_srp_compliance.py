"""Tests for SRP Dogma compliance scoring integration.

Tests the helper functions added to srp_workflow.py:
- _build_compliance_payload: slot-grouped items to flag-based items
- _fetch_compliance_score: async HTTP call to character-service
- _should_auto_approve: dual-score auto-approval logic
"""

import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.srp_workflow import (
    _build_compliance_payload,
    _fetch_compliance_score,
    _should_auto_approve,
    FLAG_RANGES,
)


# ──────────────────── _build_compliance_payload ────────────────────────


class TestBuildCompliancePayload:
    """Tests for converting slot-grouped killmail items to compliance payload."""

    def test_normal_case_all_slots(self):
        """Full fitting with all slot types produces correct flags."""
        killmail_items = {
            "high": [
                {"type_id": 3170, "quantity": 2},
            ],
            "med": [
                {"type_id": 3841, "quantity": 1},
            ],
            "low": [
                {"type_id": 2048, "quantity": 1},
            ],
            "rig": [
                {"type_id": 26082, "quantity": 1},
            ],
            "drones": [
                {"type_id": 2488, "quantity": 3},
            ],
        }

        result = _build_compliance_payload(42, killmail_items)

        assert result["doctrine_id"] == 42
        items = result["killmail_items"]

        # 2 high + 1 med + 1 low + 1 rig + 3 drones = 8
        assert len(items) == 8

        # High slots start at flag 27
        high_items = [i for i in items if 27 <= i["flag"] <= 34]
        assert len(high_items) == 2
        assert high_items[0] == {"type_id": 3170, "flag": 27}
        assert high_items[1] == {"type_id": 3170, "flag": 28}

        # Med slot starts at flag 19
        med_items = [i for i in items if 19 <= i["flag"] <= 26]
        assert len(med_items) == 1
        assert med_items[0] == {"type_id": 3841, "flag": 19}

        # Low slot starts at flag 11
        low_items = [i for i in items if 11 <= i["flag"] <= 18]
        assert len(low_items) == 1
        assert low_items[0] == {"type_id": 2048, "flag": 11}

        # Rig slot starts at flag 92
        rig_items = [i for i in items if 92 <= i["flag"] <= 99]
        assert len(rig_items) == 1
        assert rig_items[0] == {"type_id": 26082, "flag": 92}

        # Drones all use flag 87
        drone_items = [i for i in items if i["flag"] == 87]
        assert len(drone_items) == 3
        for d in drone_items:
            assert d["type_id"] == 2488

    def test_empty_slots(self):
        """Empty killmail items produces empty payload."""
        result = _build_compliance_payload(10, {})
        assert result["doctrine_id"] == 10
        assert result["killmail_items"] == []

    def test_partial_slots(self):
        """Only some slots populated — missing slots produce no items."""
        killmail_items = {
            "high": [{"type_id": 100, "quantity": 1}],
        }
        result = _build_compliance_payload(5, killmail_items)
        assert len(result["killmail_items"]) == 1
        assert result["killmail_items"][0] == {"type_id": 100, "flag": 27}

    def test_drones_expand_quantity(self):
        """Drones with quantity > 1 expand to individual items."""
        killmail_items = {
            "drones": [
                {"type_id": 2488, "quantity": 5},
                {"type_id": 2486, "quantity": 2},
            ],
        }
        result = _build_compliance_payload(1, killmail_items)
        items = result["killmail_items"]
        assert len(items) == 7
        assert all(i["flag"] == 87 for i in items)
        assert sum(1 for i in items if i["type_id"] == 2488) == 5
        assert sum(1 for i in items if i["type_id"] == 2486) == 2

    def test_multiple_module_types_in_same_slot(self):
        """Different module types in same slot get sequential flags."""
        killmail_items = {
            "high": [
                {"type_id": 100, "quantity": 2},
                {"type_id": 200, "quantity": 1},
            ],
        }
        result = _build_compliance_payload(1, killmail_items)
        items = result["killmail_items"]
        assert len(items) == 3
        assert items[0] == {"type_id": 100, "flag": 27}
        assert items[1] == {"type_id": 100, "flag": 28}
        assert items[2] == {"type_id": 200, "flag": 29}

    def test_quantity_defaults_to_one(self):
        """Items without explicit quantity default to 1."""
        killmail_items = {
            "low": [{"type_id": 999}],
        }
        result = _build_compliance_payload(1, killmail_items)
        assert len(result["killmail_items"]) == 1
        assert result["killmail_items"][0] == {"type_id": 999, "flag": 11}

    def test_slot_overflow_stops_at_range_end(self):
        """More items than a slot's flag range get capped."""
        # High has 8 flags (27-34), try to fit 10 items
        killmail_items = {
            "high": [{"type_id": 100, "quantity": 10}],
        }
        result = _build_compliance_payload(1, killmail_items)
        high_items = [i for i in result["killmail_items"] if 27 <= i["flag"] <= 34]
        assert len(high_items) == 8  # capped at range size


# ──────────────────── FLAG_RANGES ──────────────────────────────────────


class TestFlagRanges:
    """Validate FLAG_RANGES constant matches killmail_matcher's FLAG_SLOT_MAP."""

    def test_high_range(self):
        assert list(FLAG_RANGES["high"]) == list(range(27, 35))

    def test_med_range(self):
        assert list(FLAG_RANGES["med"]) == list(range(19, 27))

    def test_low_range(self):
        assert list(FLAG_RANGES["low"]) == list(range(11, 19))

    def test_rig_range(self):
        assert list(FLAG_RANGES["rig"]) == list(range(92, 100))

    def test_each_range_has_8_flags(self):
        for slot, r in FLAG_RANGES.items():
            assert len(list(r)) == 8, f"{slot} should have 8 flags"


# ──────────────────── _fetch_compliance_score ──────────────────────────


class TestFetchComplianceScore:
    """Tests for the async HTTP call to character-service."""

    @pytest.mark.asyncio
    async def test_success_returns_score(self):
        """Successful API call returns the compliance score."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"compliance_score": 0.95}

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.srp_workflow.httpx.AsyncClient", return_value=mock_client):
            score = await _fetch_compliance_score(42, {"high": [{"type_id": 100, "quantity": 1}]})

        assert score == 0.95
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert "/api/doctrines/compliance" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_service_down_returns_none(self):
        """Connection error returns None (graceful fallback)."""
        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.ConnectError("Connection refused")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.srp_workflow.httpx.AsyncClient", return_value=mock_client):
            score = await _fetch_compliance_score(42, {"high": []})

        assert score is None

    @pytest.mark.asyncio
    async def test_http_error_returns_none(self):
        """HTTP 500 returns None (graceful fallback)."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error", request=MagicMock(), response=MagicMock()
        )

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.srp_workflow.httpx.AsyncClient", return_value=mock_client):
            score = await _fetch_compliance_score(42, {})

        assert score is None

    @pytest.mark.asyncio
    async def test_timeout_returns_none(self):
        """Timeout returns None (graceful fallback)."""
        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.TimeoutException("Timeout")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.srp_workflow.httpx.AsyncClient", return_value=mock_client):
            score = await _fetch_compliance_score(42, {})

        assert score is None

    @pytest.mark.asyncio
    async def test_builds_correct_payload(self):
        """Verify the payload sent to character-service is correct."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"compliance_score": 0.88}

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        killmail_items = {
            "high": [{"type_id": 3170, "quantity": 1}],
            "drones": [{"type_id": 2488, "quantity": 2}],
        }

        with patch("app.services.srp_workflow.httpx.AsyncClient", return_value=mock_client):
            await _fetch_compliance_score(99, killmail_items)

        call_kwargs = mock_client.post.call_args[1]
        payload = call_kwargs["json"]
        assert payload["doctrine_id"] == 99
        assert len(payload["killmail_items"]) == 3  # 1 high + 2 drones


# ──────────────────── _should_auto_approve ─────────────────────────────


class TestShouldAutoApprove:
    """Tests for dual-score auto-approval logic."""

    def test_compliance_higher_approves(self):
        """Compliance score higher than threshold approves, even if fuzzy is low."""
        assert _should_auto_approve(0.5, 0.95, 0.90, False) is True

    def test_fuzzy_higher_approves(self):
        """Fuzzy score higher than threshold approves, even if compliance is low."""
        assert _should_auto_approve(0.95, 0.5, 0.90, False) is True

    def test_both_below_threshold_rejects(self):
        """Both scores below threshold results in pending."""
        assert _should_auto_approve(0.5, 0.6, 0.90, False) is False

    def test_review_required_blocks_approval(self):
        """Review flag prevents auto-approval even with high scores."""
        assert _should_auto_approve(0.95, 0.98, 0.90, True) is False

    def test_compliance_none_uses_fuzzy_only(self):
        """When compliance is None, only fuzzy score is used."""
        assert _should_auto_approve(0.95, None, 0.90, False) is True
        assert _should_auto_approve(0.5, None, 0.90, False) is False

    def test_both_zero_and_none_rejects(self):
        """match_score=0 and compliance=None always rejects."""
        assert _should_auto_approve(0.0, None, 0.90, False) is False

    def test_zero_match_with_compliance_approves(self):
        """Zero fuzzy but high compliance still approves."""
        assert _should_auto_approve(0.0, 0.95, 0.90, False) is True

    def test_exact_threshold_approves(self):
        """Score exactly at threshold should approve."""
        assert _should_auto_approve(0.90, None, 0.90, False) is True

    def test_just_below_threshold_rejects(self):
        """Score just below threshold should not approve."""
        assert _should_auto_approve(0.899, None, 0.90, False) is False

    def test_compliance_at_threshold_approves(self):
        """Compliance exactly at threshold approves."""
        assert _should_auto_approve(0.0, 0.90, 0.90, False) is True

    def test_compliance_zero_fuzzy_zero_rejects(self):
        """Both scores at zero rejects (no doctrine match)."""
        assert _should_auto_approve(0.0, 0.0, 0.90, False) is False

    def test_high_threshold_harder_to_approve(self):
        """Higher threshold requires higher scores."""
        assert _should_auto_approve(0.95, 0.95, 0.99, False) is False
        assert _should_auto_approve(0.99, None, 0.99, False) is True
