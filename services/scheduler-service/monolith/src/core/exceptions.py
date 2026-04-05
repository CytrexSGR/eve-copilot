"""Stub exceptions for monolith compatibility.

These exception classes are imported by various monolith modules
(market service, character sync, ESI client, etc.) but the original
src.core.exceptions module was deleted during monolith decommission.
This shim provides the minimal interface needed to keep imports working.
"""


class EVECopilotError(Exception):
    """Base exception for all EVE Co-Pilot errors."""
    pass


class ExternalAPIError(EVECopilotError):
    """Raised when an external API call (ESI, zKillboard, etc.) fails."""
    pass


class DatabaseError(EVECopilotError):
    """Raised when a database operation fails."""
    pass


class AuthenticationError(EVECopilotError):
    """Raised when authentication or token operations fail."""
    pass


class ValidationError(EVECopilotError):
    """Raised when data validation fails."""
    pass
