"""Tests for Character Auto-Sync job."""
import pytest
from unittest.mock import MagicMock, Mock
from jobs.character_auto_sync import CharacterAutoSync


class TestCharacterAutoSync:
    """Test character auto-sync job."""

    @pytest.fixture
    def mock_repo(self):
        return MagicMock()

    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    @pytest.fixture
    def syncer(self, mock_repo, mock_db):
        return CharacterAutoSync(repository=mock_repo, db_pool=mock_db)

    def test_get_active_characters(self, syncer, mock_db):
        """Test fetching active characters."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [(12345,), (67890,)]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)
        mock_db.get_connection.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_db.get_connection.return_value.__exit__ = Mock(return_value=False)

        result = syncer.get_active_characters()

        assert result == [12345, 67890]

    def test_get_active_characters_empty(self, syncer, mock_db):
        """Test fetching active characters when none exist."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)
        mock_db.get_connection.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_db.get_connection.return_value.__exit__ = Mock(return_value=False)

        result = syncer.get_active_characters()

        assert result == []

    def test_get_active_characters_db_error(self, syncer, mock_db):
        """Test fetching active characters with database error."""
        mock_db.get_connection.return_value.__enter__ = Mock(
            side_effect=Exception("DB connection failed")
        )

        result = syncer.get_active_characters()

        assert result == []

    def test_sync_all_success(self, syncer, mock_repo, mock_db):
        """Test sync with all characters succeeding."""
        # Setup: 2 active characters
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [(12345,), (67890,)]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)
        mock_db.get_connection.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_db.get_connection.return_value.__exit__ = Mock(return_value=False)

        mock_repo.sync_character.return_value = {
            "wallet": True,
            "skills": True,
            "assets": True
        }

        result = syncer.sync()

        assert result["success"] is True
        assert result["synced"] == 2
        assert result["failed"] == 0
        assert len(result["characters"]) == 2

    def test_sync_with_partial_failures(self, syncer, mock_repo, mock_db):
        """Test sync with some data types failing."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [(12345,)]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)
        mock_db.get_connection.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_db.get_connection.return_value.__exit__ = Mock(return_value=False)

        # One data type fails (wallet = False)
        mock_repo.sync_character.return_value = {
            "wallet": False,
            "skills": True,
            "assets": True
        }

        result = syncer.sync()

        assert result["synced"] == 0
        assert result["failed"] == 1

    def test_sync_with_character_exceptions(self, syncer, mock_repo, mock_db):
        """Test sync with some characters throwing exceptions."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [(12345,), (67890,)]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)
        mock_db.get_connection.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_db.get_connection.return_value.__exit__ = Mock(return_value=False)

        mock_repo.sync_character.side_effect = [
            {"wallet": True, "skills": True, "assets": True},
            Exception("Token expired")
        ]

        result = syncer.sync()

        assert result["synced"] == 1
        assert result["failed"] == 1
        # Check that error is captured
        assert "error" in result["characters"][1]
        assert "Token expired" in result["characters"][1]["error"]

    def test_sync_logs_duration(self, syncer, mock_repo, mock_db):
        """Test that sync includes duration."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)
        mock_db.get_connection.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_db.get_connection.return_value.__exit__ = Mock(return_value=False)

        result = syncer.sync()

        assert "duration_ms" in result
        assert result["duration_ms"] >= 0

    def test_sync_includes_timestamp(self, syncer, mock_repo, mock_db):
        """Test that sync includes timestamp."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)
        mock_db.get_connection.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_db.get_connection.return_value.__exit__ = Mock(return_value=False)

        result = syncer.sync()

        assert "timestamp" in result
        # Verify it's a valid ISO format timestamp
        assert "T" in result["timestamp"]

    def test_sync_no_characters(self, syncer, mock_repo, mock_db):
        """Test sync with no active characters."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)
        mock_db.get_connection.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_db.get_connection.return_value.__exit__ = Mock(return_value=False)

        result = syncer.sync()

        assert result["success"] is True
        assert result["synced"] == 0
        assert result["failed"] == 0
        assert result["characters"] == []
        # Repo should not be called when no characters
        mock_repo.sync_character.assert_not_called()
