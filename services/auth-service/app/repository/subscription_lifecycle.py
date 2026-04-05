"""Subscription lifecycle management — activate, extend, query active state."""

from datetime import datetime, timezone, timedelta
from typing import Optional, List

from app.database import db_cursor
from app.models.subscription import (
    Product,
    Subscription,
    SubscriptionWithProduct,
)


class SubscriptionLifecycleMixin:
    """Methods for managing the lifecycle of subscriptions."""

    def get_active_subscriptions(self, character_id: int) -> List[SubscriptionWithProduct]:
        """Get active subscriptions for a character with product details."""
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT
                    s.id, s.character_id, s.product_id, s.starts_at, s.expires_at,
                    s.payment_id, s.created_at,
                    p.id as p_id, p.slug, p.name, p.description, p.price_isk,
                    p.duration_days, p.is_active, p.features, p.created_at as p_created_at
                FROM subscriptions s
                JOIN products p ON s.product_id = p.id
                WHERE s.character_id = %s AND s.expires_at > NOW()
                ORDER BY s.expires_at DESC
                """,
                (character_id,),
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

    def get_customer_features(self, character_id: int) -> List[str]:
        """Get all features from active subscriptions."""
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT DISTINCT unnest(p.features::text[]) as feature
                FROM subscriptions s
                JOIN products p ON s.product_id = p.id
                WHERE s.character_id = %s AND s.expires_at > NOW()
                """,
                (character_id,),
            )
            return [row["feature"] for row in cur.fetchall()]

    def extend_subscription(self, subscription_id: int, days: int) -> Optional[Subscription]:
        """Extend an existing subscription."""
        with db_cursor() as cur:
            cur.execute(
                """
                UPDATE subscriptions
                SET expires_at = expires_at + interval '%s days'
                WHERE id = %s
                RETURNING id, character_id, product_id, starts_at, expires_at, payment_id, created_at
                """,
                (days, subscription_id),
            )
            row = cur.fetchone()
            if row:
                return Subscription(**row)
            return None
