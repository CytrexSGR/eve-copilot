"""Tests for AppContext."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from copilot_server.core.context import AppContext, get_app_context, set_app_context


class TestAppContext:
    """Tests for AppContext initialization."""

    def test_initial_state(self):
        """Context starts uninitialized."""
        ctx = AppContext()
        assert ctx.llm_client is None
        assert ctx.mcp_client is None
        assert ctx.db_pool is None
        assert ctx.session_manager is None
        assert ctx.agent_runtime is None
        assert ctx.is_initialized is False

    def test_get_context_before_init_raises(self):
        """get_app_context raises if not initialized."""
        set_app_context(AppContext())
        with pytest.raises(RuntimeError, match="not initialized"):
            get_app_context()

    @pytest.mark.asyncio
    async def test_double_init_warns(self):
        """Double initialization logs warning."""
        ctx = AppContext()
        ctx._initialized = True

        with patch('copilot_server.core.context.logger') as mock_logger:
            await ctx.initialize("postgres://...", "anthropic")
            mock_logger.warning.assert_called_once()

    def test_set_and_get_context(self):
        """set_app_context and get_app_context work together."""
        ctx = AppContext()
        ctx._initialized = True  # Simulate initialized state
        set_app_context(ctx)

        result = get_app_context()
        assert result is ctx

    def test_is_initialized_property(self):
        """is_initialized reflects internal state."""
        ctx = AppContext()
        assert ctx.is_initialized is False

        ctx._initialized = True
        assert ctx.is_initialized is True

        ctx._initialized = False
        assert ctx.is_initialized is False

    def test_get_context_with_none_context_raises(self):
        """get_app_context raises if context is None."""
        set_app_context(None)
        with pytest.raises(RuntimeError, match="not initialized"):
            get_app_context()


class TestAppContextShutdown:
    """Tests for AppContext shutdown."""

    @pytest.mark.asyncio
    async def test_shutdown_with_no_services(self):
        """Shutdown gracefully handles uninitialized services."""
        ctx = AppContext()
        # Should not raise even when services are None
        await ctx.shutdown()
        assert ctx.is_initialized is False

    @pytest.mark.asyncio
    async def test_shutdown_clears_initialized_flag(self):
        """Shutdown sets is_initialized to False."""
        ctx = AppContext()
        ctx._initialized = True
        await ctx.shutdown()
        assert ctx.is_initialized is False
