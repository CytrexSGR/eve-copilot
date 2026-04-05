"""Finance Service routers."""

from app.routers.wallet import router as wallet_router
from app.routers.mining import router as mining_router
from app.routers.invoices import router as invoices_router
from app.routers.reports import router as reports_router
from app.routers.srp import router as srp_router
from app.routers.buyback import router as buyback_router

__all__ = [
    "wallet_router",
    "mining_router",
    "invoices_router",
    "reports_router",
    "srp_router",
    "buyback_router",
]
