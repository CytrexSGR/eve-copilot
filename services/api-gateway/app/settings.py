"""API Gateway configuration."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Gateway settings from environment."""

    # Service identification
    service_name: str = "eve-api-gateway"
    environment: str = "development"
    log_level: str = "INFO"

    # CORS
    cors_origins: str = "*"

    # Microservice URLs (host environment - Docker uses service names)
    auth_service_url: str = "http://localhost:8010"
    war_intel_service_url: str = "http://localhost:8002"
    scheduler_service_url: str = "http://localhost:8003"
    market_service_url: str = "http://localhost:8004"
    production_service_url: str = "http://localhost:8005"
    shopping_service_url: str = "http://localhost:8006"
    character_service_url: str = "http://localhost:8007"
    mcp_service_url: str = "http://localhost:8008"
    wormhole_service_url: str = "http://localhost:8012"
    dotlan_service_url: str = "http://localhost:8014"
    hr_service_url: str = "http://localhost:8015"
    finance_service_url: str = "http://localhost:8016"
    military_service_url: str = "http://localhost:8020"

    # Proxy settings
    proxy_timeout: float = 60.0
    proxy_max_connections: int = 100

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()


# Route mapping: path prefix -> service URL
# Order matters: more specific routes first
SERVICE_ROUTES = {
    # Auth service (8001) — tier must be before auth (more specific prefix)
    "/api/tier": settings.auth_service_url,
    "/api/auth": settings.auth_service_url,
    "/api/settings": settings.auth_service_url,

    # War Intel service (8002) - MCP endpoints handled here too
    "/api/mcp": settings.war_intel_service_url,
    "/api/war": settings.war_intel_service_url,
    "/api/intelligence": settings.war_intel_service_url,
    "/api/alliances": settings.war_intel_service_url,
    "/api/powerbloc": settings.war_intel_service_url,
    "/api/sovereignty": settings.war_intel_service_url,
    "/api/dps": settings.war_intel_service_url,
    "/api/dogma": settings.war_intel_service_url,
    "/api/risk": settings.war_intel_service_url,
    "/api/reports": settings.war_intel_service_url,
    "/api/fingerprints": settings.war_intel_service_url,
    "/api/fleet": settings.military_service_url,
    "/api/contracts": settings.war_intel_service_url,
    "/api/jump": settings.war_intel_service_url,
    "/api/timers": settings.war_intel_service_url,
    "/api/moon": settings.war_intel_service_url,
    "/api/fuel": settings.war_intel_service_url,
    "/api/wallet": settings.war_intel_service_url,
    "/api/corp-contracts": settings.war_intel_service_url,
    "/api/events": settings.war_intel_service_url,
    "/api/military": settings.military_service_url,
    "/api/sov": settings.war_intel_service_url,
    "/api/notifications": settings.war_intel_service_url,

    # Scheduler service (8003)
    "/api/scheduler": settings.scheduler_service_url,
    "/api/jobs": settings.scheduler_service_url,

    # Market service (8004)
    "/api/orders": settings.market_service_url,
    "/api/market": settings.market_service_url,
    "/api/hunter": settings.market_service_url,
    "/api/trading": settings.market_service_url,
    "/api/alerts": settings.market_service_url,
    "/api/goals": settings.market_service_url,
    "/api/history": settings.market_service_url,
    "/api/portfolio": settings.market_service_url,
    "/api/items": settings.market_service_url,
    "/api/materials": settings.market_service_url,
    "/api/route": settings.market_service_url,
    "/api/bookmarks": settings.market_service_url,

    # Production service (8005)
    "/api/production": settings.production_service_url,
    "/api/reactions": settings.production_service_url,
    "/api/pi": settings.production_service_url,
    "/api/mining": settings.production_service_url,
    "/api/supply-chain": settings.production_service_url,

    # Shopping service (8006)
    "/api/shopping": settings.shopping_service_url,

    # Character service (8007)
    "/api/doctrines": settings.character_service_url,
    "/api/character": settings.character_service_url,
    "/api/account-groups": settings.character_service_url,
    "/api/fittings": settings.character_service_url,
    "/api/sde": settings.character_service_url,
    "/api/mastery": settings.character_service_url,
    "/api/skills": settings.character_service_url,
    "/api/research": settings.character_service_url,

    # MCP service (8008)
    "/mcp": settings.mcp_service_url,

    # Wormhole service (8011)
    "/api/wormhole": settings.wormhole_service_url,

    # DOTLAN service (8014)
    "/api/dotlan": settings.dotlan_service_url,

    # HR service (8015)
    "/api/hr": settings.hr_service_url,

    # Finance service (8016)
    "/api/finance": settings.finance_service_url,
}

# Services for health aggregation
SERVICES = {
    "auth": settings.auth_service_url,
    "war-intel": settings.war_intel_service_url,
    "scheduler": settings.scheduler_service_url,
    "market": settings.market_service_url,
    "production": settings.production_service_url,
    "shopping": settings.shopping_service_url,
    "character": settings.character_service_url,
    "mcp": settings.mcp_service_url,
    "wormhole": settings.wormhole_service_url,
    "dotlan": settings.dotlan_service_url,
    "hr": settings.hr_service_url,
    "finance": settings.finance_service_url,
    "military": settings.military_service_url,
}
