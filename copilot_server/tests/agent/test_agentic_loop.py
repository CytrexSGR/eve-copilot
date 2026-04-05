import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from copilot_server.agent.agentic_loop import AgenticStreamingLoop
from copilot_server.models.user_settings import UserSettings, AutonomyLevel
from copilot_server.agent.events import AgentEventType
from copilot_server.core.enums import RiskLevel


async def async_gen(items):
    """Helper to create async generator from list."""
    for item in items:
        yield item


@pytest.mark.asyncio
async def test_execute_single_tool_call():
    """Test loop that executes one tool and returns answer."""
    # Mock dependencies
    llm_client = Mock()
    llm_client.model = "claude-3-5-sonnet-20241022"
    llm_client.build_tool_schema = Mock(return_value=[])

    # First response: tool call
    async def mock_stream(*args, **kwargs):
        for event in [
            {"type": "content_block_start", "index": 0, "content_block": {"type": "text"}},
            {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "Let me check"}},
            {"type": "content_block_stop", "index": 0},
            {"type": "content_block_start", "index": 1, "content_block": {"type": "tool_use", "id": "toolu_1", "name": "get_market_prices"}},
            {"type": "content_block_delta", "index": 1, "delta": {"type": "input_json_delta", "partial_json": '{}'}},
            {"type": "content_block_stop", "index": 1},
            {"type": "message_stop"}
        ]:
            yield event

    llm_client._stream_response = mock_stream

    mcp_client = Mock()
    mcp_client.call_tool = Mock(return_value={"content": [{"type": "text", "text": "Price: 5.50 ISK"}]})
    mcp_client.get_tools = Mock(return_value=[])

    user_settings = UserSettings(character_id=123, autonomy_level=AutonomyLevel.RECOMMENDATIONS)

    loop = AgenticStreamingLoop(llm_client, mcp_client, user_settings)

    events = []
    async for event in loop.execute([{"role": "user", "content": "What is price of Tritanium?"}]):
        events.append(event)

    # Should emit: text chunk, tool_call_started, tool_call_completed, final answer
    assert any(e["type"] == "text" for e in events)
    assert any(e["type"] == "tool_call_started" for e in events)
    assert any(e["type"] == "tool_call_completed" for e in events)


@pytest.mark.asyncio
async def test_multiple_iterations():
    """Test loop handles multiple iterations correctly."""
    llm_client = Mock()
    llm_client.model = "claude-3-5-sonnet-20241022"
    llm_client.build_tool_schema = Mock(return_value=[])

    # Track how many times we stream
    call_count = [0]

    async def mock_stream(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            # First iteration: request a tool (use a known READ_ONLY tool)
            for event in [
                {"type": "content_block_start", "index": 0, "content_block": {"type": "tool_use", "id": "t1", "name": "get_market_prices"}},
                {"type": "content_block_delta", "index": 0, "delta": {"type": "input_json_delta", "partial_json": '{}'}},
                {"type": "content_block_stop", "index": 0},
                {"type": "message_stop"}
            ]:
                yield event
        else:
            # Second iteration: final answer (no tools)
            for event in [
                {"type": "content_block_start", "index": 0, "content_block": {"type": "text"}},
                {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "Done"}},
                {"type": "content_block_stop", "index": 0},
                {"type": "message_stop"}
            ]:
                yield event

    llm_client._stream_response = mock_stream

    mcp_client = Mock()
    mcp_client.call_tool = Mock(return_value={"content": [{"type": "text", "text": "Result"}]})
    mcp_client.get_tools = Mock(return_value=[])

    user_settings = UserSettings(character_id=123, autonomy_level=AutonomyLevel.RECOMMENDATIONS)

    loop = AgenticStreamingLoop(llm_client, mcp_client, user_settings)

    events = []
    async for event in loop.execute([{"role": "user", "content": "Test"}]):
        events.append(event)

    # Should have 2 thinking events (2 iterations)
    thinking_events = [e for e in events if e["type"] == "thinking"]
    assert len(thinking_events) == 2
    assert thinking_events[0]["iteration"] == 1
    assert thinking_events[1]["iteration"] == 2

    # Should have tool execution events
    assert any(e["type"] == "tool_call_started" for e in events)
    assert any(e["type"] == "tool_call_completed" for e in events)

    # Should have done event
    assert any(e["type"] == "done" for e in events)


@pytest.mark.asyncio
async def test_authorization_denial():
    """Test that unauthorized tools are blocked."""
    llm_client = Mock()
    llm_client.model = "claude-3-5-sonnet-20241022"
    llm_client.build_tool_schema = Mock(return_value=[])

    # Request a WRITE_HIGH_RISK tool at READ_ONLY level
    async def mock_stream(*args, **kwargs):
        for event in [
            {"type": "content_block_start", "index": 0, "content_block": {"type": "tool_use", "id": "t1", "name": "shopping_list_create"}},
            {"type": "content_block_delta", "index": 0, "delta": {"type": "input_json_delta", "partial_json": '{"name": "Test"}'}},
            {"type": "content_block_stop", "index": 0},
            {"type": "message_stop"}
        ]:
            yield event

    llm_client._stream_response = mock_stream

    mcp_client = Mock()
    mcp_client.call_tool = Mock(return_value={"content": [{"type": "text", "text": "Should not execute"}]})
    mcp_client.get_tools = Mock(return_value=[])

    # READ_ONLY level - should block writes
    user_settings = UserSettings(character_id=123, autonomy_level=AutonomyLevel.READ_ONLY)

    loop = AgenticStreamingLoop(llm_client, mcp_client, user_settings)

    events = []
    async for event in loop.execute([{"role": "user", "content": "Test"}]):
        events.append(event)

    # Should have authorization_denied event
    assert any(e["type"] == "authorization_denied" for e in events)

    # Tool should NOT have been called
    mcp_client.call_tool.assert_not_called()


@pytest.mark.asyncio
async def test_max_iterations_limit():
    """Test that loop stops after max iterations."""
    llm_client = Mock()
    llm_client.model = "claude-3-5-sonnet-20241022"
    llm_client.build_tool_schema = Mock(return_value=[])

    # Always request a tool (infinite loop without limit)
    async def always_tool(*args, **kwargs):
        for event in [
            {"type": "content_block_start", "index": 0, "content_block": {"type": "tool_use", "id": "t1", "name": "get_market_prices"}},
            {"type": "content_block_delta", "index": 0, "delta": {"type": "input_json_delta", "partial_json": '{}'}},
            {"type": "content_block_stop", "index": 0},
            {"type": "message_stop"}
        ]:
            yield event

    llm_client._stream_response = always_tool

    mcp_client = Mock()
    mcp_client.call_tool = Mock(return_value={"content": [{"type": "text", "text": "Result"}]})
    mcp_client.get_tools = Mock(return_value=[])

    user_settings = UserSettings(character_id=123, autonomy_level=AutonomyLevel.RECOMMENDATIONS)

    # Set max_iterations to 3
    loop = AgenticStreamingLoop(llm_client, mcp_client, user_settings, max_iterations=3)

    events = []
    async for event in loop.execute([{"role": "user", "content": "Test"}]):
        events.append(event)

    # Should have exactly 3 thinking events
    thinking_events = [e for e in events if e["type"] == "thinking"]
    assert len(thinking_events) == 3

    # Should have error event for max iterations
    assert any(e["type"] == "error" and "Maximum iterations" in e.get("error", "") for e in events)


@pytest.mark.asyncio
async def test_broadcast_events_to_websocket(mock_event_bus):
    """Test that agentic loop broadcasts events to WebSocket."""
    llm_client = Mock()
    llm_client.model = "claude-3-5-sonnet-20241022"
    llm_client.build_tool_schema = Mock(return_value=[])

    # Use get_market_prices which is a known READ_ONLY tool
    async def mock_stream(*args, **kwargs):
        for event in [
            {"type": "content_block_start", "index": 0, "content_block": {"type": "tool_use", "id": "t1", "name": "get_market_prices"}},
            {"type": "content_block_delta", "index": 0, "delta": {"type": "input_json_delta", "partial_json": '{"type_id": 34}'}},
            {"type": "content_block_stop", "index": 0},
            {"type": "message_stop"}
        ]:
            yield event

    llm_client._stream_response = mock_stream

    mcp_client = Mock()
    mcp_client.call_tool = Mock(return_value={"content": [{"type": "text", "text": "5.50 ISK"}]})
    mcp_client.get_tools = Mock(return_value=[])

    user_settings = UserSettings(character_id=123, autonomy_level=AutonomyLevel.RECOMMENDATIONS)

    loop = AgenticStreamingLoop(llm_client, mcp_client, user_settings, event_bus=mock_event_bus)

    async for _ in loop.execute([{"role": "user", "content": "Price?"}], session_id="sess-123"):
        pass

    # Verify events were published
    published_events = mock_event_bus.get_published_events("sess-123")
    assert any(e.type == AgentEventType.TOOL_CALL_STARTED for e in published_events)
    assert any(e.type == AgentEventType.TOOL_CALL_COMPLETED for e in published_events)


# =============================================================================
# Tests for Extracted Helper Methods
# =============================================================================


class TestEnrichToolCallsWithRisk:
    """Tests for _enrich_tool_calls_with_risk method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.llm = Mock()
        self.llm.model = "claude-3-5-sonnet-20241022"
        self.mcp = Mock()
        self.mcp.get_tools = Mock(return_value=[])
        self.settings = UserSettings(character_id=123, autonomy_level=AutonomyLevel.RECOMMENDATIONS)
        self.loop = AgenticStreamingLoop(
            llm_client=self.llm,
            mcp_client=self.mcp,
            user_settings=self.settings
        )

    def test_known_tool_gets_risk_level(self):
        """Known tools should get their configured risk level."""
        with patch('copilot_server.agent.agentic_loop.get_tool_risk_level') as mock_risk:
            mock_risk.return_value = RiskLevel.READ_ONLY
            tool_calls = [{"name": "get_market_prices", "input": {}}]

            self.loop._enrich_tool_calls_with_risk(tool_calls)

            assert tool_calls[0]["risk_level"] == RiskLevel.READ_ONLY
            mock_risk.assert_called_once_with("get_market_prices")

    def test_unknown_tool_defaults_to_critical(self):
        """Unknown tools should default to CRITICAL risk."""
        with patch('copilot_server.agent.agentic_loop.get_tool_risk_level') as mock_risk:
            mock_risk.side_effect = ValueError("Unknown tool")
            tool_calls = [{"name": "unknown_dangerous_tool", "input": {}}]

            self.loop._enrich_tool_calls_with_risk(tool_calls)

            assert tool_calls[0]["risk_level"] == RiskLevel.CRITICAL

    def test_multiple_tools_enriched(self):
        """Multiple tools should all be enriched."""
        with patch('copilot_server.agent.agentic_loop.get_tool_risk_level') as mock_risk:
            mock_risk.side_effect = [
                RiskLevel.READ_ONLY,
                RiskLevel.WRITE_LOW_RISK,
                RiskLevel.WRITE_HIGH_RISK
            ]
            tool_calls = [
                {"name": "get_market_prices", "input": {}},
                {"name": "create_shopping_list", "input": {}},
                {"name": "delete_shopping_list", "input": {}}
            ]

            self.loop._enrich_tool_calls_with_risk(tool_calls)

            assert tool_calls[0]["risk_level"] == RiskLevel.READ_ONLY
            assert tool_calls[1]["risk_level"] == RiskLevel.WRITE_LOW_RISK
            assert tool_calls[2]["risk_level"] == RiskLevel.WRITE_HIGH_RISK

    def test_empty_tool_calls_list(self):
        """Empty tool calls list should not cause errors."""
        tool_calls = []
        self.loop._enrich_tool_calls_with_risk(tool_calls)
        assert tool_calls == []


class TestProcessChunkToEvent:
    """Tests for _process_chunk_to_event method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.llm = Mock()
        self.llm.model = "claude-3-5-sonnet-20241022"
        self.mcp = Mock()
        self.mcp.get_tools = Mock(return_value=[])
        self.settings = UserSettings(character_id=123, autonomy_level=AutonomyLevel.RECOMMENDATIONS)
        self.loop = AgenticStreamingLoop(
            llm_client=self.llm,
            mcp_client=self.mcp,
            user_settings=self.settings
        )

    def test_openai_text_chunk(self):
        """OpenAI text chunks should yield text events."""
        chunk = {"choices": [{"delta": {"content": "Hello"}}]}

        event = self.loop._process_chunk_to_event(chunk, "openai")

        assert event == {"type": "text", "text": "Hello"}

    def test_openai_empty_content(self):
        """OpenAI chunk with empty content should return None."""
        chunk = {"choices": [{"delta": {"content": ""}}]}

        event = self.loop._process_chunk_to_event(chunk, "openai")

        assert event is None

    def test_openai_no_content(self):
        """OpenAI chunk without content should return None."""
        chunk = {"choices": [{"delta": {"role": "assistant"}}]}

        event = self.loop._process_chunk_to_event(chunk, "openai")

        assert event is None

    def test_openai_empty_choices(self):
        """OpenAI chunk with empty choices should return None."""
        chunk = {"choices": []}

        event = self.loop._process_chunk_to_event(chunk, "openai")

        assert event is None

    def test_anthropic_text_chunk(self):
        """Anthropic text chunks should yield text events."""
        chunk = {
            "type": "content_block_delta",
            "delta": {"type": "text_delta", "text": "World"}
        }

        event = self.loop._process_chunk_to_event(chunk, "anthropic")

        assert event == {"type": "text", "text": "World"}

    def test_anthropic_non_text_delta(self):
        """Anthropic non-text delta should return None."""
        chunk = {
            "type": "content_block_delta",
            "delta": {"type": "input_json_delta", "partial_json": "{}"}
        }

        event = self.loop._process_chunk_to_event(chunk, "anthropic")

        assert event is None

    def test_anthropic_non_delta_chunk(self):
        """Anthropic non-delta chunk should return None."""
        chunk = {"type": "message_start"}

        event = self.loop._process_chunk_to_event(chunk, "anthropic")

        assert event is None

    def test_anthropic_empty_text(self):
        """Anthropic chunk with empty text should still return event."""
        chunk = {
            "type": "content_block_delta",
            "delta": {"type": "text_delta", "text": ""}
        }

        event = self.loop._process_chunk_to_event(chunk, "anthropic")

        # Empty text still returns an event (this matches original behavior)
        assert event == {"type": "text", "text": ""}


class TestBuildOpenAIAssistantMessage:
    """Tests for _build_openai_assistant_message method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.llm = Mock()
        self.llm.model = "claude-3-5-sonnet-20241022"
        self.mcp = Mock()
        self.mcp.get_tools = Mock(return_value=[])
        self.settings = UserSettings(character_id=123, autonomy_level=AutonomyLevel.RECOMMENDATIONS)
        self.loop = AgenticStreamingLoop(
            llm_client=self.llm,
            mcp_client=self.mcp,
            user_settings=self.settings
        )

    def test_builds_correct_format(self):
        """Should build OpenAI format with tool_calls field."""
        tool_calls = [
            {"id": "call_1", "name": "get_market_prices", "input": {"type_id": 34}}
        ]

        msg = self.loop._build_openai_assistant_message(tool_calls)

        assert msg["role"] == "assistant"
        assert msg["content"] is None
        assert len(msg["tool_calls"]) == 1
        assert msg["tool_calls"][0]["id"] == "call_1"
        assert msg["tool_calls"][0]["type"] == "function"
        assert msg["tool_calls"][0]["function"]["name"] == "get_market_prices"
        assert msg["tool_calls"][0]["function"]["arguments"] == '{"type_id": 34}'

    def test_multiple_tool_calls(self):
        """Should handle multiple tool calls."""
        tool_calls = [
            {"id": "call_1", "name": "get_market_prices", "input": {"type_id": 34}},
            {"id": "call_2", "name": "get_item_info", "input": {"type_id": 35}}
        ]

        msg = self.loop._build_openai_assistant_message(tool_calls)

        assert len(msg["tool_calls"]) == 2
        assert msg["tool_calls"][0]["id"] == "call_1"
        assert msg["tool_calls"][1]["id"] == "call_2"

    def test_empty_input(self):
        """Should handle empty input."""
        tool_calls = [
            {"id": "call_1", "name": "get_trade_hubs", "input": {}}
        ]

        msg = self.loop._build_openai_assistant_message(tool_calls)

        assert msg["tool_calls"][0]["function"]["arguments"] == "{}"

    def test_empty_tool_calls(self):
        """Should handle empty tool calls list."""
        tool_calls = []

        msg = self.loop._build_openai_assistant_message(tool_calls)

        assert msg["role"] == "assistant"
        assert msg["content"] is None
        assert msg["tool_calls"] == []


@pytest.mark.asyncio
class TestExecuteSingleTool:
    """Tests for _execute_single_tool method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.llm = Mock()
        self.llm.model = "claude-3-5-sonnet-20241022"
        self.mcp = Mock()
        self.mcp.get_tools = Mock(return_value=[])
        # Default: tool execution succeeds
        self.mcp.call_tool = Mock(return_value={"content": [{"type": "text", "text": "Success"}]})
        self.settings = UserSettings(character_id=123, autonomy_level=AutonomyLevel.SUPERVISED)
        self.loop = AgenticStreamingLoop(
            llm_client=self.llm,
            mcp_client=self.mcp,
            user_settings=self.settings
        )

    async def test_authorization_denied(self):
        """Tool should be blocked when authorization fails."""
        tool_call = {"id": "call_1", "name": "delete_shopping_list", "input": {"list_id": 1}}

        # Use READ_ONLY level which should block deletes
        self.loop.settings = UserSettings(character_id=123, autonomy_level=AutonomyLevel.READ_ONLY)
        self.loop.auth_checker = MagicMock()
        self.loop.auth_checker.check_authorization.return_value = (False, "Not allowed at READ_ONLY level")

        events = []
        async for event in self.loop._execute_single_tool(tool_call, None):
            events.append(event)

        assert events[0]["type"] == "tool_call_started"
        assert events[1]["type"] == "authorization_denied"
        assert events[1]["reason"] == "Not allowed at READ_ONLY level"
        assert events[2]["type"] == "tool_result"
        assert events[2]["is_error"] is True

        # Tool should NOT have been called
        self.mcp.call_tool.assert_not_called()

    async def test_successful_execution(self):
        """Successful tool execution should yield completed event."""
        tool_call = {"id": "call_1", "name": "get_market_prices", "input": {"type_id": 34}}
        self.loop.auth_checker = MagicMock()
        self.loop.auth_checker.check_authorization.return_value = (True, None)

        events = []
        async for event in self.loop._execute_single_tool(tool_call, None):
            events.append(event)

        assert events[0]["type"] == "tool_call_started"
        assert events[0]["tool"] == "get_market_prices"
        assert events[1]["type"] == "tool_call_completed"
        assert events[1]["tool"] == "get_market_prices"
        assert events[2]["type"] == "tool_result"
        assert "is_error" not in events[2]
        assert events[2]["tool_use_id"] == "call_1"

        # Tool should have been called
        self.mcp.call_tool.assert_called_once()

    async def test_tool_execution_error(self):
        """Tool execution error should yield failed event."""
        tool_call = {"id": "call_1", "name": "get_market_prices", "input": {}}
        self.loop.auth_checker = MagicMock()
        self.loop.auth_checker.check_authorization.return_value = (True, None)
        self.mcp.call_tool = Mock(side_effect=Exception("Database connection failed"))

        events = []
        async for event in self.loop._execute_single_tool(tool_call, None):
            events.append(event)

        assert events[0]["type"] == "tool_call_started"
        assert events[1]["type"] == "tool_call_failed"
        assert events[1]["error"] == "Database connection failed"
        assert events[1]["retries_exhausted"] is False
        assert events[2]["type"] == "tool_result"
        assert events[2]["is_error"] is True

    async def test_publishes_to_event_bus(self):
        """Should publish events to EventBus when provided."""
        tool_call = {"id": "call_1", "name": "get_market_prices", "input": {}}
        self.loop.auth_checker = MagicMock()
        self.loop.auth_checker.check_authorization.return_value = (True, None)

        # Create mock event bus
        event_bus = MagicMock()
        event_bus.publish = AsyncMock()
        self.loop.event_bus = event_bus

        events = []
        async for event in self.loop._execute_single_tool(tool_call, "sess-123"):
            events.append(event)

        # Should have published start and complete events
        assert event_bus.publish.call_count == 2
        # First call should be TOOL_CALL_STARTED
        first_call_args = event_bus.publish.call_args_list[0]
        assert first_call_args[0][0] == "sess-123"
        assert first_call_args[0][1].type == AgentEventType.TOOL_CALL_STARTED
        # Second call should be TOOL_CALL_COMPLETED
        second_call_args = event_bus.publish.call_args_list[1]
        assert second_call_args[0][0] == "sess-123"
        assert second_call_args[0][1].type == AgentEventType.TOOL_CALL_COMPLETED

    async def test_no_event_bus_publish_without_session_id(self):
        """Should not publish to EventBus without session_id."""
        tool_call = {"id": "call_1", "name": "get_market_prices", "input": {}}
        self.loop.auth_checker = MagicMock()
        self.loop.auth_checker.check_authorization.return_value = (True, None)

        event_bus = MagicMock()
        event_bus.publish = AsyncMock()
        self.loop.event_bus = event_bus

        events = []
        async for event in self.loop._execute_single_tool(tool_call, None):
            events.append(event)

        # Should NOT have published any events (no session_id)
        event_bus.publish.assert_not_called()


@pytest.mark.asyncio
class TestExecuteToolCalls:
    """Tests for _execute_tool_calls method."""

    def setup_method(self):
        self.llm = MagicMock()
        self.llm.model = "claude-3-5-sonnet-20241022"
        self.mcp = MagicMock()
        self.mcp.get_tools = MagicMock(return_value=[])
        self.settings = UserSettings(character_id=123, autonomy_level=AutonomyLevel.SUPERVISED)
        self.loop = AgenticStreamingLoop(
            llm_client=self.llm,
            mcp_client=self.mcp,
            user_settings=self.settings
        )

    async def test_executes_all_tools(self):
        """Should execute all tool calls and yield events."""
        tool_calls = [
            {"id": "call_1", "name": "tool_a", "input": {}},
            {"id": "call_2", "name": "tool_b", "input": {}}
        ]
        self.mcp.call_tool.return_value = {"content": [{"type": "text", "text": "ok"}]}

        with patch.object(self.loop.auth_checker, 'check_authorization') as mock_auth:
            mock_auth.return_value = (True, None)

            events = []
            async for event in self.loop._execute_tool_calls(
                tool_calls, [], [], "anthropic", None
            ):
                events.append(event)

            # Should have 2 started + 2 completed events
            started = [e for e in events if e.get("type") == "tool_call_started"]
            completed = [e for e in events if e.get("type") == "tool_call_completed"]
            assert len(started) == 2
            assert len(completed) == 2

    async def test_builds_openai_format_message(self):
        """Should build OpenAI format when provider is openai."""
        tool_calls = [{"id": "call_1", "name": "tool_a", "input": {}}]
        self.mcp.call_tool.return_value = {"content": [{"type": "text", "text": "ok"}]}
        current_messages = []

        with patch.object(self.loop.auth_checker, 'check_authorization') as mock_auth:
            mock_auth.return_value = (True, None)

            events = []
            async for event in self.loop._execute_tool_calls(
                tool_calls, current_messages, [], "openai", None
            ):
                events.append(event)

            # Check assistant message format
            assert current_messages[0]["role"] == "assistant"
            assert "tool_calls" in current_messages[0]

    async def test_builds_anthropic_format_message(self):
        """Should build Anthropic format when provider is anthropic."""
        tool_calls = [{"id": "call_1", "name": "tool_a", "input": {}}]
        self.mcp.call_tool.return_value = {"content": [{"type": "text", "text": "ok"}]}
        current_messages = []
        assistant_content_blocks = [
            {"type": "text", "partial_text": "Let me check", "partial_json": ""}
        ]

        with patch.object(self.loop.auth_checker, 'check_authorization') as mock_auth:
            mock_auth.return_value = (True, None)

            events = []
            async for event in self.loop._execute_tool_calls(
                tool_calls, current_messages, assistant_content_blocks, "anthropic", None
            ):
                events.append(event)

            # Check assistant message format (Anthropic uses content array)
            assert current_messages[0]["role"] == "assistant"
            assert "content" in current_messages[0]
            assert isinstance(current_messages[0]["content"], list)

    async def test_adds_tool_results_to_conversation(self):
        """Should add tool results to conversation history."""
        tool_calls = [{"id": "call_1", "name": "tool_a", "input": {}}]
        self.mcp.call_tool.return_value = {"content": [{"type": "text", "text": "result"}]}
        current_messages = []

        with patch.object(self.loop.auth_checker, 'check_authorization') as mock_auth:
            mock_auth.return_value = (True, None)

            events = []
            async for event in self.loop._execute_tool_calls(
                tool_calls, current_messages, [], "anthropic", None
            ):
                events.append(event)

            # Should have assistant message + user message with tool results
            assert len(current_messages) == 2
            assert current_messages[1]["role"] == "user"

    async def test_openai_tool_result_format(self):
        """Should use OpenAI tool result format when provider is openai."""
        tool_calls = [{"id": "call_1", "name": "tool_a", "input": {}}]
        self.mcp.call_tool.return_value = {"content": [{"type": "text", "text": "result"}]}
        current_messages = []

        with patch.object(self.loop.auth_checker, 'check_authorization') as mock_auth:
            mock_auth.return_value = (True, None)

            events = []
            async for event in self.loop._execute_tool_calls(
                tool_calls, current_messages, [], "openai", None
            ):
                events.append(event)

            # OpenAI format: separate tool message with tool_call_id
            tool_result_msg = current_messages[1]
            assert tool_result_msg["role"] == "tool"
            assert tool_result_msg["tool_call_id"] == "call_1"
