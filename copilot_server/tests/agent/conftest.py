"""Pytest fixtures for agent tests."""

import pytest
from unittest.mock import MagicMock, AsyncMock


@pytest.fixture
def mock_llm_client():
    """Mock LLM client for testing."""
    client = MagicMock()
    client.model = "test-model"
    client.provider = "anthropic"
    client.build_tool_schema = MagicMock(return_value=[])
    client._stream_response = AsyncMock(return_value=async_generator([]))
    return client


@pytest.fixture
def mock_mcp_client():
    """Mock MCP client for testing."""
    client = MagicMock()
    client.get_tools = MagicMock(return_value=[])
    client.call_tool = MagicMock(return_value={"content": [{"type": "text", "text": "ok"}]})
    return client


@pytest.fixture
def mock_user_settings():
    """Mock user settings for testing."""
    settings = MagicMock()
    settings.autonomy_level = 3
    return settings


@pytest.fixture
def mock_event_bus():
    """Mock EventBus for testing."""
    event_bus = MagicMock()
    # Track published events by session_id
    event_bus._published_events = {}

    async def publish_side_effect(session_id, event):
        """Async publish for event tracking."""
        if session_id not in event_bus._published_events:
            event_bus._published_events[session_id] = []
        event_bus._published_events[session_id].append(event)

    event_bus.publish = AsyncMock(side_effect=publish_side_effect)
    event_bus.get_published_events = lambda session_id: event_bus._published_events.get(session_id, [])

    return event_bus


@pytest.fixture
def mock_orchestrator():
    """Mock orchestrator for testing."""
    orchestrator = AsyncMock()
    orchestrator.mcp = MagicMock()
    orchestrator.mcp.get_tools.return_value = []
    return orchestrator


async def async_generator(items):
    """Helper to create async generator from list."""
    for item in items:
        yield item
