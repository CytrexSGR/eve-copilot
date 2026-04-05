"""Fitting constraint validation."""

from collections import Counter
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class FittingViolation:
    """A single fitting constraint violation."""
    resource: str       # "cpu", "pg", "calibration", "maxGroupFitted", "maxTypeFitted"
    used: float         # actual amount used or fitted
    total: float        # allowed limit
    type_name: Optional[str] = None  # module name for group/type violations
    group_name: Optional[str] = None


ATTR_MAX_GROUP_FITTED = 1544
ATTR_MAX_TYPE_FITTED = 2431

# Hardcoded fitting rules not present in SDE
HARDCODED_GROUP_LIMITS = {
    330: 1,  # Cloaking devices — max 1 per ship
}


def validate_resource_limits(
    ship_cpu: float, used_cpu: float,
    ship_pg: float, used_pg: float,
    ship_cal: float, used_cal: float,
) -> List[FittingViolation]:
    """Check CPU, PG, and calibration limits."""
    violations = []
    if used_cpu > ship_cpu:
        violations.append(FittingViolation("cpu", used_cpu, ship_cpu))
    if used_pg > ship_pg:
        violations.append(FittingViolation("pg", used_pg, ship_pg))
    if used_cal > ship_cal:
        violations.append(FittingViolation("calibration", used_cal, ship_cal))
    return violations


def validate_max_group_fitted(
    module_type_ids: List[int],
    module_groups: Dict[int, int],
    max_group_fitted: Dict[int, int],
) -> List[FittingViolation]:
    """Check maxGroupFitted limits (e.g., only 1 Damage Control).

    max_group_fitted: {type_id: limit} -- any type_id with this attr means
    its entire group is limited to that many modules.
    """
    if not max_group_fitted:
        return []

    # Map group_id -> limit (from any type that has the restriction)
    group_limits: Dict[int, int] = {}
    for tid, limit in max_group_fitted.items():
        gid = module_groups.get(tid)
        if gid is not None:
            group_limits[gid] = limit

    # Count modules per group
    group_counts: Counter = Counter()
    for tid in module_type_ids:
        gid = module_groups.get(tid)
        if gid is not None:
            group_counts[gid] += 1

    violations = []
    for gid, count in group_counts.items():
        limit = group_limits.get(gid)
        if limit is not None and count > limit:
            violations.append(FittingViolation(
                resource="maxGroupFitted", used=count, total=limit,
            ))
    return violations


def validate_max_type_fitted(
    module_type_ids: List[int],
    max_type_fitted: Dict[int, int],
) -> List[FittingViolation]:
    """Check maxTypeFitted limits."""
    if not max_type_fitted:
        return []
    type_counts = Counter(module_type_ids)
    violations = []
    for tid, count in type_counts.items():
        limit = max_type_fitted.get(tid)
        if limit is not None and count > limit:
            violations.append(FittingViolation(
                resource="maxTypeFitted", used=count, total=limit,
            ))
    return violations


def validate_hardcoded_rules(
    module_type_ids: List[int],
    module_groups: Dict[int, int],
) -> List[FittingViolation]:
    """Check hardcoded fitting rules not present in SDE."""
    violations = []
    group_counts: Counter = Counter()
    for tid in module_type_ids:
        gid = module_groups.get(tid)
        if gid is not None:
            group_counts[gid] += 1

    for gid, limit in HARDCODED_GROUP_LIMITS.items():
        if group_counts.get(gid, 0) > limit:
            violations.append(FittingViolation(
                resource="maxGroupFitted",
                used=group_counts[gid],
                total=limit,
                group_name=f"group_{gid}",
            ))
    return violations


def load_fitting_constraints(db, module_type_ids: List[int]) -> dict:
    """Load maxGroupFitted and maxTypeFitted from SDE for fitted modules.

    Returns: {"max_group_fitted": {type_id: limit}, "max_type_fitted": {type_id: limit}}
    """
    from psycopg2.extras import RealDictCursor

    unique_ids = list(set(module_type_ids))
    if not unique_ids:
        return {"max_group_fitted": {}, "max_type_fitted": {}}

    with db.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT "typeID", "attributeID",
                   COALESCE("valueFloat", "valueInt"::float) as value
            FROM "dgmTypeAttributes"
            WHERE "typeID" = ANY(%s)
              AND "attributeID" IN (%s, %s)
        """, (unique_ids, ATTR_MAX_GROUP_FITTED, ATTR_MAX_TYPE_FITTED))

        max_group = {}
        max_type = {}
        for row in cur.fetchall():
            val = int(row["value"])
            if row["attributeID"] == ATTR_MAX_GROUP_FITTED:
                max_group[row["typeID"]] = val
            elif row["attributeID"] == ATTR_MAX_TYPE_FITTED:
                max_type[row["typeID"]] = val

    return {"max_group_fitted": max_group, "max_type_fitted": max_type}
