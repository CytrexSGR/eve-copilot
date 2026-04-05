"""Production service routers."""
from app.routers.simulation import router as simulation_router
from app.routers.chains import router as chains_router
from app.routers.economics import router as economics_router
from app.routers.pi import router as pi_router
from app.routers.pi_requirements import router as pi_requirements_router
from app.routers.reaction_requirements import router as reaction_requirements_router
from app.routers.supply_chain import router as supply_chain_router
from app.routers.mining import router as mining_router
from app.routers.optimize import router as optimize_router
from app.routers.reactions import router as reactions_router
from app.routers.ledger import router as ledger_router
from app.routers.tax import router as tax_router
from app.routers.workflow import router as workflow_router
from app.routers.invention import router as invention_router
from app.routers.compare import router as compare_router
from app.routers.internal import router as internal_router
from app.routers.projects import router as projects_router

__all__ = [
    "simulation_router",
    "chains_router",
    "economics_router",
    "pi_router",
    "pi_requirements_router",
    "reaction_requirements_router",
    "supply_chain_router",
    "mining_router",
    "optimize_router",
    "reactions_router",
    "ledger_router",
    "tax_router",
    "workflow_router",
    "invention_router",
    "compare_router",
    "internal_router",
    "projects_router",
]
