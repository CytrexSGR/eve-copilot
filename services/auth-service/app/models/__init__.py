"""Auth service models."""

from app.models.token import (
    AuthUrlResponse,
    OAuthTokenResponse,
    CharacterInfo,
    CharacterListResponse,
    StoredToken,
    AuthState,
)

from app.models.subscription import (
    # Customer models
    CustomerBase,
    Customer,
    CustomerCreate,
    # Product models
    ProductBase,
    Product,
    ProductCreate,
    ProductUpdate,
    # Subscription models
    SubscriptionBase,
    Subscription,
    SubscriptionWithProduct,
    ActiveSubscription,
    # Payment models
    PaymentBase,
    Payment,
    PaymentMatch,
    # Payment code models
    PaymentCode,
    PaymentCodeCreate,
    # Feature flag models
    FeatureFlag,
    # System config models
    SystemConfig,
    SystemConfigUpdate,
    # Response models
    PublicProfile,
    CheckoutResponse,
    FeatureCheckResponse,
    SubscriptionRequiredError,
)

__all__ = [
    # Token models
    "AuthUrlResponse",
    "OAuthTokenResponse",
    "CharacterInfo",
    "CharacterListResponse",
    "StoredToken",
    "AuthState",
    # Customer models
    "CustomerBase",
    "Customer",
    "CustomerCreate",
    # Product models
    "ProductBase",
    "Product",
    "ProductCreate",
    "ProductUpdate",
    # Subscription models
    "SubscriptionBase",
    "Subscription",
    "SubscriptionWithProduct",
    "ActiveSubscription",
    # Payment models
    "PaymentBase",
    "Payment",
    "PaymentMatch",
    # Payment code models
    "PaymentCode",
    "PaymentCodeCreate",
    # Feature flag models
    "FeatureFlag",
    # System config models
    "SystemConfig",
    "SystemConfigUpdate",
    # Response models
    "PublicProfile",
    "CheckoutResponse",
    "FeatureCheckResponse",
    "SubscriptionRequiredError",
]
