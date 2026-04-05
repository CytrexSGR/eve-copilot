"""
Platform Account store — manages multi-character accounts.

Tables: platform_accounts, account_characters
Pattern: db_cursor from app.database (RealDictCursor, auto-commit)
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List

from app.database import db_cursor

logger = logging.getLogger(__name__)

JWT_EXPIRY_DAYS = 30


# --- Pure functions (testable without DB) ---

def build_jwt_claims(
    account_id: int,
    character_id: int,
    character_name: str,
    tier: str,
    corporation_id: Optional[int] = None,
    alliance_id: Optional[int] = None,
    active_modules: Optional[List[str]] = None,
    org_plan: Optional[Dict[str, Any]] = None,
    character_ids: Optional[List[int]] = None,
) -> Dict[str, Any]:
    """Build JWT payload with account + tier + module context."""
    now = datetime.now(timezone.utc)
    claims = {
        "sub": str(character_id),
        "name": character_name,
        "account_id": account_id,
        "tier": tier,
        "iat": now,
        "exp": now + timedelta(days=JWT_EXPIRY_DAYS),
        "type": "public_session",
    }
    if corporation_id:
        claims["corp_id"] = corporation_id
    if alliance_id:
        claims["alliance_id"] = alliance_id
    # Module-based gating claims
    claims["active_modules"] = active_modules or []
    claims["org_plan"] = org_plan
    claims["character_ids"] = character_ids or [character_id]
    return claims


def should_update_corp_info(
    corporation_id: Optional[int],
    alliance_id: Optional[int],
) -> bool:
    """Decide if we should fetch corp/alliance from ESI on this login."""
    if not corporation_id or corporation_id == 0:
        return True
    if alliance_id is None:
        return True
    return False


# --- DB access class ---

class AccountRepository:
    """Repository for platform_accounts + account_characters."""

    def get_or_create_account(
        self,
        character_id: int,
        character_name: str,
        corporation_id: Optional[int] = None,
        alliance_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Find existing account for this character, or create a new one.

        Logic:
        1. Check account_characters for character_id
        2. If found -> return that account (update last_login)
        3. If not found -> create new platform_account + link character
        """
        with db_cursor() as cur:
            # 1. Check if character already linked to an account
            cur.execute(
                """
                SELECT pa.id, pa.primary_character_id, pa.primary_character_name,
                       pa.effective_tier, pa.corporation_id, pa.alliance_id,
                       pa.created_at, pa.last_login
                FROM account_characters ac
                JOIN platform_accounts pa ON ac.account_id = pa.id
                WHERE ac.character_id = %s
                """,
                (character_id,),
            )
            existing = cur.fetchone()

            if existing:
                # Update last_login + corp/alliance if needed
                updates = ["last_login = now()"]
                params: list = []
                if corporation_id and corporation_id != existing["corporation_id"]:
                    updates.append("corporation_id = %s")
                    params.append(corporation_id)
                if alliance_id is not None and alliance_id != existing["alliance_id"]:
                    updates.append("alliance_id = %s")
                    params.append(alliance_id)

                params.append(existing["id"])
                cur.execute(
                    f"UPDATE platform_accounts SET {', '.join(updates)} WHERE id = %s",
                    tuple(params),
                )
                # Re-read
                cur.execute(
                    """
                    SELECT id, primary_character_id, primary_character_name,
                           effective_tier, corporation_id, alliance_id,
                           created_at, last_login
                    FROM platform_accounts WHERE id = %s
                    """,
                    (existing["id"],),
                )
                return cur.fetchone()

            # 2. Create new account
            cur.execute(
                """
                INSERT INTO platform_accounts
                    (primary_character_id, primary_character_name,
                     corporation_id, alliance_id)
                VALUES (%s, %s, %s, %s)
                RETURNING id, primary_character_id, primary_character_name,
                          effective_tier, corporation_id, alliance_id,
                          created_at, last_login
                """,
                (character_id, character_name, corporation_id, alliance_id),
            )
            account = cur.fetchone()

            # 3. Link character
            cur.execute(
                """
                INSERT INTO account_characters
                    (account_id, character_id, character_name, is_primary)
                VALUES (%s, %s, %s, true)
                ON CONFLICT (character_id) DO NOTHING
                """,
                (account["id"], character_id, character_name),
            )
            return account

    def add_character_to_account(
        self,
        account_id: int,
        character_id: int,
        character_name: str,
    ) -> bool:
        """Link an additional character to an existing account."""
        with db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO account_characters
                    (account_id, character_id, character_name, is_primary)
                VALUES (%s, %s, %s, false)
                ON CONFLICT (character_id) DO UPDATE SET
                    account_id = EXCLUDED.account_id,
                    character_name = EXCLUDED.character_name
                """,
                (account_id, character_id, character_name),
            )
            return cur.rowcount > 0

    def get_account_characters(self, account_id: int) -> List[Dict[str, Any]]:
        """List all characters linked to an account."""
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT character_id, character_name, is_primary, added_at
                FROM account_characters
                WHERE account_id = %s
                ORDER BY is_primary DESC, added_at ASC
                """,
                (account_id,),
            )
            return cur.fetchall()

    def get_account_by_character(self, character_id: int) -> Optional[Dict[str, Any]]:
        """Look up an account by any linked character_id."""
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT pa.id, pa.primary_character_id, pa.primary_character_name,
                       pa.effective_tier, pa.corporation_id, pa.alliance_id,
                       pa.created_at, pa.last_login
                FROM account_characters ac
                JOIN platform_accounts pa ON ac.account_id = pa.id
                WHERE ac.character_id = %s
                """,
                (character_id,),
            )
            return cur.fetchone()

    def update_effective_tier(self, account_id: int, tier: str) -> bool:
        """Update cached effective tier on the account."""
        with db_cursor() as cur:
            cur.execute(
                """
                UPDATE platform_accounts SET effective_tier = %s
                WHERE id = %s
                """,
                (tier, account_id),
            )
            return cur.rowcount > 0

    def remove_character_from_account(
        self, account_id: int, character_id: int
    ) -> bool:
        """Unlink a character from an account. Cannot remove primary."""
        with db_cursor() as cur:
            cur.execute(
                """
                DELETE FROM account_characters
                WHERE account_id = %s AND character_id = %s AND is_primary = false
                """,
                (account_id, character_id),
            )
            return cur.rowcount > 0
