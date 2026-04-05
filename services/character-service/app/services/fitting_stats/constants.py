"""SDE attribute IDs, effect IDs, skill constants, and flags."""

# --- SDE Attribute IDs ---
ATTR_HI_SLOTS = 14
ATTR_MED_SLOTS = 13
ATTR_LOW_SLOTS = 12
ATTR_RIG_SLOTS = 1137
ATTR_POWER_OUTPUT = 11
ATTR_CPU_OUTPUT = 48
ATTR_CPU_NEED = 50
ATTR_POWER_NEED = 30
ATTR_MAX_VELOCITY = 37
ATTR_AGILITY = 70
ATTR_SIG_RADIUS = 552
ATTR_CALIBRATION_OUTPUT = 1132
ATTR_CALIBRATION_COST = 1153
ATTR_TURRET_SLOTS = 102
ATTR_LAUNCHER_SLOTS = 101
ATTR_CAP_CAPACITY = 482
ATTR_CAP_RECHARGE = 55
ATTR_DRONE_CAPACITY = 283
ATTR_DRONE_BANDWIDTH = 1271
ATTR_MAX_TARGET_RANGE = 76
ATTR_SCAN_RES = 564
ATTR_MAX_LOCKED = 192
ATTR_SCAN_RADAR = 208
ATTR_SCAN_LADAR = 209
ATTR_SCAN_MAGNETO = 210
ATTR_SCAN_GRAVI = 211
ATTR_WARP_SPEED_MULT = 600
ATTR_MASS = 4
ATTR_CAP_NEED = 6
ATTR_DURATION = 73
ATTR_RATE_OF_FIRE = 51
ATTR_DRONE_BW_NEED = 1272
ATTR_VOLUME = 161
ATTR_DAMAGE_MULT = 64
ATTR_EM_DAMAGE = 114
ATTR_EXPLOSIVE_DAMAGE = 116
ATTR_KINETIC_DAMAGE = 117
ATTR_THERMAL_DAMAGE = 118
ATTR_META_LEVEL = 633
ATTR_CHARGE_GROUP1 = 604
ATTR_CHARGE_GROUP2 = 605
ATTR_CHARGE_GROUP3 = 606
ATTR_CHARGE_GROUP4 = 609
ATTR_CHARGE_GROUP5 = 610

# Defense attributes
ATTR_SHIELD_RECHARGE = 479   # shieldRechargeRate (ms)
ATTR_SHIELD_HP = 263
ATTR_ARMOR_HP = 265
ATTR_HULL_HP = 9
ATTR_SHIELD_EM_RESIST = 271
ATTR_SHIELD_THERMAL_RESIST = 274
ATTR_SHIELD_KINETIC_RESIST = 273
ATTR_SHIELD_EXPLOSIVE_RESIST = 272
ATTR_ARMOR_EM_RESIST = 267
ATTR_ARMOR_THERMAL_RESIST = 270
ATTR_ARMOR_KINETIC_RESIST = 269
ATTR_ARMOR_EXPLOSIVE_RESIST = 268
ATTR_HULL_EM_RESIST = 113
ATTR_HULL_THERMAL_RESIST = 110
ATTR_HULL_KINETIC_RESIST = 109
ATTR_HULL_EXPLOSIVE_RESIST = 111

# Cap booster
ATTR_CAP_BOOSTER_BONUS = 67     # capacitorBonus on cap booster charges (GJ injected)

# Repair modules
ATTR_SHIELD_BOOST_AMOUNT = 68    # HP per cycle (Shield Boosters)
ATTR_ARMOR_REPAIR_AMOUNT = 84    # HP per cycle (Armor Repairers)
ATTR_HULL_REPAIR_AMOUNT = 1886   # HP per cycle (Hull Repairers)

# Ship extras
ATTR_DRONE_CONTROL_RANGE = 858   # meters
ATTR_CARGO_CAPACITY = 38         # m3
ATTR_MAX_ACTIVE_DRONES = 352     # maxActiveDrones (default 5)

# Drone flag
FLAG_DRONE_BAY = 87

# Propulsion effect IDs (both AB and MWD share groupID 46 in SDE)
EFFECT_AFTERBURNER = 6731       # moduleBonusAfterburner
EFFECT_MWD = 6730               # moduleBonusMicrowarpdrive
GROUP_PROPULSION_MODULE = 46    # invGroups groupID for AB/MWD modules
GROUP_WARP_CORE_STABILIZER = 315  # invGroups groupID for WCS modules

# Groups excluded from cap simulation — WCS requires manual activation.
# Propmods (AB/MWD) are included because EVE's fitting window assumes all active
# modules are running. Siege/Bastion/Industrial Core are excluded in engine.py
# via ACTIVATION_REQUIRED_EFFECTS.
CAP_SIM_EXCLUDED_GROUPS = {GROUP_WARP_CORE_STABILIZER}

# Propulsion attributes
ATTR_SPEED_BOOST_FACTOR = 20   # speedBoostFactor (%)
ATTR_SPEED_FACTOR = 567        # speedFactor (thrust, Newtons)
ATTR_MASS_ADDITION = 796       # massAddition (kg, MWD only)
ATTR_SIG_RADIUS_MOD = 554      # signatureRadiusModifier (% for MWD sig bloom)

# Networked Sensor Array (NSA) — carriers/supers only
# Like propmods, NSA has a scan resolution bonus (attr 566) that has NO modifierInfo
# in the SDE, so it must be applied manually.
EFFECT_NSA = 6567                       # moduleBonusNetworkedSensorArray
ATTR_SCAN_RES_BONUS_PCT = 566          # scanResolutionBonus (% bonus to scan resolution)

# Weapon fitting reduction skills (applied to turret/launcher modules only)
SKILL_WEAPON_UPGRADES = 3318          # -5% CPU/level for turrets/launchers
SKILL_ADVANCED_WEAPON_UPGRADES = 11207  # -2% PG/level for turrets/launchers
DEFAULT_FITTING_SKILL_LEVEL = 5       # Assume All V

# Propmod/Drone skills (applied in hardcoded sections, not via Dogma engine)
SKILL_ACCELERATION_CONTROL = 3452     # +5%/level to AB/MWD speed boost
SKILL_DRONE_INTERFACING = 3442        # +10%/level to drone damage

# Drone control range skills (domain: charID in SDE — must be applied manually).
# {skill_type_id: bonus_meters_per_level}
DRONE_RANGE_SKILLS = {
    3437: 5000,    # Drone Avionics: +5km/level
    23566: 3000,   # Advanced Drone Avionics: +3km/level
}

# Drone damage skills with hardcoded droneDmgBonus effect (effectID 1730).
# These apply +X% per level to drones that require the skill.
# SDE encodes these with NULL modifierInfo — must be applied manually.
# {skill_type_id: bonus_percent_per_level}
DRONE_DAMAGE_SKILLS = {
    24241: 5,   # Light Drone Operation
    33699: 5,   # Medium Drone Operation
    3441: 5,    # Heavy Drone Operation
    23594: 5,   # Sentry Drone Interfacing
    12484: 2,   # Amarr Drone Specialization
    12485: 2,   # Minmatar Drone Specialization
    12486: 2,   # Gallente Drone Specialization
    12487: 2,   # Caldari Drone Specialization
    60515: 2,   # Mutated Drone Specialization
}

# SDE required skill attributes (requiredSkill1/2/3)
ATTR_REQUIRED_SKILL_1 = 182
ATTR_REQUIRED_SKILL_2 = 183
ATTR_REQUIRED_SKILL_3 = 184

# --- Missile skill bonuses ---
# Missile Launcher Operation is the universal required skill for all launchers.
SKILL_MISSILE_LAUNCHER_OP = 3319

# Character ROF skills for missile launchers (hardcoded / character-scope).
# {skill_type_id: bonus_percent_per_level}  (negative = faster ROF)
# MLO and Rapid Launch apply to ALL launchers (skillTypeID=3319=MLO).
MISSILE_ROF_SKILLS = {
    3319: -2,    # Missile Launcher Operation: -2%/level
    21071: -3,   # Rapid Launch: -3%/level
}
# Missile specialization ROF: -2%/level, but only for launchers requiring the spec.
# {specialization_skill_id: rof_bonus_percent_per_level}
MISSILE_SPEC_ROF_SKILLS = {
    20209: -2,  # Rocket Specialization
    20210: -2,  # Light Missile Specialization
    20211: -2,  # Heavy Missile Specialization (HML)
    20212: -2,  # Cruise Missile Specialization
    20213: -2,  # Torpedo Specialization
    25718: -2,  # Heavy Assault Missile Specialization (HAM)
    41409: -2,  # XL Torpedo Specialization
    41410: -2,  # XL Cruise Missile Specialization
}

# Missile type damage skills with hardcoded missileXXXDmgBonus effects (NULL modifierInfo).
# These apply +5% per level to ALL damage types of charges that require this skill.
# {skill_type_id: bonus_percent_per_level}
MISSILE_DAMAGE_SKILLS = {
    3320: 5,    # Rockets
    3321: 5,    # Light Missiles
    3324: 5,    # Heavy Missiles
    3325: 5,    # Torpedoes
    3326: 5,    # Cruise Missiles
    25719: 5,   # Heavy Assault Missiles
}

# Missile specialization damage bonus: +2%/level (hardcoded, NULL modifierInfo).
# Only applies to T2 charges that require the specialization skill.
MISSILE_SPEC_DAMAGE_SKILLS = {
    20209: 2,   # Rocket Specialization
    20210: 2,   # Light Missile Specialization
    20211: 2,   # Heavy Missile Specialization (HML)
    20212: 2,   # Cruise Missile Specialization
    20213: 2,   # Torpedo Specialization
    25718: 2,   # Heavy Assault Missile Specialization (HAM)
    41409: 2,   # XL Torpedo Specialization
    41410: 2,   # XL Cruise Missile Specialization
}

# Warhead Upgrades: +2%/level to each damage type of all missiles (targets MLO skill).
SKILL_WARHEAD_UPGRADES = 20315
WARHEAD_UPGRADES_BONUS = 2  # percent per level

# BCS-style missile damage multiplier attribute (from fitted modules like BCS).
# domain: charID, func: ItemModifier — the Dogma engine doesn't handle charID
# modifiers, so we apply them manually in offense calculations.
ATTR_MISSILE_DMG_BONUS = 213

# --- Applied DPS / Weapon attrs ---
ATTR_TRACKING_SPEED = 160         # turret tracking speed (rad/s)
ATTR_OPTIMAL_RANGE = 54           # turret/missile optimal range (m)
ATTR_FALLOFF_RANGE = 158          # turret falloff range (m)
ATTR_WEAPON_SIG_RESOLUTION = 120  # signatureResolution on turrets (m)
ATTR_EXPLOSION_RADIUS = 654       # missile explosion radius (m)
ATTR_EXPLOSION_VELOCITY = 653     # missile explosion velocity (m/s)
ATTR_DAMAGE_REDUCTION_FACTOR = 1353  # missile DRF

# Target profiles: standard EVE ship classes for applied DPS calculation
TARGET_PROFILES = {
    "frigate":       {"sig_radius": 35,   "velocity": 400, "distance": 5000},
    "destroyer":     {"sig_radius": 65,   "velocity": 350, "distance": 8000},
    "cruiser":       {"sig_radius": 150,  "velocity": 200, "distance": 15000},
    "battlecruiser": {"sig_radius": 270,  "velocity": 150, "distance": 20000},
    "battleship":    {"sig_radius": 450,  "velocity": 100, "distance": 30000},
    "capital":       {"sig_radius": 3000, "velocity": 60,  "distance": 50000},
    "structure":     {"sig_radius": 10000, "velocity": 0,  "distance": 0},
}

# NPC damage profiles for EHP calculation
DAMAGE_PROFILES = {
    "omni":          {"em": 0.25, "thermal": 0.25, "kinetic": 0.25, "explosive": 0.25},
    "guristas":      {"em": 0.0,  "thermal": 0.39, "kinetic": 0.61, "explosive": 0.0},
    "sansha":        {"em": 0.53, "thermal": 0.47, "kinetic": 0.0,  "explosive": 0.0},
    "angels":        {"em": 0.0,  "thermal": 0.0,  "kinetic": 0.43, "explosive": 0.57},
    "serpentis":     {"em": 0.0,  "thermal": 0.40, "kinetic": 0.60, "explosive": 0.0},
    "blood_raiders": {"em": 0.50, "thermal": 0.48, "kinetic": 0.0,  "explosive": 0.02},
    "rogue_drones":  {"em": 0.0,  "thermal": 0.38, "kinetic": 0.38, "explosive": 0.24},
    "em_only":       {"em": 1.0,  "thermal": 0.0,  "kinetic": 0.0,  "explosive": 0.0},
    "thermal_only":  {"em": 0.0,  "thermal": 1.0,  "kinetic": 0.0,  "explosive": 0.0},
    "kinetic_only":  {"em": 0.0,  "thermal": 0.0,  "kinetic": 1.0,  "explosive": 0.0},
    "explosive_only": {"em": 0.0, "thermal": 0.0,  "kinetic": 0.0,  "explosive": 1.0},
}

# --- SDE Effect IDs ---
EFFECT_TURRET_FITTED = 42
EFFECT_LAUNCHER_FITTED = 40

# --- Fighter constants ---
GROUP_LIGHT_FIGHTER = 1652
GROUP_HEAVY_FIGHTER = 1653
GROUP_SUPPORT_FIGHTER = 1537
FIGHTER_COMBAT_GROUPS = {GROUP_LIGHT_FIGHTER, GROUP_HEAVY_FIGHTER}
EFFECT_FIGHTER_ATTACK = 6465    # AttackM (primary attack ability)
EFFECT_FIGHTER_MISSILES = 6431  # Fighter missile volley
EFFECT_FIGHTER_BOMB = 6485      # Fighter bombing run
ATTR_SQUADRON_SIZE = 2215       # fighterSquadronMaxSize
