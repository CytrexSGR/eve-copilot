"""
Custom exceptions for copilot_server.
Provides semantic error handling across the application.
"""

from typing import Optional, Any


class CopilotError(Exception):
    """Base exception for all copilot server errors."""

    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ServiceNotInitializedError(CopilotError):
    """Raised when a service is accessed before initialization."""
    pass


class SessionNotFoundError(CopilotError):
    """Raised when a session cannot be found."""

    def __init__(self, session_id: str):
        super().__init__(f"Session not found: {session_id}")
        self.session_id = session_id


class AuthorizationError(CopilotError):
    """Raised when an operation is not authorized."""

    def __init__(self, tool: str, reason: str):
        super().__init__(f"Authorization denied for {tool}: {reason}")
        self.tool = tool
        self.reason = reason


class ToolExecutionError(CopilotError):
    """Raised when tool execution fails."""

    def __init__(self, tool: str, error: str, retries_exhausted: bool = False):
        super().__init__(f"Tool '{tool}' execution failed: {error}")
        self.tool = tool
        self.error = error
        self.retries_exhausted = retries_exhausted


class MessageValidationError(CopilotError):
    """Raised when message content is invalid."""
    pass


class LLMError(CopilotError):
    """Raised when LLM call fails."""

    def __init__(self, message: str, provider: str = "unknown", details: Optional[dict] = None):
        super().__init__(message, details)
        self.provider = provider


class DatabaseError(CopilotError):
    """Raised when database operation fails."""
    pass


class ConfigurationError(CopilotError):
    """Raised when configuration is invalid or missing."""
    pass


class MCPError(CopilotError):
    """Raised when MCP client operation fails."""

    def __init__(self, message: str, server: Optional[str] = None, details: Optional[dict] = None):
        super().__init__(message, details)
        self.server = server
