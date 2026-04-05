"""Subscription query and reporting operations."""

from typing import Optional, List, Dict, Any

from app.database import db_cursor
from app.models.subscription import (
    Customer,
    Product,
    Payment,
    SubscriptionWithProduct,
)


class SubscriptionQueryMixin:
    """Methods for listing and reporting on subscription data."""

    def list_customers(self, limit: int = 100, offset: int = 0) -> List[Customer]:
        """List customers with pagination."""
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT character_id, character_name, corporation_id, alliance_id,
                       created_at, last_login
                FROM customers
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
                """,
                (limit, offset),
            )
            return [Customer(**row) for row in cur.fetchall()]

    def list_products(self, active_only: bool = True) -> List[Product]:
        """List all products, optionally filtered by active status."""
        with db_cursor() as cur:
            if active_only:
                cur.execute(
                    """
                    SELECT id, slug, name, description, price_isk, duration_days,
                           is_active, features, created_at
                    FROM products
                    WHERE is_active = true
                    ORDER BY price_isk ASC
                    """
                )
            else:
                cur.execute(
                    """
                    SELECT id, slug, name, description, price_isk, duration_days,
                           is_active, features, created_at
                    FROM products
                    ORDER BY price_isk ASC
                    """
                )
            return [Product(**row) for row in cur.fetchall()]

    def list_subscriptions(
        self, active_only: bool = False, limit: int = 100
    ) -> List[SubscriptionWithProduct]:
        """List subscriptions (admin view)."""
        with db_cursor() as cur:
            if active_only:
                cur.execute(
                    """
                    SELECT
                        s.id, s.character_id, s.product_id, s.starts_at, s.expires_at,
                        s.payment_id, s.created_at,
                        p.id as p_id, p.slug, p.name, p.description, p.price_isk,
                        p.duration_days, p.is_active, p.features, p.created_at as p_created_at
                    FROM subscriptions s
                    JOIN products p ON s.product_id = p.id
                    WHERE s.expires_at > NOW()
                    ORDER BY s.created_at DESC
                    LIMIT %s
                    """,
                    (limit,),
                )
            else:
                cur.execute(
                    """
                    SELECT
                        s.id, s.character_id, s.product_id, s.starts_at, s.expires_at,
                        s.payment_id, s.created_at,
                        p.id as p_id, p.slug, p.name, p.description, p.price_isk,
                        p.duration_days, p.is_active, p.features, p.created_at as p_created_at
                    FROM subscriptions s
                    JOIN products p ON s.product_id = p.id
                    ORDER BY s.created_at DESC
                    LIMIT %s
                    """,
                    (limit,),
                )
            results = []
            for row in cur.fetchall():
                product = Product(
                    id=row["p_id"],
                    slug=row["slug"],
                    name=row["name"],
                    description=row["description"],
                    price_isk=row["price_isk"],
                    duration_days=row["duration_days"],
                    is_active=row["is_active"],
                    features=row["features"],
                    created_at=row["p_created_at"],
                )
                subscription = SubscriptionWithProduct(
                    id=row["id"],
                    character_id=row["character_id"],
                    product_id=row["product_id"],
                    starts_at=row["starts_at"],
                    expires_at=row["expires_at"],
                    payment_id=row["payment_id"],
                    created_at=row["created_at"],
                    product=product,
                )
                results.append(subscription)
            return results

    def list_payments(
        self, status: Optional[str] = None, limit: int = 100
    ) -> List[Payment]:
        """List payments, optionally filtered by status."""
        with db_cursor() as cur:
            if status:
                cur.execute(
                    """
                    SELECT id, journal_ref_id, from_character_id, from_character_name,
                           amount, reason, received_at, status, matched_customer_id,
                           payment_code, processed_at, notes, created_at
                    FROM payments
                    WHERE status = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (status, limit),
                )
            else:
                cur.execute(
                    """
                    SELECT id, journal_ref_id, from_character_id, from_character_name,
                           amount, reason, received_at, status, matched_customer_id,
                           payment_code, processed_at, notes, created_at
                    FROM payments
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (limit,),
                )
            return [Payment(**row) for row in cur.fetchall()]

    def get_stats(self) -> Dict[str, Any]:
        """Get dashboard statistics."""
        with db_cursor() as cur:
            stats = {}

            # Total customers
            cur.execute("SELECT COUNT(*) as count FROM customers")
            stats["total_customers"] = cur.fetchone()["count"]

            # Active subscriptions
            cur.execute(
                "SELECT COUNT(*) as count FROM subscriptions WHERE expires_at > NOW()"
            )
            stats["active_subscriptions"] = cur.fetchone()["count"]

            # Pending payments
            cur.execute(
                "SELECT COUNT(*) as count FROM payments WHERE status = 'pending'"
            )
            stats["pending_payments"] = cur.fetchone()["count"]

            # Total revenue (processed payments)
            cur.execute(
                """
                SELECT COALESCE(SUM(amount), 0) as total
                FROM payments
                WHERE status = 'processed'
                """
            )
            stats["total_revenue_isk"] = cur.fetchone()["total"]

            # Revenue last 30 days
            cur.execute(
                """
                SELECT COALESCE(SUM(amount), 0) as total
                FROM payments
                WHERE status = 'processed' AND processed_at > NOW() - interval '30 days'
                """
            )
            stats["revenue_30d_isk"] = cur.fetchone()["total"]

            # Active products
            cur.execute("SELECT COUNT(*) as count FROM products WHERE is_active = true")
            stats["active_products"] = cur.fetchone()["count"]

            return stats
