"""
ESI Corporation Role detection for auto-admin assignment.

Maps EVE Online corporation roles to platform roles:
  CEO, Director → admin
  Station_Manager, Accountant, Config_*, Personnel_Manager → officer
  Other roles → member (not auto-assigned)
"""
import logging
from typing import List, Dict, Any, Optional

import httpx

logger = logging.getLogger(__name__)

ESI_BASE = "https://esi.evetech.net/latest"

# ESI roles that map to platform admin
ADMIN_ROLES = {"CEO", "Director"}

# ESI roles that map to platform officer
OFFICER_ROLES = {
    "Station_Manager", "Accountant", "Personnel_Manager",
    "Config_Equipment", "Config_Starbase_Equipment",
    "Contract_Manager", "Diplomat",
}


def is_director(roles: Optional[List[str]]) -> bool:
    """Check if ESI roles include Director."""
    if not roles:
        return False
    return "Director" in roles


def is_ceo(roles: Optional[List[str]]) -> bool:
    """Check if ESI roles include CEO."""
    if not roles:
        return False
    return "CEO" in roles


def get_highest_corp_role(roles: Optional[List[str]]) -> Optional[str]:
    """Map ESI roles to highest platform role.

    Returns: 'admin', 'officer', 'member', or None
    """
    if not roles:
        return None

    role_set = set(roles)

    if role_set & ADMIN_ROLES:
        return "admin"
    if role_set & OFFICER_ROLES:
        return "officer"
    if role_set:
        return "member"
    return None


def build_role_assignment(
    character_id: int,
    corporation_id: Optional[int],
    esi_roles: Optional[List[str]],
) -> Optional[Dict[str, Any]]:
    """Build a role assignment dict from ESI roles, or None if no role.

    Only auto-assigns admin and officer — member is implicit.
    """
    if not corporation_id or not esi_roles:
        return None

    platform_role = get_highest_corp_role(esi_roles)
    if not platform_role or platform_role == "member":
        return None

    return {
        "character_id": character_id,
        "corporation_id": corporation_id,
        "role": platform_role,
        "auto_assigned": True,
    }


async def fetch_character_roles(
    character_id: int, access_token: str,
) -> List[str]:
    """Fetch ESI corporation roles for a character.

    Requires scope: esi-characters.read_corporation_roles.v1
    Returns list of role strings e.g. ["Director", "Station_Manager"]
    """
    url = f"{ESI_BASE}/characters/{character_id}/roles/"
    headers = {"Authorization": f"Bearer {access_token}"}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("roles", [])
            elif resp.status_code == 403:
                logger.debug(f"ESI 403 for character {character_id} roles — may lack scope")
                return []
            else:
                logger.warning(f"ESI character roles returned {resp.status_code}")
                return []
    except Exception as e:
        logger.warning(f"ESI character roles fetch failed: {e}")
        return []
