"""Tests for custom exceptions."""

import pytest
from copilot_server.core.exceptions import (
    CopilotError,
    ServiceNotInitializedError,
    SessionNotFoundError,
    AuthorizationError,
    ToolExecutionError,
    MessageValidationError,
    LLMError,
    DatabaseError,
    ConfigurationError,
    MCPError
)


class TestCopilotError:
    """Tests for base CopilotError."""

    def test_message_and_details(self):
        """Base error stores message and details."""
        err = CopilotError("Something went wrong", {"code": 123})
        assert str(err) == "Something went wrong"
        assert err.message == "Something went wrong"
        assert err.details == {"code": 123}

    def test_default_details(self):
        """Details defaults to empty dict."""
        err = CopilotError("Error")
        assert err.details == {}

    def test_is_exception(self):
        """CopilotError is an Exception."""
        err = CopilotError("test")
        assert isinstance(err, Exception)


class TestSessionNotFoundError:
    """Tests for SessionNotFoundError."""

    def test_includes_session_id(self):
        """Error includes session_id in message."""
        err = SessionNotFoundError("sess-abc-123")
        assert "sess-abc-123" in str(err)
        assert err.session_id == "sess-abc-123"

    def test_is_copilot_error(self):
        """SessionNotFoundError inherits from CopilotError."""
        err = SessionNotFoundError("test")
        assert isinstance(err, CopilotError)


class TestAuthorizationError:
    """Tests for AuthorizationError."""

    def test_includes_tool_and_reason(self):
        """Error includes tool and reason."""
        err = AuthorizationError("dangerous_tool", "requires approval")
        assert err.tool == "dangerous_tool"
        assert err.reason == "requires approval"
        assert "dangerous_tool" in str(err)
        assert "requires approval" in str(err)


class TestToolExecutionError:
    """Tests for ToolExecutionError."""

    def test_includes_retry_info(self):
        """Error includes retry information."""
        err = ToolExecutionError("my_tool", "timeout", retries_exhausted=True)
        assert err.tool == "my_tool"
        assert err.error == "timeout"
        assert err.retries_exhausted is True

    def test_default_retries_not_exhausted(self):
        """Default is retries not exhausted."""
        err = ToolExecutionError("tool", "error")
        assert err.retries_exhausted is False


class TestLLMError:
    """Tests for LLMError."""

    def test_includes_provider(self):
        """Error includes provider info."""
        err = LLMError("API failed", provider="anthropic")
        assert err.provider == "anthropic"
        assert "API failed" in str(err)

    def test_default_provider(self):
        """Provider defaults to unknown."""
        err = LLMError("error")
        assert err.provider == "unknown"


class TestMCPError:
    """Tests for MCPError."""

    def test_includes_server(self):
        """Error includes server info."""
        err = MCPError("Connection failed", server="eve-tools")
        assert err.server == "eve-tools"

    def test_no_server(self):
        """Server can be None."""
        err = MCPError("error")
        assert err.server is None


class TestExceptionHierarchy:
    """Tests for exception inheritance."""

    def test_all_inherit_from_copilot_error(self):
        """All custom exceptions inherit from CopilotError."""
        exceptions = [
            ServiceNotInitializedError("msg"),
            SessionNotFoundError("sess"),
            AuthorizationError("tool", "reason"),
            ToolExecutionError("tool", "err"),
            MessageValidationError("msg"),
            LLMError("msg"),
            DatabaseError("msg"),
            ConfigurationError("msg"),
            MCPError("msg")
        ]
        for exc in exceptions:
            assert isinstance(exc, CopilotError), f"{type(exc).__name__} should inherit from CopilotError"

    def test_can_catch_all_with_copilot_error(self):
        """Can catch all custom exceptions with CopilotError."""
        try:
            raise SessionNotFoundError("test")
        except CopilotError as e:
            assert True
        else:
            assert False, "Should have caught exception"
