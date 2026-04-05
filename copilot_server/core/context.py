"""
Application Context for Dependency Injection.
Centralizes all service initialization and provides FastAPI dependencies.
"""

import logging
from typing import Optional, Union
import asyncpg
import json

from ..llm.anthropic_client import AnthropicClient
from ..llm.openai_client import OpenAIClient
from ..mcp.client import MCPClient
from ..mcp.orchestrator import ToolOrchestrator
from ..agent.sessions import AgentSessionManager
from ..agent.runtime import AgentRuntime
from ..models.user_settings import get_default_settings

logger = logging.getLogger(__name__)


class AppContext:
    """
    Centralized application context holding all service instances.

    Usage:
        context = AppContext()
        await context.initialize(config)

        # In FastAPI routes:
        @router.get("/")
        async def endpoint(ctx: AppContext = Depends(get_app_context)):
            return await ctx.agent_runtime.execute(...)
    """

    def __init__(self):
        self.llm_client: Optional[Union[AnthropicClient, OpenAIClient]] = None
        self.mcp_client: Optional[MCPClient] = None
        self.db_pool: Optional[asyncpg.Pool] = None
        self.session_manager: Optional[AgentSessionManager] = None
        self.agent_runtime: Optional[AgentRuntime] = None
        self._initialized = False

    async def initialize(
        self,
        database_url: str,
        llm_provider: str,
        openai_api_key: Optional[str] = None,
        openai_model: Optional[str] = None
    ) -> None:
        """
        Initialize all services in correct order.

        Args:
            database_url: PostgreSQL connection string
            llm_provider: "anthropic" or "openai"
            openai_api_key: OpenAI API key (if provider is openai)
            openai_model: OpenAI model name (if provider is openai)
        """
        if self._initialized:
            logger.warning("AppContext already initialized")
            return

        # 1. Initialize LLM client
        if llm_provider == "anthropic":
            self.llm_client = AnthropicClient()
            logger.info("Using Anthropic Claude as LLM provider")
        elif llm_provider == "openai":
            self.llm_client = OpenAIClient(
                api_key=openai_api_key,
                model=openai_model
            )
            logger.info(f"Using OpenAI {openai_model} as LLM provider")
        else:
            raise ValueError(f"Unknown LLM provider: {llm_provider}")

        # 2. Initialize MCP client
        self.mcp_client = MCPClient()
        tools = self.mcp_client.get_tools()
        logger.info(f"Loaded {len(tools)} MCP tools")

        # 3. Initialize database pool
        async def init_connection(conn):
            await conn.set_type_codec(
                'jsonb',
                encoder=json.dumps,
                decoder=json.loads,
                schema='pg_catalog'
            )
            await conn.set_type_codec(
                'json',
                encoder=json.dumps,
                decoder=json.loads,
                schema='pg_catalog'
            )

        self.db_pool = await asyncpg.create_pool(
            database_url,
            min_size=2,
            max_size=10,
            init=init_connection
        )
        logger.info("Database pool initialized")

        # 4. Initialize session manager
        self.session_manager = AgentSessionManager()
        await self.session_manager.startup()
        logger.info("Session manager initialized")

        # 5. Initialize agent runtime
        user_settings = get_default_settings(character_id=-1)
        orchestrator = ToolOrchestrator(self.mcp_client, self.llm_client, user_settings)

        self.agent_runtime = AgentRuntime(
            session_manager=self.session_manager,
            llm_client=self.llm_client,
            orchestrator=orchestrator
        )
        logger.info("Agent runtime initialized")

        self._initialized = True

    async def shutdown(self) -> None:
        """Shutdown all services gracefully."""
        if self.session_manager:
            await self.session_manager.shutdown()
            logger.info("Session manager shutdown complete")

        if self.db_pool:
            await self.db_pool.close()
            logger.info("Database pool closed")

        self._initialized = False

    @property
    def is_initialized(self) -> bool:
        return self._initialized


# Global singleton (initialized in main.py startup)
_app_context: Optional[AppContext] = None


def get_app_context() -> AppContext:
    """FastAPI dependency to get the app context."""
    if _app_context is None or not _app_context.is_initialized:
        raise RuntimeError("AppContext not initialized. Call initialize() first.")
    return _app_context


def set_app_context(context: AppContext) -> None:
    """Set the global app context (called from main.py startup)."""
    global _app_context
    _app_context = context
