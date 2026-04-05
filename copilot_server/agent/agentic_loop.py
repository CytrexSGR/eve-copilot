"""
Agentic Streaming Loop
Executes multi-turn tool-calling workflow with streaming.
"""

import logging
import json
import time
from typing import List, Dict, Any, AsyncIterator, Optional, Tuple
from ..llm.anthropic_client import AnthropicClient
from ..mcp.client import MCPClient
from ..models.user_settings import UserSettings
from ..governance.authorization import AuthorizationChecker
from ..governance.tool_classification import get_tool_risk_level
from ..core.enums import RiskLevel
from .tool_extractor import ToolCallExtractor
from .events import ToolCallStartedEvent, ToolCallCompletedEvent, PlanProposedEvent, WaitingForApprovalEvent
from .sessions import EventBus
from .approval_manager import ApprovalManager
from .retry_handler import RetryHandler, RetryableError
from .context_manager import ContextWindowManager

logger = logging.getLogger(__name__)


class AgenticStreamingLoop:
    """
    Executes agentic loop with streaming and tool execution.

    Flow:
    1. Stream LLM response
    2. Extract tool calls from stream
    3. Execute tools (with authorization)
    4. Feed results back to LLM
    5. Repeat until final answer
    6. Stream events to client
    """

    # Maximum tokens for LLM response. Capped for cost control.
    # Claude can output 100k+, but we limit to prevent runaway costs.
    MAX_RESPONSE_TOKENS = 4096

    def __init__(
        self,
        llm_client: AnthropicClient,
        mcp_client: MCPClient,
        user_settings: UserSettings,
        max_iterations: int = 5,
        event_bus: Optional[EventBus] = None,
        max_context_messages: int = 20
    ):
        self.llm = llm_client
        self.mcp = mcp_client
        self.settings = user_settings
        self.max_iterations = max_iterations
        self.auth_checker = AuthorizationChecker(user_settings)
        self.approval_manager = ApprovalManager(user_settings.autonomy_level)
        self.event_bus = event_bus  # Optional EventBus for broadcasting
        self.retry_handler = RetryHandler(max_retries=3)
        self.context_manager = ContextWindowManager(max_messages=max_context_messages)

    async def execute(
        self,
        messages: List[Dict[str, Any]],
        system: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Execute agentic loop with streaming.

        Args:
            messages: Conversation history
            system: System prompt
            session_id: Session ID for events

        Yields:
            Stream events: text chunks, tool calls, results, errors
        """
        iteration = 0
        current_messages = messages.copy()

        # Apply context window management
        current_messages = self.context_manager.truncate(current_messages, system)
        context_summary = self.context_manager.get_context_summary(current_messages)
        logger.info(
            f"Context: {context_summary['total_messages']} messages, "
            f"~{context_summary['estimated_tokens']} tokens"
        )

        tools = self.mcp.get_tools()
        claude_tools = self.llm.build_tool_schema(tools) if tools else []

        # Detect provider from LLM client
        provider = getattr(self.llm, "provider", "anthropic")
        if provider not in ("anthropic", "openai"):
            provider = "anthropic"  # Default fallback
        logger.info(f"Using LLM provider: {provider}")

        while iteration < self.max_iterations:
            iteration += 1
            logger.info(f"Agentic loop iteration {iteration}/{self.max_iterations}")

            # Yield thinking event
            yield {
                "type": "thinking",
                "iteration": iteration
            }

            # Stream and extract tool calls
            extractor, assistant_content_blocks, event_stream = await self._stream_and_extract(
                current_messages, system, claude_tools, provider
            )

            # Yield text events from stream
            async for event in event_stream:
                yield event

            # Check if tools were called
            tool_calls = extractor.get_tool_calls()

            if not tool_calls:
                # No tool calls - final answer reached
                logger.debug("No tool calls detected - final answer reached")
                yield {"type": "done"}
                return

            # Enrich tool calls with risk levels
            self._enrich_tool_calls_with_risk(tool_calls)

            # Check if any tools require approval
            requires_approval = any(
                self.approval_manager.requires_approval(
                    tc["name"],
                    tc["input"],
                    tc["risk_level"]
                )
                for tc in tool_calls
            )

            if False and requires_approval and session_id:  # BYPASS: Skip approval for now
                # Create plan and wait for approval
                logger.info(f"Tool calls require approval at autonomy level {self.settings.autonomy_level}")

                # Build assistant message for conversation
                assistant_message_content = self._build_assistant_content(assistant_content_blocks)
                current_messages.append({
                    "role": "assistant",
                    "content": assistant_message_content
                })

                # Create approval plan
                plan = self.approval_manager.create_approval_plan(
                    session_id=session_id,
                    tool_calls=tool_calls,
                    purpose=f"Execute {len(tool_calls)} tool(s)"
                )

                # Yield plan_proposed event
                yield {
                    "type": "plan_proposed",
                    "plan_id": plan.id,
                    "purpose": plan.purpose,
                    "steps": [
                        {
                            "tool": step.tool,
                            "arguments": step.arguments,
                            "risk_level": step.risk_level.value
                        }
                        for step in plan.steps
                    ],
                    "max_risk_level": plan.max_risk_level.value,
                    "tool_count": len(plan.steps),
                    "auto_executing": False
                }

                # Publish PLAN_PROPOSED event to EventBus
                if self.event_bus:
                    event = PlanProposedEvent(
                        session_id=session_id,
                        plan_id=plan.id,
                        purpose=plan.purpose,
                        steps=[
                            {"tool": step.tool, "arguments": step.arguments}
                            for step in plan.steps
                        ],
                        max_risk_level=plan.max_risk_level.value,
                        tool_count=len(plan.steps),
                        auto_executing=False
                    )
                    await self.event_bus.publish(session_id, event)

                # Yield waiting_for_approval event
                yield {
                    "type": "waiting_for_approval",
                    "plan_id": plan.id,
                    "message": f"Plan requires approval due to {plan.max_risk_level.value} risk operations"
                }

                # Publish WAITING_FOR_APPROVAL event to EventBus
                if self.event_bus:
                    waiting_event = WaitingForApprovalEvent(
                        session_id=session_id,
                        plan_id=plan.id,
                        message=f"Plan requires approval due to {plan.max_risk_level.value} risk operations"
                    )
                    await self.event_bus.publish(session_id, waiting_event)

                # Stop execution - wait for user to approve/reject
                logger.info(f"Waiting for approval of plan {plan.id}")
                return

            # Execute tool calls
            async for event in self._execute_tool_calls(
                tool_calls, current_messages, assistant_content_blocks, provider, session_id
            ):
                yield event

        # Max iterations reached
        logger.warning(f"Max iterations ({self.max_iterations}) reached")
        yield {
            "type": "error",
            "error": "Maximum iterations reached without final answer"
        }

    async def _stream_and_extract(
        self,
        current_messages: List[Dict[str, Any]],
        system: Optional[str],
        claude_tools: List[Dict[str, Any]],
        provider: str
    ) -> Tuple[ToolCallExtractor, List[Dict[str, Any]], AsyncIterator[Dict[str, Any]]]:
        """
        Stream LLM response and extract tool calls.

        Args:
            current_messages: Conversation history
            system: System prompt
            claude_tools: Tool schemas
            provider: LLM provider ("anthropic" or "openai")

        Returns:
            Tuple of (extractor, assistant_content_blocks, event_generator)
            The event_generator yields text events as they come in.
        """
        extractor = ToolCallExtractor()
        assistant_content_blocks = []

        base_params = {
            "model": self.llm.model,
            "messages": current_messages,
            "system": system or "",
            "max_tokens": self.MAX_RESPONSE_TOKENS,
            "tools": claude_tools,
            "stream": True
        }

        if provider == "openai":
            stream_generator = self.llm._stream_response(base_params, convert_format=False)
        else:
            stream_generator = self.llm._stream_response(base_params)

        async def process_stream():
            async for chunk in stream_generator:
                extractor.process_chunk(chunk, provider=provider)

                # Yield text event if present
                event = self._process_chunk_to_event(chunk, provider)
                if event:
                    yield event

                # Build assistant content blocks
                if chunk.get("type") == "content_block_start":
                    content_block = chunk.get("content_block", {})
                    assistant_content_blocks.append({
                        "type": content_block.get("type"),
                        "id": content_block.get("id"),
                        "name": content_block.get("name"),
                        "partial_text": "",
                        "partial_json": ""
                    })
                elif chunk.get("type") == "content_block_delta":
                    index = chunk.get("index", 0)
                    if index < len(assistant_content_blocks):
                        delta = chunk.get("delta", {})
                        if delta.get("type") == "text_delta":
                            assistant_content_blocks[index]["partial_text"] += delta.get("text", "")
                        elif delta.get("type") == "input_json_delta":
                            assistant_content_blocks[index]["partial_json"] += delta.get("partial_json", "")
                    else:
                        logger.warning(f"Chunk index {index} out of bounds (have {len(assistant_content_blocks)} blocks)")

        return extractor, assistant_content_blocks, process_stream()

    async def _execute_tool_calls(
        self,
        tool_calls: List[Dict[str, Any]],
        current_messages: List[Dict[str, Any]],
        assistant_content_blocks: List[Dict[str, Any]],
        provider: str,
        session_id: Optional[str]
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Execute all tool calls and add results to conversation.

        Args:
            tool_calls: List of tool calls to execute
            current_messages: Conversation history (modified in place)
            assistant_content_blocks: Content blocks from LLM (for Anthropic format)
            provider: LLM provider
            session_id: Session ID for events

        Yields:
            Events from tool execution
        """
        logger.info(f"Executing {len(tool_calls)} tool calls (auto-approved)")

        # Build assistant message for conversation
        if provider == "openai":
            assistant_message = self._build_openai_assistant_message(tool_calls)
            current_messages.append(assistant_message)
        else:
            assistant_message_content = self._build_assistant_content(assistant_content_blocks)
            current_messages.append({
                "role": "assistant",
                "content": assistant_message_content
            })

        # Execute tools and collect results
        tool_results = []

        for tool_call in tool_calls:
            async for event in self._execute_single_tool(tool_call, session_id):
                if event.get("type") == "tool_result":
                    tool_results.append(event)
                else:
                    yield event

        # Add tool results to conversation
        if provider == "openai":
            for tool_result in tool_results:
                current_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_result["tool_use_id"],
                    "content": tool_result["content"]
                })
        else:
            current_messages.append({
                "role": "user",
                "content": tool_results
            })

    def _enrich_tool_calls_with_risk(self, tool_calls: List[Dict[str, Any]]) -> None:
        """
        Add risk levels to tool calls in place.

        Args:
            tool_calls: List of tool call dictionaries to enrich
        """
        for tool_call in tool_calls:
            try:
                risk_level = get_tool_risk_level(tool_call["name"])
                tool_call["risk_level"] = risk_level
            except ValueError:
                # Unknown tool - default to CRITICAL
                tool_call["risk_level"] = RiskLevel.CRITICAL
                logger.error(f"Unknown tool '{tool_call['name']}' - defaulting to CRITICAL risk")

    def _process_chunk_to_event(
        self,
        chunk: Dict[str, Any],
        provider: str
    ) -> Optional[Dict[str, Any]]:
        """
        Convert streaming chunk to yield event.

        Args:
            chunk: Streaming chunk from LLM
            provider: LLM provider ("openai" or "anthropic")

        Returns:
            Event dictionary if chunk contains text, None otherwise
        """
        if provider == "openai":
            # Raw OpenAI format
            if "choices" in chunk and chunk["choices"]:
                delta = chunk["choices"][0].get("delta", {})
                if "content" in delta and delta["content"]:
                    return {"type": "text", "text": delta["content"]}
        else:
            # Anthropic format
            if chunk.get("type") == "content_block_delta":
                delta = chunk.get("delta", {})
                if delta.get("type") == "text_delta":
                    return {"type": "text", "text": delta.get("text", "")}
        return None

    def _build_openai_assistant_message(
        self,
        tool_calls: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Build OpenAI format assistant message with tool calls.

        Args:
            tool_calls: List of tool call dictionaries

        Returns:
            OpenAI format assistant message
        """
        openai_tool_calls = []
        for tc in tool_calls:
            openai_tool_calls.append({
                "id": tc["id"],
                "type": "function",
                "function": {
                    "name": tc["name"],
                    "arguments": json.dumps(tc["input"])
                }
            })
        return {
            "role": "assistant",
            "content": None,
            "tool_calls": openai_tool_calls
        }

    async def _execute_single_tool(
        self,
        tool_call: Dict[str, Any],
        session_id: Optional[str]
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Execute a single tool with authorization and retry.

        Yields:
            Events (tool_call_started, tool_call_completed, tool_call_failed, authorization_denied)

        The final yielded item has type "tool_result" with the result dict.

        Args:
            tool_call: Tool call dictionary with id, name, input
            session_id: Optional session ID for event publishing
        """
        tool_name = tool_call.get("name")
        tool_input = tool_call.get("input", {})
        tool_id = tool_call.get("id")

        if not tool_name:
            logger.error(f"Tool call missing 'name' field: {tool_call}")
            yield {"type": "tool_call_failed", "tool": "unknown", "error": "Missing tool name"}
            yield {
                "type": "tool_result",
                "tool_use_id": tool_id or "unknown",
                "content": "Error: Tool call missing 'name' field",
                "is_error": True
            }
            return

        if not tool_id:
            logger.warning(f"Tool call missing 'id' field, generating one")
            tool_id = f"call_{tool_name}_{int(time.time())}"

        # Yield started event
        yield {"type": "tool_call_started", "tool": tool_name, "arguments": tool_input}

        # Publish to EventBus if available
        if self.event_bus and session_id:
            event = ToolCallStartedEvent(
                session_id=session_id,
                plan_id=None,
                step_index=0,
                tool=tool_name,
                arguments=tool_input
            )
            await self.event_bus.publish(session_id, event)

        # Check authorization
        allowed, denial_reason = self.auth_checker.check_authorization(
            tool_name,
            tool_input
        )

        if not allowed:
            logger.warning(f"Tool '{tool_name}' blocked: {denial_reason}")

            # Yield authorization denied event
            yield {"type": "authorization_denied", "tool": tool_name, "reason": denial_reason}

            yield {
                "type": "tool_result",
                "tool_use_id": tool_id,
                "content": f"Authorization Error: {denial_reason}",
                "is_error": True
            }
            return

        # Execute tool with retry logic
        logger.info(f"Executing tool: {tool_name}")
        start_time = time.time()

        try:
            async def execute_tool():
                result = self.mcp.call_tool(tool_name, tool_input)

                # Check if result indicates retryable error
                if isinstance(result, dict) and "error" in result:
                    if self.retry_handler.is_retryable_error(Exception(result["error"])):
                        raise RetryableError(result["error"])

                return result

            result = await self.retry_handler.execute_with_retry(execute_tool)
            duration_ms = int((time.time() - start_time) * 1000)

            # Yield tool_call_completed event
            yield {"type": "tool_call_completed", "tool": tool_name, "result": result}

            # Publish TOOL_CALL_COMPLETED event to EventBus
            if self.event_bus and session_id:
                # Create result preview (first 200 chars)
                result_preview = self._format_tool_result(result)[:200]
                event = ToolCallCompletedEvent(
                    session_id=session_id,
                    plan_id=None,
                    step_index=0,
                    tool=tool_name,
                    duration_ms=duration_ms,
                    result_preview=result_preview
                )
                await self.event_bus.publish(session_id, event)

            # Format for LLM
            yield {
                "type": "tool_result",
                "tool_use_id": tool_id,
                "content": self._format_tool_result(result)
            }

        except RetryableError as e:
            # All retries exhausted
            logger.error(f"Tool {tool_name} failed after retries: {e}")

            # Yield error event
            yield {
                "type": "tool_call_failed",
                "tool": tool_name,
                "error": str(e),
                "retries_exhausted": True
            }

            # Add error to tool results so LLM can adapt
            yield {
                "type": "tool_result",
                "tool_use_id": tool_id,
                "content": f"Tool execution failed after {self.retry_handler.max_retries} retries: {e}",
                "is_error": True
            }

        except Exception as e:
            # Non-retryable error
            logger.error(f"Tool {tool_name} failed with non-retryable error: {e}")

            yield {
                "type": "tool_call_failed",
                "tool": tool_name,
                "error": str(e),
                "retries_exhausted": False
            }

            yield {
                "type": "tool_result",
                "tool_use_id": tool_id,
                "content": f"Tool execution error: {e}",
                "is_error": True
            }

    def _build_assistant_content(self, content_blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Build assistant content blocks for conversation."""
        result = []

        for block in content_blocks:
            if block["type"] == "text":
                result.append({
                    "type": "text",
                    "text": block["partial_text"]
                })
            elif block["type"] == "tool_use":
                result.append({
                    "type": "tool_use",
                    "id": block["id"],
                    "name": block["name"],
                    "input": json.loads(block["partial_json"])
                })

        return result

    def _format_tool_result(self, result: Dict[str, Any]) -> str:
        """Format tool result for LLM."""
        if "error" in result:
            return f"Error: {result['error']}"

        if "content" in result:
            # Extract text from content blocks
            texts = []
            for block in result["content"]:
                if block.get("type") == "text":
                    texts.append(block.get("text", ""))
            return "\n".join(texts) if texts else str(result)

        return str(result)
