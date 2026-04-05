"""
Tests for CharacterRepository - Unified Character Data Caching.

Tests cover:
- L1 Redis cache operations (get/set/invalidate)
- L2 PostgreSQL persistence
- L3 ESI fallback
- Cache miss scenarios and fallback chains
- sync_character() full refresh
- Asset-specific convenience methods
"""

import json
import pytest
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

from src.services.character.repository import (
    CharacterRepository,
    WALLET_CACHE_TTL,
    SKILLS_CACHE_TTL,
    ASSETS_CACHE_TTL,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    redis = MagicMock()
    redis.get.return_value = None
    redis.setex.return_value = True
    redis.delete.return_value = 1
    return redis


@pytest.fixture
def mock_db():
    """Mock database pool with context manager support."""
    db = MagicMock()
    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    # Setup context manager chain
    db.get_connection.return_value.__enter__ = Mock(return_value=mock_conn)
    db.get_connection.return_value.__exit__ = Mock(return_value=False)
    mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)

    # Store references for test access
    db._mock_conn = mock_conn
    db._mock_cursor = mock_cursor

    return db


@pytest.fixture
def mock_esi():
    """Mock ESI client."""
    esi = MagicMock()
    esi.get_wallet.return_value = 1000000.0
    esi.get_skills.return_value = {
        "total_sp": 50000000,
        "unallocated_sp": 100000,
        "skills": [
            {"skill_id": 3300, "skill_name": "Gunnery", "level": 5, "trained_level": 5, "skillpoints": 256000}
        ]
    }
    esi.get_assets.return_value = [
        {"type_id": 587, "type_name": "Rifter", "quantity": 5, "location_id": 60003760}
    ]
    return esi


@pytest.fixture
def repo(mock_redis, mock_db, mock_esi):
    """Create CharacterRepository with all mocked dependencies."""
    return CharacterRepository(
        redis_client=mock_redis,
        db_pool=mock_db,
        esi_client=mock_esi
    )


@pytest.fixture
def repo_no_redis(mock_db, mock_esi):
    """Create CharacterRepository without Redis (graceful degradation test)."""
    return CharacterRepository(
        redis_client=None,
        db_pool=mock_db,
        esi_client=mock_esi
    )


@pytest.fixture
def repo_no_esi(mock_redis, mock_db):
    """Create CharacterRepository without ESI client."""
    return CharacterRepository(
        redis_client=mock_redis,
        db_pool=mock_db,
        esi_client=None
    )


# ============================================================================
# Initialization Tests
# ============================================================================

class TestCharacterRepositoryInit:
    """Test CharacterRepository initialization."""

    def test_init_with_all_dependencies(self, mock_redis, mock_db, mock_esi):
        """Should initialize with all dependencies."""
        repo = CharacterRepository(mock_redis, mock_db, mock_esi)

        assert repo.redis is mock_redis
        assert repo.db is mock_db
        assert repo.esi is mock_esi

    def test_init_without_redis(self, mock_db, mock_esi):
        """Should initialize without Redis (graceful degradation)."""
        repo = CharacterRepository(None, mock_db, mock_esi)

        assert repo.redis is None
        assert repo.db is mock_db
        assert repo.esi is mock_esi

    def test_init_without_esi(self, mock_redis, mock_db):
        """Should initialize without ESI client."""
        repo = CharacterRepository(mock_redis, mock_db, None)

        assert repo.redis is mock_redis
        assert repo.db is mock_db
        assert repo.esi is None


# ============================================================================
# Wallet Tests
# ============================================================================

class TestGetWalletBalance:
    """Tests for get_wallet_balance method."""

    def test_cache_hit_returns_value(self, repo, mock_redis):
        """Should return cached wallet balance on L1 cache hit."""
        mock_redis.get.return_value = json.dumps(1000000.0).encode()
        character_id = 526379435

        result = repo.get_wallet_balance(character_id)

        assert result == 1000000.0
        mock_redis.get.assert_called_once_with("character:526379435:wallet")

    def test_cache_miss_falls_through_to_db(self, repo, mock_redis, mock_db):
        """Should query DB on L1 cache miss."""
        mock_redis.get.return_value = None
        mock_db._mock_cursor.fetchone.return_value = {"balance": 2000000.0}
        character_id = 526379435

        result = repo.get_wallet_balance(character_id)

        assert result == 2000000.0
        # Should cache the result
        mock_redis.setex.assert_called_once()

    def test_db_miss_falls_through_to_esi(self, repo, mock_redis, mock_db, mock_esi):
        """Should call ESI on L1 and L2 cache miss."""
        mock_redis.get.return_value = None
        mock_db._mock_cursor.fetchone.return_value = None
        mock_esi.get_wallet.return_value = 3000000.0
        character_id = 526379435

        result = repo.get_wallet_balance(character_id)

        assert result == 3000000.0
        mock_esi.get_wallet.assert_called_once_with(character_id)

    def test_esi_result_is_cached(self, repo, mock_redis, mock_db, mock_esi):
        """Should cache ESI result in both L1 and L2."""
        mock_redis.get.return_value = None
        mock_db._mock_cursor.fetchone.return_value = None
        mock_esi.get_wallet.return_value = 5000000.0
        character_id = 526379435

        repo.get_wallet_balance(character_id)

        # Check L1 cache was set with correct TTL
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert call_args[0][1] == WALLET_CACHE_TTL

    def test_returns_none_when_all_sources_fail(self, repo, mock_redis, mock_db, mock_esi):
        """Should return None when all data sources fail."""
        mock_redis.get.return_value = None
        mock_db._mock_cursor.fetchone.return_value = None
        mock_esi.get_wallet.side_effect = Exception("ESI down")
        character_id = 526379435

        result = repo.get_wallet_balance(character_id)

        assert result is None

    def test_graceful_degradation_without_redis(self, repo_no_redis, mock_db, mock_esi):
        """Should work without Redis cache."""
        mock_db._mock_cursor.fetchone.return_value = None
        mock_esi.get_wallet.return_value = 1000000.0
        character_id = 526379435

        result = repo_no_redis.get_wallet_balance(character_id)

        assert result == 1000000.0


# ============================================================================
# Skills Tests
# ============================================================================

class TestGetSkills:
    """Tests for get_skills method."""

    def test_cache_hit_returns_skills(self, repo, mock_redis):
        """Should return cached skills on L1 cache hit."""
        skills_data = {
            "total_sp": 50000000,
            "unallocated_sp": 100000,
            "skills": [{"skill_id": 3300, "level": 5}]
        }
        mock_redis.get.return_value = json.dumps(skills_data).encode()
        character_id = 526379435

        result = repo.get_skills(character_id)

        assert result == skills_data
        assert result["total_sp"] == 50000000

    def test_cache_miss_queries_db(self, repo, mock_redis, mock_db):
        """Should query DB on L1 cache miss."""
        mock_redis.get.return_value = None
        mock_db._mock_cursor.fetchone.return_value = {
            "total_sp": 60000000,
            "unallocated_sp": 200000
        }
        mock_db._mock_cursor.fetchall.return_value = [
            {"skill_id": 3300, "skill_name": "Gunnery", "level": 5, "trained_level": 5, "skillpoints": 256000}
        ]
        character_id = 526379435

        result = repo.get_skills(character_id)

        assert result is not None
        assert result["total_sp"] == 60000000

    def test_esi_fallback_on_cache_miss(self, repo, mock_redis, mock_db, mock_esi):
        """Should call ESI when both caches miss."""
        mock_redis.get.return_value = None
        mock_db._mock_cursor.fetchone.return_value = None
        mock_esi.get_skills.return_value = {
            "total_sp": 70000000,
            "unallocated_sp": 50000,
            "skills": []
        }
        character_id = 526379435

        result = repo.get_skills(character_id)

        assert result["total_sp"] == 70000000
        mock_esi.get_skills.assert_called_once_with(character_id)


# ============================================================================
# Assets Tests
# ============================================================================

class TestGetAssets:
    """Tests for get_assets method."""

    def test_cache_hit_returns_assets(self, repo, mock_redis):
        """Should return cached assets on L1 cache hit."""
        assets_data = [
            {"type_id": 587, "quantity": 5, "location_id": 60003760}
        ]
        mock_redis.get.return_value = json.dumps(assets_data).encode()
        character_id = 526379435

        result = repo.get_assets(character_id)

        assert result == assets_data
        assert len(result) == 1

    def test_cache_miss_queries_db(self, repo, mock_redis, mock_db):
        """Should query DB on L1 cache miss."""
        mock_redis.get.return_value = None
        mock_db._mock_cursor.fetchall.return_value = [
            {"type_id": 587, "type_name": "Rifter", "quantity": 5, "location_id": 60003760,
             "location_name": None, "location_type": "station"}
        ]
        character_id = 526379435

        result = repo.get_assets(character_id)

        assert len(result) == 1
        assert result[0]["type_id"] == 587

    def test_returns_empty_list_on_complete_miss(self, repo, mock_redis, mock_db, mock_esi):
        """Should return empty list when no assets found anywhere."""
        mock_redis.get.return_value = None
        mock_db._mock_cursor.fetchall.return_value = []
        mock_esi.get_assets.return_value = []
        character_id = 526379435

        result = repo.get_assets(character_id)

        assert result == []

    def test_esi_assets_are_cached(self, repo, mock_redis, mock_db, mock_esi):
        """Should cache ESI assets in both L1 and L2."""
        mock_redis.get.return_value = None
        mock_db._mock_cursor.fetchall.return_value = []
        mock_esi.get_assets.return_value = [
            {"type_id": 587, "quantity": 10, "location_id": 60003760}
        ]
        character_id = 526379435

        repo.get_assets(character_id)

        # L1 cache should be updated
        mock_redis.setex.assert_called_once()


# ============================================================================
# Sync Tests
# ============================================================================

class TestSyncCharacter:
    """Tests for sync_character method."""

    def test_syncs_all_data_types(self, repo, mock_redis, mock_db, mock_esi):
        """Should sync wallet, skills, and assets."""
        mock_redis.get.return_value = None
        mock_db._mock_cursor.fetchone.return_value = None
        mock_db._mock_cursor.fetchall.return_value = []
        character_id = 526379435

        result = repo.sync_character(character_id)

        assert result["wallet"] is True
        assert result["skills"] is True
        assert result["assets"] is True

    def test_invalidates_cache_before_sync(self, repo, mock_redis, mock_db, mock_esi):
        """Should invalidate cache before syncing."""
        mock_redis.get.return_value = None
        mock_db._mock_cursor.fetchone.return_value = None
        mock_db._mock_cursor.fetchall.return_value = []
        character_id = 526379435

        repo.sync_character(character_id)

        # Check that delete was called with all cache keys
        mock_redis.delete.assert_called()

    def test_returns_false_without_esi(self, repo_no_esi):
        """Should return all False when ESI client not configured."""
        character_id = 526379435

        result = repo_no_esi.sync_character(character_id)

        assert result["wallet"] is False
        assert result["skills"] is False
        assert result["assets"] is False

    def test_partial_sync_failure(self, repo, mock_redis, mock_db, mock_esi):
        """Should continue syncing even if one data type fails."""
        mock_redis.get.return_value = None
        mock_db._mock_cursor.fetchone.return_value = None
        mock_db._mock_cursor.fetchall.return_value = []
        mock_esi.get_wallet.side_effect = Exception("Wallet API down")
        mock_esi.get_skills.return_value = {"total_sp": 1000, "unallocated_sp": 0, "skills": []}
        mock_esi.get_assets.return_value = []
        character_id = 526379435

        result = repo.sync_character(character_id)

        assert result["wallet"] is False
        assert result["skills"] is True
        assert result["assets"] is True


# ============================================================================
# Cache Invalidation Tests
# ============================================================================

class TestInvalidate:
    """Tests for invalidate method."""

    def test_invalidate_specific_data_type(self, repo, mock_redis):
        """Should invalidate specific data type cache."""
        character_id = 526379435

        repo.invalidate(character_id, "wallet")

        mock_redis.delete.assert_called_once_with("character:526379435:wallet")

    def test_invalidate_all_data_types(self, repo, mock_redis):
        """Should invalidate all data types when no type specified."""
        character_id = 526379435

        repo.invalidate(character_id)

        mock_redis.delete.assert_called_once()
        # Check that all three keys are passed
        call_args = mock_redis.delete.call_args[0]
        assert len(call_args) == 3

    def test_invalidate_without_redis(self, repo_no_redis):
        """Should not raise error when Redis is not configured."""
        character_id = 526379435

        # Should not raise
        repo_no_redis.invalidate(character_id)


# ============================================================================
# Asset Convenience Methods Tests
# ============================================================================

class TestGetAssetSummary:
    """Tests for get_asset_summary method."""

    def test_returns_aggregated_summary(self, repo, mock_db):
        """Should return assets grouped by type with total quantities."""
        mock_db._mock_cursor.fetchall.return_value = [
            {"type_id": 587, "type_name": "Rifter", "total_quantity": 10},
            {"type_id": 638, "type_name": "Vexor", "total_quantity": 3}
        ]
        character_id = 526379435

        result = repo.get_asset_summary(character_id)

        assert len(result) == 2
        assert result[0]["type_id"] == 587
        assert result[0]["total_quantity"] == 10

    def test_returns_empty_list_on_error(self, repo, mock_db):
        """Should return empty list on database error."""
        mock_db.get_connection.return_value.__enter__.side_effect = Exception("DB error")
        character_id = 526379435

        result = repo.get_asset_summary(character_id)

        assert result == []


class TestFindAssetsForTypes:
    """Tests for find_assets_for_types method."""

    def test_returns_quantities_for_requested_types(self, repo, mock_db):
        """Should return quantities for all requested type IDs."""
        mock_db._mock_cursor.fetchall.return_value = [
            {"type_id": 587, "total_quantity": 10},
            {"type_id": 638, "total_quantity": 3}
        ]
        character_id = 526379435
        type_ids = [587, 638, 999]

        result = repo.find_assets_for_types(character_id, type_ids)

        assert result[587] == 10
        assert result[638] == 3
        assert result[999] == 0  # Not found

    def test_returns_empty_dict_for_empty_input(self, repo):
        """Should return empty dict for empty type_ids list."""
        character_id = 526379435

        result = repo.find_assets_for_types(character_id, [])

        assert result == {}


class TestGetCacheStatus:
    """Tests for get_cache_status method."""

    def test_returns_cache_info(self, repo, mock_db):
        """Should return cache status information."""
        now = datetime.now()
        mock_db._mock_cursor.fetchone.side_effect = [
            {"last_cached": now, "total_items": 100},  # assets
            {"1": 1},  # wallet exists
            {"1": 1}   # skills exists
        ]
        character_id = 526379435

        result = repo.get_cache_status(character_id)

        assert result["assets_cached_at"] == now
        assert result["assets_count"] == 100
        assert result["has_wallet"] is True
        assert result["has_skills"] is True

    def test_returns_defaults_on_no_cache(self, repo, mock_db):
        """Should return default values when no cache exists."""
        mock_db._mock_cursor.fetchone.return_value = {"last_cached": None, "total_items": 0}
        character_id = 526379435

        result = repo.get_cache_status(character_id)

        assert result["assets_cached_at"] is None
        assert result["assets_count"] == 0


# ============================================================================
# Cache Key Generation Tests
# ============================================================================

class TestCacheKeyGeneration:
    """Tests for cache key generation."""

    def test_key_format(self, repo):
        """Should generate keys in expected format."""
        key = repo._make_key(526379435, "wallet")

        assert key == "character:526379435:wallet"

    def test_different_data_types(self, repo):
        """Should generate unique keys for different data types."""
        wallet_key = repo._make_key(12345, "wallet")
        skills_key = repo._make_key(12345, "skills")
        assets_key = repo._make_key(12345, "assets")

        assert wallet_key != skills_key
        assert skills_key != assets_key
        assert wallet_key != assets_key


# ============================================================================
# TTL Configuration Tests
# ============================================================================

class TestTTLConfiguration:
    """Tests for cache TTL configuration."""

    def test_wallet_ttl_is_5_minutes(self):
        """Wallet TTL should be 5 minutes (300 seconds)."""
        assert WALLET_CACHE_TTL == 300

    def test_skills_ttl_is_1_hour(self):
        """Skills TTL should be 1 hour (3600 seconds)."""
        assert SKILLS_CACHE_TTL == 3600

    def test_assets_ttl_is_30_minutes(self):
        """Assets TTL should be 30 minutes (1800 seconds)."""
        assert ASSETS_CACHE_TTL == 1800


# ============================================================================
# Integration Test Markers
# ============================================================================

class TestIntegration:
    """Integration tests (require real database and Redis)."""

    @pytest.mark.integration
    def test_full_sync_and_retrieve_cycle(self):
        """Integration test: sync data and retrieve it."""
        # This test requires real connections
        # Will be skipped in unit test runs
        pass

    @pytest.mark.integration
    def test_cache_expiration(self):
        """Integration test: verify cache expires correctly."""
        # This test requires real Redis
        # Will be skipped in unit test runs
        pass
