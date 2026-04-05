"""Shared ESI client library for all EVE Co-Pilot services.

Usage:
    from eve_shared.esi import EsiClient, esi_circuit_breaker, TokenLock, TokenEncryption

    client = EsiClient()
    data = client.get("/characters/12345/wallet/", token="...")
    pages = client.get_all_pages("/characters/12345/assets/", token="...")
"""

from eve_shared.esi.client import EsiClient
from eve_shared.esi.circuit_breaker import EsiCircuitBreaker, esi_circuit_breaker
from eve_shared.esi.token_lock import TokenLock
from eve_shared.esi.pagination import fetch_all_pages, fetch_cursor_pages
from eve_shared.esi.encryption import TokenEncryption

__all__ = [
    "EsiClient",
    "EsiCircuitBreaker",
    "esi_circuit_breaker",
    "TokenLock",
    "fetch_all_pages",
    "fetch_cursor_pages",
    "TokenEncryption",
]
