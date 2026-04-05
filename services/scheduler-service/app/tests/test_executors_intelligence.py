"""Tests for intelligence executor functions."""

import sys
import pytest
from unittest.mock import patch, MagicMock

from app.jobs.executors.intelligence import (
    run_battle_cleanup,
    run_sov_tracker,
    run_fw_tracker,
    run_doctrine_clustering,
)


class TestRunBattleCleanup:
    """Tests for inline SQL battle cleanup."""

    @patch.dict("sys.modules", {"psycopg2": MagicMock()})
    def test_cleanup_succeeds(self):
        """Battle cleanup should mark old battles as ended."""
        mock_pg = sys.modules["psycopg2"]
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.rowcount = 3
        mock_cur.fetchone.return_value = (5,)
        mock_conn.cursor.return_value = mock_cur
        mock_pg.connect.return_value = mock_conn

        result = run_battle_cleanup()
        assert result is True
        assert mock_cur.execute.call_count == 2  # UPDATE + SELECT COUNT
        mock_conn.commit.assert_called_once()

    @patch.dict("sys.modules", {"psycopg2": MagicMock()})
    def test_cleanup_handles_db_error(self):
        """Should return False on database error."""
        mock_pg = sys.modules["psycopg2"]
        mock_pg.connect.side_effect = Exception("Connection refused")
        result = run_battle_cleanup()
        assert result is False

    @patch.dict("sys.modules", {"psycopg2": MagicMock()})
    def test_cleanup_no_stale_battles(self):
        """Should succeed even with 0 battles cleaned."""
        mock_pg = sys.modules["psycopg2"]
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.rowcount = 0
        mock_cur.fetchone.return_value = (10,)
        mock_conn.cursor.return_value = mock_cur
        mock_pg.connect.return_value = mock_conn

        result = run_battle_cleanup()
        assert result is True


class TestRunSovTracker:
    """Tests for sovereignty tracker via war-intel-service API."""

    @patch("app.jobs.executors.intelligence._call_service")
    def test_sov_tracker_success(self, mock_call):
        mock_call.return_value = {
            "status": "completed",
            "details": {
                "total_campaigns": 48,
                "new": 5,
                "updated": 43,
                "deleted": 2,
            },
        }
        result = run_sov_tracker()
        assert result is True
        mock_call.assert_called_once()
        url = mock_call.call_args[0][0]
        assert "/internal/refresh-sov-campaigns" in url

    @patch("app.jobs.executors.intelligence._call_service")
    def test_sov_tracker_failure(self, mock_call):
        mock_call.return_value = {
            "status": "failed",
            "details": {"error": "ESI timeout"},
        }
        result = run_sov_tracker()
        assert result is False

    @patch("app.jobs.executors.intelligence._call_service")
    def test_sov_tracker_connection_error(self, mock_call):
        mock_call.side_effect = Exception("Connection refused")
        result = run_sov_tracker()
        assert result is False


class TestRunFwTracker:
    """Tests for faction warfare tracker via war-intel-service API."""

    @patch("app.jobs.executors.intelligence._call_service")
    def test_fw_tracker_success(self, mock_call):
        mock_call.return_value = {
            "status": "completed",
            "details": {
                "systems_updated": 200,
                "hotspots": 15,
                "snapshots_deleted": 1400,
            },
        }
        result = run_fw_tracker()
        assert result is True
        url = mock_call.call_args[0][0]
        assert "/internal/refresh-fw-status" in url

    @patch("app.jobs.executors.intelligence._call_service")
    def test_fw_tracker_failure(self, mock_call):
        mock_call.return_value = {
            "status": "failed",
            "details": {"error": "ESI error"},
        }
        result = run_fw_tracker()
        assert result is False


class TestRunDoctrineClustering:
    """Tests for doctrine clustering (still subprocess)."""

    @patch("app.jobs.executors._helpers._run_python_script")
    def test_delegates_to_subprocess(self, mock_run):
        """Doctrine clustering should delegate to subprocess."""
        mock_run.return_value = True
        result = run_doctrine_clustering()
        assert result is True
        mock_run.assert_called_once_with("doctrine_clustering.py", timeout=300)

    @patch("app.jobs.executors._helpers._run_python_script")
    def test_subprocess_failure(self, mock_run):
        mock_run.return_value = False
        result = run_doctrine_clustering()
        assert result is False
