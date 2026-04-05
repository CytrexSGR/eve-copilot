"""Module subscription repository — pure functions + DB queries.

Tables: module_subscriptions, org_plans, org_seat_assignments, module_pricing
Pattern: db_cursor from app.database (RealDictCursor, auto-commit)
"""
from datetime import datetime, timezone
from typing import Optional


# --- Bundle definitions ---

BUNDLE_CONTENTS = {
    "intel_pack": [
        "warfare_intel", "war_economy", "wormhole_intel",
        "doctrine_intel", "battle_analysis",
    ],
    "entity_pack": [
        "corp_intel_unlimited", "alliance_intel_unlimited", "powerbloc_intel_unlimited",
    ],
    "pilot_complete": [
        "warfare_intel", "war_economy", "wormhole_intel",
        "doctrine_intel", "battle_analysis",
        "character_suite", "market_analysis",
        "corp_intel_unlimited", "alliance_intel_unlimited", "powerbloc_intel_unlimited",
    ],
}

# Entity modules: any _1/_5/_unlimited variant grants the base module
ENTITY_MODULE_GROUPS = {
    "corp_intel": ["corp_intel_1", "corp_intel_5", "corp_intel_unlimited"],
    "alliance_intel": ["alliance_intel_1", "alliance_intel_5", "alliance_intel_unlimited"],
    "powerbloc_intel": ["powerbloc_intel_1", "powerbloc_intel_5", "powerbloc_intel_unlimited"],
}


# --- Pure functions (testable without DB) ---

def resolve_active_modules(subscription_rows: list[dict]) -> list[str]:
    """Given module_subscriptions rows, return sorted list of active (non-expired) module names.

    Deduplicates by module_name. Only includes modules where expires_at > now.
    """
    now = datetime.now(timezone.utc)
    active = set()
    for row in subscription_rows:
        if row["expires_at"] > now:
            active.add(row["module_name"])
    return sorted(active)


def build_module_jwt_claims(
    active_modules: list[str],
    org_plan: Optional[dict],
) -> dict:
    """Build JWT claims dict for module-based gating."""
    return {
        "active_modules": active_modules,
        "org_plan": org_plan,
    }


def is_trial_available(subscription_rows: list[dict], module_name: str) -> bool:
    """Check if a module trial is available (never used before).

    Returns True if no row with matching module_name has trial_used=True.
    """
    for row in subscription_rows:
        if row["module_name"] == module_name and row.get("trial_used"):
            return False
    return True


def expand_bundle(bundle_name: str) -> list[str]:
    """Expand a bundle name into its constituent module names.

    If bundle_name is not a known bundle, returns it as a single-element list.
    """
    return BUNDLE_CONTENTS.get(bundle_name, [bundle_name])


def has_module_access(active_modules: list[str], required_module: str) -> bool:
    """Check if user has access to a required module.

    Handles entity module groups: e.g., having 'corp_intel_5' grants
    access to 'corp_intel' (the base group name).
    """
    # Direct match
    if required_module in active_modules:
        return True

    # Check entity group: if required_module is a group base name,
    # any variant in active_modules grants access
    if required_module in ENTITY_MODULE_GROUPS:
        group_variants = ENTITY_MODULE_GROUPS[required_module]
        for variant in group_variants:
            if variant in active_modules:
                return True

    return False


# --- DB query functions ---

def get_active_modules_for_account(cursor, account_id: int) -> list[dict]:
    """Fetch all active module subscriptions for an account."""
    cursor.execute(
        """SELECT module_name, scope, expires_at, trial_used
           FROM module_subscriptions
           WHERE account_id = %s AND expires_at > NOW()
           ORDER BY expires_at DESC""",
        (account_id,),
    )
    return cursor.fetchall()


def get_org_plan_for_character(
    cursor,
    character_id: int,
    corp_id: Optional[int],
    alliance_id: Optional[int],
) -> Optional[dict]:
    """Resolve org plan + seat status for a character.

    Checks corporation plan first, then alliance plan.
    Returns dict with plan info and seat status, or None.
    """
    if not corp_id and not alliance_id:
        return None

    # Check corporation plan first, then alliance
    for org_type, org_id in [("corporation", corp_id), ("alliance", alliance_id)]:
        if not org_id:
            continue
        cursor.execute(
            """SELECT op.id, op.plan_name, op.heavy_seats, op.expires_at,
                      EXISTS(
                          SELECT 1 FROM org_seat_assignments osa
                          WHERE osa.org_plan_id = op.id AND osa.character_id = %s
                      ) AS has_seat,
                      (SELECT COUNT(*) FROM org_seat_assignments osa2
                       WHERE osa2.org_plan_id = op.id) AS seats_used
               FROM org_plans op
               WHERE op.org_type = %s AND op.org_id = %s AND op.expires_at > NOW()
               ORDER BY op.expires_at DESC LIMIT 1""",
            (character_id, org_type, org_id),
        )
        row = cursor.fetchone()
        if row:
            return {
                "type": org_type,
                "plan": row["plan_name"],
                "has_seat": row["has_seat"],
                "heavy_seats": row["heavy_seats"],
                "seats_used": row["seats_used"],
                "expires_at": row["expires_at"].isoformat() if row["expires_at"] else None,
            }
    return None


def create_module_subscription(
    cursor,
    account_id: int,
    module_name: str,
    duration_days: int = 30,
    scope: Optional[dict] = None,
    is_trial: bool = False,
) -> int:
    """Create a module subscription. Returns subscription ID."""
    cursor.execute(
        """INSERT INTO module_subscriptions
               (account_id, module_name, scope, expires_at, trial_used)
           VALUES (%s, %s, %s, NOW() + INTERVAL '1 day' * %s, %s)
           RETURNING id""",
        (account_id, module_name, scope or {}, duration_days, is_trial),
    )
    return cursor.fetchone()["id"]
