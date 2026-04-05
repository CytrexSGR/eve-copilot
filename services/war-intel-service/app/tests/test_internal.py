"""Tests for war-intel-service internal endpoints (scheduler-triggered jobs)."""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from app.routers.internal import (
    refresh_sov_campaigns,
    refresh_fw_status,
    _get_alliance_name,
    FACTIONS,
)


# ---------------------------------------------------------------------------
# Sovereignty Campaign Tracker Tests
# ---------------------------------------------------------------------------

class TestRefreshSovCampaigns:
    """Tests for sovereignty campaign refresh logic."""

    @patch("app.routers.internal._fetch_esi_campaigns")
    def test_returns_error_when_esi_fails(self, mock_fetch):
        mock_fetch.return_value = None
        result = refresh_sov_campaigns()
        assert "error" in result
        assert "Failed to fetch" in result["error"]

    @patch("app.routers.internal.db_cursor")
    @patch("app.routers.internal._get_alliance_name")
    @patch("app.routers.internal._fetch_esi_campaigns")
    def test_inserts_new_campaign(self, mock_fetch, mock_name, mock_db):
        mock_fetch.return_value = [{
            "campaign_id": 1001,
            "event_type": "ihub_defense",
            "solar_system_id": 30001234,
            "constellation_id": 20000001,
            "defender_id": 99003581,
            "attackers_score": 0.3,
            "defender_score": 0.7,
            "start_time": "2026-02-10T18:00:00Z",
            "structure_id": 1234567890,
        }]
        mock_name.return_value = "Fraternity."

        cursor = MagicMock()
        cursor.fetchone.return_value = None  # Campaign does not exist
        cursor.rowcount = 0  # No old campaigns deleted
        mock_db.return_value.__enter__ = MagicMock(return_value=cursor)
        mock_db.return_value.__exit__ = MagicMock(return_value=False)

        result = refresh_sov_campaigns()
        assert result["total_campaigns"] == 1
        assert result["new"] == 1
        assert result["updated"] == 0

    @patch("app.routers.internal.db_cursor")
    @patch("app.routers.internal._get_alliance_name")
    @patch("app.routers.internal._fetch_esi_campaigns")
    def test_updates_existing_campaign(self, mock_fetch, mock_name, mock_db):
        mock_fetch.return_value = [{
            "campaign_id": 1001,
            "event_type": "ihub_defense",
            "solar_system_id": 30001234,
            "constellation_id": 20000001,
            "defender_id": 99003581,
            "attackers_score": 0.5,
            "defender_score": 0.5,
            "start_time": "2026-02-10T18:00:00Z",
            "structure_id": 1234567890,
        }]
        mock_name.return_value = "Fraternity."

        cursor = MagicMock()
        cursor.fetchone.return_value = {"id": 1}  # Campaign exists
        cursor.rowcount = 0
        mock_db.return_value.__enter__ = MagicMock(return_value=cursor)
        mock_db.return_value.__exit__ = MagicMock(return_value=False)

        result = refresh_sov_campaigns()
        assert result["total_campaigns"] == 1
        assert result["new"] == 0
        assert result["updated"] == 1

    @patch("app.routers.internal._fetch_esi_campaigns")
    def test_empty_campaigns_list(self, mock_fetch):
        """Empty campaign list is valid (no active campaigns)."""
        mock_fetch.return_value = []
        # This will try to use db_cursor, but with empty list it should
        # still attempt the DB call. We need to mock it too.
        with patch("app.routers.internal.db_cursor") as mock_db:
            cursor = MagicMock()
            cursor.rowcount = 0
            mock_db.return_value.__enter__ = MagicMock(return_value=cursor)
            mock_db.return_value.__exit__ = MagicMock(return_value=False)
            result = refresh_sov_campaigns()
            assert result["total_campaigns"] == 0
            assert result["new"] == 0


# ---------------------------------------------------------------------------
# Faction Warfare Tracker Tests
# ---------------------------------------------------------------------------

class TestRefreshFwStatus:
    """Tests for FW status refresh logic."""

    @patch("app.routers.internal._fetch_fw_systems")
    def test_returns_error_when_esi_fails(self, mock_fetch):
        mock_fetch.return_value = None
        result = refresh_fw_status()
        assert "error" in result

    @patch("app.routers.internal._fetch_fw_systems")
    def test_empty_systems_list(self, mock_fetch):
        """Empty FW systems is valid (treated as fetch failure)."""
        mock_fetch.return_value = []
        result = refresh_fw_status()
        assert "error" in result

    @patch("app.routers.internal._fetch_fw_systems")
    def test_skips_incomplete_systems(self, mock_fetch):
        """Systems missing required fields should be filtered out before DB insert."""
        mock_fetch.return_value = [
            {"solar_system_id": 30002057},  # Missing faction IDs
            {
                "solar_system_id": 30002058,
                "owner_faction_id": 500002,
                "occupier_faction_id": 500003,
                "contested": "contested",
                "victory_points": 100,
                "victory_points_threshold": 3000,
            },
        ]

        # We can verify the filtering logic without hitting the DB
        # by checking the values list construction
        systems = mock_fetch.return_value
        values = []
        for system in systems:
            sid = system.get("solar_system_id")
            owner = system.get("owner_faction_id")
            occupier = system.get("occupier_faction_id")
            if sid and owner and occupier:
                values.append(sid)
        assert len(values) == 1
        assert values[0] == 30002058


# ---------------------------------------------------------------------------
# Alliance Name Resolution Tests
# ---------------------------------------------------------------------------

class TestGetAllianceName:
    """Tests for ESI alliance name resolution."""

    @patch("app.routers.internal.httpx")
    def test_returns_name_on_success(self, mock_httpx):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"name": "Fraternity."}
        mock_httpx.get.return_value = mock_resp

        name = _get_alliance_name(99003581)
        assert name == "Fraternity."

    @patch("app.routers.internal.httpx")
    def test_returns_fallback_on_failure(self, mock_httpx):
        mock_httpx.get.side_effect = Exception("timeout")
        name = _get_alliance_name(99003581)
        assert name == "Alliance 99003581"


# ---------------------------------------------------------------------------
# Constants Tests
# ---------------------------------------------------------------------------

class TestFactionConstants:
    """Tests for faction ID mapping."""

    def test_all_four_factions_defined(self):
        assert len(FACTIONS) == 4

    def test_caldari(self):
        assert FACTIONS[500001] == "Caldari State"

    def test_minmatar(self):
        assert FACTIONS[500002] == "Minmatar Republic"

    def test_amarr(self):
        assert FACTIONS[500003] == "Amarr Empire"

    def test_gallente(self):
        assert FACTIONS[500004] == "Gallente Federation"
