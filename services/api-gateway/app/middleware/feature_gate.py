"""
Feature-Gate Middleware for SaaS tier + module enforcement.

Intercepts every request before ProxyMiddleware:
1. Extract character_id + active_modules + org_plan from JWT session cookie
2. Check endpoint against module_map.yaml (first match wins)
3. If no module match, fall through to tier_map.yaml check
4. Allow or deny (403 module_required / upgrade_required)
"""
import logging

import httpx
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

# --- Re-export everything tests and other modules import from here ---
from app.middleware.tier_config import (  # noqa: F401
    TIER_HIERARCHY,
    DEFAULT_TIER,
    ENTITY_MODULE_GROUPS,
    JWT_SECRET,
    JWT_ALGORITHM,
    REDIS_HOST,
    REDIS_PORT,
    TIER_CACHE_TTL,
    AUTH_SERVICE_URL,
    TierMap,
    load_tier_map,
    load_module_map,
)
from app.middleware.redis_pool import get_redis
from app.middleware.gate_helpers import (  # noqa: F401
    _matches_pattern,
    _matches_module_pattern,
    _has_module,
    check_module_access,
    get_required_tier,
    _decode_jwt,
    _decode_jwt_full,
)

logger = logging.getLogger(__name__)

try:
    from eve_shared.metrics import saas_feature_gate_decisions, saas_tier_resolutions
except ImportError:
    saas_feature_gate_decisions = None
    saas_tier_resolutions = None


class FeatureGateMiddleware(BaseHTTPMiddleware):
    """Enforces tier-based access control on API endpoints."""

    def __init__(self, app, enabled: bool = True):
        super().__init__(app)
        self.enabled = enabled
        self.tier_map = load_tier_map()
        self.module_map = load_module_map()
        self._http_client = httpx.AsyncClient(timeout=5.0)
        module_count = sum(len(v) for v in self.module_map.values())
        logger.info(
            f"FeatureGateMiddleware(enabled={enabled}, "
            f"pub={len(self.tier_map.public)}, free={len(self.tier_map.free)}, "
            f"pilot={len(self.tier_map.pilot)}, corp={len(self.tier_map.corporation)}, "
            f"alliance={len(self.tier_map.alliance)}, "
            f"modules={len(self.module_map)} groups/{module_count} patterns)"
        )

    async def _resolve_tier(self, character_id: int) -> str:
        """Resolve tier: Redis cache -> auth-service -> fallback free."""
        cache_key = f"tier:{character_id}"

        # 1. Redis cache
        r = get_redis()
        if r:
            try:
                cached = r.get(cache_key)
                if cached:
                    if saas_tier_resolutions:
                        saas_tier_resolutions.labels(source="redis_cache").inc()
                    return cached
            except Exception:
                pass

        # 2. Auth-service
        try:
            resp = await self._http_client.get(
                f"{AUTH_SERVICE_URL}/api/tier/internal/resolve/{character_id}"
            )
            if resp.status_code == 200:
                tier = resp.json().get("tier", "free")
                if saas_tier_resolutions:
                    saas_tier_resolutions.labels(source="auth_service").inc()
                if r:
                    try:
                        r.setex(cache_key, TIER_CACHE_TTL, tier)
                    except Exception:
                        pass
                return tier
        except Exception as e:
            logger.warning(f"Tier resolution failed for {character_id}: {e}")

        if saas_tier_resolutions:
            saas_tier_resolutions.labels(source="fallback").inc()
        return "free"

    async def dispatch(self, request: Request, call_next):
        if not self.enabled:
            return await call_next(request)

        path = request.url.path

        # --- Phase 1: Module-based gating (checked first) ---
        if self.module_map:
            session_token = request.cookies.get("session")
            jwt_payload = _decode_jwt_full(session_token) if session_token else None

            active_modules = (jwt_payload.get("active_modules") or []) if jwt_payload else []
            org_plan = (jwt_payload.get("org_plan")) if jwt_payload else None

            allowed, required_module = check_module_access(
                active_modules, org_plan, path, self.module_map
            )

            if allowed is True:
                # Module check passed -- allow request
                return await call_next(request)

            if allowed is False:
                # Module check failed -- return 403
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": "module_required",
                        "module": required_module,
                        "upgrade_url": "/pricing",
                    },
                )

            # allowed is None -- endpoint not in module_map, fall through to tier check

        # --- Phase 2: Tier-based gating (legacy fallback) ---
        required_tier = get_required_tier(path, self.tier_map)

        # Public: no auth needed
        if required_tier == "public":
            if saas_feature_gate_decisions:
                saas_feature_gate_decisions.labels(decision="allow", required_tier="public").inc()
            return await call_next(request)

        # Extract user identity + tier from JWT
        session_token = request.cookies.get("session")
        character_id, jwt_tier = _decode_jwt(session_token) if session_token else (None, None)

        # Free tier: anonymous OK (public data), logged-in gets extras
        if required_tier == "free":
            if saas_feature_gate_decisions:
                saas_feature_gate_decisions.labels(decision="allow", required_tier="free").inc()
            return await call_next(request)

        # Paid tiers: must be logged in
        if not character_id:
            if saas_feature_gate_decisions:
                saas_feature_gate_decisions.labels(decision="login_required", required_tier=required_tier).inc()
            return JSONResponse(
                status_code=401,
                content={
                    "error": "login_required",
                    "message": "Please log in to access this feature.",
                    "required_tier": required_tier,
                },
            )

        # Check tier level -- prefer JWT claim, fall back to Redis/auth-service
        if jwt_tier:
            effective_tier = jwt_tier
            if saas_tier_resolutions:
                saas_tier_resolutions.labels(source="jwt_claim").inc()
        else:
            effective_tier = await self._resolve_tier(character_id)
        effective_rank = TIER_HIERARCHY.get(effective_tier, 0)
        required_rank = TIER_HIERARCHY.get(required_tier, 1)

        if effective_rank < required_rank:
            if saas_feature_gate_decisions:
                saas_feature_gate_decisions.labels(decision="deny", required_tier=required_tier).inc()
            return JSONResponse(
                status_code=403,
                content={
                    "error": "upgrade_required",
                    "message": f"This feature requires {required_tier} tier or higher.",
                    "current_tier": effective_tier,
                    "required_tier": required_tier,
                    "upgrade_url": "/pricing",
                },
            )

        if saas_feature_gate_decisions:
            saas_feature_gate_decisions.labels(decision="allow", required_tier=required_tier).inc()
        return await call_next(request)
