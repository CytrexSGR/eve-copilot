"""Test SyncOrchestrator for parallel sync operations."""
import pytest
from pathlib import Path
import importlib.util
import sys
from unittest.mock import Mock, MagicMock, patch
from types import ModuleType


# Modules that get mocked during test loading - must be restored after
_POISONED_MODULES = [
    'src.database', 'src.core.exceptions', 'src.services.character.service',
    'psycopg2.extras', 'services.character_sync.base', 'services',
    'services.character_sync', 'services.character_sync.wallet_sync',
    'services.character_sync.skills_sync', 'services.character_sync.skill_queue_sync',
    'services.character_sync.assets_sync', 'services.character_sync.orders_sync',
    'services.character_sync.industry_jobs_sync', 'services.character_sync.blueprints_sync',
    'services.character_sync.orchestrator',
]


@pytest.fixture(autouse=True, scope="module")
def _restore_sys_modules():
    """Prevent sys.modules pollution from leaking to other test files."""
    saved = {}
    for key in _POISONED_MODULES:
        saved[key] = sys.modules.get(key)
    yield
    global _orchestrator_class, _base_sync_class
    _orchestrator_class = None
    _base_sync_class = None
    for key in _POISONED_MODULES:
        if saved[key] is not None:
            sys.modules[key] = saved[key]
        else:
            sys.modules.pop(key, None)


# Cache for loaded modules
_orchestrator_class = None
_base_sync_class = None


def _setup_mocks():
    """Set up all required mocks for module loading."""
    # Create mock for src.database
    mock_db = MagicMock()
    mock_db.get_db_connection = MagicMock()
    mock_db.get_item_info = MagicMock(return_value={"typeName": "Test Item"})
    sys.modules['src.database'] = mock_db

    # Import the actual exceptions we need for testing
    from src.core.exceptions import AuthenticationError, ExternalAPIError
    mock_exceptions = MagicMock()
    mock_exceptions.AuthenticationError = AuthenticationError
    mock_exceptions.ExternalAPIError = ExternalAPIError
    sys.modules['src.core.exceptions'] = mock_exceptions

    # Mock the CharacterService
    mock_char_service_module = MagicMock()
    sys.modules['src.services.character.service'] = mock_char_service_module

    # Mock psycopg2.extras
    mock_psycopg2_extras = MagicMock()
    mock_psycopg2_extras.execute_values = MagicMock()
    sys.modules['psycopg2.extras'] = mock_psycopg2_extras


def _load_base_sync():
    """Load BaseSyncOperation class."""
    global _base_sync_class
    if _base_sync_class is not None:
        return _base_sync_class

    _setup_mocks()

    base_path = Path(__file__).parent.parent.parent.parent.parent / "services" / "character_sync" / "base.py"
    spec = importlib.util.spec_from_file_location("services.character_sync.base", base_path)
    base_module = importlib.util.module_from_spec(spec)
    sys.modules['services.character_sync.base'] = base_module
    spec.loader.exec_module(base_module)

    # Also create the parent package in sys.modules
    if 'services' not in sys.modules:
        services_pkg = ModuleType('services')
        sys.modules['services'] = services_pkg

    if 'services.character_sync' not in sys.modules:
        char_sync_pkg = ModuleType('services.character_sync')
        char_sync_pkg.base = base_module
        char_sync_pkg.BaseSyncOperation = base_module.BaseSyncOperation
        sys.modules['services.character_sync'] = char_sync_pkg

    _base_sync_class = base_module.BaseSyncOperation
    return _base_sync_class


def _load_sync_class(name, filename):
    """Load a sync class module."""
    _load_base_sync()

    sync_path = Path(__file__).parent.parent.parent.parent.parent / "services" / "character_sync" / filename
    spec = importlib.util.spec_from_file_location(f"services.character_sync.{filename[:-3]}", sync_path)
    sync_module = importlib.util.module_from_spec(spec)
    sys.modules[f'services.character_sync.{filename[:-3]}'] = sync_module
    spec.loader.exec_module(sync_module)

    # Add to the character_sync package
    char_sync_pkg = sys.modules['services.character_sync']
    setattr(char_sync_pkg, name, getattr(sync_module, name))

    return getattr(sync_module, name)


def _load_all_sync_classes():
    """Load all sync classes needed for orchestrator."""
    classes = {}

    # Load all sync classes
    sync_mappings = [
        ('WalletSync', 'wallet_sync.py'),
        ('SkillsSync', 'skills_sync.py'),
        ('SkillQueueSync', 'skill_queue_sync.py'),
        ('AssetsSync', 'assets_sync.py'),
        ('OrdersSync', 'orders_sync.py'),
        ('IndustryJobsSync', 'industry_jobs_sync.py'),
        ('BlueprintsSync', 'blueprints_sync.py'),
    ]

    for class_name, filename in sync_mappings:
        classes[class_name] = _load_sync_class(class_name, filename)

    return classes


def _load_orchestrator():
    """Load SyncOrchestrator class."""
    global _orchestrator_class
    if _orchestrator_class is not None:
        return _orchestrator_class

    # Load all sync classes first
    _load_all_sync_classes()

    orchestrator_path = Path(__file__).parent.parent.parent.parent.parent / "services" / "character_sync" / "orchestrator.py"
    spec = importlib.util.spec_from_file_location("services.character_sync.orchestrator", orchestrator_path)
    orchestrator_module = importlib.util.module_from_spec(spec)
    sys.modules['services.character_sync.orchestrator'] = orchestrator_module
    spec.loader.exec_module(orchestrator_module)

    # Add to the character_sync package
    char_sync_pkg = sys.modules['services.character_sync']
    char_sync_pkg.SyncOrchestrator = orchestrator_module.SyncOrchestrator

    _orchestrator_class = orchestrator_module.SyncOrchestrator
    return _orchestrator_class


class TestSyncOrchestrator:
    """Test parallel sync orchestration."""

    def test_sync_all_calls_all_operations(self):
        """sync_all should execute all sync operations."""
        SyncOrchestrator = _load_orchestrator()

        mock_service = Mock()
        orchestrator = SyncOrchestrator(mock_service)

        # Mock all sync classes at the orchestrator module level
        orchestrator_module = sys.modules['services.character_sync.orchestrator']

        with patch.object(orchestrator_module, 'WalletSync', Mock(return_value=Mock(sync=Mock(return_value={"success": True})))), \
             patch.object(orchestrator_module, 'SkillsSync', Mock(return_value=Mock(sync=Mock(return_value={"success": True})))), \
             patch.object(orchestrator_module, 'SkillQueueSync', Mock(return_value=Mock(sync=Mock(return_value={"success": True})))), \
             patch.object(orchestrator_module, 'AssetsSync', Mock(return_value=Mock(sync=Mock(return_value={"success": True})))), \
             patch.object(orchestrator_module, 'OrdersSync', Mock(return_value=Mock(sync=Mock(return_value={"success": True})))), \
             patch.object(orchestrator_module, 'IndustryJobsSync', Mock(return_value=Mock(sync=Mock(return_value={"success": True})))), \
             patch.object(orchestrator_module, 'BlueprintsSync', Mock(return_value=Mock(sync=Mock(return_value={"success": True})))):

            result = orchestrator.sync_all(12345)

            assert result["success"] is True
            assert "wallet" in result
            assert "skills" in result
            assert "assets" in result

    def test_sync_all_continues_on_failure(self):
        """sync_all should continue even if some syncs fail."""
        SyncOrchestrator = _load_orchestrator()

        mock_service = Mock()
        orchestrator = SyncOrchestrator(mock_service)

        orchestrator_module = sys.modules['services.character_sync.orchestrator']

        with patch.object(orchestrator_module, 'WalletSync', Mock(return_value=Mock(sync=Mock(return_value={"success": True, "balance": 1000})))), \
             patch.object(orchestrator_module, 'SkillsSync', Mock(return_value=Mock(sync=Mock(return_value={"success": False, "error": "API error"})))), \
             patch.object(orchestrator_module, 'SkillQueueSync', Mock(return_value=Mock(sync=Mock(return_value={"success": True})))), \
             patch.object(orchestrator_module, 'AssetsSync', Mock(return_value=Mock(sync=Mock(return_value={"success": True})))), \
             patch.object(orchestrator_module, 'OrdersSync', Mock(return_value=Mock(sync=Mock(return_value={"success": True})))), \
             patch.object(orchestrator_module, 'IndustryJobsSync', Mock(return_value=Mock(sync=Mock(return_value={"success": True})))), \
             patch.object(orchestrator_module, 'BlueprintsSync', Mock(return_value=Mock(sync=Mock(return_value={"success": True})))):

            result = orchestrator.sync_all(12345)

            # Overall success because at least one worked
            assert result["success"] is True
            assert result["wallet"]["success"] is True
            assert result["skills"]["success"] is False

    def test_sync_all_returns_summary(self):
        """sync_all should return a summary with counts."""
        SyncOrchestrator = _load_orchestrator()

        mock_service = Mock()
        orchestrator = SyncOrchestrator(mock_service)

        orchestrator_module = sys.modules['services.character_sync.orchestrator']

        with patch.object(orchestrator_module, 'WalletSync', Mock(return_value=Mock(sync=Mock(return_value={"success": True})))), \
             patch.object(orchestrator_module, 'SkillsSync', Mock(return_value=Mock(sync=Mock(return_value={"success": False})))), \
             patch.object(orchestrator_module, 'SkillQueueSync', Mock(return_value=Mock(sync=Mock(return_value={"success": True})))), \
             patch.object(orchestrator_module, 'AssetsSync', Mock(return_value=Mock(sync=Mock(return_value={"success": True})))), \
             patch.object(orchestrator_module, 'OrdersSync', Mock(return_value=Mock(sync=Mock(return_value={"success": True})))), \
             patch.object(orchestrator_module, 'IndustryJobsSync', Mock(return_value=Mock(sync=Mock(return_value={"success": True})))), \
             patch.object(orchestrator_module, 'BlueprintsSync', Mock(return_value=Mock(sync=Mock(return_value={"success": True})))):

            result = orchestrator.sync_all(12345)

            assert "summary" in result
            assert result["summary"]["successful_syncs"] == 6
            assert result["summary"]["failed_syncs"] == 1
            assert "synced_at" in result["summary"]

    def test_sync_all_returns_character_id(self):
        """sync_all should include character_id in result."""
        SyncOrchestrator = _load_orchestrator()

        mock_service = Mock()
        orchestrator = SyncOrchestrator(mock_service)

        orchestrator_module = sys.modules['services.character_sync.orchestrator']

        with patch.object(orchestrator_module, 'WalletSync', Mock(return_value=Mock(sync=Mock(return_value={"success": True})))), \
             patch.object(orchestrator_module, 'SkillsSync', Mock(return_value=Mock(sync=Mock(return_value={"success": True})))), \
             patch.object(orchestrator_module, 'SkillQueueSync', Mock(return_value=Mock(sync=Mock(return_value={"success": True})))), \
             patch.object(orchestrator_module, 'AssetsSync', Mock(return_value=Mock(sync=Mock(return_value={"success": True})))), \
             patch.object(orchestrator_module, 'OrdersSync', Mock(return_value=Mock(sync=Mock(return_value={"success": True})))), \
             patch.object(orchestrator_module, 'IndustryJobsSync', Mock(return_value=Mock(sync=Mock(return_value={"success": True})))), \
             patch.object(orchestrator_module, 'BlueprintsSync', Mock(return_value=Mock(sync=Mock(return_value={"success": True})))):

            result = orchestrator.sync_all(12345)

            assert result["character_id"] == 12345
