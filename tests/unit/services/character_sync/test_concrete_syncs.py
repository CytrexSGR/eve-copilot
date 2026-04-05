"""Test concrete sync operation classes."""
import pytest
from pathlib import Path
import importlib.util
import sys
from unittest.mock import Mock, MagicMock
from types import ModuleType


# Modules that get mocked during test loading - must be restored after
_POISONED_MODULES = [
    'src.database', 'src.core.exceptions', 'src.services.character.service',
    'psycopg2.extras', 'services.character_sync.base', 'services',
    'services.character_sync', 'services.character_sync.wallet_sync',
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
    global _base_sync_class, _wallet_sync_class, _skills_sync_class, _assets_sync_class
    global _skill_queue_sync_class, _orders_sync_class, _industry_jobs_sync_class, _blueprints_sync_class
    _base_sync_class = None
    _wallet_sync_class = None
    _skills_sync_class = None
    _assets_sync_class = None
    _skill_queue_sync_class = None
    _orders_sync_class = None
    _industry_jobs_sync_class = None
    _blueprints_sync_class = None
    for key in _POISONED_MODULES:
        if saved[key] is not None:
            sys.modules[key] = saved[key]
        else:
            sys.modules.pop(key, None)


# Cache for loaded modules
_base_sync_class = None
_wallet_sync_class = None
_skills_sync_class = None
_assets_sync_class = None


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


def _load_wallet_sync():
    """Load WalletSync class."""
    global _wallet_sync_class
    if _wallet_sync_class is not None:
        return _wallet_sync_class

    # Ensure base is loaded first
    _load_base_sync()

    wallet_path = Path(__file__).parent.parent.parent.parent.parent / "services" / "character_sync" / "wallet_sync.py"
    spec = importlib.util.spec_from_file_location("services.character_sync.wallet_sync", wallet_path)
    wallet_module = importlib.util.module_from_spec(spec)
    sys.modules['services.character_sync.wallet_sync'] = wallet_module
    spec.loader.exec_module(wallet_module)

    _wallet_sync_class = wallet_module.WalletSync
    return _wallet_sync_class


def _load_skills_sync():
    """Load SkillsSync class."""
    global _skills_sync_class
    if _skills_sync_class is not None:
        return _skills_sync_class

    # Ensure base is loaded first
    _load_base_sync()

    skills_path = Path(__file__).parent.parent.parent.parent.parent / "services" / "character_sync" / "skills_sync.py"
    spec = importlib.util.spec_from_file_location("services.character_sync.skills_sync", skills_path)
    skills_module = importlib.util.module_from_spec(spec)
    sys.modules['services.character_sync.skills_sync'] = skills_module
    spec.loader.exec_module(skills_module)

    _skills_sync_class = skills_module.SkillsSync
    return _skills_sync_class


def _load_assets_sync():
    """Load AssetsSync class."""
    global _assets_sync_class
    if _assets_sync_class is not None:
        return _assets_sync_class

    # Ensure base is loaded first
    _load_base_sync()

    assets_path = Path(__file__).parent.parent.parent.parent.parent / "services" / "character_sync" / "assets_sync.py"
    spec = importlib.util.spec_from_file_location("services.character_sync.assets_sync", assets_path)
    assets_module = importlib.util.module_from_spec(spec)
    sys.modules['services.character_sync.assets_sync'] = assets_module
    spec.loader.exec_module(assets_module)

    _assets_sync_class = assets_module.AssetsSync
    return _assets_sync_class


class TestWalletSync:
    """Test WalletSync operation."""

    def test_extends_base(self):
        BaseSyncOperation = _load_base_sync()
        WalletSync = _load_wallet_sync()

        assert issubclass(WalletSync, BaseSyncOperation)

    def test_get_sync_column_returns_wallets(self):
        WalletSync = _load_wallet_sync()

        sync = WalletSync(Mock())
        assert sync.get_sync_column() == "wallets_synced_at"

    def test_fetch_calls_character_service(self):
        WalletSync = _load_wallet_sync()

        mock_service = Mock()
        mock_balance = Mock()
        mock_balance.balance = 1000000.0
        mock_service.get_wallet_balance.return_value = mock_balance

        sync = WalletSync(mock_service)
        result = sync.fetch_from_esi(12345)

        mock_service.get_wallet_balance.assert_called_once_with(12345)

    def test_transform_data_extracts_balance(self):
        WalletSync = _load_wallet_sync()

        mock_service = Mock()
        sync = WalletSync(mock_service)

        mock_data = Mock()
        mock_data.balance = 5000000.0

        result = sync.transform_data(mock_data)
        assert result == 5000000.0

    def test_get_result_key_returns_balance(self):
        WalletSync = _load_wallet_sync()

        sync = WalletSync(Mock())
        assert sync.get_result_key() == "balance"

    def test_get_result_value_returns_balance_directly(self):
        WalletSync = _load_wallet_sync()

        sync = WalletSync(Mock())
        result = sync.get_result_value(1234567.89)
        assert result == 1234567.89


class TestSkillsSync:
    """Test SkillsSync operation."""

    def test_extends_base(self):
        BaseSyncOperation = _load_base_sync()
        SkillsSync = _load_skills_sync()

        assert issubclass(SkillsSync, BaseSyncOperation)

    def test_get_sync_column_returns_skills(self):
        SkillsSync = _load_skills_sync()

        sync = SkillsSync(Mock())
        assert sync.get_sync_column() == "skills_synced_at"

    def test_fetch_calls_character_service(self):
        SkillsSync = _load_skills_sync()

        mock_service = Mock()
        mock_skills = Mock()
        mock_skills.skills = []
        mock_skills.total_sp = 10000000
        mock_skills.unallocated_sp = 5000
        mock_service.get_skills.return_value = mock_skills

        sync = SkillsSync(mock_service)
        result = sync.fetch_from_esi(12345)

        mock_service.get_skills.assert_called_once_with(12345)

    def test_transform_data_extracts_skills_and_stores_sp(self):
        SkillsSync = _load_skills_sync()

        mock_service = Mock()
        sync = SkillsSync(mock_service)

        # Create mock skill objects with model_dump method
        mock_skill1 = Mock()
        mock_skill1.model_dump.return_value = {"skill_id": 1, "level": 5}
        mock_skill2 = Mock()
        mock_skill2.model_dump.return_value = {"skill_id": 2, "level": 3}

        mock_data = Mock()
        mock_data.skills = [mock_skill1, mock_skill2]
        mock_data.total_sp = 10000000
        mock_data.unallocated_sp = 5000

        result = sync.transform_data(mock_data)

        assert len(result) == 2
        assert result[0] == {"skill_id": 1, "level": 5}
        assert result[1] == {"skill_id": 2, "level": 3}
        assert sync._total_sp == 10000000
        assert sync._unallocated_sp == 5000

    def test_get_result_key_returns_skill_count(self):
        SkillsSync = _load_skills_sync()

        sync = SkillsSync(Mock())
        assert sync.get_result_key() == "skill_count"


class TestAssetsSync:
    """Test AssetsSync operation."""

    def test_extends_base(self):
        BaseSyncOperation = _load_base_sync()
        AssetsSync = _load_assets_sync()

        assert issubclass(AssetsSync, BaseSyncOperation)

    def test_get_sync_column_returns_assets(self):
        AssetsSync = _load_assets_sync()

        sync = AssetsSync(Mock())
        assert sync.get_sync_column() == "assets_synced_at"

    def test_fetch_calls_character_service(self):
        AssetsSync = _load_assets_sync()

        mock_service = Mock()
        mock_assets = Mock()
        mock_assets.assets = []
        mock_service.get_assets.return_value = mock_assets

        sync = AssetsSync(mock_service)
        result = sync.fetch_from_esi(12345)

        mock_service.get_assets.assert_called_once_with(12345)

    def test_transform_data_adds_type_names(self):
        AssetsSync = _load_assets_sync()

        # Set up the mock for get_item_info - use "Test Item" as that's what's set during module loading
        # The mock is set at module load time in _setup_mocks()
        sys.modules['src.database'].get_item_info = MagicMock(return_value={"typeName": "Test Item"})

        mock_service = Mock()
        sync = AssetsSync(mock_service)

        # Create mock asset with model_dump method
        mock_asset = Mock()
        mock_asset.model_dump.return_value = {
            "item_id": 100,
            "type_id": 34,
            "location_id": 60003760,
            "quantity": 1000
        }

        mock_data = Mock()
        mock_data.assets = [mock_asset]

        result = sync.transform_data(mock_data)

        assert len(result) == 1
        assert result[0]["type_name"] == "Test Item"
        assert result[0]["type_id"] == 34

    def test_get_result_key_returns_asset_count(self):
        AssetsSync = _load_assets_sync()

        sync = AssetsSync(Mock())
        assert sync.get_result_key() == "asset_count"


# Cache for new sync classes
_skill_queue_sync_class = None
_orders_sync_class = None
_industry_jobs_sync_class = None
_blueprints_sync_class = None


def _load_skill_queue_sync():
    """Load SkillQueueSync class."""
    global _skill_queue_sync_class
    if _skill_queue_sync_class is not None:
        return _skill_queue_sync_class

    # Ensure base is loaded first
    _load_base_sync()

    skill_queue_path = Path(__file__).parent.parent.parent.parent.parent / "services" / "character_sync" / "skill_queue_sync.py"
    spec = importlib.util.spec_from_file_location("services.character_sync.skill_queue_sync", skill_queue_path)
    skill_queue_module = importlib.util.module_from_spec(spec)
    sys.modules['services.character_sync.skill_queue_sync'] = skill_queue_module
    spec.loader.exec_module(skill_queue_module)

    _skill_queue_sync_class = skill_queue_module.SkillQueueSync
    return _skill_queue_sync_class


def _load_orders_sync():
    """Load OrdersSync class."""
    global _orders_sync_class
    if _orders_sync_class is not None:
        return _orders_sync_class

    # Ensure base is loaded first
    _load_base_sync()

    orders_path = Path(__file__).parent.parent.parent.parent.parent / "services" / "character_sync" / "orders_sync.py"
    spec = importlib.util.spec_from_file_location("services.character_sync.orders_sync", orders_path)
    orders_module = importlib.util.module_from_spec(spec)
    sys.modules['services.character_sync.orders_sync'] = orders_module
    spec.loader.exec_module(orders_module)

    _orders_sync_class = orders_module.OrdersSync
    return _orders_sync_class


def _load_industry_jobs_sync():
    """Load IndustryJobsSync class."""
    global _industry_jobs_sync_class
    if _industry_jobs_sync_class is not None:
        return _industry_jobs_sync_class

    # Ensure base is loaded first
    _load_base_sync()

    industry_jobs_path = Path(__file__).parent.parent.parent.parent.parent / "services" / "character_sync" / "industry_jobs_sync.py"
    spec = importlib.util.spec_from_file_location("services.character_sync.industry_jobs_sync", industry_jobs_path)
    industry_jobs_module = importlib.util.module_from_spec(spec)
    sys.modules['services.character_sync.industry_jobs_sync'] = industry_jobs_module
    spec.loader.exec_module(industry_jobs_module)

    _industry_jobs_sync_class = industry_jobs_module.IndustryJobsSync
    return _industry_jobs_sync_class


def _load_blueprints_sync():
    """Load BlueprintsSync class."""
    global _blueprints_sync_class
    if _blueprints_sync_class is not None:
        return _blueprints_sync_class

    # Ensure base is loaded first
    _load_base_sync()

    blueprints_path = Path(__file__).parent.parent.parent.parent.parent / "services" / "character_sync" / "blueprints_sync.py"
    spec = importlib.util.spec_from_file_location("services.character_sync.blueprints_sync", blueprints_path)
    blueprints_module = importlib.util.module_from_spec(spec)
    sys.modules['services.character_sync.blueprints_sync'] = blueprints_module
    spec.loader.exec_module(blueprints_module)

    _blueprints_sync_class = blueprints_module.BlueprintsSync
    return _blueprints_sync_class


class TestSkillQueueSync:
    """Test SkillQueueSync operation."""

    def test_extends_base(self):
        BaseSyncOperation = _load_base_sync()
        SkillQueueSync = _load_skill_queue_sync()

        assert issubclass(SkillQueueSync, BaseSyncOperation)

    def test_get_sync_column(self):
        SkillQueueSync = _load_skill_queue_sync()

        sync = SkillQueueSync(Mock())
        assert sync.get_sync_column() == "skill_queue_synced_at"

    def test_fetch_calls_character_service(self):
        SkillQueueSync = _load_skill_queue_sync()

        mock_service = Mock()
        mock_queue = Mock()
        mock_queue.queue = []
        mock_service.get_skill_queue.return_value = mock_queue

        sync = SkillQueueSync(mock_service)
        result = sync.fetch_from_esi(12345)

        mock_service.get_skill_queue.assert_called_once_with(12345)

    def test_get_result_key_returns_queue_length(self):
        SkillQueueSync = _load_skill_queue_sync()

        sync = SkillQueueSync(Mock())
        assert sync.get_result_key() == "queue_length"

    def test_parse_datetime_handles_z_suffix(self):
        SkillQueueSync = _load_skill_queue_sync()

        sync = SkillQueueSync(Mock())
        result = sync._parse_datetime("2024-01-15T10:30:00Z")
        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_parse_datetime_handles_none(self):
        SkillQueueSync = _load_skill_queue_sync()

        sync = SkillQueueSync(Mock())
        result = sync._parse_datetime(None)
        assert result is None


class TestOrdersSync:
    """Test OrdersSync operation."""

    def test_extends_base(self):
        BaseSyncOperation = _load_base_sync()
        OrdersSync = _load_orders_sync()

        assert issubclass(OrdersSync, BaseSyncOperation)

    def test_get_sync_column(self):
        OrdersSync = _load_orders_sync()

        sync = OrdersSync(Mock())
        assert sync.get_sync_column() == "orders_synced_at"

    def test_fetch_calls_character_service(self):
        OrdersSync = _load_orders_sync()

        mock_service = Mock()
        mock_orders = Mock()
        mock_orders.orders = []
        mock_service.get_market_orders.return_value = mock_orders

        sync = OrdersSync(mock_service)
        result = sync.fetch_from_esi(12345)

        mock_service.get_market_orders.assert_called_once_with(12345)

    def test_get_result_key_returns_order_count(self):
        OrdersSync = _load_orders_sync()

        sync = OrdersSync(Mock())
        assert sync.get_result_key() == "order_count"


class TestIndustryJobsSync:
    """Test IndustryJobsSync operation."""

    def test_extends_base(self):
        BaseSyncOperation = _load_base_sync()
        IndustryJobsSync = _load_industry_jobs_sync()

        assert issubclass(IndustryJobsSync, BaseSyncOperation)

    def test_get_sync_column(self):
        IndustryJobsSync = _load_industry_jobs_sync()

        sync = IndustryJobsSync(Mock())
        assert sync.get_sync_column() == "industry_jobs_synced_at"

    def test_fetch_calls_character_service_with_include_completed(self):
        IndustryJobsSync = _load_industry_jobs_sync()

        mock_service = Mock()
        mock_jobs = Mock()
        mock_jobs.jobs = []
        mock_service.get_industry_jobs.return_value = mock_jobs

        sync = IndustryJobsSync(mock_service)
        result = sync.fetch_from_esi(12345)

        mock_service.get_industry_jobs.assert_called_once_with(12345, include_completed=True)

    def test_get_result_key_returns_job_count(self):
        IndustryJobsSync = _load_industry_jobs_sync()

        sync = IndustryJobsSync(Mock())
        assert sync.get_result_key() == "job_count"

    def test_has_activity_names_constant(self):
        IndustryJobsSync = _load_industry_jobs_sync()

        # Verify ACTIVITY_NAMES is available
        from services.character_sync import industry_jobs_sync
        assert hasattr(industry_jobs_sync, 'ACTIVITY_NAMES')
        assert industry_jobs_sync.ACTIVITY_NAMES[1] == "Manufacturing"
        assert industry_jobs_sync.ACTIVITY_NAMES[8] == "Invention"


class TestBlueprintsSync:
    """Test BlueprintsSync operation."""

    def test_extends_base(self):
        BaseSyncOperation = _load_base_sync()
        BlueprintsSync = _load_blueprints_sync()

        assert issubclass(BlueprintsSync, BaseSyncOperation)

    def test_get_sync_column(self):
        BlueprintsSync = _load_blueprints_sync()

        sync = BlueprintsSync(Mock())
        assert sync.get_sync_column() == "blueprints_synced_at"

    def test_fetch_calls_character_service(self):
        BlueprintsSync = _load_blueprints_sync()

        mock_service = Mock()
        mock_blueprints = Mock()
        mock_blueprints.blueprints = []
        mock_service.get_blueprints.return_value = mock_blueprints

        sync = BlueprintsSync(mock_service)
        result = sync.fetch_from_esi(12345)

        mock_service.get_blueprints.assert_called_once_with(12345)

    def test_get_result_key_returns_blueprint_count(self):
        BlueprintsSync = _load_blueprints_sync()

        sync = BlueprintsSync(Mock())
        assert sync.get_result_key() == "blueprint_count"
