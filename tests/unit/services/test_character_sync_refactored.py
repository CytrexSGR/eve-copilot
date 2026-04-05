"""Test refactored character_sync_service uses new classes."""
import pytest
from pathlib import Path
import importlib.util
import sys
from unittest.mock import patch, Mock, MagicMock


# Modules that get mocked during test loading - must be restored after
_POISONED_MODULES = [
    'src.database', 'src.core.config', 'src.core.database',
    'src.services.character.service', 'src.services.auth.service',
    'src.services.auth.repository', 'src.integrations.esi.client',
    'services.character_sync.orchestrator', 'services.character_sync.wallet_sync',
    'services.character_sync.skills_sync', 'services.character_sync.skill_queue_sync',
    'services.character_sync.assets_sync', 'services.character_sync.orders_sync',
    'services.character_sync.industry_jobs_sync', 'services.character_sync.blueprints_sync',
]


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


def _load_service_module():
    """Load character_sync_service directly to avoid import chain."""
    global _cached_module
    if _cached_module is not None:
        return _cached_module

    service_path = Path(__file__).parent.parent.parent.parent / "services" / "character_sync_service.py"
    spec = importlib.util.spec_from_file_location("character_sync_service", service_path)
    module = importlib.util.module_from_spec(spec)

    # Mock database dependencies
    mock_db = MagicMock()
    sys.modules['src.database'] = mock_db

    # Mock core dependencies
    mock_config = MagicMock()
    mock_config.get_settings = MagicMock(return_value=MagicMock())
    sys.modules['src.core.config'] = mock_config

    mock_database_pool = MagicMock()
    sys.modules['src.core.database'] = mock_database_pool

    # Mock service dependencies
    mock_char_service_module = MagicMock()
    sys.modules['src.services.character.service'] = mock_char_service_module

    mock_auth_service = MagicMock()
    sys.modules['src.services.auth.service'] = mock_auth_service

    mock_auth_repo = MagicMock()
    sys.modules['src.services.auth.repository'] = mock_auth_repo

    mock_esi = MagicMock()
    sys.modules['src.integrations.esi.client'] = mock_esi

    # Mock the sync classes - create actual mock classes that can be instantiated
    mock_orchestrator_class = MagicMock()
    mock_orchestrator_mod = MagicMock()
    mock_orchestrator_mod.SyncOrchestrator = mock_orchestrator_class
    sys.modules['services.character_sync.orchestrator'] = mock_orchestrator_mod

    mock_wallet_class = MagicMock()
    mock_wallet_mod = MagicMock()
    mock_wallet_mod.WalletSync = mock_wallet_class
    sys.modules['services.character_sync.wallet_sync'] = mock_wallet_mod

    mock_skills_class = MagicMock()
    mock_skills_mod = MagicMock()
    mock_skills_mod.SkillsSync = mock_skills_class
    sys.modules['services.character_sync.skills_sync'] = mock_skills_mod

    mock_skill_queue_class = MagicMock()
    mock_skill_queue_mod = MagicMock()
    mock_skill_queue_mod.SkillQueueSync = mock_skill_queue_class
    sys.modules['services.character_sync.skill_queue_sync'] = mock_skill_queue_mod

    mock_assets_class = MagicMock()
    mock_assets_mod = MagicMock()
    mock_assets_mod.AssetsSync = mock_assets_class
    sys.modules['services.character_sync.assets_sync'] = mock_assets_mod

    mock_orders_class = MagicMock()
    mock_orders_mod = MagicMock()
    mock_orders_mod.OrdersSync = mock_orders_class
    sys.modules['services.character_sync.orders_sync'] = mock_orders_mod

    mock_industry_class = MagicMock()
    mock_industry_mod = MagicMock()
    mock_industry_mod.IndustryJobsSync = mock_industry_class
    sys.modules['services.character_sync.industry_jobs_sync'] = mock_industry_mod

    mock_blueprints_class = MagicMock()
    mock_blueprints_mod = MagicMock()
    mock_blueprints_mod.BlueprintsSync = mock_blueprints_class
    sys.modules['services.character_sync.blueprints_sync'] = mock_blueprints_mod

    spec.loader.exec_module(module)
    _cached_module = module
    return module


class TestCharacterSyncRefactored:
    """Verify character_sync_service uses sync operation classes."""

    def test_uses_sync_orchestrator(self):
        """CharacterSyncService.sync_all should use SyncOrchestrator."""
        module = _load_service_module()

        # Get the class and mock the orchestrator
        CharacterSyncService = module.CharacterSyncService
        service = CharacterSyncService(Mock())

        # Mock the orchestrator property
        mock_orch = MagicMock()
        mock_orch.sync_all.return_value = {"success": True}
        service._orchestrator = mock_orch

        result = service.sync_all(12345)

        mock_orch.sync_all.assert_called_once_with(12345)
        assert result["success"] is True

    def test_sync_wallet_uses_class(self):
        """sync_wallet should delegate to WalletSync class."""
        module = _load_service_module()

        CharacterSyncService = module.CharacterSyncService
        service = CharacterSyncService(Mock())

        # Patch WalletSync at module level
        mock_wallet_class = MagicMock()
        mock_wallet_instance = MagicMock()
        mock_wallet_instance.sync.return_value = {"success": True, "balance": 1000}
        mock_wallet_class.return_value = mock_wallet_instance

        original_wallet = module.WalletSync
        module.WalletSync = mock_wallet_class

        try:
            result = service.sync_wallet(12345)

            mock_wallet_instance.sync.assert_called_once_with(12345)
            assert result["success"] is True
        finally:
            module.WalletSync = original_wallet

    def test_sync_skills_uses_class(self):
        """sync_skills should delegate to SkillsSync class."""
        module = _load_service_module()

        CharacterSyncService = module.CharacterSyncService
        service = CharacterSyncService(Mock())

        # Patch SkillsSync at module level
        mock_skills_class = MagicMock()
        mock_skills_instance = MagicMock()
        mock_skills_instance.sync.return_value = {"success": True, "skill_count": 100}
        mock_skills_class.return_value = mock_skills_instance

        original_skills = module.SkillsSync
        module.SkillsSync = mock_skills_class

        try:
            result = service.sync_skills(12345)

            mock_skills_instance.sync.assert_called_once_with(12345)
            assert result["success"] is True
        finally:
            module.SkillsSync = original_skills

    def test_module_reduced_in_size(self):
        """Refactored module should be under 150 lines."""
        service_path = Path(__file__).parent.parent.parent.parent / "services" / "character_sync_service.py"
        source = service_path.read_text()
        line_count = len(source.split('\n'))

        assert line_count < 150, f"Module has {line_count} lines, expected < 150"
