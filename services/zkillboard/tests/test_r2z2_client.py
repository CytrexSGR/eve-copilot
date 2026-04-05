"""Unit tests for R2Z2 client."""

import pytest
from unittest.mock import MagicMock
from services.zkillboard.r2z2_client import (
    R2Z2Client,
    R2Z2Package,
    R2Z2RateLimited,
    R2Z2Blocked,
)


class TestR2Z2Package:
    """Tests for R2Z2Package dataclass."""

    def test_package_creation(self):
        pkg = R2Z2Package(
            killmail_id=123,
            hash="abc",
            zkb={"totalValue": 100.0},
            killmail={"killmail_id": 123},
            sequence_id=1,
            uploaded_at=1000,
        )
        assert pkg.killmail_id == 123
        assert pkg.hash == "abc"
        assert pkg.sequence_id == 1

    def test_package_always_has_killmail(self):
        """R2Z2 always includes killmail data (unlike RedisQ)."""
        pkg = R2Z2Package(
            killmail_id=456,
            hash="def",
            zkb={},
            killmail={"killmail_id": 456, "solar_system_id": 30000142},
            sequence_id=2,
            uploaded_at=2000,
        )
        assert pkg.killmail is not None
        assert pkg.killmail["solar_system_id"] == 30000142


class TestToProcessFormat:
    """Tests for converting R2Z2 packages to process_live_kill format."""

    def test_format_includes_killmail(self):
        """R2Z2 format should include inline killmail (no ESI fetch needed)."""
        client = R2Z2Client.__new__(R2Z2Client)
        pkg = R2Z2Package(
            killmail_id=789,
            hash="ghi",
            zkb={"totalValue": 500000.0, "npc": False, "hash": "ghi"},
            killmail={"killmail_id": 789, "solar_system_id": 30000142},
            sequence_id=100,
            uploaded_at=3000,
        )
        result = client.to_process_format(pkg)
        assert result["killmail_id"] == 789
        assert result["zkb"]["totalValue"] == 500000.0
        assert result["killmail"]["solar_system_id"] == 30000142

    def test_format_matches_process_live_kill_contract(self):
        """Output must have killmail_id, zkb, and killmail keys."""
        client = R2Z2Client.__new__(R2Z2Client)
        pkg = R2Z2Package(
            killmail_id=1,
            hash="x",
            zkb={"hash": "x"},
            killmail={"killmail_id": 1},
            sequence_id=1,
            uploaded_at=0,
        )
        result = client.to_process_format(pkg)
        assert "killmail_id" in result
        assert "zkb" in result
        assert "killmail" in result

    def test_format_injects_hash_into_zkb(self):
        """If zkb lacks hash, inject it from package.hash (prevents silent drops)."""
        client = R2Z2Client.__new__(R2Z2Client)
        pkg = R2Z2Package(
            killmail_id=42,
            hash="top_level_hash",
            zkb={"totalValue": 100.0},  # No "hash" key!
            killmail={"killmail_id": 42},
            sequence_id=5,
            uploaded_at=0,
        )
        result = client.to_process_format(pkg)
        assert result["zkb"]["hash"] == "top_level_hash"

    def test_format_preserves_existing_zkb_hash(self):
        """If zkb already has hash, don't overwrite it."""
        client = R2Z2Client.__new__(R2Z2Client)
        pkg = R2Z2Package(
            killmail_id=42,
            hash="top_level",
            zkb={"hash": "zkb_level", "totalValue": 100.0},
            killmail={"killmail_id": 42},
            sequence_id=5,
            uploaded_at=0,
        )
        result = client.to_process_format(pkg)
        assert result["zkb"]["hash"] == "zkb_level"


class TestR2Z2Exceptions:
    """Tests for R2Z2 exception types."""

    def test_rate_limited_default_retry(self):
        exc = R2Z2RateLimited()
        assert exc.retry_after == 10

    def test_rate_limited_custom_retry(self):
        exc = R2Z2RateLimited(retry_after=30)
        assert exc.retry_after == 30

    def test_blocked_exception(self):
        exc = R2Z2Blocked()
        assert isinstance(exc, Exception)


class TestR2Z2ClientInit:
    """Tests for R2Z2Client initialization."""

    def test_default_init(self):
        client = R2Z2Client()
        assert client._running is True
        assert client._session is None
        assert client._consecutive_errors == 0

    def test_init_with_session(self):
        mock_session = MagicMock()
        client = R2Z2Client(session=mock_session)
        assert client._session is mock_session


class TestR2Z2ClientStop:
    """Tests for stop signal."""

    def test_stop_sets_running_false(self):
        client = R2Z2Client()
        assert client._running is True
        client.stop()
        assert client._running is False
