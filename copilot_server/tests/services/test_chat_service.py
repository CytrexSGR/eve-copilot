"""Tests for ChatService."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from copilot_server.services.chat_service import ChatService
from copilot_server.agent.messages import AgentMessage


class TestChatService:
    """Tests for ChatService."""

    @pytest.fixture
    def mock_deps(self):
        """Create mock dependencies."""
        return {
            "session_manager": AsyncMock(),
            "runtime": AsyncMock(),
            "db_pool": MagicMock(),
            "llm_client": MagicMock(),
            "mcp_client": MagicMock()
        }

    @pytest.fixture
    def service(self, mock_deps):
        """Create ChatService with mocks."""
        return ChatService(**mock_deps)

    @pytest.mark.asyncio
    async def test_get_or_create_session_creates_new(self, service, mock_deps):
        """Creates new session when no session_id."""
        mock_session = MagicMock()
        mock_deps["session_manager"].create_session.return_value = mock_session

        result = await service.get_or_create_session(None, character_id=123)

        assert result == mock_session
        mock_deps["session_manager"].create_session.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_or_create_session_loads_existing(self, service, mock_deps):
        """Loads existing session when session_id provided."""
        mock_session = MagicMock()
        mock_deps["session_manager"].load_session.return_value = mock_session

        result = await service.get_or_create_session("sess-123", character_id=123)

        assert result == mock_session
        mock_deps["session_manager"].load_session.assert_called_with("sess-123")

    @pytest.mark.asyncio
    async def test_get_or_create_session_raises_if_not_found(self, service, mock_deps):
        """Raises ValueError if session not found."""
        mock_deps["session_manager"].load_session.return_value = None

        with pytest.raises(ValueError, match="Session not found"):
            await service.get_or_create_session("invalid-id", character_id=123)

    @pytest.mark.asyncio
    async def test_save_user_message(self, service, mock_deps):
        """Saves user message to database."""
        # Setup mock connection and repo
        mock_conn = AsyncMock()
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=None)
        mock_deps["db_pool"].acquire.return_value = mock_conn

        with patch('copilot_server.services.chat_service.MessageRepository') as MockRepo:
            mock_repo_instance = AsyncMock()
            MockRepo.return_value = mock_repo_instance

            result = await service.save_user_message("sess-123", "Hello, world!")

            # Verify message was created with correct attributes
            assert result.session_id == "sess-123"
            assert result.role == "user"
            assert result.content == "Hello, world!"
            mock_repo_instance.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_assistant_message(self, service, mock_deps):
        """Saves assistant message with content blocks."""
        # Setup mock connection
        mock_conn = AsyncMock()
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=None)
        mock_deps["db_pool"].acquire.return_value = mock_conn

        content_blocks = [{"type": "text", "text": "Response"}]
        token_usage = {"input_tokens": 100, "output_tokens": 50}

        with patch('copilot_server.services.chat_service.MessageRepository') as MockRepo:
            mock_repo_instance = AsyncMock()
            MockRepo.return_value = mock_repo_instance

            result = await service.save_assistant_message(
                "sess-123",
                "Response",
                content_blocks=content_blocks,
                token_usage=token_usage
            )

            assert result.session_id == "sess-123"
            assert result.role == "assistant"
            assert result.content == "Response"
            assert result.token_usage == token_usage
            mock_repo_instance.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_chat(self, service, mock_deps):
        """Executes chat via runtime."""
        mock_session = MagicMock()
        mock_deps["runtime"].execute.return_value = {"response": "test"}

        result = await service.execute_chat(mock_session)

        assert result == {"response": "test"}
        mock_deps["runtime"].execute.assert_called_once_with(mock_session)

    @pytest.mark.asyncio
    async def test_get_chat_history(self, service, mock_deps):
        """Gets chat history from database."""
        # Setup mock connection
        mock_conn = AsyncMock()
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=None)
        mock_deps["db_pool"].acquire.return_value = mock_conn

        # Create mock messages
        mock_messages = [
            AgentMessage(
                id="msg-1",
                session_id="sess-123",
                role="user",
                content="Hello",
                content_blocks=[],
                created_at=datetime(2024, 1, 1, 12, 0, 0),
                token_usage=None
            ),
            AgentMessage(
                id="msg-2",
                session_id="sess-123",
                role="assistant",
                content="Hi there!",
                content_blocks=[{"type": "text", "text": "Hi there!"}],
                created_at=datetime(2024, 1, 1, 12, 0, 1),
                token_usage={"input_tokens": 10, "output_tokens": 5}
            )
        ]

        with patch('copilot_server.services.chat_service.MessageRepository') as MockRepo:
            mock_repo_instance = AsyncMock()
            mock_repo_instance.get_by_session.return_value = mock_messages
            MockRepo.return_value = mock_repo_instance

            result = await service.get_chat_history("sess-123", limit=50)

            assert len(result) == 2
            assert result[0]["id"] == "msg-1"
            assert result[0]["role"] == "user"
            assert result[0]["content"] == "Hello"
            assert result[1]["id"] == "msg-2"
            assert result[1]["role"] == "assistant"
            assert result[1]["token_usage"] == {"input_tokens": 10, "output_tokens": 5}
            mock_repo_instance.get_by_session.assert_called_once_with("sess-123", 50)

    @pytest.mark.asyncio
    async def test_get_chat_history_default_limit(self, service, mock_deps):
        """Uses default limit of 100 for chat history."""
        mock_conn = AsyncMock()
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=None)
        mock_deps["db_pool"].acquire.return_value = mock_conn

        with patch('copilot_server.services.chat_service.MessageRepository') as MockRepo:
            mock_repo_instance = AsyncMock()
            mock_repo_instance.get_by_session.return_value = []
            MockRepo.return_value = mock_repo_instance

            await service.get_chat_history("sess-123")

            mock_repo_instance.get_by_session.assert_called_once_with("sess-123", 100)
