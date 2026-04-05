"""Subscription system database operations.

CRUD operations live here. Lifecycle and query/reporting methods are
provided via mixin classes from sibling modules:
  - subscription_lifecycle.py  (activate, extend, active-state queries)
  - subscription_queries.py    (list, stats, reporting)
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any

from psycopg2.extras import RealDictCursor, Json

from app.database import db_cursor
from app.repository.tier_store import generate_payment_code
from app.models.subscription import (
    Customer,
    Product,
    Subscription,
    SubscriptionWithProduct,
    Payment,
    PaymentCode,
    FeatureFlag,
    SystemConfig,
)
from app.repository.subscription_lifecycle import SubscriptionLifecycleMixin
from app.repository.subscription_queries import SubscriptionQueryMixin


class SubscriptionRepository(SubscriptionLifecycleMixin, SubscriptionQueryMixin):
    """Repository for all subscription-related database operations.

    CRUD operations are defined directly on this class.
    Lifecycle management is inherited from SubscriptionLifecycleMixin.
    Query/reporting operations are inherited from SubscriptionQueryMixin.
    """

    # ==================== Customers ====================

    def get_customer(self, character_id: int) -> Optional[Customer]:
        """Get customer by character ID."""
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT character_id, character_name, corporation_id, alliance_id,
                       created_at, last_login
                FROM customers
                WHERE character_id = %s
                """,
                (character_id,),
            )
            row = cur.fetchone()
            if row:
                return Customer(**row)
            return None

    def get_or_create_customer(
        self,
        character_id: int,
        character_name: str,
        corporation_id: Optional[int] = None,
        alliance_id: Optional[int] = None,
    ) -> Customer:
        """Get existing customer or create new one (upsert)."""
        with db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO customers (character_id, character_name, corporation_id, alliance_id, last_login)
                VALUES (%s, %s, %s, %s, NOW())
                ON CONFLICT (character_id) DO UPDATE SET
                    character_name = EXCLUDED.character_name,
                    corporation_id = EXCLUDED.corporation_id,
                    alliance_id = EXCLUDED.alliance_id,
                    last_login = NOW()
                RETURNING character_id, character_name, corporation_id, alliance_id, created_at, last_login
                """,
                (character_id, character_name, corporation_id, alliance_id),
            )
            row = cur.fetchone()
            return Customer(**row)

    def update_customer_login(self, character_id: int) -> bool:
        """Update last login timestamp."""
        with db_cursor() as cur:
            cur.execute(
                """
                UPDATE customers SET last_login = NOW()
                WHERE character_id = %s
                """,
                (character_id,),
            )
            return cur.rowcount > 0

    # ==================== Products ====================

    def get_product(self, product_id: int) -> Optional[Product]:
        """Get product by ID."""
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT id, slug, name, description, price_isk, duration_days,
                       is_active, features, created_at
                FROM products
                WHERE id = %s
                """,
                (product_id,),
            )
            row = cur.fetchone()
            if row:
                return Product(**row)
            return None

    def get_product_by_slug(self, slug: str) -> Optional[Product]:
        """Get product by slug."""
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT id, slug, name, description, price_isk, duration_days,
                       is_active, features, created_at
                FROM products
                WHERE slug = %s
                """,
                (slug,),
            )
            row = cur.fetchone()
            if row:
                return Product(**row)
            return None

    def find_products_by_price(self, amount: int) -> List[Product]:
        """Find products matching an ISK amount."""
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT id, slug, name, description, price_isk, duration_days,
                       is_active, features, created_at
                FROM products
                WHERE is_active = true AND price_isk = %s
                """,
                (amount,),
            )
            return [Product(**row) for row in cur.fetchall()]

    def create_product(self, data: Dict[str, Any]) -> Product:
        """Create a new product."""
        with db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO products (slug, name, description, price_isk, duration_days, is_active, features)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id, slug, name, description, price_isk, duration_days, is_active, features, created_at
                """,
                (
                    data["slug"],
                    data["name"],
                    data.get("description"),
                    data["price_isk"],
                    data.get("duration_days", 30),
                    data.get("is_active", True),
                    Json(data.get("features", [])),
                ),
            )
            row = cur.fetchone()
            return Product(**row)

    def update_product(self, product_id: int, data: Dict[str, Any]) -> Optional[Product]:
        """Update product with dynamic fields."""
        if not data:
            return self.get_product(product_id)

        # Build dynamic update query
        set_clauses = []
        values = []
        for key, value in data.items():
            if value is not None:
                if key == "features":
                    set_clauses.append(f"{key} = %s")
                    values.append(Json(value))
                else:
                    set_clauses.append(f"{key} = %s")
                    values.append(value)

        if not set_clauses:
            return self.get_product(product_id)

        values.append(product_id)

        with db_cursor() as cur:
            cur.execute(
                f"""
                UPDATE products SET {', '.join(set_clauses)}
                WHERE id = %s
                RETURNING id, slug, name, description, price_isk, duration_days, is_active, features, created_at
                """,
                tuple(values),
            )
            row = cur.fetchone()
            if row:
                return Product(**row)
            return None

    def delete_product(self, product_id: int) -> bool:
        """Soft delete product (set inactive)."""
        with db_cursor() as cur:
            cur.execute(
                """
                UPDATE products SET is_active = false
                WHERE id = %s
                """,
                (product_id,),
            )
            return cur.rowcount > 0

    # ==================== Subscriptions (create) ====================

    def create_subscription(
        self,
        character_id: int,
        product_id: int,
        payment_id: Optional[int] = None,
    ) -> Subscription:
        """Create a new subscription with automatic expiry calculation."""
        with db_cursor() as cur:
            # Get product duration
            cur.execute("SELECT duration_days FROM products WHERE id = %s", (product_id,))
            product = cur.fetchone()
            duration_days = product["duration_days"] if product else 30

            now = datetime.now(timezone.utc)
            expires_at = now + timedelta(days=duration_days)

            cur.execute(
                """
                INSERT INTO subscriptions (character_id, product_id, starts_at, expires_at, payment_id)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, character_id, product_id, starts_at, expires_at, payment_id, created_at
                """,
                (character_id, product_id, now, expires_at, payment_id),
            )
            row = cur.fetchone()
            return Subscription(**row)

    # ==================== Payments ====================

    def create_payment(self, data: Dict[str, Any]) -> Payment:
        """Record an incoming payment."""
        with db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO payments (
                    journal_ref_id, from_character_id, from_character_name,
                    amount, reason, received_at, status, payment_code
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, journal_ref_id, from_character_id, from_character_name,
                          amount, reason, received_at, status, matched_customer_id,
                          payment_code, processed_at, notes, created_at
                """,
                (
                    data["journal_ref_id"],
                    data["from_character_id"],
                    data.get("from_character_name"),
                    data["amount"],
                    data.get("reason"),
                    data["received_at"],
                    data.get("status", "pending"),
                    data.get("payment_code"),
                ),
            )
            row = cur.fetchone()
            return Payment(**row)

    def update_payment_status(
        self,
        payment_id: int,
        status: str,
        matched_customer_id: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> Optional[Payment]:
        """Update payment status."""
        with db_cursor() as cur:
            cur.execute(
                """
                UPDATE payments SET
                    status = %s,
                    matched_customer_id = COALESCE(%s, matched_customer_id),
                    notes = COALESCE(%s, notes),
                    processed_at = CASE WHEN %s IN ('processed', 'failed') THEN NOW() ELSE processed_at END
                WHERE id = %s
                RETURNING id, journal_ref_id, from_character_id, from_character_name,
                          amount, reason, received_at, status, matched_customer_id,
                          payment_code, processed_at, notes, created_at
                """,
                (status, matched_customer_id, notes, status, payment_id),
            )
            row = cur.fetchone()
            if row:
                return Payment(**row)
            return None

    def get_payment_by_journal_ref(self, journal_ref_id: int) -> Optional[Payment]:
        """Get payment by journal reference ID (for deduplication)."""
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT id, journal_ref_id, from_character_id, from_character_name,
                       amount, reason, received_at, status, matched_customer_id,
                       payment_code, processed_at, notes, created_at
                FROM payments
                WHERE journal_ref_id = %s
                """,
                (journal_ref_id,),
            )
            row = cur.fetchone()
            if row:
                return Payment(**row)
            return None

    # ==================== Payment Codes ====================

    def generate_payment_code(self) -> str:
        """Generate a unique PAY-XXXXX code."""
        return generate_payment_code(db_cursor, "payment_codes", "code")

    def create_payment_code(
        self,
        character_id: int,
        product_id: Optional[int] = None,
        amount: Optional[int] = None,
    ) -> PaymentCode:
        """Create a payment code for ISK transfer."""
        code = self.generate_payment_code()
        expires_at = datetime.now(timezone.utc) + timedelta(hours=24)

        with db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO payment_codes (code, character_id, product_id, amount_expected, expires_at)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING code, character_id, product_id, amount_expected, created_at, expires_at, used_at
                """,
                (code, character_id, product_id, amount, expires_at),
            )
            row = cur.fetchone()
            return PaymentCode(**row)

    def get_payment_code(self, code: str) -> Optional[PaymentCode]:
        """Get a valid (not expired, not used) payment code."""
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT code, character_id, product_id, amount_expected, created_at, expires_at, used_at
                FROM payment_codes
                WHERE code = %s AND expires_at > NOW() AND used_at IS NULL
                """,
                (code,),
            )
            row = cur.fetchone()
            if row:
                return PaymentCode(**row)
            return None

    def mark_code_used(self, code: str) -> bool:
        """Mark a payment code as used."""
        with db_cursor() as cur:
            cur.execute(
                """
                UPDATE payment_codes SET used_at = NOW()
                WHERE code = %s AND used_at IS NULL
                """,
                (code,),
            )
            return cur.rowcount > 0

    # ==================== Feature Flags ====================

    def get_feature_flags(self) -> List[FeatureFlag]:
        """Get all feature flags."""
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT slug, name, route_patterns, is_public
                FROM feature_flags
                ORDER BY slug
                """
            )
            return [FeatureFlag(**row) for row in cur.fetchall()]

    def get_feature_for_route(self, route: str) -> Optional[FeatureFlag]:
        """Find feature flag matching a route pattern."""
        with db_cursor() as cur:
            # Get all features and check patterns
            cur.execute(
                """
                SELECT slug, name, route_patterns, is_public
                FROM feature_flags
                """
            )
            for row in cur.fetchall():
                patterns = row["route_patterns"] or []
                for pattern in patterns:
                    # Convert glob pattern to simple matching
                    # Pattern: /api/wars/* should match /api/wars/anything
                    if pattern.endswith("/*"):
                        prefix = pattern[:-1]  # Remove trailing *
                        if route.startswith(prefix):
                            return FeatureFlag(**row)
                    elif route == pattern:
                        return FeatureFlag(**row)
            return None

    # ==================== System Config ====================

    def get_config(self, key: str) -> Optional[str]:
        """Get a single config value."""
        with db_cursor() as cur:
            cur.execute(
                "SELECT value FROM system_config WHERE key = %s",
                (key,),
            )
            row = cur.fetchone()
            if row:
                return row["value"]
            return None

    def get_all_config(self) -> Dict[str, str]:
        """Get all config as a dictionary."""
        with db_cursor() as cur:
            cur.execute("SELECT key, value FROM system_config")
            return {row["key"]: row["value"] for row in cur.fetchall()}

    def set_config(self, key: str, value: str) -> SystemConfig:
        """Set a config value (upsert)."""
        with db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO system_config (key, value)
                VALUES (%s, %s)
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
                RETURNING key, value, description
                """,
                (key, value),
            )
            row = cur.fetchone()
            return SystemConfig(**row)

    # ==================== Service Wallets ====================

    def get_active_service_wallet(self) -> Optional[Dict[str, Any]]:
        """Get the active service wallet for receiving ISK."""
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT id, character_id, character_name, is_active, last_journal_ref_id
                FROM service_wallets
                WHERE is_active = true
                LIMIT 1
                """
            )
            return cur.fetchone()

    def update_wallet_journal_ref(self, wallet_id: int, ref_id: int) -> bool:
        """Update the last processed journal reference."""
        with db_cursor() as cur:
            cur.execute(
                """
                UPDATE service_wallets SET last_journal_ref_id = %s
                WHERE id = %s
                """,
                (ref_id, wallet_id),
            )
            return cur.rowcount > 0


# Singleton instance for use in routers
subscription_repo = SubscriptionRepository()
