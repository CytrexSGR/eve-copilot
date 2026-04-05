"""
Tier resolution and subscription management for SaaS feature-gating.

Tier hierarchy: free < pilot < corporation < alliance < coalition
Stacking: Alliance includes Corp includes Pilot includes Free.
"""
import math
import secrets
import string
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)

TIER_HIERARCHY = {
    "free": 0,
    "pilot": 1,
    "corporation": 2,
    "alliance": 3,
    "coalition": 4,
}

ACTIVE_STATUSES = {"active", "grace"}

GRACE_PERIOD_DAYS = 3
WARNING_DAYS = 7


def compute_subscription_status_detail(sub: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compute detailed status info for a subscription.
    Pure function — no DB, no side effects.
    """
    if sub is None:
        return {
            "phase": "none", "tier": "free", "days_remaining": 0,
            "grace_days_remaining": 0, "warning": None,
            "access_until": None, "expires_at": None, "auto_renew": False,
        }

    now = datetime.now(timezone.utc)
    status = sub.get("status", "expired")
    expires_at = sub.get("expires_at")
    tier = sub.get("tier", "free")
    auto_renew = sub.get("auto_renew", False)

    if status == "cancelled":
        return {
            "phase": "cancelled", "tier": tier, "days_remaining": 0,
            "grace_days_remaining": 0, "warning": None,
            "access_until": None, "expires_at": expires_at.isoformat() if expires_at else None,
            "auto_renew": False,
        }

    if status == "expired":
        return {
            "phase": "expired", "tier": tier, "days_remaining": 0,
            "grace_days_remaining": 0, "warning": "subscription_expired",
            "access_until": None, "expires_at": expires_at.isoformat() if expires_at else None,
            "auto_renew": auto_renew,
        }

    if status == "grace":
        days_since_expiry = math.floor((now - expires_at).total_seconds() / 86400) if expires_at else 0
        grace_remaining = max(0, GRACE_PERIOD_DAYS - days_since_expiry)
        access_until = (expires_at + timedelta(days=GRACE_PERIOD_DAYS)) if expires_at else None
        return {
            "phase": "grace", "tier": tier, "days_remaining": 0,
            "grace_days_remaining": grace_remaining,
            "warning": "subscription_grace",
            "access_until": access_until.isoformat() if access_until else None,
            "expires_at": expires_at.isoformat() if expires_at else None,
            "auto_renew": auto_renew,
        }

    # Active
    days_remaining = max(0, math.floor((expires_at - now).total_seconds() / 86400)) if expires_at else 0
    warning = "subscription_expiring" if (expires_at and (expires_at - now).total_seconds() < WARNING_DAYS * 86400) else None
    phase = "expiring_soon" if warning else "active"
    return {
        "phase": phase, "tier": tier, "days_remaining": days_remaining,
        "grace_days_remaining": 0, "warning": warning,
        "access_until": expires_at.isoformat() if expires_at else None,
        "expires_at": expires_at.isoformat() if expires_at else None,
        "auto_renew": auto_renew,
    }


def tier_includes(effective_tier: str, required_tier: str) -> bool:
    """Check if effective_tier grants access to required_tier features."""
    return TIER_HIERARCHY.get(effective_tier, 0) >= TIER_HIERARCHY.get(required_tier, 0)


def resolve_effective_tier(
    own_subs: List[Dict[str, Any]],
    corp_subs: List[Dict[str, Any]],
    alliance_subs: List[Dict[str, Any]],
) -> str:
    """
    Determine effective tier from all applicable subscriptions.
    Stacking: highest tier wins across personal, corp, and alliance subs.
    Only active/grace subscriptions count.
    """
    all_subs = own_subs + corp_subs + alliance_subs
    best_tier = "free"
    best_rank = 0

    for sub in all_subs:
        if sub.get("status") not in ACTIVE_STATUSES:
            continue
        tier = sub.get("tier", "free")
        rank = TIER_HIERARCHY.get(tier, 0)
        if rank > best_rank:
            best_rank = rank
            best_tier = tier

    return best_tier


_PAY_CODE_CHARS = string.ascii_uppercase + string.digits


def generate_payment_code(db_cursor_fn, table: str, column: str) -> str:
    """Generate a unique PAY-XXXXX reference code.

    Shared by TierRepository (tier_payments.reference_code) and
    SubscriptionRepository (payment_codes.code).

    Args:
        db_cursor_fn: Callable context-manager that yields a DB cursor.
        table: Table to check for uniqueness (e.g. 'tier_payments').
        column: Column holding existing codes (e.g. 'reference_code').

    Returns:
        A unique code in the format PAY-XXXXX (A-Z, 0-9).

    Raises:
        RuntimeError: If a unique code cannot be generated after 10 attempts.
    """
    for _ in range(10):
        code = "PAY-" + "".join(secrets.choice(_PAY_CODE_CHARS) for _ in range(5))
        with db_cursor_fn() as cur:
            cur.execute(
                f"SELECT 1 FROM {table} WHERE {column} = %s",
                (code,),
            )
            if not cur.fetchone():
                return code
    raise RuntimeError("Could not generate unique payment code")


class TierRepository:
    """Database operations for tier subscriptions, payments, and roles.

    Uses auth-service db_cursor pattern (RealDictCursor, auto-commit).
    """

    def __init__(self):
        from app.database import db_cursor
        self._db_cursor = db_cursor

    # --- Tier Resolution (called by gateway via internal endpoint) ---

    def get_character_tier(self, character_id: int) -> Dict[str, Any]:
        """Full tier resolution for a character."""
        with self._db_cursor() as cur:
            # 1. Own pilot subscription
            cur.execute("""
                SELECT id, tier, status, expires_at
                FROM tier_subscriptions
                WHERE paid_by = %s AND status IN ('active', 'grace')
                ORDER BY expires_at DESC
            """, (character_id,))
            own_subs = [dict(r) for r in cur.fetchall()]

            # 2. Corp subscription (character's corp from platform_accounts)
            cur.execute("""
                SELECT ts.id, ts.tier, ts.status, ts.expires_at
                FROM tier_subscriptions ts
                WHERE ts.corporation_id = (
                    SELECT pa.corporation_id
                    FROM platform_accounts pa
                    JOIN account_characters ac ON ac.account_id = pa.id
                    WHERE ac.character_id = %s
                )
                  AND ts.status IN ('active', 'grace')
                  AND ts.corporation_id IS NOT NULL
                ORDER BY ts.expires_at DESC
            """, (character_id,))
            corp_subs = [dict(r) for r in cur.fetchall()]

            # 3. Alliance subscription (character's alliance from platform_accounts)
            cur.execute("""
                SELECT ts.id, ts.tier, ts.status, ts.expires_at
                FROM tier_subscriptions ts
                WHERE ts.alliance_id = (
                    SELECT pa.alliance_id
                    FROM platform_accounts pa
                    JOIN account_characters ac ON ac.account_id = pa.id
                    WHERE ac.character_id = %s
                )
                  AND ts.status IN ('active', 'grace')
                  AND ts.alliance_id IS NOT NULL
                ORDER BY ts.expires_at DESC
            """, (character_id,))
            alliance_subs = [dict(r) for r in cur.fetchall()]

        effective = resolve_effective_tier(own_subs, corp_subs, alliance_subs)

        # Find the winning subscription for metadata
        all_active = [s for s in (own_subs + corp_subs + alliance_subs)
                      if s.get("status") in ACTIVE_STATUSES]
        winner = max(
            all_active,
            key=lambda s: TIER_HIERARCHY.get(s["tier"], 0),
            default=None,
        )

        return {
            "tier": effective,
            "subscription_id": winner["id"] if winner else None,
            "expires_at": winner["expires_at"].isoformat() if winner else None,
        }

    # --- Subscriptions ---

    def create_subscription(
        self, tier: str, paid_by: int,
        corporation_id: int = None, alliance_id: int = None,
        duration_days: int = 30,
    ) -> Dict[str, Any]:
        with self._db_cursor() as cur:
            cur.execute("""
                INSERT INTO tier_subscriptions
                    (tier, paid_by, corporation_id, alliance_id, expires_at)
                VALUES (%s, %s, %s, %s, NOW() + INTERVAL '1 day' * %s)
                RETURNING id, tier, paid_by, corporation_id, alliance_id,
                          status, expires_at, auto_renew, created_at
            """, (tier, paid_by, corporation_id, alliance_id, duration_days))
            return dict(cur.fetchone())

    def get_active_subscription(self, **filters) -> Optional[Dict[str, Any]]:
        """Get active subscription by filters."""
        conditions = ["status IN ('active', 'grace')"]
        params = []
        for key, val in filters.items():
            if val is not None and key in ("paid_by", "corporation_id", "alliance_id", "tier"):
                conditions.append(f"{key} = %s")
                params.append(val)

        with self._db_cursor() as cur:
            cur.execute(f"""
                SELECT * FROM tier_subscriptions
                WHERE {' AND '.join(conditions)}
                ORDER BY expires_at DESC LIMIT 1
            """, params)
            row = cur.fetchone()
            return dict(row) if row else None

    def expire_subscriptions(self) -> int:
        """Mark expired subscriptions. Returns count changed."""
        with self._db_cursor() as cur:
            # Active → Grace (past expiry)
            cur.execute("""
                UPDATE tier_subscriptions
                SET status = 'grace', updated_at = NOW()
                WHERE status = 'active' AND expires_at < NOW()
            """)
            grace_count = cur.rowcount

            if grace_count > 0:
                try:
                    from eve_shared.metrics import saas_subscriptions_transitions
                    saas_subscriptions_transitions.labels(
                        from_status="active", to_status="grace"
                    ).inc(grace_count)
                except Exception:
                    pass

            # Grace → Expired (3 days after expiry)
            cur.execute("""
                UPDATE tier_subscriptions
                SET status = 'expired', updated_at = NOW()
                WHERE status = 'grace'
                  AND expires_at < NOW() - INTERVAL '3 days'
            """)
            expired_count = cur.rowcount

            if expired_count > 0:
                try:
                    from eve_shared.metrics import saas_subscriptions_transitions
                    saas_subscriptions_transitions.labels(
                        from_status="grace", to_status="expired"
                    ).inc(expired_count)
                except Exception:
                    pass

            return grace_count + expired_count

    # --- Payments ---

    def create_payment_record(
        self, character_id: int, amount: int, reference_code: str,
        tier: str = None, corporation_id: int = None, alliance_id: int = None,
    ) -> Dict[str, Any]:
        with self._db_cursor() as cur:
            cur.execute("""
                INSERT INTO tier_payments
                    (character_id, amount, reference_code, tier, corporation_id, alliance_id)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING *
            """, (character_id, amount, reference_code, tier, corporation_id, alliance_id))
            return dict(cur.fetchone())

    def get_pending_payments(self) -> List[Dict[str, Any]]:
        with self._db_cursor() as cur:
            cur.execute("""
                SELECT id, reference_code, amount, character_id,
                       tier, corporation_id, alliance_id
                FROM tier_payments WHERE status = 'pending'
            """)
            return [dict(r) for r in cur.fetchall()]

    def verify_payment(
        self, reference_code: str, esi_journal_id: int,
    ) -> Optional[Dict[str, Any]]:
        """Mark payment as verified and link ESI journal entry."""
        with self._db_cursor() as cur:
            # Dedup check
            cur.execute(
                "SELECT id FROM tier_payments WHERE esi_journal_id = %s",
                (esi_journal_id,),
            )
            if cur.fetchone():
                return None

            cur.execute("""
                UPDATE tier_payments
                SET status = 'verified', esi_journal_id = %s, verified_at = NOW()
                WHERE reference_code = %s AND status = 'pending'
                RETURNING *
            """, (esi_journal_id, reference_code))
            row = cur.fetchone()
            if row:
                try:
                    from eve_shared.metrics import saas_payments_total, saas_payments_isk
                    saas_payments_total.labels(status="verified").inc()
                    saas_payments_isk.labels(tier=row.get("tier", "pilot")).inc(row.get("amount", 0))
                except Exception:
                    pass
            return dict(row) if row else None

    def generate_reference_code(self) -> str:
        """Generate unique PAY-XXXXX reference code."""
        return generate_payment_code(
            self._db_cursor, "tier_payments", "reference_code"
        )

    # --- Pricing ---

    def get_pricing(self, tier: str = None) -> List[Dict[str, Any]]:
        with self._db_cursor() as cur:
            if tier:
                cur.execute(
                    "SELECT * FROM tier_pricing WHERE tier = %s AND is_active = true",
                    (tier,),
                )
            else:
                cur.execute(
                    "SELECT * FROM tier_pricing WHERE is_active = true ORDER BY base_price_isk"
                )
            return [dict(r) for r in cur.fetchall()]

    # --- Platform Roles ---

    def get_role(self, corporation_id: int, character_id: int) -> Optional[str]:
        with self._db_cursor() as cur:
            cur.execute("""
                SELECT role FROM platform_roles
                WHERE corporation_id = %s AND character_id = %s
            """, (corporation_id, character_id))
            row = cur.fetchone()
            return row["role"] if row else None

    def set_role(
        self, corporation_id: int, character_id: int, role: str, granted_by: int,
    ) -> Dict[str, Any]:
        with self._db_cursor() as cur:
            cur.execute("""
                INSERT INTO platform_roles (corporation_id, character_id, role, granted_by)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (corporation_id, character_id)
                DO UPDATE SET role = EXCLUDED.role,
                             granted_by = EXCLUDED.granted_by,
                             granted_at = NOW()
                RETURNING *
            """, (corporation_id, character_id, role, granted_by))
            return dict(cur.fetchone())

    def remove_role(self, corporation_id: int, character_id: int) -> bool:
        with self._db_cursor() as cur:
            cur.execute("""
                DELETE FROM platform_roles
                WHERE corporation_id = %s AND character_id = %s
            """, (corporation_id, character_id))
            return cur.rowcount > 0

    def list_roles(self, corporation_id: int) -> List[Dict[str, Any]]:
        with self._db_cursor() as cur:
            cur.execute("""
                SELECT pr.*, ac.character_name
                FROM platform_roles pr
                LEFT JOIN account_characters ac ON ac.character_id = pr.character_id
                WHERE pr.corporation_id = %s
                ORDER BY pr.role, ac.character_name
            """, (corporation_id,))
            return [dict(r) for r in cur.fetchall()]

    # --- Service Wallet ---

    def get_active_wallet(self) -> Optional[Dict[str, Any]]:
        with self._db_cursor() as cur:
            cur.execute("""
                SELECT * FROM service_wallets
                WHERE is_active = true
                ORDER BY id DESC LIMIT 1
            """)
            row = cur.fetchone()
            return dict(row) if row else None

    def update_wallet_journal_ref(self, wallet_id: int, ref_id: int) -> bool:
        with self._db_cursor() as cur:
            cur.execute("""
                UPDATE service_wallets SET last_journal_ref_id = %s WHERE id = %s
            """, (ref_id, wallet_id))
            return cur.rowcount > 0

    # --- Tier Cache ---

    def update_tier_cache(self, character_id: int, tier: str,
                          corporation_id: int = None, alliance_id: int = None):
        with self._db_cursor() as cur:
            cur.execute("""
                INSERT INTO character_tier_cache
                    (character_id, effective_tier, corporation_id, alliance_id, updated_at)
                VALUES (%s, %s, %s, %s, NOW())
                ON CONFLICT (character_id) DO UPDATE SET
                    effective_tier = EXCLUDED.effective_tier,
                    corporation_id = EXCLUDED.corporation_id,
                    alliance_id = EXCLUDED.alliance_id,
                    updated_at = NOW()
            """, (character_id, tier, corporation_id, alliance_id))

    def get_cached_tier(self, character_id: int) -> Optional[str]:
        with self._db_cursor() as cur:
            cur.execute("""
                SELECT effective_tier FROM character_tier_cache
                WHERE character_id = %s
                  AND updated_at > NOW() - INTERVAL '10 minutes'
            """, (character_id,))
            row = cur.fetchone()
            return row["effective_tier"] if row else None
