"""Subscription system models."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


# === Customer Models ===

class CustomerBase(BaseModel):
    """Base customer model."""
    character_id: int
    character_name: str
    corporation_id: Optional[int] = None
    alliance_id: Optional[int] = None


class Customer(CustomerBase):
    """Customer with timestamps."""
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


class CustomerCreate(BaseModel):
    """Create customer from ESI data."""
    character_id: int
    character_name: str
    corporation_id: Optional[int] = None
    alliance_id: Optional[int] = None


# === Product Models ===

class ProductBase(BaseModel):
    """Base product model."""
    slug: str
    name: str
    description: Optional[str] = None
    price_isk: int
    duration_days: int = 30
    is_active: bool = True
    features: List[str] = []


class Product(ProductBase):
    """Product with ID."""
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class ProductCreate(ProductBase):
    """Create product."""
    pass


class ProductUpdate(BaseModel):
    """Update product - all fields optional."""
    slug: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    price_isk: Optional[int] = None
    duration_days: Optional[int] = None
    is_active: Optional[bool] = None
    features: Optional[List[str]] = None


# === Subscription Models ===

class SubscriptionBase(BaseModel):
    """Base subscription model."""
    character_id: int
    product_id: int
    starts_at: datetime
    expires_at: datetime


class Subscription(SubscriptionBase):
    """Subscription with ID."""
    id: int
    payment_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class SubscriptionWithProduct(Subscription):
    """Subscription with product details."""
    product: Product


class ActiveSubscription(BaseModel):
    """Active subscription for user profile."""
    product_slug: str
    product_name: str
    features: List[str]
    expires_at: datetime
    days_remaining: int


# === Payment Models ===

class PaymentBase(BaseModel):
    """Base payment model."""
    journal_ref_id: int
    from_character_id: int
    from_character_name: Optional[str] = None
    amount: int
    reason: Optional[str] = None
    received_at: datetime


class Payment(PaymentBase):
    """Payment with status."""
    id: int
    status: str  # pending, matched, processed, failed
    matched_customer_id: Optional[int] = None
    payment_code: Optional[str] = None
    processed_at: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PaymentMatch(BaseModel):
    """Manual payment matching."""
    customer_id: int
    product_id: int


# === Payment Code Models ===

class PaymentCode(BaseModel):
    """Payment code for ISK transfer."""
    code: str
    character_id: int
    product_id: Optional[int] = None
    amount_expected: Optional[int] = None
    created_at: datetime
    expires_at: datetime
    used_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PaymentCodeCreate(BaseModel):
    """Generate payment code."""
    product_id: Optional[int] = None


# === Feature Flag Models ===

class FeatureFlag(BaseModel):
    """Feature flag for access control."""
    slug: str
    name: str
    route_patterns: List[str] = []
    is_public: bool = False

    class Config:
        from_attributes = True


# === System Config Models ===

class SystemConfig(BaseModel):
    """System configuration."""
    key: str
    value: str
    description: Optional[str] = None

    class Config:
        from_attributes = True


class SystemConfigUpdate(BaseModel):
    """Update config value."""
    value: str


# === Response Models ===

class PublicProfile(BaseModel):
    """Public user profile."""
    character_id: int
    character_name: str
    subscriptions: List[ActiveSubscription]
    features: List[str]


class CheckoutResponse(BaseModel):
    """Checkout response with payment instructions."""
    payment_code: str
    amount_isk: int
    billing_character: str
    expires_at: datetime
    instructions: str


class FeatureCheckResponse(BaseModel):
    """Feature access check response."""
    has_access: bool
    feature: str
    products: List[Product] = []
    payment_code: Optional[str] = None


class SubscriptionRequiredError(BaseModel):
    """403 error response."""
    error: str = "subscription_required"
    feature: str
    products: List[Product]
    payment_code: Optional[str] = None
