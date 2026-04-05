"""FittingStatsService — orchestrator combining all fitting stat modules."""

import hashlib
import json
import logging
from typing import List, Dict, Optional

from psycopg2.extras import RealDictCursor

from app.services.fitting_service import FittingService, FittingItem
from app.services.dogma.engine import DogmaEngine
from app.services.skill_prerequisites_service import (
    SkillPrerequisitesService, SKILL_LEVEL_ATTRS, SP_PER_LEVEL,
)

from .models import (
    FittingStatsRequest, FittingStatsResponse,
    NavigationStats, CapacitorStats,
    TargetingStats, RepairStats,
    ModuleDetailItem, FittingSkillRequirement,
)
from .constants import (
    ATTR_HI_SLOTS, ATTR_MED_SLOTS, ATTR_LOW_SLOTS, ATTR_RIG_SLOTS,
    ATTR_POWER_OUTPUT, ATTR_CPU_OUTPUT, ATTR_CALIBRATION_OUTPUT,
    ATTR_TURRET_SLOTS, ATTR_LAUNCHER_SLOTS,
    ATTR_CAP_CAPACITY, ATTR_CAP_RECHARGE,
    ATTR_DRONE_CAPACITY, ATTR_DRONE_BANDWIDTH,
    ATTR_MAX_TARGET_RANGE, ATTR_SCAN_RES, ATTR_MAX_LOCKED,
    ATTR_SCAN_RADAR, ATTR_SCAN_LADAR, ATTR_SCAN_MAGNETO, ATTR_SCAN_GRAVI,
    ATTR_WARP_SPEED_MULT, ATTR_MASS,
    ATTR_MAX_VELOCITY, ATTR_AGILITY, ATTR_SIG_RADIUS,
    ATTR_SHIELD_HP, ATTR_ARMOR_HP, ATTR_HULL_HP,
    ATTR_SHIELD_EM_RESIST, ATTR_SHIELD_THERMAL_RESIST,
    ATTR_SHIELD_KINETIC_RESIST, ATTR_SHIELD_EXPLOSIVE_RESIST,
    ATTR_ARMOR_EM_RESIST, ATTR_ARMOR_THERMAL_RESIST,
    ATTR_ARMOR_KINETIC_RESIST, ATTR_ARMOR_EXPLOSIVE_RESIST,
    ATTR_HULL_EM_RESIST, ATTR_HULL_THERMAL_RESIST,
    ATTR_HULL_KINETIC_RESIST, ATTR_HULL_EXPLOSIVE_RESIST,
    ATTR_MAX_ACTIVE_DRONES,
    ATTR_DRONE_CONTROL_RANGE, ATTR_CARGO_CAPACITY,
    ATTR_CAP_NEED, ATTR_DURATION, ATTR_RATE_OF_FIRE,
    ATTR_CPU_NEED, ATTR_POWER_NEED,
    ATTR_SHIELD_BOOST_AMOUNT, ATTR_ARMOR_REPAIR_AMOUNT, ATTR_HULL_REPAIR_AMOUNT,
    EFFECT_TURRET_FITTED, EFFECT_LAUNCHER_FITTED,
    DEFAULT_FITTING_SKILL_LEVEL,
    DRONE_RANGE_SKILLS,
)
from .calculations import (
    calculate_capacitor, calculate_align_time, calculate_warp_time,
    calculate_lock_time, calculate_scanability,
    calculate_turret_hit_chance, calculate_missile_application,
    calculate_effective_rep, calculate_sustainable_tank,
)
from .models import AppliedDPS
from .constants import TARGET_PROFILES, DAMAGE_PROFILES
from .offense import OffenseMixin
from .defense import DefenseMixin
from .navigation import NavigationMixin
from .resources import ResourcesMixin
from .validation import ValidationMixin

logger = logging.getLogger(__name__)


class FittingStatsService(
    OffenseMixin,
    DefenseMixin,
    NavigationMixin,
    ResourcesMixin,
    ValidationMixin,
):
    """Calculate combined fitting stats."""

    @staticmethod
    def _is_module_active(flag: int, module_states: Optional[Dict[int, str]]) -> bool:
        """Check if a module at the given flag is actively contributing (active or overheated).

        Active modules drain cap, deal DPS, and provide reps.
        Returns True by default (backward compat when module_states is None).
        """
        if module_states is None:
            return True
        state = module_states.get(flag, "active")
        return state in ("active", "overheated")

    @staticmethod
    def _is_module_online(flag: int, module_states: Optional[Dict[int, str]]) -> bool:
        """Check if a module at the given flag is online (uses CPU/PG but may not be active).

        Online modules consume CPU and powergrid but do not drain cap or deal DPS.
        Returns True by default (backward compat when module_states is None).
        """
        if module_states is None:
            return True
        state = module_states.get(flag, "active")
        return state in ("online", "active", "overheated")

    def __init__(self, db, redis=None):
        self.db = db
        self.redis = redis
        self.fitting_service = FittingService(db, redis)

    # Cache TTL: 5 minutes — SDE is static, character skills sync every 15 min
    CACHE_TTL = 300

    @staticmethod
    def _build_cache_key(req: FittingStatsRequest) -> str:
        """Build a deterministic Redis cache key from a fitting stats request."""
        # Serialize request to canonical JSON (sorted keys for determinism)
        canonical = req.model_dump_json()
        key_hash = hashlib.sha256(canonical.encode()).hexdigest()[:16]
        return f"fitting-stats:{key_hash}"

    def _get_cached(self, key: str) -> Optional[FittingStatsResponse]:
        """Try to load cached fitting stats from Redis."""
        if not self.redis:
            return None
        try:
            cached = self.redis.get(key)
            if cached:
                return FittingStatsResponse.model_validate_json(cached)
        except Exception:
            pass  # Redis down or deserialization error — continue without cache
        return None

    def _set_cached(self, key: str, response: FittingStatsResponse):
        """Cache fitting stats response in Redis."""
        if not self.redis:
            return
        try:
            self.redis.set(key, response.model_dump_json(), ex=self.CACHE_TTL)
        except Exception:
            pass  # Redis down — continue without cache

    def calculate_stats(self, req: FittingStatsRequest) -> FittingStatsResponse:
        """Calculate combined stats for a fitting.

        Results are cached in Redis for 5 minutes. Identical fitting requests
        (same ship, modules, skills, charges, etc.) skip the full Dogma pipeline.
        """
        # Check Redis cache first
        cache_key = self._build_cache_key(req)
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        # 1. Get ship info
        ship_info = self._get_ship_info(req.ship_type_id)

        # 2. Get base ship attributes (includes mass/cargo from invTypes)
        base_ship_attrs = self._get_ship_attributes(req.ship_type_id)

        # 2.5. Load character skills if character_id provided
        skill_levels = None
        skill_source = "all_v"
        character_id = req.character_id
        if character_id:
            skill_levels, char_name = self._load_character_skills(character_id)
            if skill_levels:
                skill_source = char_name or f"Character {character_id}"

        # 2.6. Load character implants if requested
        implant_type_ids = []
        active_implants_list = []
        if character_id and req.include_implants:
            implant_type_ids = self._load_character_implants(character_id)
            if implant_type_ids:
                active_implants_list = self._resolve_implant_names(implant_type_ids)

        # 2.7. Load booster type_ids if provided
        booster_type_ids = []
        if req.boosters:
            booster_type_ids = [b.type_id for b in req.boosters]

        # 3. Run Dogma engine for modified attributes
        # Only process items in actual fitting slots (not drone bay, cargo, etc.)
        FITTING_FLAGS = set(range(11, 35)) | set(range(92, 100))  # low/mid/hi + rigs
        module_type_ids = []
        module_flags = []
        for item in req.items:
            if item.flag not in FITTING_FLAGS:
                continue
            for _ in range(item.quantity):
                module_type_ids.append(item.type_id)
                module_flags.append(item.flag)

        # Collect unique charge type IDs for Dogma engine
        charge_type_ids = list(set(req.charges.values())) if req.charges else []

        dogma = DogmaEngine(self.db)
        modified_ship_attrs, modified_module_attrs, charge_bonuses, modified_charges = dogma.calculate_modified_attributes(
            req.ship_type_id, module_type_ids, skill_levels=skill_levels,
            simulation_mode=req.simulation_mode,
            implant_type_ids=implant_type_ids if implant_type_ids else None,
            module_flags=module_flags,
            flag_states=req.module_states,
            booster_type_ids=booster_type_ids if booster_type_ids else None,
            mode_type_id=req.mode_type_id,
            charge_type_ids=charge_type_ids if charge_type_ids else None,
        )

        # 3.1. Resolve T3D mode name if mode_type_id provided
        mode_name = None
        if req.mode_type_id:
            with self.db.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute('''
                    SELECT "typeName" FROM "invTypes" WHERE "typeID" = %s
                ''', (req.mode_type_id,))
                row = cur.fetchone()
                if row:
                    mode_name = row["typeName"]

        # Merge: Dogma values take precedence, keep base values for attrs
        # not in dgmTypeAttributes (mass/cargo from invTypes)
        ship_attrs = {**base_ship_attrs, **modified_ship_attrs}

        # 3.5. Add fitted module mass to ship mass (EVE adds all module masses)
        ship_attrs = self._add_module_mass(ship_attrs, req.items)

        # 3.6. Apply fleet boosts (command burst buffs) if provided
        active_boosts_list = None
        if req.fleet_boosts:
            from .fleet_boosts import apply_fleet_boosts, BUFF_DEFINITIONS
            boost_inputs = [{"buff_id": b.buff_id, "value": b.value} for b in req.fleet_boosts]
            ship_attrs = apply_fleet_boosts(ship_attrs, boost_inputs)
            active_boosts_list = []
            for b in req.fleet_boosts:
                defn = BUFF_DEFINITIONS.get(b.buff_id)
                if defn:
                    active_boosts_list.append({
                        "buff_id": b.buff_id,
                        "name": defn["name"],
                        "value": b.value,
                    })

        # 3.7. Apply projected effects (webs, paints, neuts, remote reps) if provided
        projected_summary = None
        incoming_rep_shield = 0.0
        incoming_rep_armor = 0.0
        cap_drain_external = 0.0
        if req.projected_effects:
            from .projected import apply_projected_effects
            proj_inputs = [
                {"effect_type": p.effect_type, "strength": p.strength, "count": p.count}
                for p in req.projected_effects
            ]
            proj_result = apply_projected_effects(ship_attrs, proj_inputs)
            ship_attrs = proj_result["modified_attrs"]
            cap_drain_external = proj_result["cap_drain_per_s"]
            incoming_rep_shield = proj_result["incoming_rep_shield"]
            incoming_rep_armor = proj_result["incoming_rep_armor"]
            projected_summary = proj_result["summary"]

        # 4. Calculate slot usage
        slots = self._calc_slot_usage(ship_attrs, req.items)

        # 5. Calculate resource usage (PG/CPU/calibration/hardpoints/drones)
        resources = self._calc_resource_usage(ship_attrs, req.items, modified_module_attrs,
                                               module_states=req.module_states)

        # 6. Calculate DPS (with Dogma-modified module attributes)
        drone_bw_total = ship_attrs.get(ATTR_DRONE_BANDWIDTH, 0)
        max_active_drones = int(ship_attrs.get(ATTR_MAX_ACTIVE_DRONES, 5))
        offense = self._calc_offense(req, modified_module_attrs, drone_bw_total, max_active_drones,
                                     skill_levels=skill_levels, charge_bonuses=charge_bonuses)

        # 6.5. Detect Triglavian spool-up weapons and calculate spool DPS variants
        if offense.weapon_dps > 0 and modified_module_attrs:
            from .spool import is_spool_weapon, calculate_spool_dps, ATTR_SPOOL_BONUS_PER_CYCLE, ATTR_SPOOL_MAX_BONUS
            from .models import SpoolStats
            for item in req.items:
                if not (27 <= item.flag <= 34):
                    continue
                if not self._is_module_active(item.flag, req.module_states):
                    continue
                m_attrs = modified_module_attrs.get(item.type_id, {})
                if is_spool_weapon(m_attrs):
                    bonus_per_cycle = m_attrs.get(ATTR_SPOOL_BONUS_PER_CYCLE, 0)
                    max_bonus = m_attrs.get(ATTR_SPOOL_MAX_BONUS, 0)
                    cycle_time_ms = m_attrs.get(ATTR_RATE_OF_FIRE, 0)
                    spool_result = calculate_spool_dps(
                        offense.weapon_dps, bonus_per_cycle, max_bonus, cycle_time_ms
                    )
                    offense.spool = SpoolStats(**spool_result)
                    break  # Only one spool weapon type per fit

        # 6.7. Calculate fighter DPS (carriers/supercarriers)
        fighter_total_dps = 0.0
        fighter_details_list = []
        if req.fighters:
            from .fighters import load_fighter_data, calculate_fighter_dps
            from .models import FighterDPSStats
            fighter_data = load_fighter_data(
                self.db,
                [{"type_id": f.type_id, "quantity": f.quantity} for f in req.fighters],
            )
            for fd in fighter_data:
                result = calculate_fighter_dps(fd["attrs"], fd["quantity"])
                fighter_total_dps += result["total_dps"]
                fighter_details_list.append(FighterDPSStats(
                    type_name=fd["type_name"],
                    type_id=fd["type_id"],
                    squadron_size=result["squadron_size"],
                    squadrons=fd["quantity"],
                    dps_per_squadron=result["dps_per_squadron"],
                    total_dps=result["total_dps"],
                    damage_type=result["damage_type"],
                ))
            offense.fighter_dps = round(fighter_total_dps, 1)
            offense.fighter_details = fighter_details_list if fighter_details_list else None
            offense.total_dps = round(offense.weapon_dps + offense.drone_dps + fighter_total_dps, 1)

        # 7. Calculate EHP locally via Dogma-modified ship attributes
        defense = self._calc_defense_local(ship_attrs)

        # 8. Capacitor simulation (with Dogma-modified module attributes)
        capacitor = self._calc_capacitor(ship_attrs, req.items, modified_module_attrs,
                                          charges=req.charges,
                                          module_states=req.module_states)

        # 8.5. Apply propmod effects (AB/MWD velocity boost, mass addition, sig bloom).
        # EVE's fitting window shows stats with propmod active by default.
        ship_attrs = self._apply_propmod_effects(ship_attrs, req.items, skill_levels=skill_levels)

        # 8.6. NSA scan resolution: handled by Dogma engine via effect 6567's
        # modifierInfo (ItemModifier, attr 564 PostPercent from attr 566).
        # Unlike propmods, NSA effects ARE in the SDE — no manual application needed.

        # 9. Navigation stats (uses Dogma-modified velocity/agility/mass)
        mass = ship_attrs.get(ATTR_MASS, 0)
        agility = ship_attrs.get(ATTR_AGILITY, 0)
        warp_mult = ship_attrs.get(ATTR_WARP_SPEED_MULT, 1.0)
        navigation = NavigationStats(
            max_velocity=ship_attrs.get(ATTR_MAX_VELOCITY, 0),
            align_time=calculate_align_time(mass, agility),
            warp_speed=round(warp_mult, 2),
            warp_time_5au=calculate_warp_time(warp_mult, 5.0),
            warp_time_20au=calculate_warp_time(warp_mult, 20.0),
            agility=round(agility, 4),
            signature_radius=ship_attrs.get(ATTR_SIG_RADIUS, 0),
            mass=mass,
            cargo_capacity=ship_attrs.get(ATTR_CARGO_CAPACITY, 0),
        )

        # 10. Targeting stats
        targeting = self._calc_targeting(ship_attrs)
        drone_range = ship_attrs.get(ATTR_DRONE_CONTROL_RANGE, 0)
        for skill_id, bonus_per_level in DRONE_RANGE_SKILLS.items():
            if skill_levels is not None:
                level = skill_levels.get(skill_id, 0)
            else:
                level = DEFAULT_FITTING_SKILL_LEVEL
            drone_range += bonus_per_level * level
        targeting.drone_control_range = drone_range

        # 11. Repairs (active + passive shield regen, using Dogma-modified module attrs)
        repairs = self._calc_repairs(req, ship_attrs, modified_module_attrs=modified_module_attrs)

        # 11.2. Calculate cap-limited sustainable tank
        rep_cap_per_sec = 0.0
        for item in req.items:
            if not self._is_module_active(item.flag, req.module_states):
                continue
            m_attrs = modified_module_attrs.get(item.type_id, {})
            # Shield boosters: attr 68 (shieldBoostAmount) means it's a shield repper
            # Armor repairers: attr 84 (armorDamageAmount) means it's an armor repper
            has_rep = m_attrs.get(68, 0) > 0 or m_attrs.get(84, 0) > 0
            if has_rep:
                cap_need = m_attrs.get(6, 0)  # attr 6 = capNeed
                duration = m_attrs.get(73, 0)  # attr 73 = duration in ms
                if duration > 0 and cap_need > 0:
                    rep_cap_per_sec += (cap_need / (duration / 1000.0)) * item.quantity

        sustainable = calculate_sustainable_tank(
            raw_shield_rep=repairs.shield_rep,
            raw_armor_rep=repairs.armor_rep,
            cap_stable=capacitor.stable,
            cap_stable_pct=capacitor.stable_percent,
            rep_cap_need_per_sec=rep_cap_per_sec,
            cap_recharge_rate=capacitor.peak_recharge_rate,
        )
        repairs.sustained_shield_rep = sustainable["shield_sustained"]
        repairs.sustained_armor_rep = sustainable["armor_sustained"]

        # 11.5. Mark overheated stats when any module is overheated.
        # The Dogma engine already applies overload bonuses (effectCategoryID 5)
        # to module attrs for overheated modules, so the computed DPS/rep values
        # already include overload bonuses. We tag them in the response.
        has_overheated = req.module_states and any(
            s == "overheated" for s in req.module_states.values()
        )
        if has_overheated:
            offense.overheated_weapon_dps = offense.weapon_dps
            offense.overheated_total_dps = offense.total_dps
            if repairs.shield_rep > 0 or repairs.armor_rep > 0:
                repairs.overheated_shield_rep = repairs.shield_rep
                repairs.overheated_armor_rep = repairs.armor_rep

        # 12. Applied DPS (if target profile specified)
        applied_dps = None
        if req.target_profile and req.target_profile in TARGET_PROFILES:
            applied_dps = self._calc_applied_dps(
                offense, modified_module_attrs, req.items,
                req.target_profile, ship_attrs, req.charges,
                target_projected=req.target_projected,
                modified_charges=modified_charges,
            )

            # 12.5. If spool stats exist, calculate applied DPS spool variants
            #        Scale paper spool min/max/avg by the application factor
            if offense.spool and applied_dps and offense.total_dps > 0:
                from .models import SpoolStats
                app_factor = applied_dps.total_applied_dps / offense.total_dps
                applied_dps.spool_applied = SpoolStats(
                    min_dps=round(offense.spool.min_dps * app_factor, 1),
                    max_dps=round(offense.spool.max_dps * app_factor, 1),
                    avg_dps=round(offense.spool.avg_dps * app_factor, 1),
                    cycles_to_max=offense.spool.cycles_to_max,
                    time_to_max_s=offense.spool.time_to_max_s,
                )

        # 13. Validate fitting constraints
        violations = self._validate_fitting(ship_attrs, req.items, modified_module_attrs)

        # 14. Build enriched module details
        module_details = self._build_module_details(
            req.items, modified_module_attrs, req.charges
        )

        # 15. Build required skills list
        required_skills = self._build_required_skills(
            req.ship_type_id, req.items, skill_levels
        )

        # 16. Determine which module flags are activatable (have cycle time)
        activatable_flags = self._get_activatable_flags(req.items)

        response = FittingStatsResponse(
            ship=ship_info,
            slots=slots,
            resources=resources,
            offense=offense,
            defense=defense,
            capacitor=capacitor,
            navigation=navigation,
            targeting=targeting,
            repairs=repairs,
            applied_dps=applied_dps,
            violations=violations,
            module_details=module_details,
            required_skills=required_skills,
            skill_source=skill_source,
            character_id=character_id,
            active_implants=active_implants_list,
            mode=mode_name,
            active_boosts=active_boosts_list,
            projected_effects_summary=projected_summary,
            activatable_flags=activatable_flags,
        )

        # Cache the result for subsequent identical requests
        self._set_cached(cache_key, response)

        return response

    def _load_character_skills(self, character_id: int) -> tuple:
        """Load character skills from DB.

        Returns: (skill_levels dict {skill_type_id: level}, character_name)
        Returns ({}, None) if character not found.
        """
        with self.db.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT character_name FROM characters WHERE character_id = %s
            """, (character_id,))
            row = cur.fetchone()
            if not row:
                return {}, None
            char_name = row["character_name"]

            cur.execute("""
                SELECT skill_id, trained_skill_level
                FROM character_skills
                WHERE character_id = %s
            """, (character_id,))
            skill_levels = {r["skill_id"]: r["trained_skill_level"] for r in cur.fetchall()}

        return skill_levels, char_name

    def _load_character_implants(self, character_id: int) -> List[int]:
        """Load character implant type_ids from DB."""
        with self.db.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT implant_type_id FROM character_implants
                WHERE character_id = %s ORDER BY slot
            """, (character_id,))
            return [r["implant_type_id"] for r in cur.fetchall()]

    def _resolve_implant_names(self, implant_type_ids: List[int]) -> list:
        """Resolve implant type_ids to ActiveImplant models."""
        from .models import ActiveImplant
        with self.db.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT t."typeID" as type_id, t."typeName" as type_name,
                       COALESCE(s.value, 0)::int as slot
                FROM "invTypes" t
                LEFT JOIN (
                    SELECT "typeID", COALESCE("valueInt","valueFloat") as value
                    FROM "dgmTypeAttributes" WHERE "attributeID" = 331
                ) s ON s."typeID" = t."typeID"
                WHERE t."typeID" = ANY(%s)
                ORDER BY slot
            """, (list(implant_type_ids),))
            return [
                ActiveImplant(type_id=r["type_id"], type_name=r["type_name"], slot=r["slot"])
                for r in cur.fetchall()
            ]

    def _get_ship_info(self, ship_type_id: int) -> dict:
        """Get ship name and group from SDE."""
        with self.db.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT t."typeID", t."typeName",
                       g."groupName"
                FROM "invTypes" t
                JOIN "invGroups" g ON t."groupID" = g."groupID"
                WHERE t."typeID" = %s
            """, (ship_type_id,))
            row = cur.fetchone()
            if not row:
                return {"type_id": ship_type_id, "name": "Unknown", "group_name": "Unknown"}
            return {
                "type_id": row["typeID"],
                "name": row["typeName"],
                "group_name": row["groupName"],
            }

    def _get_ship_attributes(self, ship_type_id: int) -> dict:
        """Get ship attributes from SDE as {attr_id: value}."""
        attr_ids = [
            ATTR_HI_SLOTS, ATTR_MED_SLOTS, ATTR_LOW_SLOTS, ATTR_RIG_SLOTS,
            ATTR_POWER_OUTPUT, ATTR_CPU_OUTPUT,
            ATTR_MAX_VELOCITY, ATTR_AGILITY, ATTR_SIG_RADIUS,
            ATTR_CALIBRATION_OUTPUT, ATTR_TURRET_SLOTS, ATTR_LAUNCHER_SLOTS,
            ATTR_CAP_CAPACITY, ATTR_CAP_RECHARGE,
            ATTR_DRONE_CAPACITY, ATTR_DRONE_BANDWIDTH,
            ATTR_MAX_TARGET_RANGE, ATTR_SCAN_RES, ATTR_MAX_LOCKED,
            ATTR_SCAN_RADAR, ATTR_SCAN_LADAR, ATTR_SCAN_MAGNETO, ATTR_SCAN_GRAVI,
            ATTR_WARP_SPEED_MULT, ATTR_MASS, ATTR_MAX_ACTIVE_DRONES,
            ATTR_CARGO_CAPACITY, ATTR_DRONE_CONTROL_RANGE,
            # Defense attributes
            ATTR_SHIELD_HP, ATTR_ARMOR_HP, ATTR_HULL_HP,
            ATTR_SHIELD_EM_RESIST, ATTR_SHIELD_THERMAL_RESIST,
            ATTR_SHIELD_KINETIC_RESIST, ATTR_SHIELD_EXPLOSIVE_RESIST,
            ATTR_ARMOR_EM_RESIST, ATTR_ARMOR_THERMAL_RESIST,
            ATTR_ARMOR_KINETIC_RESIST, ATTR_ARMOR_EXPLOSIVE_RESIST,
            ATTR_HULL_EM_RESIST, ATTR_HULL_THERMAL_RESIST,
            ATTR_HULL_KINETIC_RESIST, ATTR_HULL_EXPLOSIVE_RESIST,
        ]
        with self.db.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT "attributeID",
                       COALESCE("valueFloat", "valueInt"::float) as value
                FROM "dgmTypeAttributes"
                WHERE "typeID" = %s
                  AND "attributeID" = ANY(%s)
            """, (ship_type_id, attr_ids))
            attrs = {row["attributeID"]: row["value"] for row in cur.fetchall()}

            # Mass is stored in invTypes.mass, not dgmTypeAttributes
            if ATTR_MASS not in attrs or attrs[ATTR_MASS] == 0:
                cur.execute("""
                    SELECT "mass" FROM "invTypes" WHERE "typeID" = %s
                """, (ship_type_id,))
                mass_row = cur.fetchone()
                if mass_row and mass_row["mass"]:
                    attrs[ATTR_MASS] = float(mass_row["mass"])

            # Cargo capacity stored in invTypes.capacity, not dgmTypeAttributes
            if ATTR_CARGO_CAPACITY not in attrs or attrs[ATTR_CARGO_CAPACITY] == 0:
                cur.execute("""
                    SELECT "capacity" FROM "invTypes" WHERE "typeID" = %s
                """, (ship_type_id,))
                cap_row = cur.fetchone()
                if cap_row and cap_row["capacity"]:
                    attrs[ATTR_CARGO_CAPACITY] = float(cap_row["capacity"])

            # Default drone control range is 20km for all ships
            if ATTR_DRONE_CONTROL_RANGE not in attrs:
                attrs[ATTR_DRONE_CONTROL_RANGE] = 20000.0

            return attrs

    def _get_activatable_flags(self, items: list) -> list:
        """Return flags of modules that have an activation cycle (durationAttributeID)."""
        type_ids = list({item.type_id for item in items if item.flag != 87})  # exclude drones
        if not type_ids:
            return []
        with self.db.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('''
                SELECT DISTINCT te."typeID"
                FROM "dgmTypeEffects" te
                JOIN "dgmEffects" e ON e."effectID" = te."effectID"
                WHERE te."typeID" = ANY(%s) AND e."durationAttributeID" IS NOT NULL
            ''', (type_ids,))
            activatable_types = {row["typeID"] for row in cur.fetchall()}
        return [item.flag for item in items if item.type_id in activatable_types]

    def _build_module_details(
        self,
        items: List[FittingItem],
        modified_module_attrs: Dict[int, Dict[int, float]],
        charges: Optional[Dict[int, int]] = None,
    ) -> List[ModuleDetailItem]:
        """Build enriched per-module detail list for the response.

        Uses Dogma-modified attributes for CPU/PG/cap values.
        Resolves type names and charge names from SDE.
        """
        if not items:
            return []

        # Classify flags into slot types
        def _slot_type(flag: int) -> str:
            if 27 <= flag <= 34:
                return "high"
            if 19 <= flag <= 26:
                return "mid"
            if 11 <= flag <= 18:
                return "low"
            if 92 <= flag <= 99:
                return "rig"
            if flag == 87:
                return "drone"
            return "other"

        # Collect all type IDs we need to resolve names for
        all_type_ids = list(set(i.type_id for i in items))
        charge_type_ids = list(set(charges.values())) if charges else []
        resolve_ids = list(set(all_type_ids + charge_type_ids))

        with self.db.cursor(cursor_factory=RealDictCursor) as cur:
            # Resolve type names
            cur.execute("""
                SELECT "typeID", "typeName"
                FROM "invTypes"
                WHERE "typeID" = ANY(%s)
            """, (resolve_ids,))
            type_names = {row["typeID"]: row["typeName"] for row in cur.fetchall()}

            # Get turret/launcher effects for hardpoint_type
            cur.execute("""
                SELECT "typeID", "effectID"
                FROM "dgmTypeEffects"
                WHERE "typeID" = ANY(%s)
                  AND "effectID" IN (%s, %s)
            """, (all_type_ids, EFFECT_TURRET_FITTED, EFFECT_LAUNCHER_FITTED))
            hardpoint_map: Dict[int, str] = {}
            for row in cur.fetchall():
                if row["effectID"] == EFFECT_TURRET_FITTED:
                    hardpoint_map[row["typeID"]] = "turret"
                elif row["effectID"] == EFFECT_LAUNCHER_FITTED:
                    hardpoint_map[row["typeID"]] = "launcher"

        details = []
        for item in items:
            slot = _slot_type(item.flag)
            if slot == "other":
                continue

            # Use Dogma-modified attrs (already includes all ship/skill bonuses)
            attrs = modified_module_attrs.get(item.type_id, {})
            cpu = round(attrs.get(ATTR_CPU_NEED, 0), 1)
            pg = round(attrs.get(ATTR_POWER_NEED, 0), 1)
            pg = round(pg, 1)
            cap_need = attrs.get(ATTR_CAP_NEED, 0)
            duration = attrs.get(ATTR_DURATION, 0)
            rof = attrs.get(ATTR_RATE_OF_FIRE, 0)
            cycle_time_ms = max(duration, rof)

            cap_per_sec = 0.0
            if cap_need > 0 and cycle_time_ms > 0:
                cap_per_sec = round(cap_need / (cycle_time_ms / 1000.0), 1)

            # Resolve charge for this slot
            charge_tid = charges.get(item.flag) if charges else None
            charge_name = type_names.get(charge_tid) if charge_tid else None

            details.append(ModuleDetailItem(
                type_id=item.type_id,
                type_name=type_names.get(item.type_id, f"Type {item.type_id}"),
                slot_type=slot,
                flag=item.flag,
                quantity=item.quantity,
                cpu=cpu,
                pg=pg,
                cap_need=round(cap_need, 1),
                cycle_time_ms=round(cycle_time_ms, 1),
                cap_per_sec=cap_per_sec,
                charge_type_id=charge_tid,
                charge_name=charge_name,
                hardpoint_type=hardpoint_map.get(item.type_id),
            ))

        # Sort by slot order: high → mid → low → rig → drone
        slot_order = {"high": 0, "mid": 1, "low": 2, "rig": 3, "drone": 4}
        details.sort(key=lambda d: (slot_order.get(d.slot_type, 9), d.flag))
        return details

    def _build_required_skills(
        self,
        ship_type_id: int,
        items: List[FittingItem],
        skill_levels: Optional[Dict[int, int]] = None,
    ) -> List[FittingSkillRequirement]:
        """Build list of all skills required to use every item in the fitting.

        Batch-queries SDE for direct skill requirements, then uses
        SkillPrerequisitesService for recursive prerequisite chains.
        Merges to keep highest required level per skill_id.
        """
        # Collect all unique type_ids (ship + modules/drones)
        all_type_ids = list(set([ship_type_id] + [i.type_id for i in items]))

        # All skill/level attribute IDs we need
        all_attr_ids = []
        for skill_attr, level_attr in SKILL_LEVEL_ATTRS:
            all_attr_ids.extend([skill_attr, level_attr])

        with self.db.cursor(cursor_factory=RealDictCursor) as cur:
            # Batch query: get all skill requirement attrs for all items at once
            cur.execute("""
                SELECT "typeID", "attributeID",
                       COALESCE("valueFloat", "valueInt")::float as value
                FROM "dgmTypeAttributes"
                WHERE "typeID" = ANY(%s)
                  AND "attributeID" = ANY(%s)
            """, (all_type_ids, all_attr_ids))

            # Build per-type attr map
            type_attrs: Dict[int, Dict[int, float]] = {}
            for row in cur.fetchall():
                tid = row["typeID"]
                if tid not in type_attrs:
                    type_attrs[tid] = {}
                type_attrs[tid][row["attributeID"]] = row["value"]

            # Resolve type names for required_by
            cur.execute("""
                SELECT "typeID", "typeName"
                FROM "invTypes"
                WHERE "typeID" = ANY(%s)
            """, (all_type_ids,))
            type_names = {row["typeID"]: row["typeName"] for row in cur.fetchall()}

        # Extract direct skill requirements per item
        # skill_id → {required_level, required_by set}
        skill_map: Dict[int, Dict] = {}  # skill_id → {"level": int, "required_by": set}

        for type_id in all_type_ids:
            attrs = type_attrs.get(type_id, {})
            item_name = type_names.get(type_id, f"Type {type_id}")

            for skill_attr, level_attr in SKILL_LEVEL_ATTRS:
                if skill_attr in attrs and level_attr in attrs:
                    skill_id = int(attrs[skill_attr])
                    level = int(attrs[level_attr])
                    if skill_id > 0 and level > 0:
                        if skill_id not in skill_map:
                            skill_map[skill_id] = {"level": level, "required_by": {item_name}}
                        else:
                            skill_map[skill_id]["level"] = max(skill_map[skill_id]["level"], level)
                            skill_map[skill_id]["required_by"].add(item_name)

        if not skill_map:
            return []

        # Use SkillPrerequisitesService to get recursive prerequisites
        prereq_svc = SkillPrerequisitesService(self.db)

        # For each direct skill requirement, get its full prerequisite chain
        all_flat: Dict[int, Dict] = {}  # skill_id → {"level", "required_by", "rank", "sp_required"}
        for skill_id, info in list(skill_map.items()):
            flat = prereq_svc.get_flat_prerequisites(skill_id, info["level"])
            for sid, req in flat.items():
                if sid not in all_flat:
                    all_flat[sid] = {
                        "level": req.level,
                        "required_by": set(info["required_by"]),
                        "rank": req.rank,
                        "skill_name": req.skill_name,
                    }
                else:
                    all_flat[sid]["level"] = max(all_flat[sid]["level"], req.level)
                    all_flat[sid]["required_by"].update(info["required_by"])

        # Build result list
        result = []
        for skill_id, info in all_flat.items():
            level = info["level"]
            rank = info["rank"]
            sp = int(SP_PER_LEVEL.get(level, 0) * rank)

            trained = None
            if skill_levels is not None:
                trained = skill_levels.get(skill_id, 0)

            result.append(FittingSkillRequirement(
                skill_id=skill_id,
                skill_name=info["skill_name"],
                required_level=level,
                trained_level=trained,
                rank=rank,
                sp_required=sp,
                required_by=sorted(info["required_by"]),
            ))

        # Sort: undertrained/missing first, then by skill name
        def sort_key(s: FittingSkillRequirement):
            if s.trained_level is not None:
                met = 1 if s.trained_level >= s.required_level else 0
            else:
                met = 0  # unknown = show first
            return (met, s.skill_name)

        result.sort(key=sort_key)
        return result

    def _calc_capacitor(self, ship_attrs: dict, items: List[FittingItem],
                        modified_module_attrs: Optional[Dict[int, Dict[int, float]]] = None,
                        charges: Optional[Dict[int, int]] = None,
                        module_states: Optional[Dict[int, str]] = None) -> CapacitorStats:
        """Calculate capacitor stats using Dogma-modified module attributes.

        Uses modified_module_attrs from the Dogma engine which include ship bonuses,
        skill bonuses, and module interaction effects on cap_need/duration/rof.
        Falls back to SDE base values if modified attrs not available.

        Cap boosters: if a module's loaded charge has ATTR_CAP_BOOSTER_BONUS (67),
        it injects GJ per cycle instead of draining.

        Only active/overheated modules contribute to cap drain. Online-only and
        offline modules are excluded.
        """
        from .constants import ATTR_CAP_BOOSTER_BONUS, CAP_SIM_EXCLUDED_GROUPS

        cap_capacity = ship_attrs.get(ATTR_CAP_CAPACITY, 0)
        cap_recharge_ms = ship_attrs.get(ATTR_CAP_RECHARGE, 0)

        if not items:
            return calculate_capacitor(cap_capacity, cap_recharge_ms, 0)

        # Use Dogma-modified module attrs if available, otherwise query SDE
        if modified_module_attrs is None:
            module_type_ids = list(set(i.type_id for i in items))
            cap_attr_ids = [ATTR_CAP_NEED, ATTR_DURATION, ATTR_RATE_OF_FIRE]

            with self.db.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT "typeID", "attributeID",
                           COALESCE("valueFloat", "valueInt"::float) as value
                    FROM "dgmTypeAttributes"
                    WHERE "typeID" = ANY(%s)
                      AND "attributeID" = ANY(%s)
                """, (module_type_ids, cap_attr_ids))

                mod_attrs: Dict[int, Dict[int, float]] = {}
                for row in cur.fetchall():
                    tid = row["typeID"]
                    if tid not in mod_attrs:
                        mod_attrs[tid] = {}
                    mod_attrs[tid][row["attributeID"]] = row["value"]
        else:
            mod_attrs = modified_module_attrs

        # Identify activation-required modules to exclude from cap drain.
        # Propmods (groupID 46: AB/MWD) and WCS (groupID 315) drain cap only
        # when manually activated — they should not be in the passive cap sim.
        fitted_type_ids = list(set(
            i.type_id for i in items if i.flag != 5 and i.flag != 87
        ))
        excluded_type_ids: set = set()
        if fitted_type_ids:
            excluded_group_list = list(CAP_SIM_EXCLUDED_GROUPS)
            with self.db.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT "typeID"
                    FROM "invTypes"
                    WHERE "typeID" = ANY(%s) AND "groupID" = ANY(%s)
                """, (fitted_type_ids, excluded_group_list))
                excluded_type_ids = {row["typeID"] for row in cur.fetchall()}

        # Resolve cap booster charge attributes if charges are loaded
        charge_attrs: Dict[int, Dict[int, float]] = {}
        if charges:
            charge_type_ids = list(set(charges.values()))
            if charge_type_ids:
                with self.db.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT "typeID", "attributeID",
                               COALESCE("valueFloat", "valueInt"::float) as value
                        FROM "dgmTypeAttributes"
                        WHERE "typeID" = ANY(%s)
                          AND "attributeID" = %s
                    """, (charge_type_ids, ATTR_CAP_BOOSTER_BONUS))
                    for row in cur.fetchall():
                        tid = row["typeID"]
                        if tid not in charge_attrs:
                            charge_attrs[tid] = {}
                        charge_attrs[tid][row["attributeID"]] = row["value"]

        # Build per-module drain list for discrete simulation
        total_cap_per_sec = 0.0
        module_drains = []  # [(cap_need_gj, cycle_time_ms), ...]

        for item in items:
            # Only fitted modules (not cargo/drones)
            if item.flag == 5 or item.flag == 87:
                continue
            # Skip non-active modules — only active/overheated modules drain cap
            if not self._is_module_active(item.flag, module_states):
                continue
            # Skip activation-required modules (propmods, WCS) — passive sim only
            if item.type_id in excluded_type_ids:
                continue
            attrs = mod_attrs.get(item.type_id, {})
            duration = attrs.get(ATTR_DURATION, 0)
            rate_of_fire = attrs.get(ATTR_RATE_OF_FIRE, 0)
            cycle_time_ms = max(duration, rate_of_fire)
            if cycle_time_ms <= 0:
                continue

            # Check if this module has a loaded cap booster charge.
            # EVE's fitting window shows stability WITHOUT cap booster injection
            # (charges require manual loading). Include the module's own cap drain
            # but do NOT inject GJ per cycle into the stability simulation.
            charge_type = charges.get(item.flag) if charges else None
            if charge_type and charge_type in charge_attrs:
                inject_gj = charge_attrs[charge_type].get(ATTR_CAP_BOOSTER_BONUS, 0)
                if inject_gj > 0:
                    cap_need = attrs.get(ATTR_CAP_NEED, 0)
                    if cap_need > 0:
                        for _ in range(item.quantity):
                            module_drains.append((cap_need, cycle_time_ms))
                        total_cap_per_sec += (cap_need / (cycle_time_ms / 1000.0)) * item.quantity
                    continue

            cap_need = attrs.get(ATTR_CAP_NEED, 0)
            if cap_need <= 0:
                continue
            # Each fitted instance is a separate module activation
            for _ in range(item.quantity):
                module_drains.append((cap_need, cycle_time_ms))
            total_cap_per_sec += (cap_need / (cycle_time_ms / 1000.0)) * item.quantity

        return calculate_capacitor(cap_capacity, cap_recharge_ms, total_cap_per_sec,
                                   module_drains=module_drains)

    def _calc_applied_dps(self, offense, modified_module_attrs, items,
                          target_profile_name, ship_attrs, charges=None,
                          target_projected=None, modified_charges=None) -> AppliedDPS:
        """Calculate applied DPS against a target profile.

        Uses turret tracking, missile application, and drone sig reduction.
        If target_projected is provided, webs reduce target velocity and
        paints increase target sig radius before application calculations.
        """
        from .constants import (
            ATTR_TRACKING_SPEED, ATTR_OPTIMAL_RANGE, ATTR_FALLOFF_RANGE,
            ATTR_WEAPON_SIG_RESOLUTION, ATTR_EXPLOSION_RADIUS,
            ATTR_EXPLOSION_VELOCITY, ATTR_DAMAGE_REDUCTION_FACTOR,
            EFFECT_TURRET_FITTED, EFFECT_LAUNCHER_FITTED,
        )

        profile = TARGET_PROFILES[target_profile_name]
        target_sig = profile["sig_radius"]
        target_vel = profile["velocity"]
        target_dist = profile["distance"]

        # Apply projected effects on the TARGET (webs slow it, paints increase sig)
        if target_projected:
            from .projected import apply_projected_effects, STACKING_PENALTIES
            target_attrs = {37: target_vel, 552: target_sig}
            proj_inputs = [
                {"effect_type": p.effect_type, "strength": p.strength, "count": p.count}
                for p in target_projected
            ]
            proj_result = apply_projected_effects(target_attrs, proj_inputs)
            target_vel = proj_result["modified_attrs"].get(37, target_vel)
            target_sig = proj_result["modified_attrs"].get(552, target_sig)

        # Get weapon type info from SDE (turret vs launcher vs drone)
        weapon_type_ids = []
        for item in items:
            if item.flag == 87 or item.flag == 5:
                continue
            weapon_type_ids.append(item.type_id)

        turret_types = set()
        launcher_types = set()
        if weapon_type_ids:
            with self.db.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT "typeID", "effectID"
                    FROM "dgmTypeEffects"
                    WHERE "typeID" = ANY(%s)
                      AND "effectID" IN (%s, %s)
                """, (list(set(weapon_type_ids)), EFFECT_TURRET_FITTED, EFFECT_LAUNCHER_FITTED))
                for row in cur.fetchall():
                    if row["effectID"] == EFFECT_TURRET_FITTED:
                        turret_types.add(row["typeID"])
                    elif row["effectID"] == EFFECT_LAUNCHER_FITTED:
                        launcher_types.add(row["typeID"])

        # Calculate turret applied DPS
        turret_hit_chance = 1.0
        if turret_types and target_dist > 0:
            # Get turret weapon attributes from SDE
            turret_ids = list(turret_types)
            with self.db.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT "typeID", "attributeID",
                           COALESCE("valueFloat", "valueInt"::float) as value
                    FROM "dgmTypeAttributes"
                    WHERE "typeID" = ANY(%s)
                      AND "attributeID" = ANY(%s)
                """, (turret_ids, [ATTR_TRACKING_SPEED, ATTR_OPTIMAL_RANGE,
                                   ATTR_FALLOFF_RANGE, ATTR_WEAPON_SIG_RESOLUTION]))
                turret_attrs = {}
                for row in cur.fetchall():
                    tid = row["typeID"]
                    if tid not in turret_attrs:
                        turret_attrs[tid] = {}
                    turret_attrs[tid][row["attributeID"]] = row["value"]

            # Average hit chance across all fitted turrets
            hit_chances = []
            for tid in turret_types:
                attrs = turret_attrs.get(tid, {})
                # Use Dogma-modified values if available
                mod_attrs = modified_module_attrs.get(tid, attrs)
                tracking = mod_attrs.get(ATTR_TRACKING_SPEED, attrs.get(ATTR_TRACKING_SPEED, 0))
                optimal = mod_attrs.get(ATTR_OPTIMAL_RANGE, attrs.get(ATTR_OPTIMAL_RANGE, 0))
                falloff = mod_attrs.get(ATTR_FALLOFF_RANGE, attrs.get(ATTR_FALLOFF_RANGE, 0))
                sig_res = mod_attrs.get(ATTR_WEAPON_SIG_RESOLUTION, attrs.get(ATTR_WEAPON_SIG_RESOLUTION, 40))

                # Angular velocity = target_velocity / distance
                angular = target_vel / target_dist if target_dist > 0 else 0
                hc = calculate_turret_hit_chance(
                    angular, tracking, sig_res, target_sig,
                    target_dist, optimal, falloff
                )
                hit_chances.append(hc)

            turret_hit_chance = sum(hit_chances) / len(hit_chances) if hit_chances else 1.0

        # Calculate missile damage factor using AMMO attributes (not launcher)
        missile_dmg_factor = 1.0
        if launcher_types:
            # Collect charge (ammo) type IDs from the charges dict
            charge_type_ids = set()
            if charges:
                for item in items:
                    if item.type_id in launcher_types and item.flag in charges:
                        charge_type_ids.add(charges[item.flag])

            # Use Dogma-modified charge attrs if available, else fall back to SDE query
            missile_attrs = {}
            query_ids = list(charge_type_ids) if charge_type_ids else list(launcher_types)

            if modified_charges:
                # Use Dogma-modified values (includes MGE bonuses)
                for tid in query_ids:
                    if tid in modified_charges:
                        missile_attrs[tid] = modified_charges[tid]

            # Fall back to SDE for any charges not in modified_charges
            missing_ids = [tid for tid in query_ids if tid not in missile_attrs]
            if missing_ids:
                with self.db.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT "typeID", "attributeID",
                               COALESCE("valueFloat", "valueInt"::float) as value
                        FROM "dgmTypeAttributes"
                        WHERE "typeID" = ANY(%s)
                          AND "attributeID" = ANY(%s)
                    """, (missing_ids, [ATTR_EXPLOSION_RADIUS, ATTR_EXPLOSION_VELOCITY,
                                         ATTR_DAMAGE_REDUCTION_FACTOR]))
                    for row in cur.fetchall():
                        tid = row["typeID"]
                        if tid not in missile_attrs:
                            missile_attrs[tid] = {}
                        missile_attrs[tid][row["attributeID"]] = row["value"]

            factors = []
            lookup_ids = charge_type_ids if charge_type_ids else launcher_types
            for tid in lookup_ids:
                attrs = missile_attrs.get(tid, {})
                exp_radius = attrs.get(ATTR_EXPLOSION_RADIUS, 150)
                exp_vel = attrs.get(ATTR_EXPLOSION_VELOCITY, 100)
                drf = attrs.get(ATTR_DAMAGE_REDUCTION_FACTOR, 5.53)
                f = calculate_missile_application(
                    target_sig, target_vel, exp_radius, exp_vel, drf
                )
                factors.append(f)

            missile_dmg_factor = sum(factors) / len(factors) if factors else 1.0

        # Drone applied DPS: simplified — min(1, target_sig / drone_optimal_sig)
        # Drones orbit and track targets well, main reduction is sig ratio
        drone_factor = min(1.0, target_sig / 150.0) if target_sig > 0 else 1.0

        # Apply factors to paper DPS
        turret_applied = offense.weapon_dps * turret_hit_chance
        missile_applied = 0.0
        # If we have launchers, split weapon DPS between turrets and missiles
        if launcher_types and turret_types:
            # Approximate 50/50 split (actual depends on fit)
            turret_applied = offense.weapon_dps * 0.5 * turret_hit_chance
            missile_applied = offense.weapon_dps * 0.5 * missile_dmg_factor
        elif launcher_types:
            turret_applied = 0.0
            missile_applied = offense.weapon_dps * missile_dmg_factor

        drone_applied = offense.drone_dps * drone_factor

        total_applied = round(turret_applied + missile_applied + drone_applied, 1)

        return AppliedDPS(
            target_profile=target_profile_name,
            turret_applied_dps=round(turret_applied, 1),
            missile_applied_dps=round(missile_applied, 1),
            drone_applied_dps=round(drone_applied, 1),
            total_applied_dps=total_applied,
            turret_hit_chance=round(turret_hit_chance, 3),
            missile_damage_factor=round(missile_dmg_factor, 3),
        )

    def _calc_targeting(self, ship_attrs: dict) -> TargetingStats:
        """Calculate targeting stats from ship attributes."""
        # Determine sensor type by highest sensor strength
        sensor_values = {
            "radar": ship_attrs.get(ATTR_SCAN_RADAR, 0),
            "ladar": ship_attrs.get(ATTR_SCAN_LADAR, 0),
            "magnetometric": ship_attrs.get(ATTR_SCAN_MAGNETO, 0),
            "gravimetric": ship_attrs.get(ATTR_SCAN_GRAVI, 0),
        }
        sensor_type = max(sensor_values, key=sensor_values.get)
        sensor_strength = sensor_values[sensor_type]

        # If all zero, no sensor type
        if sensor_strength <= 0:
            sensor_type = ""

        scan_res = ship_attrs.get(ATTR_SCAN_RES, 0)
        sig_radius = ship_attrs.get(ATTR_SIG_RADIUS, 0)
        # Lock time against cruiser-sized target (sig 150m) as reference
        lock_time = calculate_lock_time(scan_res, 150.0)
        scanability = calculate_scanability(sig_radius, sensor_strength)

        return TargetingStats(
            max_range=ship_attrs.get(ATTR_MAX_TARGET_RANGE, 0),
            scan_resolution=scan_res,
            max_locked_targets=int(ship_attrs.get(ATTR_MAX_LOCKED, 0)),
            sensor_strength=round(sensor_strength, 2),
            sensor_type=sensor_type,
            lock_time=lock_time,
            scanability=scanability,
        )

    def _calc_repairs(self, req: FittingStatsRequest, ship_attrs: dict = None,
                      modified_module_attrs: Optional[Dict[int, Dict[int, float]]] = None) -> RepairStats:
        """Calculate active tank repair rates + passive shield regen.

        Uses Dogma-modified module attributes when available (includes ship bonuses,
        skill bonuses, rig bonuses, and stacking effects). Falls back to raw SDE
        values for modules not found in modified_module_attrs.
        """
        from .calculations import calculate_shield_peak_regen
        from .constants import ATTR_SHIELD_RECHARGE

        # Passive shield regen from Dogma-modified ship attributes
        shield_passive_regen = 0.0
        if ship_attrs:
            shield_hp = ship_attrs.get(ATTR_SHIELD_HP, 0)
            recharge_ms = ship_attrs.get(ATTR_SHIELD_RECHARGE, 0)
            shield_passive_regen = calculate_shield_peak_regen(shield_hp, recharge_ms)

        # Identify repair modules by checking for repair amount attributes
        repair_module_ids = [item.type_id for item in req.items
                             if item.flag != 87 and item.flag != 5]  # exclude drones/cargo
        if not repair_module_ids:
            return RepairStats(shield_passive_regen=shield_passive_regen)

        # Build type_attrs from Dogma-modified values or fall back to SDE query
        if modified_module_attrs is not None:
            type_attrs = modified_module_attrs
        else:
            # Fallback: query raw SDE values (no Dogma bonuses applied)
            with self.db.cursor(cursor_factory=RealDictCursor) as cur:
                repair_attr_ids = [
                    ATTR_SHIELD_BOOST_AMOUNT,  # 68
                    ATTR_ARMOR_REPAIR_AMOUNT,  # 84
                    ATTR_HULL_REPAIR_AMOUNT,   # 1886
                    ATTR_DURATION,             # 73 (cycle time in ms)
                ]
                cur.execute("""
                    SELECT "typeID", "attributeID",
                           COALESCE("valueFloat", "valueInt"::float) as value
                    FROM "dgmTypeAttributes"
                    WHERE "typeID" = ANY(%s)
                      AND "attributeID" = ANY(%s)
                """, (list(set(repair_module_ids)), repair_attr_ids))

                type_attrs: dict = {}
                for row in cur.fetchall():
                    tid = row["typeID"]
                    if tid not in type_attrs:
                        type_attrs[tid] = {}
                    type_attrs[tid][row["attributeID"]] = row["value"]

        shield_rep = 0.0
        armor_rep = 0.0
        hull_rep = 0.0

        for item in req.items:
            if item.flag == 87 or item.flag == 5:
                continue
            # Only active/overheated modules provide rep
            if not self._is_module_active(item.flag, req.module_states):
                continue
            attrs = type_attrs.get(item.type_id, {})
            duration_ms = attrs.get(ATTR_DURATION, 0)
            if duration_ms <= 0:
                continue

            cycle_seconds = duration_ms / 1000.0
            qty = item.quantity

            shield_amount = attrs.get(ATTR_SHIELD_BOOST_AMOUNT, 0)
            armor_amount = attrs.get(ATTR_ARMOR_REPAIR_AMOUNT, 0)
            hull_amount = attrs.get(ATTR_HULL_REPAIR_AMOUNT, 0)

            if shield_amount > 0:
                shield_rep += (shield_amount / cycle_seconds) * qty
            if armor_amount > 0:
                armor_rep += (armor_amount / cycle_seconds) * qty
            if hull_amount > 0:
                hull_rep += (hull_amount / cycle_seconds) * qty

        # Calculate effective repair rates (EHP/s) using resist pass-through
        shield_rep_ehp = 0.0
        armor_rep_ehp = 0.0
        if ship_attrs:
            # Average damage pass-through per layer (omni profile)
            shield_pass = sum(ship_attrs.get(a, 1.0) for a in [
                ATTR_SHIELD_EM_RESIST, ATTR_SHIELD_THERMAL_RESIST,
                ATTR_SHIELD_KINETIC_RESIST, ATTR_SHIELD_EXPLOSIVE_RESIST
            ]) / 4.0
            armor_pass = sum(ship_attrs.get(a, 1.0) for a in [
                ATTR_ARMOR_EM_RESIST, ATTR_ARMOR_THERMAL_RESIST,
                ATTR_ARMOR_KINETIC_RESIST, ATTR_ARMOR_EXPLOSIVE_RESIST
            ]) / 4.0
            total_shield_rep = shield_rep + shield_passive_regen
            shield_rep_ehp = calculate_effective_rep(total_shield_rep, shield_pass)
            armor_rep_ehp = calculate_effective_rep(armor_rep, armor_pass)

        sustained_tank_ehp = round(shield_rep_ehp + armor_rep_ehp, 1)

        return RepairStats(
            shield_rep=round(shield_rep, 1),
            armor_rep=round(armor_rep, 1),
            hull_rep=round(hull_rep, 1),
            shield_passive_regen=shield_passive_regen,
            shield_rep_ehp=shield_rep_ehp,
            armor_rep_ehp=armor_rep_ehp,
            sustained_tank_ehp=sustained_tank_ehp,
        )
