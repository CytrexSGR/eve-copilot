"""Dogma attribute modification engine.

Loads ship + module attributes from SDE, parses effect modifiers,
and applies them in correct operation order with stacking penalties.
"""

import logging
from collections import defaultdict
from dataclasses import replace
from typing import Dict, List, Optional, Tuple

from psycopg2.extras import RealDictCursor

from app.services.dogma.modifier_parser import DogmaModifier, parse_modifier_info
from app.services.dogma.stacking import apply_stacking_penalized_multipliers


logger = logging.getLogger(__name__)


class DogmaEngine:
    """Calculate modified attributes for a ship fitting."""

    # Effects that require manual activation — excluded from passive fitting simulation.
    # These modules (Siege, Bastion, Industrial Core) only apply bonuses when activated.
    ACTIVATION_REQUIRED_EFFECTS = {
        4575,  # industrialCoreEffect2 (Capital Industrial Core I/II)
        8119,  # industrialCompactCoreEffect2 (Large/Medium Industrial Core I/II)
        6582,  # moduleBonusSiegeModule (Siege Module I/II + variants)
        6658,  # moduleBonusBastionModule (Bastion Module I)
    }

    # EVE effect categories (effectCategoryID in dgmEffects):
    #   0 = passive (always active)
    #   1 = active (require module activation)
    #   4 = online (require power, always when online)
    #   5 = overload (only when overheated)
    #
    # Module states and which effectCategoryIDs are allowed:
    MODULE_STATE_ALLOWED_CATEGORIES: Dict[str, frozenset] = {
        "offline": frozenset(),         # no effects
        "online": frozenset({0, 4}),    # passive + online
        "active": frozenset({0, 1, 4}), # passive + active + online
        "overheated": frozenset({0, 1, 4, 5}),  # all categories
    }

    def __init__(self, db):
        self.db = db

    def calculate_modified_attributes(
        self,
        ship_type_id: int,
        fitted_module_type_ids: List[int],
        skill_levels: Optional[Dict[int, int]] = None,
        simulation_mode: bool = True,
        implant_type_ids: Optional[List[int]] = None,
        module_flags: Optional[List[int]] = None,
        flag_states: Optional[Dict[int, str]] = None,
        booster_type_ids: Optional[List[int]] = None,
        mode_type_id: Optional[int] = None,
        charge_type_ids: Optional[List[int]] = None,
    ) -> Tuple[Dict[int, float], Dict[int, Dict[int, float]], List[dict], Dict[int, Dict[int, float]]]:
        """Calculate all modified attributes for a ship + modules.

        Args:
            skill_levels: {skill_type_id: level} for pilot skills.
                          Defaults to All V (level 5) when None or missing.
            module_flags: List of slot flags parallel to fitted_module_type_ids.
                          Each flag identifies a specific slot instance.
            flag_states: {flag: state_string} for per-slot module state.
                         Valid states: "offline", "online", "active", "overheated".
                         Defaults to "active" for all modules when None.

        Returns:
            (modified_ship_attrs, modified_module_attrs, charge_bonuses, modified_charges)
            - modified_ship_attrs: {attr_id: value} for the ship
            - modified_module_attrs: {type_id: {attr_id: value}} per module type
            - charge_bonuses: list of dicts with ship hull bonuses targeting charge
              damage attrs (outside engine scope)
            - modified_charges: {charge_type_id: {attr_id: value}} with Dogma-modified
              charge attributes (e.g., explosion radius after MGE bonuses)
        """
        if skill_levels is None:
            # All V mode: no character specified, default all skills to level 5
            skill_levels = {}
            skill_default = self.DEFAULT_SKILL_LEVEL
        else:
            # Character mode: skills not in dict are untrained (level 0)
            skill_default = 0
        # 1-3b. Load base attributes, groups, required skills for ship, modules, charges
        ship_attrs, module_attrs, module_groups, module_required_skills, \
            charge_attrs, charge_required_skills = self._load_base_data(
                ship_type_id, fitted_module_type_ids, charge_type_ids,
            )

        # 1.5b-c. Load implant and booster attributes, merge into module data
        implant_type_ids = implant_type_ids or []
        booster_type_ids = booster_type_ids or []
        self._load_implant_and_booster_data(
            implant_type_ids, booster_type_ids,
            module_attrs, module_groups, module_required_skills,
        )

        # 1.5d-e. Load skill virtual modules, apply self-modifiers, merge into module_attrs
        skill_type_ids = self._build_skill_data(
            skill_levels, skill_default, module_attrs,
        )

        # 4-4d. Load and merge all modifiers (modules, implants, boosters, skills)
        modifiers = self._collect_all_modifiers(
            fitted_module_type_ids, simulation_mode, module_flags, flag_states,
            implant_type_ids, booster_type_ids, skill_type_ids,
        )

        # 5. Separate modifiers by target domain/function
        ship_modifiers, location_modifiers, owner_skill_modifiers, self_modifiers = \
            self._route_modifiers(modifiers)

        # 5.5-9. Apply all modifier stages and produce final results
        return self._apply_pipeline(
            ship_type_id, ship_attrs, module_attrs, module_groups,
            module_required_skills, charge_attrs, charge_required_skills,
            skill_levels, skill_default, mode_type_id,
            ship_modifiers, location_modifiers, owner_skill_modifiers,
            self_modifiers,
        )

    # ── Pipeline stage methods ──────────────────────────────────────────

    def _load_base_data(
        self,
        ship_type_id: int,
        fitted_module_type_ids: List[int],
        charge_type_ids: Optional[List[int]],
    ) -> Tuple[
        Dict[int, float],            # ship_attrs
        Dict[int, Dict[int, float]], # module_attrs
        Dict[int, int],              # module_groups
        Dict[int, set],              # module_required_skills
        Dict[int, Dict[int, float]], # charge_attrs
        Dict[int, set],              # charge_required_skills
    ]:
        """Pipeline stages 1-3b: Load base attributes for ship, modules, and charges.

        Loads SDE attributes, supplements ship attrs from invTypes (mass/capacity),
        loads group IDs for LocationGroupModifier, required skills for
        OwnerRequiredSkillModifier, and charge data for LocationRequiredSkillModifier.
        """
        # 1. Load base attributes for ship and all modules
        all_type_ids = [ship_type_id] + list(set(fitted_module_type_ids))
        all_attrs = self._load_all_attributes(all_type_ids)
        ship_attrs = dict(all_attrs.get(ship_type_id, {}))

        # 1.5. Supplement ship attrs with mass/capacity from invTypes
        ship_attrs = self._supplement_invtypes_attrs(ship_type_id, ship_attrs)

        module_attrs = {tid: dict(all_attrs.get(tid, {})) for tid in set(fitted_module_type_ids)}

        # 2. Load module group IDs for LocationGroupModifier
        module_groups = self._load_group_ids(list(set(fitted_module_type_ids)))

        # 3. Load required skills for OwnerRequiredSkillModifier
        module_required_skills = self._load_required_skills(list(set(fitted_module_type_ids)))

        # 3b. Load charge attributes and required skills
        charge_attrs: Dict[int, Dict[int, float]] = {}
        charge_required_skills: Dict[int, set] = {}
        charge_unique = list(set(charge_type_ids)) if charge_type_ids else []
        if charge_unique:
            charge_attrs_loaded = self._load_all_attributes(charge_unique)
            charge_attrs = {tid: dict(charge_attrs_loaded.get(tid, {})) for tid in charge_unique}
            charge_required_skills = self._load_required_skills(charge_unique)

        return ship_attrs, module_attrs, module_groups, module_required_skills, \
            charge_attrs, charge_required_skills

    def _load_implant_and_booster_data(
        self,
        implant_type_ids: List[int],
        booster_type_ids: List[int],
        module_attrs: Dict[int, Dict[int, float]],
        module_groups: Dict[int, int],
        module_required_skills: Dict[int, set],
    ) -> None:
        """Pipeline stages 1.5b-1.5c: Load implant and booster data.

        Loads attributes, group IDs, and required skills for implants and boosters,
        merging them into the existing module data dicts (in-place).
        """
        # 1.5b. Load implant attributes (for modifier source values)
        if implant_type_ids:
            implant_unique = list(set(implant_type_ids))
            implant_attrs_loaded = self._load_all_attributes(implant_unique)
            for tid in implant_unique:
                if tid not in module_attrs:
                    module_attrs[tid] = dict(implant_attrs_loaded.get(tid, {}))
            implant_groups = self._load_group_ids(implant_unique)
            module_groups.update(implant_groups)
            implant_skills = self._load_required_skills(implant_unique)
            module_required_skills.update(implant_skills)

        # 1.5c. Load booster attributes (for modifier source values)
        if booster_type_ids:
            booster_unique = list(set(booster_type_ids))
            booster_attrs_loaded = self._load_all_attributes(booster_unique)
            for tid in booster_unique:
                if tid not in module_attrs:
                    module_attrs[tid] = dict(booster_attrs_loaded.get(tid, {}))
            booster_groups = self._load_group_ids(booster_unique)
            module_groups.update(booster_groups)
            booster_skills = self._load_required_skills(booster_unique)
            module_required_skills.update(booster_skills)

    def _build_skill_data(
        self,
        skill_levels: Dict[int, int],
        skill_default: int,
        module_attrs: Dict[int, Dict[int, float]],
    ) -> List[int]:
        """Pipeline stages 1.5d-1.5e: Build skill virtual modules and apply self-modifiers.

        Determines which skills to load, creates virtual modules with injected
        skill levels, applies skill self-modifiers (2-step chain), and merges
        skill attrs into module_attrs for modifier source lookups.

        Returns:
            List of skill type_ids loaded (needed for stage 4d).
        """
        # 1.5d. Determine which skills to load
        if not skill_levels:
            # All V mode: load all skills with valid SDE effects
            skill_type_ids = list(self._get_all_skill_type_ids())
        else:
            # Character mode: only load trained skills
            skill_type_ids = [sid for sid, lvl in skill_levels.items() if lvl > 0]

        if skill_type_ids:
            skill_attrs = self._load_skill_virtual_modules(
                skill_type_ids, skill_levels, skill_default,
            )

            # 1.5e. Pre-compute skill intermediate bonuses (2-step self-modifiers)
            self._apply_skill_self_modifiers(skill_type_ids, skill_attrs)

            # Merge skill attrs into module_attrs for modifier source lookups
            module_attrs.update(skill_attrs)

        return skill_type_ids

    def _collect_all_modifiers(
        self,
        fitted_module_type_ids: List[int],
        simulation_mode: bool,
        module_flags: Optional[List[int]],
        flag_states: Optional[Dict[int, str]],
        implant_type_ids: List[int],
        booster_type_ids: List[int],
        skill_type_ids: List[int],
    ) -> List[Tuple[int, DogmaModifier]]:
        """Pipeline stages 4-4d: Load and merge all modifiers.

        Loads modifiers from fitted modules (with state filtering), implants,
        boosters, and skill pipeline effects into a single modifier list.
        """
        # 4. Load and parse all modifiers from fitted modules' effects
        modifiers = self._load_modifiers(
            fitted_module_type_ids, simulation_mode=simulation_mode,
            module_flags=module_flags, flag_states=flag_states,
        )

        # 4b. Load implant modifiers and merge
        if implant_type_ids:
            implant_modifiers = self._load_modifiers(
                implant_type_ids, simulation_mode=True,  # implants are always active
            )
            modifiers.extend(implant_modifiers)

        # 4c. Load booster modifiers and merge
        if booster_type_ids:
            booster_modifiers = self._load_modifiers(
                booster_type_ids, simulation_mode=True,  # boosters are always active
            )
            modifiers.extend(booster_modifiers)

        # 4d. Load skill pipeline modifiers (excludes self-mods, already handled in 1.5e)
        if skill_type_ids:
            skill_pipeline_modifiers = self._load_skill_pipeline_modifiers(skill_type_ids)
            modifiers.extend(skill_pipeline_modifiers)

        return modifiers

    @staticmethod
    def _route_modifiers(
        modifiers: List[Tuple[int, DogmaModifier]],
    ) -> Tuple[
        List[Tuple[int, DogmaModifier]],  # ship_modifiers
        List[Tuple[int, DogmaModifier]],  # location_modifiers
        List[Tuple[int, DogmaModifier]],  # owner_skill_modifiers
        List[Tuple[int, DogmaModifier]],  # self_modifiers
    ]:
        """Pipeline stage 5: Route modifiers into domain-specific buckets.

        Separates the combined modifier list into:
        - ship_modifiers: ItemModifier(domain=shipID) targeting ship attrs
        - location_modifiers: LocationGroupModifier, LocationRequiredSkillModifier,
          LocationModifier targeting module attrs
        - owner_skill_modifiers: OwnerRequiredSkillModifier targeting module/drone attrs
        - self_modifiers: ItemModifier(domain=itemID) targeting the module's own attrs
        """
        ship_modifiers = []
        location_modifiers = []
        owner_skill_modifiers = []
        self_modifiers = []
        for type_id, mod in modifiers:
            if mod.func == "ItemModifier" and mod.domain == "itemID":
                self_modifiers.append((type_id, mod))
            elif mod.func in ("ItemModifier",) and mod.domain == "shipID":
                ship_modifiers.append((type_id, mod))
            elif mod.func == "LocationGroupModifier":
                location_modifiers.append((type_id, mod))
            elif mod.func == "LocationRequiredSkillModifier":
                location_modifiers.append((type_id, mod))
            elif mod.func == "LocationModifier":
                location_modifiers.append((type_id, mod))
            elif mod.func == "OwnerRequiredSkillModifier":
                owner_skill_modifiers.append((type_id, mod))
            # EffectStopper skipped
        return ship_modifiers, location_modifiers, owner_skill_modifiers, self_modifiers

    def _apply_pipeline(
        self,
        ship_type_id: int,
        ship_attrs: Dict[int, float],
        module_attrs: Dict[int, Dict[int, float]],
        module_groups: Dict[int, int],
        module_required_skills: Dict[int, set],
        charge_attrs: Dict[int, Dict[int, float]],
        charge_required_skills: Dict[int, set],
        skill_levels: Dict[int, int],
        skill_default: int,
        mode_type_id: Optional[int],
        ship_modifiers: List[Tuple[int, DogmaModifier]],
        location_modifiers: List[Tuple[int, DogmaModifier]],
        owner_skill_modifiers: List[Tuple[int, DogmaModifier]],
        self_modifiers: List[Tuple[int, DogmaModifier]],
    ) -> Tuple[Dict[int, float], Dict[int, Dict[int, float]], List[dict], Dict[int, Dict[int, float]]]:
        """Pipeline stages 5.5-9: Apply all modifier stages and produce final results.

        Applies ship role bonuses, T3D mode modifiers, self-modifiers (overload),
        rig drawback pre-reduction, location modifiers, ship-targeting modifiers,
        owner-skill modifiers, and attribute caps — in correct Dogma order.

        Returns:
            (modified_ship_attrs, modified_module_attrs, charge_bonuses, modified_charges)
        """
        # 5.5. Apply ship hull bonuses to module attributes BEFORE module→ship transfer.
        ship_role_modifiers = self._load_ship_effects(ship_type_id, base_ship_attrs=ship_attrs)
        ship_attrs, module_attrs, charge_bonuses = self._apply_ship_role_bonuses(
            ship_attrs, module_attrs, ship_role_modifiers,
            ship_attrs, module_groups, module_required_skills, skill_levels,
            ship_type_id=ship_type_id, skill_default=skill_default,
        )

        # 5.7. Apply T3D mode modifiers (PostDiv on ship + module attrs)
        if mode_type_id:
            mode_modifiers, mode_attr_values = self._load_mode_effects(mode_type_id)
            if mode_modifiers:
                ship_attrs, module_attrs = self._apply_mode_modifiers(
                    ship_attrs, module_attrs, mode_modifiers, mode_attr_values,
                    module_groups, module_required_skills,
                )

        # 5.8. Apply self-modifiers (domain=itemID, e.g., overload bonuses).
        if self_modifiers:
            for type_id, mod in self_modifiers:
                if type_id not in module_attrs:
                    continue
                mod_value = module_attrs[type_id].get(mod.modifying_attr_id)
                if mod_value is None:
                    continue
                target = mod.modified_attr_id
                if target in module_attrs[type_id]:
                    self._apply_single_modifier(
                        module_attrs[type_id], target, mod_value, mod.operation
                    )

        # 5.95. Pre-apply rigging skill drawback reduction to rig modules.
        ATTR_RIG_DRAWBACK = 1138
        remaining_location_modifiers = []
        for source_type_id, mod in location_modifiers:
            if mod.func == "LocationGroupModifier" and mod.modified_attr_id == ATTR_RIG_DRAWBACK:
                mod_value = module_attrs.get(source_type_id, {}).get(mod.modifying_attr_id)
                if mod_value is not None and mod.group_id is not None:
                    for tid, attrs in module_attrs.items():
                        if module_groups.get(tid) == mod.group_id and ATTR_RIG_DRAWBACK in attrs:
                            self._apply_single_modifier(
                                attrs, ATTR_RIG_DRAWBACK, mod_value, mod.operation
                            )
                # Don't re-apply in step 6
            else:
                remaining_location_modifiers.append((source_type_id, mod))
        location_modifiers = remaining_location_modifiers

        # 6. Apply location modifiers to module attributes BEFORE module→ship transfer.
        modified_modules = self._apply_location_modifiers(
            module_attrs, location_modifiers, module_groups, module_required_skills
        )

        # 6b. Apply location modifiers to charge attributes (MGE → explosion radius/velocity)
        modified_charges = {}
        if charge_attrs:
            modified_charges = self._apply_location_modifiers(
                charge_attrs, location_modifiers,
                {},  # charges have no group-based modifiers
                charge_required_skills,
                source_attrs=modified_modules,
            )

        # 7. Apply ship-targeting modifiers (uses location-modifier-boosted module attrs)
        modified_ship = self._apply_modifiers(ship_attrs, modified_modules, ship_modifiers)

        # 8. Apply OwnerRequiredSkillModifier (e.g., DDA bonus on drones)
        modified_modules = self._apply_owner_skill_modifiers(
            modified_modules, module_attrs, owner_skill_modifiers, module_required_skills
        )

        # 9. Apply attribute caps (e.g., maxTargetRange capped by maximumRangeCap)
        modified_ship = self._apply_attribute_caps(modified_ship)

        return modified_ship, modified_modules, charge_bonuses, modified_charges

    # ── Constants and data-loading helpers ────────────────────────────

    # Attribute caps: some attributes are capped by another attribute's value.
    # Maps {attr_id: (cap_attr_id, default_cap_value)}.
    # Uses the ship's cap attribute value if present, else the default.
    # Reference: PyFA's maxAttributeID mechanism in modifiedAttributeDict.py.
    ATTR_CAPS = {
        76: (797, 300000.0),  # maxTargetRange capped by maximumRangeCap (default 300km)
    }

    # Attribute IDs stored in invTypes rather than dgmTypeAttributes
    ATTR_MASS = 4
    ATTR_CAPACITY = 38  # cargo capacity

    def _supplement_invtypes_attrs(
        self, type_id: int, attrs: Dict[int, float],
    ) -> Dict[int, float]:
        """Supplement attributes with mass/capacity from invTypes if missing or zero.

        Some ship attributes (mass, cargo capacity) are stored in the invTypes
        table rather than dgmTypeAttributes. Without them, Dogma modifiers that
        reference these attributes (e.g., Industrial Core mass multiplier) would
        operate on a base value of 0, producing wrong results.
        """
        need_mass = self.ATTR_MASS not in attrs or attrs[self.ATTR_MASS] == 0
        need_cap = self.ATTR_CAPACITY not in attrs or attrs[self.ATTR_CAPACITY] == 0
        if not need_mass and not need_cap:
            return attrs

        with self.db.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT "mass", "capacity" FROM "invTypes" WHERE "typeID" = %s
            """, (type_id,))
            row = cur.fetchone()

        if not row:
            return attrs

        result = dict(attrs)
        if need_mass and row["mass"]:
            result[self.ATTR_MASS] = float(row["mass"])
        if need_cap and row["capacity"]:
            result[self.ATTR_CAPACITY] = float(row["capacity"])
        return result

    def _load_all_attributes(self, type_ids: List[int]) -> Dict[int, Dict[int, float]]:
        """Load all attributes for a list of type IDs from SDE."""
        if not type_ids:
            return {}
        with self.db.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT "typeID", "attributeID",
                       COALESCE("valueFloat", "valueInt"::float) as value
                FROM "dgmTypeAttributes"
                WHERE "typeID" = ANY(%s)
            """, (type_ids,))
            result: Dict[int, Dict[int, float]] = defaultdict(dict)
            for row in cur.fetchall():
                result[row["typeID"]][row["attributeID"]] = row["value"]
            return dict(result)

    def _load_group_ids(self, type_ids: List[int]) -> Dict[int, int]:
        """Load groupID for each module type."""
        if not type_ids:
            return {}
        with self.db.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT "typeID", "groupID"
                FROM "invTypes"
                WHERE "typeID" = ANY(%s)
            """, (type_ids,))
            return {row["typeID"]: row["groupID"] for row in cur.fetchall()}

    def _load_required_skills(self, type_ids: List[int]) -> Dict[int, set]:
        """Load required skill type IDs for each module/drone type.

        Checks attrs 182 (primary), 183 (secondary), 184 (tertiary) skill requirements.
        Returns {type_id: set of required skill type IDs}.
        """
        if not type_ids:
            return {}
        # Attrs 182, 183, 184 = requiredSkill1, requiredSkill2, requiredSkill3
        SKILL_ATTRS = [182, 183, 184]
        with self.db.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT "typeID", "attributeID",
                       COALESCE("valueFloat", "valueInt"::float) as value
                FROM "dgmTypeAttributes"
                WHERE "typeID" = ANY(%s)
                  AND "attributeID" = ANY(%s)
            """, (type_ids, SKILL_ATTRS))
            result: Dict[int, set] = defaultdict(set)
            for row in cur.fetchall():
                skill_id = int(row["value"])
                if skill_id > 0:
                    result[row["typeID"]].add(skill_id)
            return dict(result)

    # Resist attribute IDs where Damage Control Op 0 should be treated as PostMul
    RESIST_ATTR_IDS = frozenset([
        267, 268, 269, 270,  # Armor EM/Exp/Kin/Th
        271, 272, 273, 274,  # Shield EM/Exp/Kin/Th
        109, 110, 111, 113,  # Hull Kin/Th/Exp/EM
    ])

    # Core pilot skill bonuses: skill_type_id → (bonus_per_level_pct, target_ship_attr_id)
    # Each gives +X% per level to a ship attribute (not stacking penalized).
    # Negative values = reduction (e.g., -5% recharge time = faster recharge).
    DEFAULT_SKILL_LEVEL = 5  # All V

    def _load_modifiers(
        self, module_type_ids: List[int], simulation_mode: bool = True,
        module_flags: Optional[List[int]] = None,
        flag_states: Optional[Dict[int, str]] = None,
    ) -> List[Tuple[int, DogmaModifier]]:
        """Load all modifiers from all effects of fitted modules.

        For each module: get effects -> for each effect: parse modifierInfo.
        Duplicate type_ids produce duplicate modifiers (one per fitted instance).

        When module_flags and flag_states are provided, each slot instance is
        filtered independently by its flag's state. This correctly handles
        duplicate modules (e.g., 2x Shield Hardener II with different states).

        Special case: Damage Control effect (effectName='damageControl') encodes
        resist modifications as Op 0 (PreAssign) in the SDE, but EVE applies them
        as Op 4 (PostMul). We override this at load time.
        """
        unique_ids = list(set(module_type_ids))
        if not unique_ids:
            return []

        with self.db.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT dte."typeID", e."effectID", e."effectName",
                       e."modifierInfo", e."durationAttributeID",
                       e."effectCategory"
                FROM "dgmTypeEffects" dte
                JOIN "dgmEffects" e ON e."effectID" = dte."effectID"
                WHERE dte."typeID" = ANY(%s)
                  AND e."modifierInfo" IS NOT NULL
                  AND e."modifierInfo" != ''
            """, (unique_ids,))

            # Build per-type modifier list
            type_modifiers: Dict[int, List[DogmaModifier]] = defaultdict(list)
            for row in cur.fetchall():
                effect_id = row.get("effectID", 0)
                effect_name = row.get("effectName", "")
                # Derive effect category since SDE effectCategory column is NULL
                # for all effects in this SDE version.
                # 5=overload, 1=active (has duration), 4=online, 0=passive
                effect_name_lower = effect_name.lower()
                if "overload" in effect_name_lower:
                    effect_cat = 5
                elif row.get("durationAttributeID") is not None:
                    effect_cat = 1
                elif "online" in effect_name_lower:
                    effect_cat = 4
                else:
                    effect_cat = 0

                # Skip activation-required effects (siege, bastion, industrial core)
                if effect_id in self.ACTIVATION_REQUIRED_EFFECTS:
                    continue

                # In fitting mode, skip active effects (require module activation).
                # Active effects have durationAttributeID set in the SDE.
                # E.g., Shield Hardener effects are active; Shield Amplifier effects are passive.
                if not simulation_mode and row.get("durationAttributeID") is not None:
                    continue

                parsed = parse_modifier_info(row["modifierInfo"])

                # Damage Control: SDE encodes resist mods as Op 0 (PreAssign)
                # but EVE actually applies them as Op 4 (PostMul)
                if effect_name == "damageControl":
                    parsed = [
                        replace(mod, operation=4) if (mod.operation == 0 and mod.modified_attr_id in self.RESIST_ATTR_IDS)
                        else mod
                        for mod in parsed
                    ]

                # Rig drawback effects: NOT stacking penalized in EVE.
                # Tag them so _apply_modifiers applies them as plain multipliers.
                # Exception: velocity drawbacks (attr 37) are NOT applied by EVE's
                # fitting window at all — skip them entirely.
                is_drawback = effect_name.startswith("drawback")
                if is_drawback:
                    parsed = [
                        replace(mod, is_drawback=True)
                        for mod in parsed
                        if mod.modified_attr_id != 37  # skip velocity drawbacks
                    ]

                # Tag all modifiers with their effect's category for per-flag filtering
                parsed = [replace(mod, effect_category=effect_cat) for mod in parsed]

                type_modifiers[row["typeID"]].extend(parsed)

        # Expand: each fitted instance of a type gets its own copy of modifiers.
        # When module_flags + flag_states are provided, filter per-slot so that
        # e.g. 2x identical hardeners can have independent on/off states.
        # Rig modules (flags 92-99) are tagged with is_rig=True so their
        # PostPercent bonuses bypass stacking penalty in _apply_modifiers().
        result = []
        if module_flags and flag_states:
            for tid, flag in zip(module_type_ids, module_flags):
                state = flag_states.get(flag, "active")
                allowed = self.MODULE_STATE_ALLOWED_CATEGORIES.get(state, frozenset({0, 1, 4}))
                is_rig = 92 <= flag <= 99
                for mod in type_modifiers.get(tid, []):
                    if mod.effect_category is None or mod.effect_category in allowed:
                        if is_rig and not mod.is_rig:
                            mod = replace(mod, is_rig=True)
                        result.append((tid, mod))
        else:
            # No explicit states → default "active" filtering (exclude overload cat 5)
            default_allowed = self.MODULE_STATE_ALLOWED_CATEGORIES["active"]
            # Build rig set from flags when available (no flag_states)
            rig_types = set()
            if module_flags:
                for tid, flag in zip(module_type_ids, module_flags):
                    if 92 <= flag <= 99:
                        rig_types.add(tid)
            for tid in module_type_ids:
                is_rig = tid in rig_types
                for mod in type_modifiers.get(tid, []):
                    if mod.effect_category is None or mod.effect_category in default_allowed:
                        if is_rig and not mod.is_rig:
                            mod = replace(mod, is_rig=True)
                        result.append((tid, mod))

        return result

    def _apply_modifiers(
        self,
        ship_attrs: Dict[int, float],
        module_attrs: Dict[int, Dict[int, float]],
        modifiers: List[Tuple[int, DogmaModifier]],
    ) -> Dict[int, float]:
        """Apply modifiers to ship attributes in correct operation order.

        Operations applied in order: 0 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7
        Operations 4, 5, 6 are stacking-penalized (except rig drawbacks).
        """
        result = dict(ship_attrs)

        # Group modifiers by target attribute and operation.
        # Separate drawback and rig values (not stacking penalized) from regular values.
        by_attr_op: Dict[int, Dict[int, List[float]]] = defaultdict(lambda: defaultdict(list))
        drawback_by_attr_op: Dict[int, Dict[int, List[float]]] = defaultdict(lambda: defaultdict(list))
        for type_id, mod in modifiers:
            mod_value = module_attrs.get(type_id, {}).get(mod.modifying_attr_id)
            if mod_value is None:
                continue
            if mod.is_drawback or mod.is_rig or mod.is_skill:
                # Rig bonuses, rig drawbacks, and skill modifiers are all exempt
                # from stacking penalty in EVE. Applied as independent multipliers.
                drawback_by_attr_op[mod.modified_attr_id][mod.operation].append(mod_value)
            else:
                by_attr_op[mod.modified_attr_id][mod.operation].append(mod_value)

        # Collect all affected attribute IDs
        all_attr_ids = set(by_attr_op.keys()) | set(drawback_by_attr_op.keys())

        # Apply in operation order
        for attr_id in all_attr_ids:
            base = result.get(attr_id, 0.0)
            ops = by_attr_op.get(attr_id, {})
            drawback_ops = drawback_by_attr_op.get(attr_id, {})

            # Op 0: PreAssign (last value wins)
            if 0 in ops:
                base = ops[0][-1]

            # Op 2: ModAdd (sum all, add to base)
            if 2 in ops:
                base += sum(ops[2])

            # Op 3: ModSub (sum all, subtract from base)
            if 3 in ops:
                base -= sum(ops[3])

            # Op 4: PostMul — regular modifiers stacking penalized
            if 4 in ops:
                base *= apply_stacking_penalized_multipliers(ops[4])

            # Op 5: PostDiv — regular modifiers stacking penalized
            if 5 in ops:
                divisor = apply_stacking_penalized_multipliers(ops[5])
                if divisor != 0:
                    base /= divisor

            # Op 6: PostPercent — regular modifiers stacking penalized
            if 6 in ops:
                pct_mults = [1.0 + (v / 100.0) for v in ops[6]]
                base *= apply_stacking_penalized_multipliers(pct_mults)

            # Rig + drawback + skill ops applied separately, NOT stacking penalized.
            # Rig bonuses (e.g., +15% armor HP) and drawbacks (e.g., -10% velocity)
            # are independent multipliers in EVE — no diminishing returns.
            if 0 in drawback_ops:
                base = drawback_ops[0][-1]
            for val in drawback_ops.get(2, []):
                base += val
            for val in drawback_ops.get(3, []):
                base -= val
            for val in drawback_ops.get(4, []):
                base *= val
            for val in drawback_ops.get(5, []):
                if val != 0:
                    base /= val
            for val in drawback_ops.get(6, []):
                base *= (1.0 + val / 100.0)
            if 7 in drawback_ops:
                base = drawback_ops[7][-1]

            # Op 7: PostAssign (last value wins, overrides everything)
            if 7 in ops:
                base = ops[7][-1]

            result[attr_id] = base

        return result

    def _apply_location_modifiers(
        self,
        module_attrs: Dict[int, Dict[int, float]],
        modifiers: List[Tuple[int, DogmaModifier]],
        module_groups: Dict[int, int],
        module_required_skills: Optional[Dict[int, set]] = None,
        source_attrs: Optional[Dict[int, Dict[int, float]]] = None,
    ) -> Dict[int, Dict[int, float]]:
        """Apply LocationGroupModifier, LocationRequiredSkillModifier, and
        LocationModifier to module attributes.

        E.g., Gyrostabilizer modifies damageMultiplier on all Projectile Turrets.
        BCS modifies rateOfFire on all modules requiring Missile Launcher Operation.
        Rig drawback effects (is_drawback=True) apply without stacking penalty.

        Args:
            source_attrs: Optional separate dict for modifier source value lookup.
                          When applying modifiers to charges, the modifier source
                          (e.g., MGE bonus attr) lives in module_attrs, not in the
                          target charge_attrs. Pass module_attrs here in that case.
        """
        result = {tid: dict(attrs) for tid, attrs in module_attrs.items()}
        if module_required_skills is None:
            module_required_skills = {}
        lookup_attrs = source_attrs if source_attrs is not None else module_attrs

        # Group modifiers by (target_attr, target_group_or_skill, operation).
        # Separate drawback values from regular values.
        # Key: (attr_id, group_id_or_None, operation)
        grouped: Dict[Tuple[int, Optional[int], int], List[float]] = defaultdict(list)
        drawback_grouped: Dict[Tuple[int, Optional[int], int], List[float]] = defaultdict(list)
        # Skill-based modifiers keyed by (attr_id, skill_type_id, operation)
        skill_grouped: Dict[Tuple[int, int, int], List[float]] = defaultdict(list)
        skill_drawback_grouped: Dict[Tuple[int, int, int], List[float]] = defaultdict(list)

        for source_type_id, mod in modifiers:
            mod_value = lookup_attrs.get(source_type_id, {}).get(mod.modifying_attr_id)
            if mod_value is None:
                continue
            if mod.func == "LocationRequiredSkillModifier" and mod.skill_type_id is not None:
                # Skill-origin modifiers route to non-stacking bucket (like drawbacks)
                target = skill_drawback_grouped if (mod.is_drawback or mod.is_skill) else skill_grouped
                key = (mod.modified_attr_id, mod.skill_type_id, mod.operation)
                target[key].append(mod_value)
            else:
                # Skill-origin modifiers route to non-stacking bucket (like drawbacks)
                target = drawback_grouped if (mod.is_drawback or mod.is_skill) else grouped
                if mod.func == "LocationGroupModifier" and mod.group_id is not None:
                    key = (mod.modified_attr_id, mod.group_id, mod.operation)
                    target[key].append(mod_value)
                elif mod.func == "LocationModifier":
                    key = (mod.modified_attr_id, None, mod.operation)
                    target[key].append(mod_value)

        # Apply regular group/location modifiers (stacking penalized)
        for (attr_id, group_id, operation), values in grouped.items():
            for tid, attrs in result.items():
                if group_id is not None and module_groups.get(tid) != group_id:
                    continue
                if attr_id not in attrs:
                    continue

                base = attrs[attr_id]
                if operation == 0:
                    base = values[-1]  # PreAssign: last value wins
                elif operation == 2:
                    base += sum(values)
                elif operation == 3:
                    base -= sum(values)
                elif operation == 4:
                    base *= apply_stacking_penalized_multipliers(values)
                elif operation == 5:
                    divs = [v for v in values if v != 0]
                    if divs:
                        base /= apply_stacking_penalized_multipliers(divs)
                elif operation == 6:
                    pct_mults = [1.0 + (v / 100.0) for v in values]
                    base *= apply_stacking_penalized_multipliers(pct_mults)
                elif operation == 7:
                    base = values[-1]  # PostAssign: last value wins
                attrs[attr_id] = base

        # Apply drawback group/location modifiers (NOT stacking penalized)
        for (attr_id, group_id, operation), values in drawback_grouped.items():
            for tid, attrs in result.items():
                if group_id is not None and module_groups.get(tid) != group_id:
                    continue
                if attr_id not in attrs:
                    continue

                base = attrs[attr_id]
                if operation == 0:
                    base = values[-1]  # PreAssign: last value wins
                else:
                    for val in values:
                        if operation == 2:
                            base += val
                        elif operation == 3:
                            base -= val
                        elif operation == 4:
                            base *= val
                        elif operation == 5:
                            if val != 0:
                                base /= val
                        elif operation == 6:
                            base *= (1.0 + val / 100.0)
                        elif operation == 7:
                            base = val
                attrs[attr_id] = base

        # Apply LocationRequiredSkillModifier (stacking penalized)
        # E.g., BCS modifies ROF on all modules requiring MLO skill
        for (attr_id, skill_type_id, operation), values in skill_grouped.items():
            for tid, attrs in result.items():
                required = module_required_skills.get(tid, set())
                if skill_type_id not in required:
                    continue
                if attr_id not in attrs:
                    continue

                base = attrs[attr_id]
                if operation == 0:
                    base = values[-1]  # PreAssign: last value wins
                elif operation == 2:
                    base += sum(values)
                elif operation == 3:
                    base -= sum(values)
                elif operation == 4:
                    base *= apply_stacking_penalized_multipliers(values)
                elif operation == 5:
                    divs = [v for v in values if v != 0]
                    if divs:
                        base /= apply_stacking_penalized_multipliers(divs)
                elif operation == 6:
                    pct_mults = [1.0 + (v / 100.0) for v in values]
                    base *= apply_stacking_penalized_multipliers(pct_mults)
                elif operation == 7:
                    base = values[-1]  # PostAssign: last value wins
                attrs[attr_id] = base

        # Apply LocationRequiredSkillModifier drawbacks (NOT stacking penalized)
        for (attr_id, skill_type_id, operation), values in skill_drawback_grouped.items():
            for tid, attrs in result.items():
                required = module_required_skills.get(tid, set())
                if skill_type_id not in required:
                    continue
                if attr_id not in attrs:
                    continue

                base = attrs[attr_id]
                if operation == 0:
                    base = values[-1]  # PreAssign: last value wins
                else:
                    for val in values:
                        if operation == 2:
                            base += val
                        elif operation == 3:
                            base -= val
                        elif operation == 4:
                            base *= val
                        elif operation == 5:
                            if val != 0:
                                base /= val
                        elif operation == 6:
                            base *= (1.0 + val / 100.0)
                        elif operation == 7:
                            base = val
                attrs[attr_id] = base

        return result

    def _apply_owner_skill_modifiers(
        self,
        module_attrs: Dict[int, Dict[int, float]],
        base_module_attrs: Dict[int, Dict[int, float]],
        modifiers: List[Tuple[int, DogmaModifier]],
        module_required_skills: Dict[int, set],
    ) -> Dict[int, Dict[int, float]]:
        """Apply OwnerRequiredSkillModifier to matching modules/drones.

        E.g., Drone Damage Amplifier modifies damageMultiplier on all
        entities that require the Drones skill (skillTypeID 3436).
        """
        result = {tid: dict(attrs) for tid, attrs in module_attrs.items()}

        # Group modifiers by (target_attr, skill_type_id, operation)
        # Separate skill-origin modifiers (not stacking penalized) from module-origin
        grouped: Dict[Tuple[int, int, int], List[float]] = defaultdict(list)
        skill_grouped: Dict[Tuple[int, int, int], List[float]] = defaultdict(list)

        for source_type_id, mod in modifiers:
            if mod.skill_type_id is None:
                continue
            mod_value = base_module_attrs.get(source_type_id, {}).get(mod.modifying_attr_id)
            if mod_value is None:
                continue
            key = (mod.modified_attr_id, mod.skill_type_id, mod.operation)
            if mod.is_skill:
                skill_grouped[key].append(mod_value)
            else:
                grouped[key].append(mod_value)

        # Apply module-origin modifiers (stacking penalized)
        for (attr_id, skill_type_id, operation), values in grouped.items():
            for tid, attrs in result.items():
                required_skills = module_required_skills.get(tid, set())
                if skill_type_id not in required_skills:
                    continue
                if attr_id not in attrs:
                    continue

                base = attrs[attr_id]
                if operation == 0:
                    base = values[-1]  # PreAssign: last value wins
                elif operation == 2:
                    base += sum(values)
                elif operation == 3:
                    base -= sum(values)
                elif operation == 4:
                    base *= apply_stacking_penalized_multipliers(values)
                elif operation == 5:
                    divs = [v for v in values if v != 0]
                    if divs:
                        base /= apply_stacking_penalized_multipliers(divs)
                elif operation == 6:
                    pct_mults = [1.0 + (v / 100.0) for v in values]
                    base *= apply_stacking_penalized_multipliers(pct_mults)
                elif operation == 7:
                    base = values[-1]  # PostAssign: last value wins
                attrs[attr_id] = base

        # Apply skill-origin modifiers (NOT stacking penalized)
        for (attr_id, skill_type_id, operation), values in skill_grouped.items():
            for tid, attrs in result.items():
                required_skills = module_required_skills.get(tid, set())
                if skill_type_id not in required_skills:
                    continue
                if attr_id not in attrs:
                    continue

                base = attrs[attr_id]
                if operation == 0:
                    base = values[-1]  # PreAssign: last value wins
                else:
                    for val in values:
                        if operation == 2:
                            base += val
                        elif operation == 3:
                            base -= val
                        elif operation == 4:
                            base *= val
                        elif operation == 5:
                            if val != 0:
                                base /= val
                        elif operation == 6:
                            base *= (1.0 + val / 100.0)
                        elif operation == 7:
                            base = val
                attrs[attr_id] = base

        return result

    def _load_ship_effects(
        self, ship_type_id: int, base_ship_attrs: Dict[int, float] = None,
    ) -> List[DogmaModifier]:
        """Load modifiers from the ship's own effects (role bonuses + per-level bonuses).

        Ship effects encode hull bonuses like "+10% drone damage per level".
        The modifying_attr_id points to a ship attribute containing the
        per-level bonus value.

        Effects with 'RoleBonus' in the name are flat bonuses (not scaled by level).
        Effects with 'eliteBonus' prefix scale by requiredSkill2 (T2 specialization).
        All others are per-level bonuses scaled by requiredSkill1 (hull class).

        Args:
            ship_type_id: The ship's typeID.
            base_ship_attrs: Pre-loaded ship attributes from _load_all_attributes().
                             Used to look up requiredSkill2 without a redundant DB query.
        """
        # Look up requiredSkill2 for T2 skill scaling from pre-loaded attrs
        ship_skill_2 = None
        if base_ship_attrs:
            val = base_ship_attrs.get(self.ATTR_REQUIRED_SKILL_2, 0)
            if val:
                ship_skill_2 = int(val)

        with self.db.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT e."effectName", e."modifierInfo"
                FROM "dgmTypeEffects" dte
                JOIN "dgmEffects" e ON e."effectID" = dte."effectID"
                WHERE dte."typeID" = %s
                  AND e."modifierInfo" IS NOT NULL
                  AND e."modifierInfo" != ''
            """, (ship_type_id,))
            modifiers = []
            for row in cur.fetchall():
                parsed = parse_modifier_info(row["modifierInfo"])
                effect_name = row.get("effectName", "") or ""

                # Ship hull effects that PreAssign agility (attr 70) are SDE display
                # artifacts — they corrupt the real base agility loaded from
                # dgmTypeAttributes.  Actual agility bonuses come from core skills
                # (Spaceship Command, Evasive Maneuvering) loaded as virtual modules.
                # Effects: shipAdvancedSpaceshipCommandAgilityBonus (1615),
                #          shipCapitalAgilityBonus (1617), and similar.
                parsed = [
                    mod for mod in parsed
                    if not (mod.operation == 0 and mod.modified_attr_id == 70)
                ]
                if not parsed:
                    continue

                is_role = "rolebonus" in effect_name.lower()
                # T2 ships: "eliteBonus*" effects scale by requiredSkill2
                is_elite = effect_name.startswith("eliteBonus")
                scaling_skill = ship_skill_2 if (is_elite and ship_skill_2) else None
                if is_role or is_elite or scaling_skill:
                    parsed = [
                        replace(mod, is_role_bonus=is_role, scaling_skill_id=scaling_skill)
                        for mod in parsed
                    ]
                modifiers.extend(parsed)
            return modifiers

    def _load_mode_effects(
        self, mode_type_id: int,
    ) -> Tuple[List[DogmaModifier], Dict[int, float]]:
        """Load modifiers and attributes for a T3D mode item.

        T3D Tactical Destroyers have modes (Defense/Propulsion/Sharpshooter).
        Each mode is a virtual item in SDE group 1306 with PostDiv effects
        that modify ship attributes.

        SDE gotcha: Mode items have published=0, so we must NOT filter
        by published=1.

        Args:
            mode_type_id: The typeID of the mode item (e.g., 34562).

        Returns:
            (modifiers, mode_attrs)
            - modifiers: list of DogmaModifier parsed from the mode's effects
            - mode_attrs: {attr_id: value} for the mode item's own attributes
        """
        with self.db.cursor(cursor_factory=RealDictCursor) as cur:
            # 1. Load mode effects (modifierInfo YAML)
            cur.execute("""
                SELECT dte."typeID", e."effectID", e."effectName",
                       e."modifierInfo"
                FROM "dgmTypeEffects" dte
                JOIN "dgmEffects" e ON e."effectID" = dte."effectID"
                WHERE dte."typeID" = %s
                  AND e."modifierInfo" IS NOT NULL
                  AND e."modifierInfo" != ''
            """, (mode_type_id,))

            modifiers: List[DogmaModifier] = []
            for row in cur.fetchall():
                parsed = parse_modifier_info(row["modifierInfo"])
                modifiers.extend(parsed)

            # 2. Load mode item's own attributes
            cur.execute("""
                SELECT "attributeID",
                       COALESCE("valueFloat", "valueInt"::double precision) as value
                FROM "dgmTypeAttributes"
                WHERE "typeID" = %s
            """, (mode_type_id,))

            mode_attrs: Dict[int, float] = {}
            for row in cur.fetchall():
                mode_attrs[row["attributeID"]] = row["value"]

        return modifiers, mode_attrs

    def _apply_mode_modifiers(
        self,
        ship_attrs: Dict[int, float],
        module_attrs: Dict[int, Dict[int, float]],
        mode_modifiers: List[DogmaModifier],
        mode_attrs: Dict[int, float],
        module_groups: Dict[int, int],
        module_required_skills: Dict[int, set],
    ) -> Tuple[Dict[int, float], Dict[int, Dict[int, float]]]:
        """Apply T3D mode PostDiv (operation 5) modifiers to ship and module attributes.

        T3D modes use three modifier types, all PostDiv (attr = attr / value):
        1. ItemModifier (domain=shipID): directly on ship attributes
           (e.g., sig radius, agility, velocity, resists)
        2. LocationRequiredSkillModifier (domain=shipID, skillTypeID): on modules
           requiring a specific skill (e.g., turret damage, optimal range)
        3. OwnerRequiredSkillModifier (domain=charID, skillTypeID): on modules by
           owner skill (e.g., missile velocity)

        Mode modifiers are NOT stacking penalized — each applies independently.

        Returns:
            (modified_ship_attrs, modified_module_attrs)
        """
        result_ship = dict(ship_attrs)
        result_modules = {tid: dict(attrs) for tid, attrs in module_attrs.items()}

        for mod in mode_modifiers:
            # Get the modifier value from mode item's own attributes
            mod_value = mode_attrs.get(mod.modifying_attr_id)
            if mod_value is None:
                continue

            if mod.func == "ItemModifier" and mod.domain == "shipID":
                # PostDiv directly on ship attribute
                if mod.modified_attr_id in result_ship and mod_value != 0:
                    result_ship[mod.modified_attr_id] /= mod_value

            elif mod.func == "LocationRequiredSkillModifier" and mod.skill_type_id is not None:
                # PostDiv on modules requiring a specific skill
                if mod_value == 0:
                    continue
                for tid, attrs in result_modules.items():
                    required = module_required_skills.get(tid, set())
                    if mod.skill_type_id in required and mod.modified_attr_id in attrs:
                        attrs[mod.modified_attr_id] /= mod_value

            elif mod.func == "OwnerRequiredSkillModifier" and mod.skill_type_id is not None:
                # PostDiv on modules by owner skill
                if mod_value == 0:
                    continue
                for tid, attrs in result_modules.items():
                    required = module_required_skills.get(tid, set())
                    if mod.skill_type_id in required and mod.modified_attr_id in attrs:
                        attrs[mod.modified_attr_id] /= mod_value

        return result_ship, result_modules

    # Attribute ID for ship's primary required skill
    ATTR_REQUIRED_SKILL_1 = 182
    ATTR_REQUIRED_SKILL_2 = 183

    # Charge/ammo damage attribute IDs — these live on charges, not modules,
    # so OwnerRequiredSkillModifier targeting these must be passed through to offense.py
    CHARGE_DAMAGE_ATTR_IDS = {114, 116, 117, 118}

    def _apply_ship_role_bonuses(
        self,
        ship_attrs: Dict[int, float],
        module_attrs: Dict[int, Dict[int, float]],
        ship_modifiers: List[DogmaModifier],
        base_ship_attrs: Dict[int, float],
        module_groups: Dict[int, int],
        module_required_skills: Dict[int, set],
        skill_levels: Dict[int, int],
        ship_type_id: Optional[int] = None,
        skill_default: int = 5,
    ) -> Tuple[Dict[int, float], Dict[int, Dict[int, float]], List[dict]]:
        """Apply ship's own role bonus effects.

        Per-level bonuses: bonus = per_level_value * skill_level (default All V).
        Role bonuses (is_role_bonus=True): bonus = value (flat, not scaled by level).

        Not stacking penalized — each bonus applies independently.

        Returns:
            (ship_attrs, module_attrs, charge_bonuses)
            charge_bonuses: list of dicts for damage bonuses targeting charges/ammo
        """
        result_ship = dict(ship_attrs)
        result_modules = {tid: dict(attrs) for tid, attrs in module_attrs.items()}
        charge_bonuses: List[dict] = []

        # Load ship's required skills for per-level bonus scaling
        # requiredSkill1 = hull class (e.g., Caldari Cruiser for Cerberus)
        # requiredSkill2 = specialization (e.g., HAC for Cerberus)
        ship_skill_1 = None
        ship_skill_2 = None
        if ship_type_id:
            ship_skill_1 = int(base_ship_attrs.get(self.ATTR_REQUIRED_SKILL_1, 0)) or None
            ship_skill_2 = int(base_ship_attrs.get(self.ATTR_REQUIRED_SKILL_2, 0)) or None
            if not ship_skill_1 or not ship_skill_2:
                with self.db.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT "attributeID",
                               COALESCE("valueFloat", "valueInt"::float) as value
                        FROM "dgmTypeAttributes"
                        WHERE "typeID" = %s AND "attributeID" IN (%s, %s)
                    """, (ship_type_id, self.ATTR_REQUIRED_SKILL_1, self.ATTR_REQUIRED_SKILL_2))
                    for row in cur.fetchall():
                        if row["value"]:
                            if row["attributeID"] == self.ATTR_REQUIRED_SKILL_1 and not ship_skill_1:
                                ship_skill_1 = int(row["value"])
                            elif row["attributeID"] == self.ATTR_REQUIRED_SKILL_2 and not ship_skill_2:
                                ship_skill_2 = int(row["value"])

        for mod in ship_modifiers:
            # Get per-level bonus value from ship's own attributes
            per_level = base_ship_attrs.get(mod.modifying_attr_id)
            if per_level is None:
                continue

            # Compute effective bonus
            if mod.is_role_bonus:
                # Role bonus: flat value (not scaled by level)
                effective_value = per_level
            else:
                # Per-level bonus: scale by appropriate ship required skill.
                # T2 ships have two skill trees: requiredSkill1 (hull class) and
                # requiredSkill2 (specialization). The effect name determines which:
                # - "eliteBonus*" effects scale by requiredSkill2 (T2 specialization)
                # - All other effects scale by requiredSkill1 (hull class)
                scaling_skill = mod.scaling_skill_id
                if scaling_skill:
                    level = skill_levels.get(scaling_skill, skill_default)
                elif ship_skill_1:
                    level = skill_levels.get(ship_skill_1, skill_default)
                else:
                    level = skill_default
                effective_value = per_level * level

            if mod.func == "ItemModifier" and mod.domain == "shipID":
                self._apply_single_modifier(
                    result_ship, mod.modified_attr_id, effective_value, mod.operation
                )

            elif mod.func == "LocationRequiredSkillModifier" and mod.skill_type_id:
                for tid, attrs in result_modules.items():
                    required = module_required_skills.get(tid, set())
                    if mod.skill_type_id in required and mod.modified_attr_id in attrs:
                        self._apply_single_modifier(
                            attrs, mod.modified_attr_id, effective_value, mod.operation
                        )

            elif mod.func == "LocationGroupModifier" and mod.group_id is not None:
                for tid, attrs in result_modules.items():
                    if module_groups.get(tid) == mod.group_id and mod.modified_attr_id in attrs:
                        self._apply_single_modifier(
                            attrs, mod.modified_attr_id, effective_value, mod.operation
                        )

            elif mod.func == "OwnerRequiredSkillModifier" and mod.skill_type_id:
                # Apply to fitted modules
                for tid, attrs in result_modules.items():
                    required = module_required_skills.get(tid, set())
                    if mod.skill_type_id in required and mod.modified_attr_id in attrs:
                        self._apply_single_modifier(
                            attrs, mod.modified_attr_id, effective_value, mod.operation
                        )
                # Collect charge bonuses for damage attrs (charges are outside engine scope)
                if mod.modified_attr_id in self.CHARGE_DAMAGE_ATTR_IDS:
                    charge_bonuses.append({
                        "modified_attr_id": mod.modified_attr_id,
                        "skill_type_id": mod.skill_type_id,
                        "value": effective_value,
                        "operation": mod.operation,
                    })

            elif mod.func == "LocationModifier":
                for tid, attrs in result_modules.items():
                    if mod.modified_attr_id in attrs:
                        self._apply_single_modifier(
                            attrs, mod.modified_attr_id, effective_value, mod.operation
                        )

        return result_ship, result_modules, charge_bonuses

    @staticmethod
    def _apply_single_modifier(
        attrs: Dict[int, float], attr_id: int, value: float, operation: int,
    ):
        """Apply a single modifier value to an attribute dict (in-place)."""
        if attr_id not in attrs:
            return
        base = attrs[attr_id]
        if operation == 0:      # PreAssign
            base = value
        elif operation == 2:    # ModAdd
            base += value
        elif operation == 3:    # ModSub
            base -= value
        elif operation == 4:    # PostMul
            base *= value
        elif operation == 5:    # PostDiv
            if value != 0:
                base /= value
        elif operation == 6:    # PostPercent
            base *= (1.0 + value / 100.0)
        elif operation == 7:    # PostAssign
            base = value
        attrs[attr_id] = base

    def _apply_attribute_caps(
        self, ship_attrs: Dict[int, float],
    ) -> Dict[int, float]:
        """Apply attribute caps from maxAttributeID relationships.

        Some attributes have a maximum value defined by another attribute.
        E.g., maxTargetRange (76) is capped by maximumRangeCap (797).
        If the cap attribute is present on the ship, use its value;
        otherwise fall back to the attribute's default.
        """
        result = dict(ship_attrs)
        for attr_id, (cap_attr_id, cap_default) in self.ATTR_CAPS.items():
            if attr_id in result:
                cap_value = result.get(cap_attr_id, cap_default)
                if result[attr_id] > cap_value:
                    result[attr_id] = cap_value
        return result

    # Attribute ID for skill level (injected at runtime, default 0 in SDE)
    ATTR_SKILL_LEVEL = 280

    def _load_skill_virtual_modules(
        self,
        skill_type_ids: List[int],
        skill_levels: Dict[int, int],
        default_level: int,
    ) -> Dict[int, Dict[int, float]]:
        """Load skill base attributes and inject skillLevel (attr 280).

        Treats skills as virtual modules: loads their dgmTypeAttributes,
        then injects attr 280 = trained skill level (or default for All-V).

        Args:
            skill_type_ids: List of skill type_ids to load.
            skill_levels: {skill_type_id: trained_level} from character.
            default_level: Level for skills not in skill_levels (5=All V, 0=char mode).

        Returns:
            {skill_type_id: {attr_id: value}} with attr 280 injected.
        """
        if not skill_type_ids:
            return {}
        skill_attrs = self._load_all_attributes(skill_type_ids)
        for sid in skill_type_ids:
            if sid not in skill_attrs:
                skill_attrs[sid] = {}
            level = skill_levels.get(sid, default_level)
            skill_attrs[sid][self.ATTR_SKILL_LEVEL] = float(level)
        return skill_attrs

    def _load_skill_pipeline_modifiers(
        self, skill_type_ids: List[int],
    ) -> List[Tuple[int, DogmaModifier]]:
        """Load skill effect modifiers for the main Dogma pipeline.

        Queries all effects for the given skill type_ids, then EXCLUDES
        self-modifiers (domain=itemID, func=ItemModifier) which are already
        handled by _apply_skill_self_modifiers in step 1.5e.

        Returns modifiers that should be routed through steps 6/7/8:
        - shipID + ItemModifier -> step 6 (ship attrs)
        - LocationGroupModifier -> step 7 (module attrs by group)
        - LocationRequiredSkillModifier -> step 7 (module attrs by skill)
        - OwnerRequiredSkillModifier -> step 8 (drone/fighter attrs)
        """
        if not skill_type_ids:
            return []

        unique_ids = list(set(skill_type_ids))
        with self.db.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT dte."typeID", e."effectID", e."effectName",
                       e."modifierInfo", e."durationAttributeID",
                       e."effectCategory"
                FROM "dgmTypeEffects" dte
                JOIN "dgmEffects" e ON e."effectID" = dte."effectID"
                WHERE dte."typeID" = ANY(%s)
                  AND e."modifierInfo" IS NOT NULL
                  AND e."modifierInfo" NOT LIKE 'null%%'
                  AND e."modifierInfo" != ''
            """, (unique_ids,))

            result = []
            for row in cur.fetchall():
                type_id = row["typeID"]
                parsed = parse_modifier_info(row["modifierInfo"])
                for mod in parsed:
                    # Skip self-modifiers -- already handled in _apply_skill_self_modifiers
                    if mod.domain == "itemID" and mod.func == "ItemModifier":
                        continue
                    # Tag as skill-origin: skill modifiers are NOT stacking penalized in EVE
                    result.append((type_id, replace(mod, is_skill=True)))
            return result

    def _apply_skill_self_modifiers(
        self,
        skill_type_ids: List[int],
        skill_attrs: Dict[int, Dict[int, float]],
    ) -> None:
        """Pre-compute skill intermediate bonus values (2-step chain Step 1).

        Loads skill effects with domain=itemID + func=ItemModifier, then applies
        them to the skill's own attribute dict. This computes the intermediate
        bonus value (e.g., shieldCapacityBonus = 5.0 * level = 25.0).

        CRITICAL: Op 0 is treated as PreMul (multiply) here, NOT PreAssign.
        This matches EVE Dogma semantics for skill self-modifiers.
        Do NOT use _apply_single_modifier (which treats op 0 as PreAssign).

        Modifies skill_attrs in-place.
        """
        if not skill_type_ids:
            return

        unique_ids = list(set(skill_type_ids))
        with self.db.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT dte."typeID", e."effectID", e."effectName",
                       e."modifierInfo", e."durationAttributeID",
                       e."effectCategory"
                FROM "dgmTypeEffects" dte
                JOIN "dgmEffects" e ON e."effectID" = dte."effectID"
                WHERE dte."typeID" = ANY(%s)
                  AND e."modifierInfo" IS NOT NULL
                  AND e."modifierInfo" NOT LIKE 'null%%'
                  AND e."modifierInfo" != ''
            """, (unique_ids,))

            for row in cur.fetchall():
                type_id = row["typeID"]
                if type_id not in skill_attrs:
                    continue
                parsed = parse_modifier_info(row["modifierInfo"])
                for mod in parsed:
                    # Only process self-modifiers (domain=itemID, func=ItemModifier)
                    if mod.domain != "itemID" or mod.func != "ItemModifier":
                        continue
                    attrs = skill_attrs[type_id]
                    mod_value = attrs.get(mod.modifying_attr_id)
                    if mod_value is None:
                        continue
                    target = mod.modified_attr_id
                    if target not in attrs:
                        continue

                    # Op 0 = PreMul for skill self-modifiers (NOT PreAssign!)
                    if mod.operation == 0:
                        attrs[target] *= mod_value
                    elif mod.operation == 2:  # ModAdd
                        attrs[target] += mod_value
                    elif mod.operation == 4:  # PostMul
                        attrs[target] *= mod_value
                    elif mod.operation == 6:  # PostPercent
                        attrs[target] *= (1.0 + mod_value / 100.0)

    def _get_all_skill_type_ids(self) -> set:
        """Get all skill type_ids that have valid YAML modifierInfo in SDE.

        Used in All-V mode to load ALL skill effects. Returns a set of type_ids
        for skills (categoryID=16) that have at least one parseable YAML effect.
        Excludes 'null...' legacy effects that our YAML parser cannot read.
        """
        with self.db.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT DISTINCT dte."typeID"
                FROM "dgmTypeEffects" dte
                JOIN "dgmEffects" e ON e."effectID" = dte."effectID"
                JOIN "invTypes" t ON t."typeID" = dte."typeID"
                JOIN "invGroups" g ON g."groupID" = t."groupID"
                WHERE g."categoryID" = 16
                  AND e."modifierInfo" IS NOT NULL
                  AND e."modifierInfo" NOT LIKE 'null%%'
                  AND e."modifierInfo" != ''
            """)
            return {row["typeID"] for row in cur.fetchall()}

