"""Helper functions for feature-gate middleware.

Pattern matching, tier comparison, module access checking, and JWT decoding.
"""
import jwt as pyjwt

import app.middleware.tier_config as tier_config
from app.middleware.tier_config import (
    DEFAULT_TIER,
    ENTITY_MODULE_GROUPS,
    TIER_HIERARCHY,
    TierMap,
)


def _matches_module_pattern(path: str, pattern: str) -> bool:
    """Check if path matches a module-map pattern.

    Supports mid-path wildcards using fnmatch:
    - Exact: /api/foo matches /api/foo
    - Trailing wildcard: /api/foo/* matches /api/foo/bar and /api/foo/bar/baz
    - Mid-path wildcard: /api/foo/*/bar matches /api/foo/123/bar
    """
    if "*" not in pattern:
        return path == pattern

    # For trailing /* patterns, use prefix matching (same as tier_map)
    # to allow multi-segment matches like /api/foo/bar/baz matching /api/foo/*
    if pattern.endswith("/*") and "*" not in pattern[:-2]:
        prefix = pattern[:-1]  # "/api/foo/" from "/api/foo/*"
        return path.startswith(prefix) or path == prefix.rstrip("/")

    # For mid-path wildcards: split into segments and match segment-by-segment
    # /api/war/battle/*/participants must match /api/war/battle/123/participants
    # but * only matches a single segment (no slashes)
    pattern_parts = pattern.split("/")
    path_parts = path.split("/")

    # If pattern ends with /*, allow extra segments after
    if pattern_parts[-1] == "*":
        # Trailing wildcard after mid-path wildcards
        if len(path_parts) < len(pattern_parts) - 1:
            return False
        # Match all parts except the trailing *
        for pp, pathp in zip(pattern_parts[:-1], path_parts[:len(pattern_parts) - 1]):
            if pp != "*" and pp != pathp:
                return False
        return True

    # Fixed-length pattern with mid-path wildcards
    if len(pattern_parts) != len(path_parts):
        return False

    for pp, pathp in zip(pattern_parts, path_parts):
        if pp == "*":
            continue  # wildcard matches any single segment
        if pp != pathp:
            return False
    return True


def _has_module(active_modules: list[str], required_module: str) -> bool:
    """Check if user has the required module, including entity group matching.

    For entity modules (corp_intel, alliance_intel, powerbloc_intel),
    any variant (_1, _5, _unlimited) grants access.
    """
    # Direct match
    if required_module in active_modules:
        return True

    # Entity group match: if required is base (corp_intel),
    # accept any variant (corp_intel_1, corp_intel_5, corp_intel_unlimited)
    variants = ENTITY_MODULE_GROUPS.get(required_module)
    if variants:
        return any(v in active_modules for v in variants)

    return False


def check_module_access(
    active_modules: list[str],
    org_plan: dict | None,
    endpoint: str,
    module_map: dict[str, list[str]],
) -> tuple[bool | None, str | None]:
    """Check if user has module access for endpoint.

    Returns (allowed, required_module):
    - (True, None) = allowed by module check
    - (False, "module_name") = blocked, needs this module
    - (None, None) = endpoint not in module_map, fall through to tier check
    """
    # Find which module this endpoint belongs to
    for module_name, patterns in module_map.items():
        for pattern in patterns:
            if _matches_module_pattern(endpoint, pattern):
                # Found a match -- now check access

                # "free" module: always allow
                if module_name == "free":
                    return (True, None)

                # corp_mgmt: requires org plan with type corporation or alliance
                if module_name == "corp_mgmt":
                    if org_plan and org_plan.get("type") in ("corporation", "alliance"):
                        return (True, None)
                    return (False, "corp_mgmt")

                # alliance_mgmt: requires org plan with type alliance
                if module_name == "alliance_mgmt":
                    if org_plan and org_plan.get("type") == "alliance":
                        return (True, None)
                    return (False, "alliance_mgmt")

                # All other modules: check active_modules list
                if _has_module(active_modules, module_name):
                    return (True, None)

                return (False, module_name)

    # No match in module_map -- fall through to tier check
    return (None, None)


def _matches_pattern(path: str, pattern: str) -> bool:
    """Check if path matches a tier-map pattern.

    Supports:
    - Exact match: /api/foo matches /api/foo
    - Wildcard: /api/foo/* matches /api/foo/bar and /api/foo/bar/baz
    """
    if pattern.endswith("/*"):
        prefix = pattern[:-1]  # "/api/foo/" from "/api/foo/*"
        return path.startswith(prefix) or path == prefix.rstrip("/")
    return path == pattern


def get_required_tier(path: str, tier_map: TierMap) -> str:
    """
    Determine minimum tier required for a route.
    Checks from most permissive (public) to most restrictive (coalition).
    First match wins -- this ensures specific free-tier overrides
    win over broader pilot-tier patterns.
    """
    for pattern in tier_map.public:
        if _matches_pattern(path, pattern):
            return "public"

    for pattern in tier_map.free:
        if _matches_pattern(path, pattern):
            return "free"

    for pattern in tier_map.pilot:
        if _matches_pattern(path, pattern):
            return "pilot"

    for pattern in tier_map.corporation:
        if _matches_pattern(path, pattern):
            return "corporation"

    for pattern in tier_map.alliance:
        if _matches_pattern(path, pattern):
            return "alliance"

    for pattern in tier_map.coalition:
        if _matches_pattern(path, pattern):
            return "coalition"

    return DEFAULT_TIER


def _decode_jwt(token: str) -> tuple:
    """Decode JWT, return (character_id, tier_from_jwt). Gateway trusts auth-service signed tokens."""
    if not tier_config.JWT_SECRET:
        return None, None
    try:
        payload = pyjwt.decode(token, tier_config.JWT_SECRET, algorithms=[tier_config.JWT_ALGORITHM])
        char_id = int(payload.get("sub", 0)) or None
        tier = payload.get("tier")
        return char_id, tier
    except Exception:
        return None, None


def _decode_jwt_full(token: str) -> dict | None:
    """Decode JWT, return full payload dict or None."""
    if not tier_config.JWT_SECRET:
        return None
    try:
        return pyjwt.decode(token, tier_config.JWT_SECRET, algorithms=[tier_config.JWT_ALGORITHM])
    except Exception:
        return None
