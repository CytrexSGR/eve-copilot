"""Fitting constraint validation — CPU/PG limits, maxGroupFitted, hardpoints."""

from typing import List, Dict

from psycopg2.extras import RealDictCursor

from app.services.fitting_service import FittingItem
from app.services.dogma.constraints import (
    validate_resource_limits,
    validate_max_group_fitted,
    validate_max_type_fitted,
    validate_hardcoded_rules,
    load_fitting_constraints,
)
from .constants import (
    ATTR_CPU_OUTPUT, ATTR_POWER_OUTPUT, ATTR_CALIBRATION_OUTPUT,
    ATTR_CALIBRATION_COST,
    ATTR_TURRET_SLOTS, ATTR_LAUNCHER_SLOTS,
    EFFECT_TURRET_FITTED, EFFECT_LAUNCHER_FITTED,
)


class ValidationMixin:
    """Mixin providing _validate_fitting."""

    def _validate_fitting(
        self,
        ship_attrs: dict,
        items: List[FittingItem],
        modified_module_attrs: Dict[int, Dict[int, float]] = None,
    ) -> List[dict]:
        """Validate fitting constraints and return violations."""
        module_type_ids = [item.type_id for item in items for _ in range(item.quantity)]
        violations = []

        # Resource limits (CPU, PG, Calibration)
        # Use Dogma-modified values when available (includes ship/skill bonuses)
        if modified_module_attrs is not None:
            used_cpu = sum(
                modified_module_attrs.get(i.type_id, {}).get(50, 0) * i.quantity
                for i in items
            )
            used_pg = sum(
                modified_module_attrs.get(i.type_id, {}).get(30, 0) * i.quantity
                for i in items
            )
        else:
            used_cpu, used_pg = self._sum_cpu_pg_with_skills(items)
        used_cal = self._sum_rig_attr(items, ATTR_CALIBRATION_COST)

        resource_violations = validate_resource_limits(
            ship_cpu=ship_attrs.get(ATTR_CPU_OUTPUT, 0),
            used_cpu=used_cpu,
            ship_pg=ship_attrs.get(ATTR_POWER_OUTPUT, 0),
            used_pg=used_pg,
            ship_cal=ship_attrs.get(ATTR_CALIBRATION_OUTPUT, 0),
            used_cal=used_cal,
        )
        violations.extend([
            {"resource": v.resource, "used": v.used, "total": v.total}
            for v in resource_violations
        ])

        # maxGroupFitted / maxTypeFitted
        constraints = load_fitting_constraints(self.db, module_type_ids)
        module_groups = self._load_module_groups(module_type_ids)

        group_violations = validate_max_group_fitted(
            module_type_ids, module_groups, constraints["max_group_fitted"]
        )
        type_violations = validate_max_type_fitted(
            module_type_ids, constraints["max_type_fitted"]
        )
        violations.extend([
            {"resource": v.resource, "used": v.used, "total": v.total}
            for v in group_violations
        ])
        violations.extend([
            {"resource": v.resource, "used": v.used, "total": v.total}
            for v in type_violations
        ])

        # Hardcoded rules (e.g., 1 cloak per ship)
        hardcoded_violations = validate_hardcoded_rules(module_type_ids, module_groups)
        violations.extend([
            {"resource": v.resource, "used": v.used, "total": v.total,
             "group_name": v.group_name}
            for v in hardcoded_violations
        ])

        # Hardpoint limits (turret/launcher)
        turret_total = int(ship_attrs.get(ATTR_TURRET_SLOTS, 0))
        launcher_total = int(ship_attrs.get(ATTR_LAUNCHER_SLOTS, 0))
        unique_type_ids = list(set(i.type_id for i in items if 27 <= i.flag <= 34))
        if unique_type_ids:
            with self.db.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT "typeID", "effectID"
                    FROM "dgmTypeEffects"
                    WHERE "typeID" = ANY(%s)
                      AND "effectID" IN (%s, %s)
                """, (unique_type_ids, EFFECT_TURRET_FITTED, EFFECT_LAUNCHER_FITTED))
                hp_effects: Dict[int, set] = {}
                for row in cur.fetchall():
                    hp_effects.setdefault(row["typeID"], set()).add(row["effectID"])

            turret_used = 0
            launcher_used = 0
            for item in items:
                if 27 <= item.flag <= 34:
                    effs = hp_effects.get(item.type_id, set())
                    if EFFECT_TURRET_FITTED in effs:
                        turret_used += item.quantity
                    if EFFECT_LAUNCHER_FITTED in effs:
                        launcher_used += item.quantity

            if turret_used > turret_total:
                violations.append({
                    "resource": "turret_hardpoints",
                    "used": turret_used,
                    "total": turret_total,
                })
            if launcher_used > launcher_total:
                violations.append({
                    "resource": "launcher_hardpoints",
                    "used": launcher_used,
                    "total": launcher_total,
                })

        return violations
