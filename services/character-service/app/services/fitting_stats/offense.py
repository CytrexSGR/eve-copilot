"""Offense calculation — weapon DPS + drone DPS."""

import logging
from typing import Optional, Dict, List

from psycopg2.extras import RealDictCursor

from app.services.dogma.stacking import apply_stacking_penalized_multipliers

from .models import OffenseStats, DamageBreakdown
from .constants import (
    ATTR_DAMAGE_MULT, ATTR_RATE_OF_FIRE,
    ATTR_EM_DAMAGE, ATTR_THERMAL_DAMAGE,
    ATTR_KINETIC_DAMAGE, ATTR_EXPLOSIVE_DAMAGE,
    ATTR_CHARGE_GROUP1, ATTR_CHARGE_GROUP2, ATTR_CHARGE_GROUP3,
    ATTR_CHARGE_GROUP4, ATTR_CHARGE_GROUP5,
    ATTR_DRONE_BW_NEED,
    FLAG_DRONE_BAY,
    DEFAULT_FITTING_SKILL_LEVEL,
    SKILL_DRONE_INTERFACING,
    DRONE_DAMAGE_SKILLS,
    ATTR_REQUIRED_SKILL_1, ATTR_REQUIRED_SKILL_2, ATTR_REQUIRED_SKILL_3,
    SKILL_MISSILE_LAUNCHER_OP,
    MISSILE_ROF_SKILLS, MISSILE_SPEC_ROF_SKILLS,
    MISSILE_DAMAGE_SKILLS, MISSILE_SPEC_DAMAGE_SKILLS,
    SKILL_WARHEAD_UPGRADES, WARHEAD_UPGRADES_BONUS,
    ATTR_MISSILE_DMG_BONUS,
)
from .calculations import calculate_weapon_dps, calculate_drone_dps

logger = logging.getLogger(__name__)


def _get_skill_level(skill_levels, skill_id):
    """Resolve a character skill level with correct default handling."""
    if skill_levels and skill_id in skill_levels:
        return skill_levels[skill_id]
    elif skill_levels is not None and skill_id not in skill_levels:
        return 0  # Character doesn't have the skill
    return DEFAULT_FITTING_SKILL_LEVEL


def _calc_drone_damage_mult(attrs, drone_type_id, drone_interfacing_mult,
                            drone_required_skills, skill_levels):
    """Calculate the combined drone damage multiplier for a single drone type.

    Applies Drone Interfacing skill bonus and all drone damage skills
    (Light/Med/Heavy Drone Operation, Specializations).

    Args:
        attrs: Dict of drone SDE attributes (keyed by attribute ID).
        drone_type_id: The type ID of the drone.
        drone_interfacing_mult: Pre-computed Drone Interfacing multiplier.
        drone_required_skills: Dict mapping drone type_id → list of required skill IDs.
        skill_levels: Character skill levels dict (or None for default All V).
    Returns:
        Combined damage multiplier (float).
    """
    drone_mult = attrs.get(ATTR_DAMAGE_MULT, 0) * drone_interfacing_mult

    required = drone_required_skills.get(drone_type_id, [])
    for skill_id in required:
        if skill_id in DRONE_DAMAGE_SKILLS:
            bonus_per_level = DRONE_DAMAGE_SKILLS[skill_id]
            level = _get_skill_level(skill_levels, skill_id)
            drone_mult *= 1 + (bonus_per_level * level) / 100

    return drone_mult


class OffenseMixin:
    """Mixin providing _calc_offense and _get_charges_damage_batch."""

    def _calc_offense(self, req, modified_module_attrs=None,
                      drone_bandwidth_total=0, max_active_drones=5,
                      skill_levels=None, charge_bonuses=None):
        """Calculate DPS from SDE data with auto-detected charges and drone DPS.

        For each weapon in high slots:
        1. If explicit charge provided (via req.charges), use that charge's damage
        2. Otherwise, auto-detect best T1 charge from the weapon's chargeGroup attrs
        3. If no charges exist (e.g. smartbombs), use weapon's own damage attrs

        Dogma-modified module attrs (e.g. Gyrostab bonus on turret damage_mult,
        BCS ROF on launchers, ship per-level bonuses) are overlaid on SDE values.

        Missile launchers additionally receive:
        - Character ROF skills (MLO, Rapid Launch, Specialization)
        - BCS missile damage multiplier (attr 213, stacking penalized)
        - Missile type damage skills (+5%/level)
        - Warhead Upgrades (+2%/level)

        For drones (flag=87):
        - Use drone's own damage_mult, rate_of_fire, and damage attrs
        - Capped by ship's drone bandwidth (only active drones contribute DPS)
        """
        try:
            # Separate weapons (high slots) and drones
            # Only active/overheated modules contribute DPS
            weapons = []  # (type_id, quantity, flag)
            drones = []   # (type_id, quantity)
            for item in req.items:
                if 27 <= item.flag <= 34:
                    if not self._is_module_active(item.flag, req.module_states):
                        continue
                    weapons.append((item.type_id, item.quantity, item.flag))
                elif item.flag == FLAG_DRONE_BAY:
                    drones.append((item.type_id, item.quantity))

            if not weapons and not drones:
                return OffenseStats()

            # Collect all unique type IDs we need attrs for
            all_type_ids = list(set(
                [w[0] for w in weapons] + [d[0] for d in drones]
            ))

            # Fetch weapon/drone attributes from SDE
            weapon_attr_ids = [
                ATTR_DAMAGE_MULT, ATTR_RATE_OF_FIRE,
                ATTR_EM_DAMAGE, ATTR_THERMAL_DAMAGE,
                ATTR_KINETIC_DAMAGE, ATTR_EXPLOSIVE_DAMAGE,
                ATTR_CHARGE_GROUP1, ATTR_CHARGE_GROUP2, ATTR_CHARGE_GROUP3,
                ATTR_CHARGE_GROUP4, ATTR_CHARGE_GROUP5,
            ]

            with self.db.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT "typeID", "attributeID",
                           COALESCE("valueFloat", "valueInt"::float) as value
                    FROM "dgmTypeAttributes"
                    WHERE "typeID" = ANY(%s)
                      AND "attributeID" = ANY(%s)
                """, (all_type_ids, weapon_attr_ids))

                type_attrs: Dict[int, Dict[int, float]] = {}
                for row in cur.fetchall():
                    tid = row["typeID"]
                    if tid not in type_attrs:
                        type_attrs[tid] = {}
                    type_attrs[tid][row["attributeID"]] = row["value"]

                # Overlay Dogma-modified module attrs (e.g. Gyrostab bonus, BCS ROF)
                if modified_module_attrs:
                    for tid, mod_attrs in modified_module_attrs.items():
                        if tid in type_attrs:
                            type_attrs[tid].update(mod_attrs)
                        else:
                            type_attrs[tid] = dict(mod_attrs)

                # --- Missile-specific pre-computation ---
                # Load required skills for weapon types (to identify missiles)
                weapon_type_ids = list(set(w[0] for w in weapons))
                weapon_required_skills: Dict[int, List[int]] = {}
                if weapon_type_ids:
                    cur.execute("""
                        SELECT "typeID", "attributeID",
                               COALESCE("valueFloat", "valueInt"::float) as value
                        FROM "dgmTypeAttributes"
                        WHERE "typeID" = ANY(%s)
                          AND "attributeID" IN (%s, %s, %s)
                    """, (weapon_type_ids,
                          ATTR_REQUIRED_SKILL_1, ATTR_REQUIRED_SKILL_2, ATTR_REQUIRED_SKILL_3))
                    for row in cur.fetchall():
                        tid = row["typeID"]
                        skill_id = int(row["value"])
                        if skill_id > 0:
                            if tid not in weapon_required_skills:
                                weapon_required_skills[tid] = []
                            weapon_required_skills[tid].append(skill_id)

                # Compute BCS missile damage multiplier from fitted modules.
                # BCS has attr 213 (missileDamageMultiplier). The Dogma engine drops
                # the charID ItemModifier, so we apply it manually here.
                bcs_damage_mults: List[float] = []
                if modified_module_attrs:
                    for item in req.items:
                        if item.flag == FLAG_DRONE_BAY:
                            continue
                        if not self._is_module_active(item.flag, req.module_states):
                            continue
                        mod_attrs = modified_module_attrs.get(item.type_id, {})
                        dmg_bonus = mod_attrs.get(ATTR_MISSILE_DMG_BONUS)
                        if dmg_bonus and dmg_bonus > 0:
                            for _ in range(item.quantity):
                                bcs_damage_mults.append(dmg_bonus)
                bcs_damage_mult = apply_stacking_penalized_multipliers(bcs_damage_mults) if bcs_damage_mults else 1.0

                # Pre-load all charge damage data in a single batch query
                charge_type_ids_set: set = set()
                if req.charges:
                    charge_type_ids_set.update(req.charges.values())
                if req.ammo_type_id:
                    charge_type_ids_set.add(req.ammo_type_id)
                charge_damage_cache = self._get_charges_damage_batch(
                    cur, list(charge_type_ids_set)
                ) if charge_type_ids_set else {}

                # Calculate weapon DPS
                total_weapon_dps = 0.0
                total_volley = 0.0
                total_em = 0.0
                total_th = 0.0
                total_ki = 0.0
                total_ex = 0.0

                for weapon_type_id, quantity, flag in weapons:
                    attrs = type_attrs.get(weapon_type_id, {})
                    damage_mult = attrs.get(ATTR_DAMAGE_MULT, 0)
                    rate_of_fire = attrs.get(ATTR_RATE_OF_FIRE, 0)

                    if rate_of_fire <= 0:
                        continue
                    # Missile launchers have no ATTR_DAMAGE_MULT — damage comes from charge
                    if damage_mult <= 0:
                        damage_mult = 1.0

                    # Check if this weapon is a missile launcher (requires MLO skill)
                    w_skills = weapon_required_skills.get(weapon_type_id, [])
                    is_missile = SKILL_MISSILE_LAUNCHER_OP in w_skills

                    # Apply character ROF skills for missile launchers
                    if is_missile:
                        # MLO (-2%/level) and Rapid Launch (-3%/level) — all launchers
                        for skill_id, bonus_pct in MISSILE_ROF_SKILLS.items():
                            level = _get_skill_level(skill_levels, skill_id)
                            rate_of_fire *= (1.0 + bonus_pct * level / 100.0)

                        # Specialization ROF (-2%/level) — only if launcher requires the spec
                        for spec_skill_id, bonus_pct in MISSILE_SPEC_ROF_SKILLS.items():
                            if spec_skill_id in w_skills:
                                level = _get_skill_level(skill_levels, spec_skill_id)
                                rate_of_fire *= (1.0 + bonus_pct * level / 100.0)

                    # Determine charge damage values
                    charge_em = 0.0
                    charge_th = 0.0
                    charge_ki = 0.0
                    charge_ex = 0.0

                    # Option 1: Explicit charge from request
                    explicit_charge_id = None
                    if req.charges and flag in req.charges:
                        explicit_charge_id = req.charges[flag]
                    elif req.ammo_type_id:
                        explicit_charge_id = req.ammo_type_id

                    if explicit_charge_id:
                        charge_dmg = charge_damage_cache.get(explicit_charge_id, {
                            "em": 0, "thermal": 0, "kinetic": 0, "explosive": 0, "required_skills": []
                        })
                        charge_em = charge_dmg.get("em", 0)
                        charge_th = charge_dmg.get("thermal", 0)
                        charge_ki = charge_dmg.get("kinetic", 0)
                        charge_ex = charge_dmg.get("explosive", 0)
                        charge_req_skills = charge_dmg.get("required_skills", [])

                        # Apply missile damage skills to charge damage
                        if is_missile:
                            missile_dmg_mult = self._calc_missile_damage_mult(
                                charge_req_skills, skill_levels, bcs_damage_mult
                            )
                            charge_em *= missile_dmg_mult
                            charge_th *= missile_dmg_mult
                            charge_ki *= missile_dmg_mult
                            charge_ex *= missile_dmg_mult

                        # Apply ship hull charge damage bonuses
                        # (e.g., Cerberus +5%/lvl kinetic missile damage)
                        if charge_bonuses:
                            for bonus in charge_bonuses:
                                if bonus["skill_type_id"] in charge_req_skills:
                                    attr_id = bonus["modified_attr_id"]
                                    val = bonus["value"]
                                    op = bonus["operation"]
                                    if op == 6:  # PostPercent
                                        factor = 1.0 + val / 100.0
                                    elif op == 4:  # PostMul
                                        factor = val
                                    else:
                                        continue
                                    if attr_id == ATTR_EM_DAMAGE:
                                        charge_em *= factor
                                    elif attr_id == ATTR_THERMAL_DAMAGE:
                                        charge_th *= factor
                                    elif attr_id == ATTR_KINETIC_DAMAGE:
                                        charge_ki *= factor
                                    elif attr_id == ATTR_EXPLOSIVE_DAMAGE:
                                        charge_ex *= factor
                    else:
                        # No explicit charge — check if weapon uses charges
                        has_charge_groups = any(
                            attrs.get(cg) is not None and attrs.get(cg, 0) > 0
                            for cg in [ATTR_CHARGE_GROUP1, ATTR_CHARGE_GROUP2,
                                       ATTR_CHARGE_GROUP3, ATTR_CHARGE_GROUP4,
                                       ATTR_CHARGE_GROUP5]
                        )
                        if not has_charge_groups:
                            # Weapon has no charge slots (smartbombs, etc.) — use own damage
                            charge_em = attrs.get(ATTR_EM_DAMAGE, 0)
                            charge_th = attrs.get(ATTR_THERMAL_DAMAGE, 0)
                            charge_ki = attrs.get(ATTR_KINETIC_DAMAGE, 0)
                            charge_ex = attrs.get(ATTR_EXPLOSIVE_DAMAGE, 0)
                        # else: weapon needs charges but none loaded → 0 DPS

                    result = calculate_weapon_dps(
                        damage_mult, rate_of_fire,
                        charge_em, charge_th, charge_ki, charge_ex
                    )

                    total_weapon_dps += result["dps"] * quantity
                    total_volley += result["volley"] * quantity
                    total_em += result["em"] * quantity
                    total_th += result["thermal"] * quantity
                    total_ki += result["kinetic"] * quantity
                    total_ex += result["explosive"] * quantity

                # Calculate drone DPS (capped by drone bandwidth)
                total_drone_dps = 0.0

                # Drone Interfacing: +10%/level to drone damage
                di_level = _get_skill_level(skill_levels, SKILL_DRONE_INTERFACING)
                drone_interfacing_mult = 1 + (10.0 * di_level) / 100

                # Load required skills for drone types (for droneDmgBonus skills)
                drone_type_ids = list(set(d[0] for d in drones))
                drone_required_skills: Dict[int, list] = {}  # type_id → [skill_type_ids]
                if drone_type_ids:
                    cur.execute("""
                        SELECT "typeID", "attributeID",
                               COALESCE("valueFloat", "valueInt"::float) as value
                        FROM "dgmTypeAttributes"
                        WHERE "typeID" = ANY(%s)
                          AND "attributeID" IN (%s, %s, %s)
                    """, (drone_type_ids,
                          ATTR_REQUIRED_SKILL_1, ATTR_REQUIRED_SKILL_2, ATTR_REQUIRED_SKILL_3))
                    for row in cur.fetchall():
                        tid = row["typeID"]
                        skill_id = int(row["value"])
                        if skill_id > 0:
                            if tid not in drone_required_skills:
                                drone_required_skills[tid] = []
                            drone_required_skills[tid].append(skill_id)

                # Pre-calculate per-drone DPS and BW for bandwidth-aware selection
                drone_entries = []
                for drone_type_id, quantity in drones:
                    attrs = type_attrs.get(drone_type_id, {})

                    drone_mult = _calc_drone_damage_mult(
                        attrs, drone_type_id, drone_interfacing_mult,
                        drone_required_skills, skill_levels
                    )

                    drone_rof = attrs.get(ATTR_RATE_OF_FIRE, 0)
                    drone_bw_need = attrs.get(ATTR_DRONE_BW_NEED, 0)
                    drone_em = attrs.get(ATTR_EM_DAMAGE, 0)
                    drone_th = attrs.get(ATTR_THERMAL_DAMAGE, 0)
                    drone_ki = attrs.get(ATTR_KINETIC_DAMAGE, 0)
                    drone_ex = attrs.get(ATTR_EXPLOSIVE_DAMAGE, 0)

                    # Calculate DPS per single drone for sorting
                    single_result = calculate_drone_dps(
                        drone_mult, drone_rof,
                        drone_em, drone_th, drone_ki, drone_ex,
                        count=1
                    )
                    # Expand: one entry per drone for bandwidth allocation
                    for _ in range(quantity):
                        drone_entries.append({
                            "type_id": drone_type_id,
                            "bw_need": drone_bw_need,
                            "dps_per_drone": single_result["dps"],
                            "attrs": attrs,
                        })

                # Sort by DPS descending (highest-value drones first)
                drone_entries.sort(key=lambda d: d["dps_per_drone"], reverse=True)

                # Allocate drones within bandwidth AND active drone limit
                # EVE default: max 5 active drones (attr 352, most ships don't have it)
                bw_remaining = drone_bandwidth_total if drone_bandwidth_total > 0 else float("inf")
                active_count = 0
                active_drones: Dict[int, int] = {}  # type_id → count
                for entry in drone_entries:
                    if active_count >= max_active_drones:
                        break
                    bw_need = entry["bw_need"]
                    if bw_need <= 0:
                        bw_need = 1  # Fallback: count as 1 Mbit/s
                    if bw_remaining >= bw_need:
                        bw_remaining -= bw_need
                        active_count += 1
                        active_drones[entry["type_id"]] = active_drones.get(entry["type_id"], 0) + 1

                # Calculate DPS for active drones only
                for drone_type_id, count in active_drones.items():
                    attrs = type_attrs.get(drone_type_id, {})
                    drone_mult = _calc_drone_damage_mult(
                        attrs, drone_type_id, drone_interfacing_mult,
                        drone_required_skills, skill_levels
                    )

                    drone_rof = attrs.get(ATTR_RATE_OF_FIRE, 0)
                    drone_em = attrs.get(ATTR_EM_DAMAGE, 0)
                    drone_th = attrs.get(ATTR_THERMAL_DAMAGE, 0)
                    drone_ki = attrs.get(ATTR_KINETIC_DAMAGE, 0)
                    drone_ex = attrs.get(ATTR_EXPLOSIVE_DAMAGE, 0)

                    result = calculate_drone_dps(
                        drone_mult, drone_rof,
                        drone_em, drone_th, drone_ki, drone_ex,
                        count=count
                    )
                    total_drone_dps += result["dps"]
                    total_em += result["em"]
                    total_th += result["thermal"]
                    total_ki += result["kinetic"]
                    total_ex += result["explosive"]

            return OffenseStats(
                weapon_dps=round(total_weapon_dps, 1),
                drone_dps=round(total_drone_dps, 1),
                total_dps=round(total_weapon_dps + total_drone_dps, 1),
                volley_damage=round(total_volley, 1),
                damage_breakdown=DamageBreakdown(
                    em=round(total_em, 1),
                    thermal=round(total_th, 1),
                    kinetic=round(total_ki, 1),
                    explosive=round(total_ex, 1),
                ),
            )
        except Exception as e:
            logger.warning(f"DPS calculation failed: {e}")
            return OffenseStats()

    def _calc_missile_damage_mult(self, charge_skills, skill_levels, bcs_mult):
        """Calculate combined missile damage multiplier from character skills + BCS.

        Args:
            charge_skills: list of required skill IDs for the loaded charge
            skill_levels: character skill levels dict
            bcs_mult: pre-computed BCS missile damage multiplier (stacking penalized)
        Returns:
            Combined multiplier to apply to all charge damage values.
        """
        mult = bcs_mult

        # Missile type damage skill (+5%/level) — e.g. Cruise Missiles
        for skill_id in charge_skills:
            if skill_id in MISSILE_DAMAGE_SKILLS:
                bonus_pct = MISSILE_DAMAGE_SKILLS[skill_id]
                level = _get_skill_level(skill_levels, skill_id)
                mult *= 1.0 + (bonus_pct * level) / 100.0

        # Missile specialization damage (+2%/level) — only T2 charges
        for skill_id in charge_skills:
            if skill_id in MISSILE_SPEC_DAMAGE_SKILLS:
                bonus_pct = MISSILE_SPEC_DAMAGE_SKILLS[skill_id]
                level = _get_skill_level(skill_levels, skill_id)
                mult *= 1.0 + (bonus_pct * level) / 100.0

        # Warhead Upgrades (+2%/level) — applies to all missiles
        # (all charges require MLO, and WU targets MLO)
        if SKILL_MISSILE_LAUNCHER_OP in charge_skills:
            level = _get_skill_level(skill_levels, SKILL_WARHEAD_UPGRADES)
            mult *= 1.0 + (WARHEAD_UPGRADES_BONUS * level) / 100.0

        return mult

    def _get_charges_damage_batch(self, cur, charge_type_ids: List[int]) -> Dict[int, dict]:
        """Get damage attributes and required skills for multiple charge types in one query.

        Args:
            cur: Database cursor (RealDictCursor)
            charge_type_ids: List of charge type IDs to look up

        Returns:
            Dict mapping type_id to {"em", "thermal", "kinetic", "explosive", "required_skills"}
        """
        if not charge_type_ids:
            return {}

        attr_ids = [
            ATTR_EM_DAMAGE, ATTR_THERMAL_DAMAGE,
            ATTR_KINETIC_DAMAGE, ATTR_EXPLOSIVE_DAMAGE,
            ATTR_REQUIRED_SKILL_1, ATTR_REQUIRED_SKILL_2, ATTR_REQUIRED_SKILL_3,
        ]
        cur.execute("""
            SELECT "typeID", "attributeID",
                   COALESCE("valueFloat", "valueInt"::float) as value
            FROM "dgmTypeAttributes"
            WHERE "typeID" = ANY(%s)
              AND "attributeID" = ANY(%s)
        """, (list(charge_type_ids), attr_ids))

        attr_map = {
            ATTR_EM_DAMAGE: "em",
            ATTR_THERMAL_DAMAGE: "thermal",
            ATTR_KINETIC_DAMAGE: "kinetic",
            ATTR_EXPLOSIVE_DAMAGE: "explosive",
        }
        skill_attrs = {ATTR_REQUIRED_SKILL_1, ATTR_REQUIRED_SKILL_2, ATTR_REQUIRED_SKILL_3}

        results: Dict[int, dict] = {}
        for row in cur.fetchall():
            tid = row["typeID"]
            if tid not in results:
                results[tid] = {"em": 0, "thermal": 0, "kinetic": 0, "explosive": 0, "required_skills": []}
            aid = row["attributeID"]
            key = attr_map.get(aid)
            if key:
                results[tid][key] = row["value"] or 0
            elif aid in skill_attrs:
                skill_id = int(row["value"]) if row["value"] else 0
                if skill_id > 0:
                    results[tid]["required_skills"].append(skill_id)

        # Ensure all requested type_ids have entries (even if no rows found)
        for tid in charge_type_ids:
            if tid not in results:
                results[tid] = {"em": 0, "thermal": 0, "kinetic": 0, "explosive": 0, "required_skills": []}

        return results
