"""Subscription management router."""

import logging
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Cookie, Query

from app.services.jwt_service import JWTService
from app.repository.subscription_store import subscription_repo
from app.models.subscription import (
    Product,
    CheckoutResponse,
    FeatureCheckResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/subscription", tags=["Subscription"])


def get_jwt_service() -> JWTService:
    """Get JWT service instance."""
    return JWTService()


@router.get("/products", response_model=List[Product])
def list_products():
    """List available products."""
    products = subscription_repo.list_products(active_only=True)
    return products


@router.post("/checkout", response_model=CheckoutResponse)
def checkout(
    product_slug: str = Query(..., description="Product to purchase"),
    session: Optional[str] = Cookie(None)
):
    """Generate payment code for checkout."""
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    jwt_svc = get_jwt_service()
    payload = jwt_svc.validate_token(session)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid session")

    # Get product
    product = subscription_repo.get_product_by_slug(product_slug)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Ensure customer exists
    subscription_repo.get_or_create_customer(
        payload["character_id"],
        payload["character_name"]
    )

    # Generate payment code
    code = subscription_repo.create_payment_code(
        character_id=payload["character_id"],
        product_id=product.id,
        amount=product.price_isk
    )

    # Get billing character name
    wallet = subscription_repo.get_active_service_wallet()
    billing_name = wallet["character_name"] if wallet else "Infinimind Billing"

    return CheckoutResponse(
        payment_code=code.code,
        amount_isk=product.price_isk,
        billing_character=billing_name,
        expires_at=code.expires_at,
        instructions=f"Transfer {product.price_isk:,} ISK to '{billing_name}' with reason: {code.code}"
    )


@router.get("/check/{feature}", response_model=FeatureCheckResponse)
def check_feature_access(
    feature: str,
    session: Optional[str] = Cookie(None)
):
    """Check if user has access to a feature."""
    config = subscription_repo.get_all_config()

    # If subscription system is disabled, allow all
    if config.get("subscription_enabled") != "true":
        return FeatureCheckResponse(has_access=True, feature=feature)

    # Check if feature is public (free)
    flags = subscription_repo.get_feature_flags()
    flag = next((f for f in flags if f.slug == feature), None)

    if flag and flag.is_public:
        return FeatureCheckResponse(has_access=True, feature=feature)

    # Get products that include this feature
    all_products = subscription_repo.list_products(active_only=True)
    matching_products = [p for p in all_products if feature in (p.features or [])]

    # Anonymous users don't have access to premium features
    if not session:
        return FeatureCheckResponse(
            has_access=False,
            feature=feature,
            products=matching_products
        )

    # Validate session
    jwt_svc = get_jwt_service()
    payload = jwt_svc.validate_token(session)
    if not payload:
        return FeatureCheckResponse(
            has_access=False,
            feature=feature,
            products=matching_products
        )

    # Check user's subscriptions
    character_id = payload["character_id"]
    user_features = subscription_repo.get_customer_features(character_id)

    if feature in user_features:
        return FeatureCheckResponse(has_access=True, feature=feature)

    # No access - return products that include this feature
    payment_code = None
    if matching_products:
        # Generate payment code for the cheapest product
        cheapest = min(matching_products, key=lambda p: p.price_isk)
        code = subscription_repo.create_payment_code(
            character_id=character_id,
            product_id=cheapest.id,
            amount=cheapest.price_isk
        )
        payment_code = code.code

    return FeatureCheckResponse(
        has_access=False,
        feature=feature,
        products=matching_products,
        payment_code=payment_code
    )
