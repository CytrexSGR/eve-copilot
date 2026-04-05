"""Admin router for subscription management."""

import logging
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Query

from app.repository.subscription_store import subscription_repo
from app.models.subscription import (
    Customer,
    Product,
    ProductCreate,
    ProductUpdate,
    Payment,
    PaymentMatch,
    SystemConfigUpdate,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["Admin"])


# === Stats ===

@router.get("/stats")
def get_stats():
    """Get subscription system statistics."""
    return subscription_repo.get_stats()


# === Customers ===

@router.get("/customers", response_model=List[Customer])
def list_customers(
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0)
):
    """List all customers."""
    return subscription_repo.list_customers(limit=limit, offset=offset)


# === Products ===

@router.get("/products", response_model=List[Product])
def list_all_products():
    """List all products (including inactive)."""
    return subscription_repo.list_products(active_only=False)


@router.post("/products", response_model=Product)
def create_product(data: ProductCreate):
    """Create new product."""
    # Check slug is unique
    existing = subscription_repo.get_product_by_slug(data.slug)
    if existing:
        raise HTTPException(status_code=400, detail="Product slug already exists")

    return subscription_repo.create_product(data.model_dump())


@router.put("/products/{product_id}", response_model=Product)
def update_product(product_id: int, data: ProductUpdate):
    """Update product."""
    existing = subscription_repo.get_product(product_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Product not found")

    # Check slug uniqueness if changing
    if data.slug and data.slug != existing.slug:
        conflict = subscription_repo.get_product_by_slug(data.slug)
        if conflict:
            raise HTTPException(status_code=400, detail="Product slug already exists")

    result = subscription_repo.update_product(
        product_id, data.model_dump(exclude_none=True)
    )
    if not result:
        raise HTTPException(status_code=404, detail="Product not found")
    return result


@router.delete("/products/{product_id}")
def delete_product(product_id: int):
    """Delete (deactivate) product."""
    existing = subscription_repo.get_product(product_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Product not found")

    subscription_repo.delete_product(product_id)
    return {"message": f"Product {product_id} deactivated"}


# === Subscriptions ===

@router.get("/subscriptions")
def list_subscriptions(
    active_only: bool = Query(True),
    limit: int = Query(100, le=500)
):
    """List all subscriptions."""
    return subscription_repo.list_subscriptions(active_only=active_only, limit=limit)


@router.post("/subscriptions")
def create_subscription_manual(
    character_id: int = Query(...),
    product_id: int = Query(...)
):
    """Manually create subscription (admin override)."""
    # Verify customer exists
    customer = subscription_repo.get_customer(character_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Verify product exists
    product = subscription_repo.get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    return subscription_repo.create_subscription(character_id, product_id)


# === Payments ===

@router.get("/payments", response_model=List[Payment])
def list_payments(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(100, le=500)
):
    """List payments."""
    return subscription_repo.list_payments(status=status, limit=limit)


@router.post("/payments/{payment_id}/match")
def match_payment(payment_id: int, data: PaymentMatch):
    """Manually match a pending payment to customer and product."""
    # Verify customer
    customer = subscription_repo.get_customer(data.customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Verify product
    product = subscription_repo.get_product(data.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Update payment status
    payment = subscription_repo.update_payment_status(
        payment_id=payment_id,
        status="matched",
        matched_customer_id=data.customer_id,
        notes=f"Manually matched by admin to product {product.name}"
    )

    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    # Create subscription
    sub = subscription_repo.create_subscription(
        character_id=data.customer_id,
        product_id=data.product_id,
        payment_id=payment_id
    )

    # Mark as processed
    subscription_repo.update_payment_status(payment_id, "processed")

    return {
        "payment": payment,
        "subscription": sub
    }


# === Config ===

@router.get("/config")
def get_config():
    """Get all system configuration."""
    return subscription_repo.get_all_config()


@router.put("/config/{key}")
def update_config(key: str, data: SystemConfigUpdate):
    """Update configuration value."""
    # Validate key exists
    current = subscription_repo.get_config(key)
    if current is None:
        raise HTTPException(status_code=404, detail=f"Config key '{key}' not found")

    subscription_repo.set_config(key, data.value)
    return {"key": key, "value": data.value}
