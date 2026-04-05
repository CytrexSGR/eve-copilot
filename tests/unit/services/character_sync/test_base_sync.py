"""Test BaseSyncOperation template method pattern."""
import pytest
from abc import ABC
from pathlib import Path
import importlib.util
import sys
from unittest.mock import Mock, patch, MagicMock


# Modules that get mocked during test loading - must be restored after
_POISONED_MODULES = ['src.database', 'src.core.exceptions', 'src.services.character.service']


@pytest.fixture(autouse=True, scope="module")
def _restore_sys_modules():
    """Prevent sys.modules pollution from leaking to other test files."""
    saved = {}
    for key in _POISONED_MODULES:
        saved[key] = sys.modules.get(key)
    yield
    global _cached_module
    _cached_module = None
    for key in _POISONED_MODULES:
        if saved[key] is not None:
            sys.modules[key] = saved[key]
        else:
            sys.modules.pop(key, None)


# Cache for loaded module
_cached_module = None


def _load_base_module():
    """Load the base module directly to avoid services/__init__.py import chain."""
    global _cached_module
    if _cached_module is not None:
        return _cached_module

    base_path = Path(__file__).parent.parent.parent.parent.parent / "services" / "character_sync" / "base.py"
    spec = importlib.util.spec_from_file_location("character_sync_base", base_path)
    module = importlib.util.module_from_spec(spec)

    # Create mock for get_db_connection that will be patched in tests
    mock_db = MagicMock()
    sys.modules['src.database'] = mock_db

    # Import the actual exceptions we need for testing (they exist and work)
    from src.core.exceptions import AuthenticationError, ExternalAPIError

    # Create a mock module that has real exceptions
    mock_exceptions = MagicMock()
    mock_exceptions.AuthenticationError = AuthenticationError
    mock_exceptions.ExternalAPIError = ExternalAPIError
    sys.modules['src.core.exceptions'] = mock_exceptions

    # Mock the CharacterService
    mock_char_service_module = MagicMock()
    sys.modules['src.services.character.service'] = mock_char_service_module

    spec.loader.exec_module(module)
    _cached_module = module
    return module


class TestBaseSyncOperation:
    """Test base sync operation class."""

    def test_is_abstract(self):
        """BaseSyncOperation should be abstract."""
        module = _load_base_module()
        BaseSyncOperation = module.BaseSyncOperation

        assert issubclass(BaseSyncOperation, ABC)

    def test_has_template_method(self):
        """Should have sync() template method."""
        module = _load_base_module()
        BaseSyncOperation = module.BaseSyncOperation

        assert hasattr(BaseSyncOperation, 'sync')

    def test_has_abstract_methods(self):
        """Should have abstract methods for customization."""
        module = _load_base_module()
        BaseSyncOperation = module.BaseSyncOperation

        # These should be abstract
        assert hasattr(BaseSyncOperation, 'fetch_from_esi')
        assert hasattr(BaseSyncOperation, 'transform_data')
        assert hasattr(BaseSyncOperation, 'save_to_db')
        assert hasattr(BaseSyncOperation, 'get_sync_column')

    def test_cannot_instantiate_directly(self):
        """Cannot instantiate abstract base class."""
        module = _load_base_module()
        BaseSyncOperation = module.BaseSyncOperation

        with pytest.raises(TypeError):
            BaseSyncOperation(Mock())

    def test_template_method_calls_hooks_in_order(self):
        """sync() should call methods in correct order."""
        module = _load_base_module()
        BaseSyncOperation = module.BaseSyncOperation

        class TestSync(BaseSyncOperation):
            call_order = []

            def fetch_from_esi(self, character_id):
                self.call_order.append('fetch')
                return {'data': 'test'}

            def transform_data(self, raw_data):
                self.call_order.append('transform')
                return [{'transformed': True}]

            def save_to_db(self, character_id, data, conn):
                self.call_order.append('save')

            def get_sync_column(self):
                return 'skills_synced_at'  # Use valid column name

            def get_result_key(self):
                return 'test_count'

        with patch.object(module, 'get_db_connection') as mock_conn:
            mock_context = Mock()
            mock_conn.return_value.__enter__ = Mock(return_value=mock_context)
            mock_conn.return_value.__exit__ = Mock(return_value=False)

            sync = TestSync(Mock())
            sync._update_sync_timestamp = Mock()
            result = sync.sync(12345)

            assert sync.call_order == ['fetch', 'transform', 'save']

    def test_template_method_returns_success_result(self):
        """sync() should return success result with data."""
        module = _load_base_module()
        BaseSyncOperation = module.BaseSyncOperation

        class TestSync(BaseSyncOperation):
            def fetch_from_esi(self, character_id):
                return {'skills': [1, 2, 3]}

            def transform_data(self, raw_data):
                return [{'id': 1}, {'id': 2}, {'id': 3}]

            def save_to_db(self, character_id, data, conn):
                pass

            def get_sync_column(self):
                return 'skills_synced_at'

            def get_result_key(self):
                return 'skill_count'

        with patch.object(module, 'get_db_connection') as mock_conn:
            mock_context = Mock()
            mock_conn.return_value.__enter__ = Mock(return_value=mock_context)
            mock_conn.return_value.__exit__ = Mock(return_value=False)

            sync = TestSync(Mock())
            sync._update_sync_timestamp = Mock()
            result = sync.sync(12345)

            assert result['success'] is True
            assert result['character_id'] == 12345
            assert result['skill_count'] == 3

    def test_template_method_handles_api_errors(self):
        """sync() should handle API errors gracefully."""
        from src.core.exceptions import AuthenticationError

        module = _load_base_module()
        BaseSyncOperation = module.BaseSyncOperation

        class TestSync(BaseSyncOperation):
            def fetch_from_esi(self, character_id):
                raise AuthenticationError("Token expired")

            def transform_data(self, raw_data):
                return []

            def save_to_db(self, character_id, data, conn):
                pass

            def get_sync_column(self):
                return 'skills_synced_at'

        sync = TestSync(Mock())
        result = sync.sync(12345)

        assert result['success'] is False
        assert 'error' in result
        assert 'Token expired' in result['error']

    def test_template_method_handles_external_api_errors(self):
        """sync() should handle ExternalAPIError gracefully."""
        from src.core.exceptions import ExternalAPIError

        module = _load_base_module()
        BaseSyncOperation = module.BaseSyncOperation

        class TestSync(BaseSyncOperation):
            def fetch_from_esi(self, character_id):
                raise ExternalAPIError("ESI", 500, "Service unavailable")

            def transform_data(self, raw_data):
                return []

            def save_to_db(self, character_id, data, conn):
                pass

            def get_sync_column(self):
                return 'skills_synced_at'

        sync = TestSync(Mock())
        result = sync.sync(12345)

        assert result['success'] is False
        assert 'error' in result

    def test_template_method_handles_database_errors(self):
        """sync() should handle database errors gracefully."""
        module = _load_base_module()
        BaseSyncOperation = module.BaseSyncOperation
        import psycopg2

        class TestSync(BaseSyncOperation):
            def fetch_from_esi(self, character_id):
                return {'data': 'test'}

            def transform_data(self, raw_data):
                return [{'item': 1}]

            def save_to_db(self, character_id, data, conn):
                raise psycopg2.Error("Database connection failed")

            def get_sync_column(self):
                return 'skills_synced_at'

        with patch.object(module, 'get_db_connection') as mock_conn:
            mock_context = Mock()
            mock_conn.return_value.__enter__ = Mock(return_value=mock_context)
            mock_conn.return_value.__exit__ = Mock(return_value=False)

            sync = TestSync(Mock())
            result = sync.sync(12345)

            assert result['success'] is False
            assert 'Database error' in result['error']

    def test_valid_sync_columns_defined(self):
        """VALID_SYNC_COLUMNS should contain all expected columns."""
        module = _load_base_module()
        VALID_SYNC_COLUMNS = module.VALID_SYNC_COLUMNS

        expected = {
            "wallets_synced_at", "skills_synced_at", "skill_queue_synced_at",
            "assets_synced_at", "orders_synced_at", "industry_jobs_synced_at",
            "blueprints_synced_at", "sp_history_synced_at"
        }
        assert VALID_SYNC_COLUMNS == expected

    def test_update_sync_timestamp_validates_column(self):
        """_update_sync_timestamp should reject invalid column names."""
        module = _load_base_module()
        BaseSyncOperation = module.BaseSyncOperation

        class TestSync(BaseSyncOperation):
            def fetch_from_esi(self, character_id):
                return {}

            def transform_data(self, raw_data):
                return []

            def save_to_db(self, character_id, data, conn):
                pass

            def get_sync_column(self):
                return 'skills_synced_at'

        sync = TestSync(Mock())
        mock_conn = Mock()

        with pytest.raises(ValueError, match="Invalid sync column"):
            sync._update_sync_timestamp(mock_conn, 12345, "malicious_column")

    def test_get_result_key_default(self):
        """get_result_key() should return 'count' by default."""
        module = _load_base_module()
        BaseSyncOperation = module.BaseSyncOperation

        class TestSync(BaseSyncOperation):
            def fetch_from_esi(self, character_id):
                return {}

            def transform_data(self, raw_data):
                return []

            def save_to_db(self, character_id, data, conn):
                pass

            def get_sync_column(self):
                return 'skills_synced_at'

        sync = TestSync(Mock())
        assert sync.get_result_key() == 'count'

    def test_get_result_value_default_with_list(self):
        """get_result_value() should return length for lists."""
        module = _load_base_module()
        BaseSyncOperation = module.BaseSyncOperation

        class TestSync(BaseSyncOperation):
            def fetch_from_esi(self, character_id):
                return {}

            def transform_data(self, raw_data):
                return []

            def save_to_db(self, character_id, data, conn):
                pass

            def get_sync_column(self):
                return 'skills_synced_at'

        sync = TestSync(Mock())
        assert sync.get_result_value([1, 2, 3, 4, 5]) == 5

    def test_get_result_value_default_with_non_list(self):
        """get_result_value() should return 1 for non-lists."""
        module = _load_base_module()
        BaseSyncOperation = module.BaseSyncOperation

        class TestSync(BaseSyncOperation):
            def fetch_from_esi(self, character_id):
                return {}

            def transform_data(self, raw_data):
                return []

            def save_to_db(self, character_id, data, conn):
                pass

            def get_sync_column(self):
                return 'skills_synced_at'

        sync = TestSync(Mock())
        assert sync.get_result_value({'single': 'item'}) == 1
        assert sync.get_result_value(42) == 1


class TestBaseSyncOperationIntegration:
    """Integration tests for BaseSyncOperation."""

    def test_concrete_subclass_works_with_mocked_dependencies(self):
        """Verify a concrete subclass works end-to-end with mocks."""
        module = _load_base_module()
        BaseSyncOperation = module.BaseSyncOperation

        class SkillsSync(BaseSyncOperation):
            """Example concrete implementation."""

            def fetch_from_esi(self, character_id):
                # Would call self.character_service.get_skills(character_id)
                return {'skills': [{'id': 1, 'level': 5}], 'total_sp': 10000}

            def transform_data(self, raw_data):
                return [
                    {'skill_id': s['id'], 'level': s['level']}
                    for s in raw_data.get('skills', [])
                ]

            def save_to_db(self, character_id, data, conn):
                # Would execute SQL to save skills
                pass

            def get_sync_column(self):
                return 'skills_synced_at'

            def get_result_key(self):
                return 'skill_count'

        with patch.object(module, 'get_db_connection') as mock_conn:
            mock_context = Mock()
            mock_conn.return_value.__enter__ = Mock(return_value=mock_context)
            mock_conn.return_value.__exit__ = Mock(return_value=False)

            mock_char_service = Mock()
            sync = SkillsSync(mock_char_service)
            sync._update_sync_timestamp = Mock()

            result = sync.sync(12345)

            assert result['success'] is True
            assert result['character_id'] == 12345
            assert result['skill_count'] == 1
