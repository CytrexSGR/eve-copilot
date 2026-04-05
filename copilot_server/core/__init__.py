from .enums import RiskLevel, AutonomyLevel
from .exceptions import (
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

# Lazy load to avoid circular imports
def get_app_context():
    from .context import get_app_context
    return get_app_context()


def set_app_context(context):
    from .context import set_app_context
    set_app_context(context)


__all__ = [
    # Enums
    "RiskLevel",
    "AutonomyLevel",
    # Exceptions
    "CopilotError",
    "ServiceNotInitializedError",
    "SessionNotFoundError",
    "AuthorizationError",
    "ToolExecutionError",
    "MessageValidationError",
    "LLMError",
    "DatabaseError",
    "ConfigurationError",
    "MCPError",
    # Context
    "get_app_context",
    "set_app_context",
]
