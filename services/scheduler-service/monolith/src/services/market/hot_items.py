"""Hot Items configuration for proactive caching."""
from dataclasses import dataclass
from typing import Set

# === MINERALS (8 items) ===
MINERALS = {
    34,   # Tritanium
    35,   # Pyerite
    36,   # Mexallon
    37,   # Isogen
    38,   # Nocxium
    39,   # Zydrine
    40,   # Megacyte
    11399 # Morphite
}

# === FUEL ISOTOPES (4 items) ===
ISOTOPES = {
    16274,  # Helium Isotopes
    17887,  # Oxygen Isotopes
    17888,  # Nitrogen Isotopes
    17889,  # Hydrogen Isotopes
}

# === FUEL BLOCKS (4 items) ===
FUEL_BLOCKS = {
    4051,   # Nitrogen Fuel Block
    4246,   # Hydrogen Fuel Block
    4247,   # Helium Fuel Block
    4312    # Oxygen Fuel Block
}

# === MOON MATERIALS (20 items) ===
MOON_MATERIALS = {
    16633,  # Hydrocarbons
    16634,  # Atmospheric Gases
    16635,  # Evaporite Deposits
    16636,  # Silicates
    16637,  # Tungsten
    16638,  # Titanium
    16639,  # Scandium
    16640,  # Cobalt
    16641,  # Chromium
    16642,  # Vanadium
    16643,  # Cadmium
    16644,  # Platinum
    16646,  # Caesium
    16647,  # Technetium
    16648,  # Hafnium
    16649,  # Mercury
    16650,  # Promethium
    16651,  # Neodymium
    16652,  # Dysprosium
    16653   # Thulium
}

# === COMMON PRODUCTION MATERIALS ===
PRODUCTION_MATERIALS = {
    # Salvage
    25589,  # Armor Plates
    25592,  # Fried Interface Circuit
    25595,  # Tripped Power Circuit
    25590,  # Alloyed Tritanium Bar
    25591,  # Burned Logic Circuit
    25593,  # Conductive Polymer
    25594,  # Contaminated Lorentz Fluid
    25596,  # Ward Console
    25597,  # Smashed Trigger Unit
    25598,  # Charred Micro Circuit
    25599,  # Fried Interface Circuit
    25600,  # Thruster Console
    25601,  # Damaged Artificial Neural Network
    25602,  # Scorched Telemetry Processor
    25603,  # Contaminated Nanite Compound
    25604,  # Malfunctioning Shield Emitter
}


@dataclass
class HotItemsConfig:
    """Configuration for hot items caching."""
    redis_ttl_seconds: int = 300  # 5 minutes
    refresh_interval_seconds: int = 240  # Refresh 1 min before expiry
    postgres_ttl_seconds: int = 3600  # 1 hour
    batch_size: int = 100  # ESI batch size


def get_hot_items() -> Set[int]:
    """Get all hot item type IDs for proactive caching."""
    return (
        MINERALS |
        ISOTOPES |
        FUEL_BLOCKS |
        MOON_MATERIALS |
        PRODUCTION_MATERIALS
    )


def get_hot_items_by_category() -> dict:
    """Get hot items organized by category."""
    return {
        "minerals": MINERALS,
        "isotopes": ISOTOPES,
        "fuel_blocks": FUEL_BLOCKS,
        "moon_materials": MOON_MATERIALS,
        "production_materials": PRODUCTION_MATERIALS
    }
