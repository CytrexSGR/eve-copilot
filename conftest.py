"""
Root conftest.py — pre-stubs external/infrastructure modules so that
services/zkillboard unit tests can be collected without a live database,
Redis, or Telegram service.

This conftest is loaded by pytest before any test collection begins,
ensuring that module-level instantiations in services/zkillboard/ (e.g.
RedisStateManager()) never attempt real connections.
"""

import sys
from unittest.mock import MagicMock


def _stub_if_missing(module_name: str) -> None:
    """Install a MagicMock stub only if the module cannot be imported for real."""
    if module_name in sys.modules:
        return
    try:
        __import__(module_name)
    except (ModuleNotFoundError, ImportError):
        sys.modules[module_name] = MagicMock()


# --- src.* stubs (no such package outside Docker) ---
_src_modules = [
    "src",
    "src.database",
    "src.route_service",
    "src.telegram_service",
    "src.auth",
    "src.core",
    "src.core.config",
]
for _mod in _src_modules:
    _stub_if_missing(_mod)

# --- Redis: stub Redis.ping() so state_manager module-level init passes ---
try:
    import redis as _redis_pkg  # real redis is installed

    _orig_redis_cls = _redis_pkg.Redis

    class _MockRedis(_orig_redis_cls):
        """Drop-in that skips real network connection in test environments."""

        def __init__(self, *args, **kwargs):
            # Don't call super().__init__ — avoid real socket creation
            pass

        def ping(self):
            return True

    _redis_pkg.Redis = _MockRedis
except ImportError:
    # redis not installed at all — stub the whole package
    _redis_pkg = MagicMock()
    sys.modules.setdefault("redis", _redis_pkg)
    sys.modules.setdefault("redis.asyncio", MagicMock())
