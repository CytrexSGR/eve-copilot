"""Resource usage — PG/CPU/calibration/hardpoints/drones, slot usage, module mass."""

from typing import List, Dict, Optional

from psycopg2.extras import RealDictCursor

from app.services.fitting_service import FittingItem
from .models import SlotUsage, ResourceUsage
from .constants import (
    ATTR_HI_SLOTS, ATTR_MED_SLOTS, ATTR_LOW_SLOTS, ATTR_RIG_SLOTS,
    ATTR_POWER_OUTPUT, ATTR_CPU_OUTPUT, ATTR_CALIBRATION_OUTPUT,
    ATTR_TURRET_SLOTS, ATTR_LAUNCHER_SLOTS,
    ATTR_DRONE_CAPACITY, ATTR_DRONE_BANDWIDTH,
    ATTR_CPU_NEED, ATTR_POWER_NEED, ATTR_CALIBRATION_COST,
    ATTR_VOLUME, ATTR_DRONE_BW_NEED,
    ATTR_MASS,
    EFFECT_TURRET_FITTED, EFFECT_LAUNCHER_FITTED,
    DEFAULT_FITTING_SKILL_LEVEL,
)


class ResourcesMixin:
    """Mixin providing resource/slot calculation methods."""

    def _calc_slot_usage(self, ship_attrs: dict, items: List[FittingItem]) -> SlotUsage:
        """Calculate how many slots are used."""
        hi_used = sum(1 for i in items if 27 <= i.flag <= 34)
        med_used = sum(1 for i in items if 19 <= i.flag <= 26)
        low_used = sum(1 for i in items if 11 <= i.flag <= 18)
        rig_used = sum(1 for i in items if 92 <= i.flag <= 99)

        return SlotUsage(
            hi_total=int(ship_attrs.get(ATTR_HI_SLOTS, 0)),
            hi_used=hi_used,
            med_total=int(ship_attrs.get(ATTR_MED_SLOTS, 0)),
            med_used=med_used,
            low_total=int(ship_attrs.get(ATTR_LOW_SLOTS, 0)),
            low_used=low_used,
            rig_total=int(ship_attrs.get(ATTR_RIG_SLOTS, 0)),
            rig_used=rig_used,
        )

    def _calc_resource_usage(
        self,
        ship_attrs: dict,
        items: List[FittingItem],
        modified_module_attrs: Dict[int, Dict[int, float]] = None,
        module_states: Optional[Dict[int, str]] = None,
    ) -> ResourceUsage:
        """Calculate PG, CPU, calibration, hardpoints, and drone usage.

        When modified_module_attrs is provided (from Dogma engine), uses those
        values for CPU/PG — they already include ship bonuses, skill reductions,
        and module interactions. Falls back to raw SDE values otherwise.

        Offline modules (module_states[flag] == "offline") are excluded from
        CPU/PG usage — they are not powered on and consume no resources.
        """
        pg_total = ship_attrs.get(ATTR_POWER_OUTPUT, 0)
        cpu_total = ship_attrs.get(ATTR_CPU_OUTPUT, 0)
        calibration_total = ship_attrs.get(ATTR_CALIBRATION_OUTPUT, 0)
        turret_hp_total = int(ship_attrs.get(ATTR_TURRET_SLOTS, 0))
        launcher_hp_total = int(ship_attrs.get(ATTR_LAUNCHER_SLOTS, 0))
        drone_bay_total = ship_attrs.get(ATTR_DRONE_CAPACITY, 0)
        drone_bw_total = ship_attrs.get(ATTR_DRONE_BANDWIDTH, 0)

        module_type_ids = list(set(i.type_id for i in items))
        if not module_type_ids:
            return ResourceUsage(
                pg_total=round(pg_total, 1),
                cpu_total=round(cpu_total, 1),
                calibration_total=round(calibration_total, 1),
                turret_hardpoints_total=turret_hp_total,
                launcher_hardpoints_total=launcher_hp_total,
                drone_bay_total=round(drone_bay_total, 1),
                drone_bandwidth_total=round(drone_bw_total, 1),
            )

        # When Dogma-modified attrs are available, use them for CPU/PG.
        # Still need SDE for calibration, drone volume, hardpoint effects.
        use_dogma = modified_module_attrs is not None

        with self.db.cursor(cursor_factory=RealDictCursor) as cur:
            # Always need calibration cost and drone BW from SDE
            # (Dogma doesn't modify these for most modules)
            sde_attr_ids = [ATTR_CALIBRATION_COST, ATTR_DRONE_BW_NEED]
            if not use_dogma:
                # Fallback: also fetch CPU/PG from SDE
                sde_attr_ids.extend([ATTR_CPU_NEED, ATTR_POWER_NEED, ATTR_VOLUME])

            cur.execute("""
                SELECT "typeID", "attributeID",
                       COALESCE("valueFloat", "valueInt"::float) as value
                FROM "dgmTypeAttributes"
                WHERE "typeID" = ANY(%s)
                  AND "attributeID" = ANY(%s)
            """, (module_type_ids, sde_attr_ids))

            sde_attrs: Dict[int, Dict[int, float]] = {}
            for row in cur.fetchall():
                tid = row["typeID"]
                if tid not in sde_attrs:
                    sde_attrs[tid] = {}
                sde_attrs[tid][row["attributeID"]] = row["value"]

            # Fetch turret/launcher effects for hardpoint counting
            cur.execute("""
                SELECT "typeID", "effectID"
                FROM "dgmTypeEffects"
                WHERE "typeID" = ANY(%s)
                  AND "effectID" IN (%s, %s)
            """, (module_type_ids, EFFECT_TURRET_FITTED, EFFECT_LAUNCHER_FITTED))

            mod_effects: Dict[int, set] = {}
            for row in cur.fetchall():
                tid = row["typeID"]
                if tid not in mod_effects:
                    mod_effects[tid] = set()
                mod_effects[tid].add(row["effectID"])

            # Fetch drone volumes from invTypes.volume (not in dgmTypeAttributes)
            drone_type_ids = list(set(i.type_id for i in items if i.flag == 87))
            drone_volumes: Dict[int, float] = {}
            if drone_type_ids:
                cur.execute("""
                    SELECT "typeID", "volume"
                    FROM "invTypes"
                    WHERE "typeID" = ANY(%s)
                """, (drone_type_ids,))
                drone_volumes = {row["typeID"]: float(row["volume"] or 0) for row in cur.fetchall()}

        # Weapon fitting skill reductions only needed when NOT using Dogma
        # (Dogma already applies all skill and ship bonuses to module attrs)
        if not use_dogma:
            wu_cpu_mult = 1 + (-5.0 * DEFAULT_FITTING_SKILL_LEVEL) / 100  # 0.75
            awu_pg_mult = 1 + (-2.0 * DEFAULT_FITTING_SKILL_LEVEL) / 100  # 0.90

        pg_used = 0.0
        cpu_used = 0.0
        calibration_used = 0.0
        turret_hp_used = 0
        launcher_hp_used = 0
        drone_bay_used = 0.0
        drone_bw_used = 0.0

        for item in items:
            effects = mod_effects.get(item.type_id, set())

            # Offline modules do not consume CPU or PG
            is_online = self._is_module_online(item.flag, module_states)

            if is_online:
                if use_dogma:
                    # Use Dogma-modified CPU/PG (already includes all bonuses)
                    dogma_attrs = modified_module_attrs.get(item.type_id, {})
                    item_cpu = dogma_attrs.get(ATTR_CPU_NEED, 0)
                    item_pg = dogma_attrs.get(ATTR_POWER_NEED, 0)
                else:
                    # Fallback: raw SDE + hardcoded weapon skill reductions
                    attrs = sde_attrs.get(item.type_id, {})
                    item_cpu = attrs.get(ATTR_CPU_NEED, 0)
                    item_pg = attrs.get(ATTR_POWER_NEED, 0)
                    is_weapon = (EFFECT_TURRET_FITTED in effects or EFFECT_LAUNCHER_FITTED in effects)
                    if is_weapon:
                        item_cpu *= wu_cpu_mult
                        item_pg *= awu_pg_mult

                pg_used += item_pg * item.quantity
                cpu_used += item_cpu * item.quantity

            # Calibration: rig-slot items (flag 92-99) — always from SDE
            if 92 <= item.flag <= 99:
                calibration_used += sde_attrs.get(item.type_id, {}).get(ATTR_CALIBRATION_COST, 0) * item.quantity

            # Turret/launcher hardpoints
            if EFFECT_TURRET_FITTED in effects:
                turret_hp_used += item.quantity
            if EFFECT_LAUNCHER_FITTED in effects:
                launcher_hp_used += item.quantity

            # Drone tracking: items with flag=87
            if item.flag == 87:
                drone_bay_used += drone_volumes.get(item.type_id, 0) * item.quantity
                drone_bw_used += sde_attrs.get(item.type_id, {}).get(ATTR_DRONE_BW_NEED, 0) * item.quantity

        # Cap drone bandwidth used at ship's total — only active drones
        # consume bandwidth, and the ship can't deploy more than its limit.
        effective_drone_bw = min(drone_bw_used, drone_bw_total)

        return ResourceUsage(
            pg_total=round(pg_total, 1),
            pg_used=round(pg_used, 1),
            cpu_total=round(cpu_total, 1),
            cpu_used=round(cpu_used, 1),
            calibration_total=round(calibration_total, 1),
            calibration_used=round(calibration_used, 1),
            turret_hardpoints_total=turret_hp_total,
            turret_hardpoints_used=turret_hp_used,
            launcher_hardpoints_total=launcher_hp_total,
            launcher_hardpoints_used=launcher_hp_used,
            drone_bay_total=round(drone_bay_total, 1),
            drone_bay_used=round(drone_bay_used, 1),
            drone_bandwidth_total=round(drone_bw_total, 1),
            drone_bandwidth_used=round(effective_drone_bw, 1),
        )

    def _sum_cpu_pg_with_skills(self, items: List[FittingItem]) -> tuple:
        """Sum CPU and PG usage with weapon fitting skill reductions applied."""
        module_type_ids = list(set(
            i.type_id for i in items if i.flag != 87 and i.flag != 5
        ))
        if not module_type_ids:
            return 0.0, 0.0

        with self.db.cursor(cursor_factory=RealDictCursor) as cur:
            # Get CPU and PG attributes
            cur.execute("""
                SELECT "typeID", "attributeID",
                       COALESCE("valueFloat", "valueInt"::float) as value
                FROM "dgmTypeAttributes"
                WHERE "typeID" = ANY(%s)
                  AND "attributeID" IN (%s, %s)
            """, (module_type_ids, ATTR_CPU_NEED, ATTR_POWER_NEED))
            mod_attrs: Dict[int, dict] = {}
            for row in cur.fetchall():
                mod_attrs.setdefault(row["typeID"], {})[row["attributeID"]] = row["value"]

            # Get turret/launcher effects to identify weapons
            cur.execute("""
                SELECT "typeID", "effectID"
                FROM "dgmTypeEffects"
                WHERE "typeID" = ANY(%s)
                  AND "effectID" IN (%s, %s)
            """, (module_type_ids, EFFECT_TURRET_FITTED, EFFECT_LAUNCHER_FITTED))
            mod_effects: Dict[int, set] = {}
            for row in cur.fetchall():
                mod_effects.setdefault(row["typeID"], set()).add(row["effectID"])

        wu_cpu_mult = 1 + (-5.0 * DEFAULT_FITTING_SKILL_LEVEL) / 100  # 0.75
        awu_pg_mult = 1 + (-2.0 * DEFAULT_FITTING_SKILL_LEVEL) / 100  # 0.90

        total_cpu = 0.0
        total_pg = 0.0
        for item in items:
            if item.flag == 87 or item.flag == 5:
                continue
            attrs = mod_attrs.get(item.type_id, {})
            effects = mod_effects.get(item.type_id, set())
            item_cpu = attrs.get(ATTR_CPU_NEED, 0)
            item_pg = attrs.get(ATTR_POWER_NEED, 0)
            if EFFECT_TURRET_FITTED in effects or EFFECT_LAUNCHER_FITTED in effects:
                item_cpu *= wu_cpu_mult
                item_pg *= awu_pg_mult
            total_cpu += item_cpu * item.quantity
            total_pg += item_pg * item.quantity
        return total_cpu, total_pg

    def _sum_module_attr(self, items: List[FittingItem], attr_id: int) -> float:
        """Sum an attribute across all fitted modules (excluding drones/cargo)."""
        module_type_ids = list(set(
            i.type_id for i in items if i.flag != 87 and i.flag != 5
        ))
        if not module_type_ids:
            return 0.0

        with self.db.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT "typeID",
                       COALESCE("valueFloat", "valueInt"::float) as value
                FROM "dgmTypeAttributes"
                WHERE "typeID" = ANY(%s)
                  AND "attributeID" = %s
            """, (module_type_ids, attr_id))
            type_values = {row["typeID"]: row["value"] for row in cur.fetchall()}

        total = 0.0
        for item in items:
            if item.flag == 87 or item.flag == 5:
                continue
            total += type_values.get(item.type_id, 0) * item.quantity
        return total

    def _sum_rig_attr(self, items: List[FittingItem], attr_id: int) -> float:
        """Sum an attribute across rig-slot items only (flag 92-99)."""
        rig_type_ids = list(set(
            i.type_id for i in items if 92 <= i.flag <= 99
        ))
        if not rig_type_ids:
            return 0.0

        with self.db.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT "typeID",
                       COALESCE("valueFloat", "valueInt"::float) as value
                FROM "dgmTypeAttributes"
                WHERE "typeID" = ANY(%s)
                  AND "attributeID" = %s
            """, (rig_type_ids, attr_id))
            type_values = {row["typeID"]: row["value"] for row in cur.fetchall()}

        total = 0.0
        for item in items:
            if 92 <= item.flag <= 99:
                total += type_values.get(item.type_id, 0) * item.quantity
        return total

    def _add_module_mass(self, ship_attrs: dict, items: List[FittingItem]) -> dict:
        """Add fitted module mass to ship mass. EVE adds all module masses.

        Reads mass from invTypes.mass (not dgmTypeAttributes).
        Excludes drones (flag 87) and cargo (flag 5).
        """
        fitted_type_ids = list(set(
            i.type_id for i in items if i.flag != 87 and i.flag != 5
        ))
        if not fitted_type_ids:
            return ship_attrs

        with self.db.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT "typeID", "mass"
                FROM "invTypes"
                WHERE "typeID" = ANY(%s)
            """, (fitted_type_ids,))
            type_mass = {row["typeID"]: float(row["mass"] or 0) for row in cur.fetchall()}

        total_module_mass = 0.0
        for item in items:
            if item.flag == 87 or item.flag == 5:
                continue
            total_module_mass += type_mass.get(item.type_id, 0) * item.quantity

        if total_module_mass > 0:
            result = dict(ship_attrs)
            result[ATTR_MASS] = result.get(ATTR_MASS, 0) + total_module_mass
            return result
        return ship_attrs

    def _load_module_groups(self, module_type_ids: list) -> Dict[int, int]:
        """Load groupID for each module type."""
        unique_ids = list(set(module_type_ids))
        if not unique_ids:
            return {}
        with self.db.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT "typeID", "groupID"
                FROM "invTypes"
                WHERE "typeID" = ANY(%s)
            """, (unique_ids,))
            return {row["typeID"]: row["groupID"] for row in cur.fetchall()}
