"""Shared SQL filter helpers for offensive and defensive intelligence queries.

Extracted from shared_offensive.py and shared_defensive.py to eliminate
duplication of _victim_filter, _attacker_filter, _params, _params_with_days.
"""

from .entity_context import EntityContext, EntityType


def _victim_filter(ctx: EntityContext) -> str:
    """WHERE clause for victim-side filtering (named params)."""
    if ctx.entity_type == EntityType.CORPORATION:
        return "km.victim_corporation_id = %(entity_id)s"
    elif ctx.entity_type == EntityType.POWERBLOC:
        return "km.victim_alliance_id = ANY(%(entity_id)s)"
    return "km.victim_alliance_id = %(entity_id)s"


def _attacker_filter(ctx: EntityContext) -> str:
    """WHERE clause for attacker-side filtering (named params)."""
    if ctx.entity_type == EntityType.CORPORATION:
        return "ka.corporation_id = %(entity_id)s"
    elif ctx.entity_type == EntityType.POWERBLOC:
        return "ka.alliance_id = ANY(%(entity_id)s)"
    return "ka.alliance_id = %(entity_id)s"


def _params(ctx: EntityContext) -> dict:
    """Base named params dict."""
    return {"entity_id": ctx.filter_value}


def _params_with_days(ctx: EntityContext, days: int) -> dict:
    """Named params dict including days."""
    return {"entity_id": ctx.filter_value, "days": days}
