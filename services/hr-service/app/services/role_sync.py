"""Role Synchronization - ESI roles to web permissions mapping.

Maps ESI corporation roles to web application permissions.
Detects privilege escalation (new Director/Hangar Access) and
generates alerts for security review.
"""

import logging
from typing import List, Dict, Any, Optional

import httpx

from eve_shared import get_db

from app.config import settings

logger = logging.getLogger(__name__)

# ESI roles that warrant escalation alerts
ESCALATION_ROLES = {
    "Director",
    "CEO",
    "Hangar_Take_1", "Hangar_Take_2", "Hangar_Take_3",
    "Hangar_Take_4", "Hangar_Take_5", "Hangar_Take_6", "Hangar_Take_7",
    "Container_Take_1", "Container_Take_2", "Container_Take_3",
    "Container_Take_4", "Container_Take_5", "Container_Take_6", "Container_Take_7",
    "Accountant",
    "Trader",
    "Station_Manager",
    "Starbase_Defense_Operator",
}


class RoleSyncService:
    """ESI role synchronization with escalation detection."""

    def __init__(self):
        self.db = get_db()

    def get_mappings(self) -> List[Dict[str, Any]]:
        """Get all active role mappings."""
        with self.db.cursor() as cur:
            cur.execute(
                """
                SELECT id, esi_role, web_permission, priority, active, created_at
                FROM role_mappings
                WHERE active = TRUE
                ORDER BY priority DESC, esi_role
                """
            )
            return [dict(r) for r in cur.fetchall()]

    def create_mapping(self, mapping: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new role mapping."""
        with self.db.cursor() as cur:
            cur.execute(
                """
                INSERT INTO role_mappings (esi_role, web_permission, priority)
                VALUES (%(esi_role)s, %(web_permission)s, %(priority)s)
                ON CONFLICT (esi_role, web_permission) WHERE active = TRUE
                DO UPDATE SET priority = EXCLUDED.priority
                RETURNING id, esi_role, web_permission, priority, active, created_at
                """,
                mapping,
            )
            row = cur.fetchone()
            
        return dict(row)

    def delete_mapping(self, mapping_id: int) -> bool:
        """Deactivate a role mapping."""
        with self.db.cursor() as cur:
            cur.execute(
                """
                UPDATE role_mappings SET active = FALSE
                WHERE id = %(id)s AND active = TRUE
                RETURNING id
                """,
                {"id": mapping_id},
            )
            row = cur.fetchone()
            
        return row is not None

    async def sync_character(self, character_id: int) -> Dict[str, Any]:
        """Sync ESI roles for a character and detect privilege escalation."""
        # Fetch current ESI roles
        esi_roles = await self._fetch_esi_roles(character_id)
        char_info = await self._fetch_character_info(character_id)
        character_name = char_info.get("name", "Unknown") if char_info else "Unknown"

        # Get previous roles from sync log
        previous_roles = self._get_previous_roles(character_id)

        # Map ESI roles to web permissions
        mappings = self.get_mappings()
        current_permissions = set()
        for role in esi_roles:
            for m in mappings:
                if m["esi_role"] == role:
                    current_permissions.add(m["web_permission"])

        # Detect changes
        previous_permissions = set(previous_roles) if previous_roles else set()
        added = list(current_permissions - previous_permissions)
        removed = list(previous_permissions - current_permissions)

        # Detect privilege escalation
        escalation_alerts = []
        new_escalation_roles = set(esi_roles) & ESCALATION_ROLES
        old_esi_roles = self._get_previous_esi_roles(character_id)
        previously_held = set(old_esi_roles) if old_esi_roles else set()

        newly_granted = new_escalation_roles - previously_held
        if newly_granted:
            for role in newly_granted:
                alert = f"ESCALATION: {character_name} ({character_id}) granted {role}"
                escalation_alerts.append(alert)
                logger.warning(alert)

        # Store sync log
        self._store_sync_log(
            character_id=character_id,
            character_name=character_name,
            esi_roles=esi_roles,
            added_roles=added,
            removed_roles=removed,
            escalation=len(escalation_alerts) > 0,
        )

        # Send Discord alert if escalation detected
        if escalation_alerts and settings.discord_webhook_url:
            await self._send_discord_alert(escalation_alerts)

        return {
            "character_id": character_id,
            "character_name": character_name,
            "current_roles": esi_roles,
            "added_roles": added,
            "removed_roles": removed,
            "escalation_alerts": escalation_alerts,
        }

    async def sync_all(self) -> Dict[str, Any]:
        """Sync roles for all authenticated characters."""
        # Get all characters from auth-service
        characters = await self._fetch_all_characters()
        synced = 0
        escalations = 0

        for char in characters:
            char_id = char.get("character_id")
            if not char_id:
                continue
            try:
                result = await self.sync_character(char_id)
                synced += 1
                if result.get("escalation_alerts"):
                    escalations += len(result["escalation_alerts"])
            except Exception:
                logger.warning(f"Failed to sync roles for {char_id}")

        return {"synced": synced, "escalations": escalations}

    # --- Internal Helpers ---

    async def _fetch_esi_roles(self, character_id: int) -> List[str]:
        """Fetch ESI roles from character-service."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{settings.character_service_url}/api/character/{character_id}/roles"
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("roles", []) if isinstance(data, dict) else data
        except Exception:
            logger.warning(f"Failed to fetch ESI roles for {character_id}")
        return []

    async def _fetch_character_info(self, character_id: int) -> Optional[Dict]:
        """Fetch character info from character-service."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{settings.character_service_url}/api/character/{character_id}/info"
                )
                if resp.status_code == 200:
                    return resp.json()
        except Exception:
            pass
        return None

    async def _fetch_all_characters(self) -> List[Dict]:
        """Fetch all authenticated characters from auth-service."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{settings.auth_service_url}/api/auth/characters"
                )
                if resp.status_code == 200:
                    return resp.json()
        except Exception:
            logger.warning("Failed to fetch characters from auth-service")
        return []

    def _get_previous_roles(self, character_id: int) -> Optional[List[str]]:
        """Get previous web permissions from last sync log."""
        with self.db.cursor() as cur:
            cur.execute(
                """
                SELECT added_roles, removed_roles
                FROM role_sync_log
                WHERE character_id = %(character_id)s
                ORDER BY synced_at DESC
                LIMIT 1
                """,
                {"character_id": character_id},
            )
            row = cur.fetchone()

        if not row:
            return None
        # Reconstruct: all added minus all removed historically
        return row.get("added_roles", [])

    def _get_previous_esi_roles(self, character_id: int) -> Optional[List[str]]:
        """Get previous ESI roles from last sync log."""
        with self.db.cursor() as cur:
            cur.execute(
                """
                SELECT esi_roles
                FROM role_sync_log
                WHERE character_id = %(character_id)s
                ORDER BY synced_at DESC
                LIMIT 1
                """,
                {"character_id": character_id},
            )
            row = cur.fetchone()

        return row["esi_roles"] if row else None

    def _store_sync_log(self, **kwargs):
        """Store role sync event in audit log."""
        import json

        with self.db.cursor() as cur:
            cur.execute(
                """
                INSERT INTO role_sync_log
                    (character_id, character_name, esi_roles, added_roles,
                     removed_roles, escalation)
                VALUES
                    (%(character_id)s, %(character_name)s,
                     %(esi_roles)s::jsonb, %(added_roles)s::jsonb,
                     %(removed_roles)s::jsonb, %(escalation)s)
                """,
                {
                    "character_id": kwargs["character_id"],
                    "character_name": kwargs["character_name"],
                    "esi_roles": json.dumps(kwargs["esi_roles"]),
                    "added_roles": json.dumps(kwargs["added_roles"]),
                    "removed_roles": json.dumps(kwargs["removed_roles"]),
                    "escalation": kwargs["escalation"],
                },
            )
            
    async def _send_discord_alert(self, alerts: List[str]):
        """Send escalation alerts to Discord webhook."""
        if not settings.discord_webhook_url:
            return

        content = "**HR ESCALATION ALERT**\n" + "\n".join(f"- {a}" for a in alerts)

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(
                    settings.discord_webhook_url,
                    json={"content": content},
                )
        except Exception:
            logger.warning("Failed to send Discord escalation alert")
