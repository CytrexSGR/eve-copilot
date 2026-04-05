"""Tests for Killmail Repository."""

from datetime import date, timedelta
from unittest.mock import MagicMock, call, patch

import pytest

from src.services.killmail.models import ItemLoss, ShipLoss
from src.services.killmail.repository import KillmailRepository


@pytest.fixture
def mock_db_pool():
    """Create a mock database pool."""
    pool = MagicMock()
    pool.get_connection = MagicMock()
    return pool


@pytest.fixture
def repository(mock_db_pool):
    """Create a KillmailRepository with mock database."""
    return KillmailRepository(db=mock_db_pool)


class TestKillmailRepository:
    """Test KillmailRepository class."""

    def test_initialization(self, mock_db_pool):
        """Test repository initialization."""
        repo = KillmailRepository(db=mock_db_pool)
        assert repo.db == mock_db_pool

    def test_store_ship_losses_empty_list(self, repository, mock_db_pool):
        """Test storing empty ship losses list."""
        result = repository.store_ship_losses([])
        assert result == 0
        mock_db_pool.get_connection.assert_not_called()

    @patch('src.services.killmail.repository.execute_values')
    def test_store_ship_losses_success(self, mock_execute_values, repository, mock_db_pool):
        """Test successfully storing ship losses."""
        # Setup
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_db_pool.get_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db_pool.get_connection.return_value.__exit__ = MagicMock(return_value=False)

        losses = [
            ShipLoss(
                system_id=30001234,
                region_id=10000002,
                ship_type_id=648,
                loss_count=5,
                date=date(2025, 12, 7)
            ),
            ShipLoss(
                system_id=30001235,
                region_id=10000002,
                ship_type_id=649,
                loss_count=3,
                date=date(2025, 12, 7),
                total_value_destroyed=500000000.0
            )
        ]

        # Execute
        result = repository.store_ship_losses(losses)

        # Verify
        assert result == 2
        mock_execute_values.assert_called_once()
        call_args = mock_execute_values.call_args

        # Check the values passed
        values = call_args[0][2]
        assert len(values) == 2
        assert values[0] == (30001234, 10000002, 648, 5, date(2025, 12, 7), 0.0)
        assert values[1] == (30001235, 10000002, 649, 3, date(2025, 12, 7), 500000000.0)

        # Check commit was called
        mock_conn.commit.assert_called_once()

    def test_store_item_losses_empty_list(self, repository, mock_db_pool):
        """Test storing empty item losses list."""
        result = repository.store_item_losses([])
        assert result == 0
        mock_db_pool.get_connection.assert_not_called()

    @patch('src.services.killmail.repository.execute_values')
    def test_store_item_losses_success(self, mock_execute_values, repository, mock_db_pool):
        """Test successfully storing item losses."""
        # Setup
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_db_pool.get_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db_pool.get_connection.return_value.__exit__ = MagicMock(return_value=False)

        losses = [
            ItemLoss(
                region_id=10000002,
                item_type_id=456,
                loss_count=100,
                date=date(2025, 12, 7)
            ),
            ItemLoss(
                region_id=10000002,
                item_type_id=457,
                loss_count=50,
                date=date(2025, 12, 7)
            )
        ]

        # Execute
        result = repository.store_item_losses(losses)

        # Verify
        assert result == 2
        mock_execute_values.assert_called_once()
        call_args = mock_execute_values.call_args

        values = call_args[0][2]
        assert len(values) == 2
        assert values[0] == (10000002, 456, 100, date(2025, 12, 7))
        assert values[1] == (10000002, 457, 50, date(2025, 12, 7))

        mock_conn.commit.assert_called_once()

    def test_get_ship_losses_all_regions(self, repository, mock_db_pool):
        """Test getting ship losses for all regions."""
        # Setup
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {
                'system_id': 30001234,
                'region_id': 10000002,
                'ship_type_id': 648,
                'loss_count': 5,
                'date': date(2025, 12, 7),
                'total_value_destroyed': 100000000.0
            }
        ]
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_db_pool.get_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db_pool.get_connection.return_value.__exit__ = MagicMock(return_value=False)

        # Execute
        result = repository.get_ship_losses(region_id=None, system_id=None, days=7)

        # Verify
        assert len(result) == 1
        assert result[0]['system_id'] == 30001234
        assert result[0]['ship_type_id'] == 648
        mock_cursor.execute.assert_called_once()

    def test_get_ship_losses_specific_region(self, repository, mock_db_pool):
        """Test getting ship losses for specific region."""
        # Setup
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_db_pool.get_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db_pool.get_connection.return_value.__exit__ = MagicMock(return_value=False)

        # Execute
        result = repository.get_ship_losses(region_id=10000002, system_id=None, days=7)

        # Verify
        assert len(result) == 0
        mock_cursor.execute.assert_called_once()
        # Check that region_id was in the query parameters
        call_args = mock_cursor.execute.call_args
        assert 10000002 in call_args[0][1]

    def test_get_ship_losses_specific_system(self, repository, mock_db_pool):
        """Test getting ship losses for specific system."""
        # Setup
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_db_pool.get_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db_pool.get_connection.return_value.__exit__ = MagicMock(return_value=False)

        # Execute
        result = repository.get_ship_losses(region_id=None, system_id=30001234, days=7)

        # Verify
        assert len(result) == 0
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args
        assert 30001234 in call_args[0][1]

    def test_get_item_losses_all_regions(self, repository, mock_db_pool):
        """Test getting item losses for all regions."""
        # Setup
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {
                'region_id': 10000002,
                'item_type_id': 456,
                'loss_count': 100,
                'date': date(2025, 12, 7)
            }
        ]
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_db_pool.get_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db_pool.get_connection.return_value.__exit__ = MagicMock(return_value=False)

        # Execute
        result = repository.get_item_losses(region_id=None, days=7)

        # Verify
        assert len(result) == 1
        assert result[0]['item_type_id'] == 456
        mock_cursor.execute.assert_called_once()

    def test_get_item_losses_specific_region(self, repository, mock_db_pool):
        """Test getting item losses for specific region."""
        # Setup
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_db_pool.get_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db_pool.get_connection.return_value.__exit__ = MagicMock(return_value=False)

        # Execute
        result = repository.get_item_losses(region_id=10000002, days=7)

        # Verify
        assert len(result) == 0
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args
        assert 10000002 in call_args[0][1]

    def test_get_system_danger_score(self, repository, mock_db_pool):
        """Test getting danger score for a system."""
        # Setup
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {'kill_count': 42}
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_db_pool.get_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db_pool.get_connection.return_value.__exit__ = MagicMock(return_value=False)

        # Execute
        result = repository.get_system_danger_score(system_id=30001234, days=7)

        # Verify
        assert result['system_id'] == 30001234
        assert result['kill_count'] == 42
        assert result['days'] == 7
        mock_cursor.execute.assert_called_once()

    def test_get_system_danger_score_no_data(self, repository, mock_db_pool):
        """Test getting danger score for system with no data."""
        # Setup
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_db_pool.get_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db_pool.get_connection.return_value.__exit__ = MagicMock(return_value=False)

        # Execute
        result = repository.get_system_danger_score(system_id=30001234, days=7)

        # Verify
        assert result['system_id'] == 30001234
        assert result['kill_count'] == 0
        assert result['days'] == 7

    def test_cleanup_old_data(self, repository, mock_db_pool):
        """Test cleanup of old data."""
        # Setup
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 10
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_db_pool.get_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db_pool.get_connection.return_value.__exit__ = MagicMock(return_value=False)

        # Execute
        result = repository.cleanup_old_data(days=30)

        # Verify
        assert result == 20  # 10 ship + 10 item deletions
        assert mock_cursor.execute.call_count == 2  # Two DELETE queries
        mock_conn.commit.assert_called_once()

    def test_get_system_region_map(self, repository, mock_db_pool):
        """Test getting system to region mapping."""
        # Setup
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {'solar_system_id': 30001234, 'region_id': 10000002},
            {'solar_system_id': 30001235, 'region_id': 10000002}
        ]
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_db_pool.get_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db_pool.get_connection.return_value.__exit__ = MagicMock(return_value=False)

        # Execute
        result = repository.get_system_region_map()

        # Verify
        assert result == {30001234: 10000002, 30001235: 10000002}
        mock_cursor.execute.assert_called_once()


# =============================================================================
# New Tests for L1 Redis Cache and Raw Killmail Operations
# =============================================================================


@pytest.fixture
def mock_redis():
    """Create a mock Redis client."""
    redis = MagicMock()
    return redis


@pytest.fixture
def mock_esi():
    """Create a mock ESI client."""
    esi = MagicMock()
    return esi


@pytest.fixture
def cached_repository(mock_db_pool, mock_redis, mock_esi):
    """Create a KillmailRepository with Redis and ESI clients."""
    return KillmailRepository(db=mock_db_pool, redis_client=mock_redis, esi_client=mock_esi)


class TestKillmailRepositoryCaching:
    """Test KillmailRepository L1 Redis caching operations."""

    def test_initialization_with_redis(self, mock_db_pool, mock_redis, mock_esi):
        """Test repository initialization with Redis and ESI clients."""
        repo = KillmailRepository(db=mock_db_pool, redis_client=mock_redis, esi_client=mock_esi)
        assert repo.db == mock_db_pool
        assert repo.redis == mock_redis
        assert repo.esi == mock_esi

    def test_initialization_without_redis(self, mock_db_pool):
        """Test repository initialization without optional dependencies."""
        repo = KillmailRepository(db=mock_db_pool)
        assert repo.db == mock_db_pool
        assert repo.redis is None
        assert repo.esi is None

    def test_get_killmail_redis_hit(self, cached_repository, mock_redis):
        """Test L1 cache hit returns killmail from Redis."""
        # Setup - Redis returns cached killmail
        mock_redis.get.return_value = '{"killmail_id": 12345, "solar_system_id": 30000142}'

        result = cached_repository.get_killmail(12345)

        assert result is not None
        assert result["killmail_id"] == 12345
        assert result["solar_system_id"] == 30000142
        mock_redis.get.assert_called_once_with("killmail:12345")

    def test_get_killmail_redis_miss_postgres_hit(self, cached_repository, mock_redis, mock_db_pool):
        """Test L2 fallback when Redis misses."""
        # Setup - Redis returns None, PostgreSQL returns data
        mock_redis.get.return_value = None

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (
            12345,  # killmail_id
            "abc123hash",  # killmail_hash
            30000142,  # solar_system_id
            10000002,  # region_id
            "2026-01-18 12:00:00",  # killmail_time
            648,  # ship_type_id
            100000000,  # ship_value
            None,  # victim_alliance_id
            98000001,  # victim_corporation_id
            1234567890  # victim_character_id
        )
        mock_cursor.description = [
            ('killmail_id',), ('killmail_hash',), ('solar_system_id',), ('region_id',),
            ('killmail_time',), ('ship_type_id',), ('ship_value',),
            ('victim_alliance_id',), ('victim_corporation_id',), ('victim_character_id',)
        ]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_db_pool.get_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db_pool.get_connection.return_value.__exit__ = MagicMock(return_value=False)

        result = cached_repository.get_killmail(12345)

        assert result is not None
        assert result["killmail_id"] == 12345
        # Should promote to Redis
        mock_redis.setex.assert_called_once()

    def test_get_killmail_not_found(self, cached_repository, mock_redis, mock_db_pool):
        """Test returns None when killmail not found anywhere."""
        # Setup - Redis and PostgreSQL both return None
        mock_redis.get.return_value = None

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_db_pool.get_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db_pool.get_connection.return_value.__exit__ = MagicMock(return_value=False)

        result = cached_repository.get_killmail(99999)

        assert result is None

    def test_get_killmail_no_redis_client(self, mock_db_pool):
        """Test get_killmail goes directly to PostgreSQL when no Redis."""
        repo = KillmailRepository(db=mock_db_pool)

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (
            12345, "hash", 30000142, 10000002, "2026-01-18", 648, 100000000, None, 98000001, 1234567890
        )
        mock_cursor.description = [
            ('killmail_id',), ('killmail_hash',), ('solar_system_id',), ('region_id',),
            ('killmail_time',), ('ship_type_id',), ('ship_value',),
            ('victim_alliance_id',), ('victim_corporation_id',), ('victim_character_id',)
        ]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_db_pool.get_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db_pool.get_connection.return_value.__exit__ = MagicMock(return_value=False)

        result = repo.get_killmail(12345)

        assert result is not None
        assert result["killmail_id"] == 12345


class TestKillmailRepositoryDeduplication:
    """Test KillmailRepository deduplication via Redis set."""

    def test_is_processed_true(self, cached_repository, mock_redis):
        """Test deduplication check returns True when already processed."""
        mock_redis.sismember.return_value = True

        result = cached_repository.is_processed(12345)

        assert result is True
        mock_redis.sismember.assert_called_once_with("killmail:processed", "12345")

    def test_is_processed_false(self, cached_repository, mock_redis):
        """Test deduplication check returns False when not processed."""
        mock_redis.sismember.return_value = False

        result = cached_repository.is_processed(12345)

        assert result is False
        mock_redis.sismember.assert_called_once_with("killmail:processed", "12345")

    def test_is_processed_no_redis_returns_false(self, mock_db_pool):
        """Test is_processed returns False when no Redis client."""
        repo = KillmailRepository(db=mock_db_pool)

        result = repo.is_processed(12345)

        assert result is False

    def test_mark_processed_success(self, cached_repository, mock_redis):
        """Test marking killmail as processed returns True for new entry."""
        mock_redis.sadd.return_value = 1  # 1 = newly added

        result = cached_repository.mark_processed(12345)

        assert result is True
        mock_redis.sadd.assert_called_once_with("killmail:processed", "12345")

    def test_mark_processed_already_exists(self, cached_repository, mock_redis):
        """Test marking killmail as processed returns False when already exists."""
        mock_redis.sadd.return_value = 0  # 0 = already existed

        result = cached_repository.mark_processed(12345)

        assert result is False

    def test_mark_processed_no_redis_returns_false(self, mock_db_pool):
        """Test mark_processed returns False when no Redis client."""
        repo = KillmailRepository(db=mock_db_pool)

        result = repo.mark_processed(12345)

        assert result is False


class TestKillmailRepositorySaveKillmail:
    """Test KillmailRepository save operations for raw killmails."""

    def test_save_killmail_success(self, cached_repository, mock_redis, mock_db_pool):
        """Test saving killmail to both L1 and L2 caches."""
        killmail = {
            "killmail_id": 12345,
            "killmail_hash": "abc123hash",
            "solar_system_id": 30000142,
            "region_id": 10000002,
            "killmail_time": "2026-01-18T12:00:00",
            "ship_type_id": 648,
            "ship_value": 100000000
        }

        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_db_pool.get_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db_pool.get_connection.return_value.__exit__ = MagicMock(return_value=False)
        mock_redis.sadd.return_value = 1

        result = cached_repository.save_killmail(killmail)

        assert result is True
        # Should write to Redis
        mock_redis.setex.assert_called_once()
        # Should write to PostgreSQL
        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()
        # Should mark as processed
        mock_redis.sadd.assert_called_once()

    def test_save_killmail_missing_id(self, cached_repository):
        """Test save_killmail fails without killmail_id."""
        killmail = {
            "solar_system_id": 30000142,
            "region_id": 10000002
        }

        result = cached_repository.save_killmail(killmail)

        assert result is False

    def test_save_killmail_no_redis_writes_only_postgres(self, mock_db_pool):
        """Test save_killmail works with only PostgreSQL."""
        repo = KillmailRepository(db=mock_db_pool)
        killmail = {
            "killmail_id": 12345,
            "killmail_hash": "abc123hash",
            "solar_system_id": 30000142,
            "region_id": 10000002,
            "killmail_time": "2026-01-18T12:00:00"
        }

        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_db_pool.get_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db_pool.get_connection.return_value.__exit__ = MagicMock(return_value=False)

        result = repo.save_killmail(killmail)

        assert result is True
        mock_cursor.execute.assert_called_once()


class TestKillmailRepositoryRecentKillmails:
    """Test KillmailRepository get_recent_killmails operations."""

    def test_get_recent_killmails_default(self, cached_repository, mock_db_pool):
        """Test getting recent killmails with default parameters."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            (12345, "hash1", 30000142, 10000002, "2026-01-18 12:00:00", 648, 100000000),
            (12346, "hash2", 30000142, 10000002, "2026-01-18 11:00:00", 649, 200000000)
        ]
        mock_cursor.description = [
            ('killmail_id',), ('killmail_hash',), ('solar_system_id',), ('region_id',),
            ('killmail_time',), ('ship_type_id',), ('ship_value',)
        ]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_db_pool.get_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db_pool.get_connection.return_value.__exit__ = MagicMock(return_value=False)

        result = cached_repository.get_recent_killmails(limit=100)

        assert len(result) == 2
        assert result[0]["killmail_id"] == 12345
        assert result[1]["killmail_id"] == 12346

    def test_get_recent_killmails_with_region_filter(self, cached_repository, mock_db_pool):
        """Test getting recent killmails filtered by region."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_cursor.description = [
            ('killmail_id',), ('killmail_hash',), ('solar_system_id',), ('region_id',),
            ('killmail_time',), ('ship_type_id',), ('ship_value',)
        ]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_db_pool.get_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db_pool.get_connection.return_value.__exit__ = MagicMock(return_value=False)

        result = cached_repository.get_recent_killmails(limit=50, region_id=10000002)

        assert len(result) == 0
        mock_cursor.execute.assert_called_once()
        # Verify region_id is in the query parameters
        call_args = mock_cursor.execute.call_args
        assert 10000002 in call_args[0][1]

    def test_get_recent_killmails_empty_result(self, cached_repository, mock_db_pool):
        """Test getting recent killmails returns empty list on error."""
        mock_db_pool.get_connection.side_effect = Exception("Database error")

        result = cached_repository.get_recent_killmails()

        assert result == []
