"""
Chat Service - Business logic for agent chat operations.
Extracted from agent_routes.py to separate concerns.
"""

import logging
from typing import Optional, AsyncIterator, Dict, Any, List

from ..agent.sessions import AgentSessionManager
from ..agent.runtime import AgentRuntime
from ..agent.messages import AgentMessage, MessageRepository
from ..agent.agentic_loop import AgenticStreamingLoop
from ..agent.streaming import SSEFormatter
from ..models.user_settings import get_default_settings, UserSettings
from ..config import SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class ChatService:
    """
    Service layer for chat operations.

    Responsibilities:
    - Session management (create, load)
    - Message persistence
    - Agent execution orchestration
    - Streaming response generation
    """

    def __init__(
        self,
        session_manager: AgentSessionManager,
        runtime: AgentRuntime,
        db_pool,
        llm_client,
        mcp_client
    ):
        """
        Initialize ChatService.

        Args:
            session_manager: AgentSessionManager for session operations
            runtime: AgentRuntime for executing agent workflows
            db_pool: asyncpg connection pool for message persistence
            llm_client: LLM client (Anthropic or OpenAI)
            mcp_client: MCP client for tool execution
        """
        self.session_manager = session_manager
        self.runtime = runtime
        self.db_pool = db_pool
        self.llm_client = llm_client
        self.mcp_client = mcp_client

    async def get_or_create_session(
        self,
        session_id: Optional[str],
        character_id: int
    ):
        """
        Load existing session or create new one.

        Args:
            session_id: Existing session ID (optional)
            character_id: EVE character ID

        Returns:
            AgentSession

        Raises:
            ValueError: If session_id provided but not found
        """
        if session_id:
            session = await self.session_manager.load_session(session_id)
            if not session:
                raise ValueError(f"Session not found: {session_id}")
            return session

        # Create new session
        user_settings = get_default_settings(character_id=character_id or -1)
        session = await self.session_manager.create_session(
            character_id=character_id,
            autonomy_level=user_settings.autonomy_level
        )
        return session

    async def save_user_message(
        self,
        session_id: str,
        content: str
    ) -> AgentMessage:
        """
        Persist user message to database.

        Args:
            session_id: Session ID
            content: Message content

        Returns:
            Saved AgentMessage
        """
        async with self.db_pool.acquire() as conn:
            repo = MessageRepository(conn)
            message = AgentMessage.create(
                session_id=session_id,
                role="user",
                content=content
            )
            await repo.save(message)
            return message

    async def save_assistant_message(
        self,
        session_id: str,
        content: str,
        content_blocks: Optional[List[Dict[str, Any]]] = None,
        token_usage: Optional[Dict[str, int]] = None
    ) -> AgentMessage:
        """
        Persist assistant message to database.

        Args:
            session_id: Session ID
            content: Text content
            content_blocks: Raw content blocks (optional)
            token_usage: Token usage stats (optional)

        Returns:
            Saved AgentMessage
        """
        async with self.db_pool.acquire() as conn:
            repo = MessageRepository(conn)
            message = AgentMessage.create(
                session_id=session_id,
                role="assistant",
                content=content,
                content_blocks=content_blocks
            )
            if token_usage:
                message.token_usage = token_usage
            await repo.save(message)
            return message

    async def execute_chat(self, session) -> Optional[Dict[str, Any]]:
        """
        Execute agent runtime for chat.

        Args:
            session: AgentSession

        Returns:
            Response dict or None
        """
        return await self.runtime.execute(session)

    async def stream_chat(
        self,
        session,
        character_id: int
    ) -> AsyncIterator[str]:
        """
        Stream chat response via SSE with tool execution.

        Args:
            session: AgentSession
            character_id: EVE character ID

        Yields:
            SSE formatted events
        """
        formatter = SSEFormatter()
        full_response = ""
        tool_calls_executed = []

        try:
            messages = session.get_messages_for_api()
            user_settings = get_default_settings(character_id=character_id or -1)

            loop = AgenticStreamingLoop(
                llm_client=self.llm_client,
                mcp_client=self.mcp_client,
                user_settings=user_settings,
                max_iterations=5,
                event_bus=self.session_manager.event_bus if self.session_manager else None
            )

            async for event in loop.execute(
                messages=messages,
                system=SYSTEM_PROMPT,
                session_id=session.id
            ):
                event_type = event.get("type")

                if event_type == "text":
                    text = event.get("text", "")
                    full_response += text
                    yield formatter.format_text_chunk(text)

                elif event_type == "thinking":
                    yield formatter.format({
                        "type": "thinking",
                        "iteration": event.get("iteration")
                    })

                elif event_type == "tool_call_started":
                    yield formatter.format({
                        "type": "tool_call_started",
                        "tool": event.get("tool"),
                        "arguments": event.get("arguments")
                    })

                elif event_type == "tool_call_completed":
                    tool_calls_executed.append({
                        "tool": event.get("tool"),
                        "result": event.get("result")
                    })
                    yield formatter.format({
                        "type": "tool_call_completed",
                        "tool": event.get("tool")
                    })

                elif event_type == "authorization_denied":
                    yield formatter.format({
                        "type": "authorization_denied",
                        "tool": event.get("tool"),
                        "reason": event.get("reason")
                    })

                elif event_type == "error":
                    yield formatter.format_error(event.get("error", "Unknown error"))
                    return

                elif event_type == "done":
                    break

            # Save assistant response
            content_blocks = [{"type": "text", "text": full_response}]
            if tool_calls_executed:
                content_blocks.append({"type": "tool_calls", "tool_calls": tool_calls_executed})

            message = await self.save_assistant_message(
                session_id=session.id,
                content=full_response,
                content_blocks=content_blocks
            )

            yield formatter.format_done(message.id)

        except Exception as e:
            logger.error(f"Chat streaming error: {e}", exc_info=True)
            yield formatter.format_error(str(e))

    async def get_chat_history(
        self,
        session_id: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get chat history for session.

        Args:
            session_id: Session ID
            limit: Max messages to return

        Returns:
            List of message dicts
        """
        async with self.db_pool.acquire() as conn:
            repo = MessageRepository(conn)
            messages = await repo.get_by_session(session_id, limit)

        return [
            {
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "content_blocks": msg.content_blocks,
                "created_at": msg.created_at.isoformat(),
                "token_usage": msg.token_usage
            }
            for msg in messages
        ]
