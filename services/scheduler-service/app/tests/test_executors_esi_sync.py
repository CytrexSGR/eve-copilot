"""Tests for ESI sync executor functions."""

import pytest
from unittest.mock import patch, MagicMock

from app.jobs.executors.esi_sync import (
    run_capability_sync,
    run_skill_snapshot,
    run_killmail_fetcher,
    run_wallet_poll,
    run_everef_importer,
)


class TestRunCapabilitySync:
    """Tests for capability sync via character-service API."""

    @patch("app.jobs.executors.esi_sync._call_service")
    def test_capability_sync_success(self, mock_call):
        mock_call.return_value = {
            "status": "completed",
            "details": {
                "characters": 4,
                "total_synced": 12,
                "errors": 0,
            },
        }
        result = run_capability_sync()
        assert result is True
        url = mock_call.call_args[0][0]
        assert "/internal/sync-capabilities" in url

    @patch("app.jobs.executors.esi_sync._call_service")
    def test_capability_sync_failure(self, mock_call):
        mock_call.return_value = {
            "status": "failed",
            "details": {"error": "auth-service unreachable"},
        }
        result = run_capability_sync()
        assert result is False

    @patch("app.jobs.executors.esi_sync._call_service")
    def test_capability_sync_connection_error(self, mock_call):
        mock_call.side_effect = Exception("Connection refused")
        result = run_capability_sync()
        assert result is False


class TestRunSkillSnapshot:
    """Tests for skill snapshot (superseded by character_sync)."""

    @patch("app.jobs.executors.esi_sync.run_character_sync")
    def test_delegates_to_character_sync(self, mock_sync):
        mock_sync.return_value = True
        result = run_skill_snapshot()
        assert result is True
        mock_sync.assert_called_once()

    @patch("app.jobs.executors.esi_sync.run_character_sync")
    def test_delegates_failure(self, mock_sync):
        mock_sync.return_value = False
        result = run_skill_snapshot()
        assert result is False


class TestRunKillmailFetcher:
    """Tests for killmail fetcher via war-intel-service API."""

    @patch("app.jobs.executors.esi_sync._call_service")
    def test_killmail_fetcher_success(self, mock_call):
        mock_call.return_value = {
            "status": "completed",
            "details": {
                "imported": 5432,
                "skipped": 12000,
                "items": 28000,
            },
        }
        result = run_killmail_fetcher()
        assert result is True
        url = mock_call.call_args[0][0]
        assert "/internal/fetch-killmails" in url
        # Verify 600s timeout for large downloads
        assert mock_call.call_args[1].get("timeout") == 600

    @patch("app.jobs.executors.esi_sync._call_service")
    def test_killmail_fetcher_failure(self, mock_call):
        mock_call.return_value = {
            "status": "failed",
            "details": {"error": "download failed"},
        }
        result = run_killmail_fetcher()
        assert result is False


class TestRunWalletPoll:
    """Tests for wallet poll (deprecated)."""

    def test_returns_true_noop(self):
        """Deprecated job should return True (no-op)."""
        result = run_wallet_poll()
        assert result is True


class TestRunEverefImporter:
    """Tests for EVE Ref importer via war-intel-service API."""

    @patch("app.jobs.executors.esi_sync._call_service")
    def test_everef_importer_success(self, mock_call):
        mock_call.return_value = {
            "status": "completed",
            "details": {
                "imported": 8000,
                "skipped": 40000,
                "items": 65000,
            },
        }
        result = run_everef_importer()
        assert result is True
        url = mock_call.call_args[0][0]
        assert "/internal/import-everef" in url
        # Verify 900s timeout
        assert mock_call.call_args[1].get("timeout") == 900

    @patch("app.jobs.executors.esi_sync._call_service")
    def test_everef_importer_failure(self, mock_call):
        mock_call.side_effect = Exception("Connection refused")
        result = run_everef_importer()
        assert result is False
