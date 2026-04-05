"""Wallet sync operation."""
from typing import Any

from .base import BaseSyncOperation


class WalletSync(BaseSyncOperation):
    """Sync character wallet balance."""

    def fetch_from_esi(self, character_id: int) -> Any:
        """Fetch wallet balance from ESI."""
        return self.character_service.get_wallet_balance(character_id)

    def transform_data(self, raw_data: Any) -> float:
        """Extract balance from response."""
        return raw_data.balance

    def save_to_db(self, character_id: int, balance: float, conn) -> None:
        """Insert wallet balance record."""
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO character_wallets (character_id, balance)
                VALUES (%s, %s)
            """, (character_id, balance))

    def get_sync_column(self) -> str:
        """Return the sync timestamp column name."""
        return "wallets_synced_at"

    def get_result_key(self) -> str:
        """Return key for result."""
        return "balance"

    def get_result_value(self, balance: float) -> Any:
        """Return the balance value."""
        return balance
