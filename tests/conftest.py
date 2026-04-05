import pytest


def _is_db_available():
    """Check if the database is reachable."""
    try:
        from src.database import get_db_connection
        with get_db_connection() as conn:
            conn.cursor().execute("SELECT 1")
        return True
    except Exception:
        return False


# Cache the result so we only check once per session
_db_available = None


def db_available():
    global _db_available
    if _db_available is None:
        _db_available = _is_db_available()
    return _db_available


def pytest_collection_modifyitems(config, items):
    """Auto-skip tests that require DB when DB is unavailable."""
    if db_available():
        return
    skip_db = pytest.mark.skip(reason="Database not available (host environment)")
    for item in items:
        # Skip tests explicitly marked requires_db
        if "requires_db" in item.keywords:
            item.add_marker(skip_db)
        # Skip all integration tests
        if "integration" in item.keywords:
            item.add_marker(skip_db)
        # Skip tests in integration/ directory
        if "/integration/" in str(item.fspath):
            item.add_marker(skip_db)


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    """Prevent settings lru_cache from leaking between tests."""
    from src.core.config import get_settings
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
