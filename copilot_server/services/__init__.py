"""
Services Module - Business logic layer for copilot operations.
Extracted from routes to separate concerns and enable testing.
"""

from .chat_service import ChatService

__all__ = ["ChatService"]
