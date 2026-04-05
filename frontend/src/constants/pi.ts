// frontend/src/constants/pi.ts

/**
 * P0 (Raw Materials) to Planet Type mapping.
 * Shows which planet types can extract each raw material.
 * Source: EVE Online Planetary Industry mechanics
 */
export const P0_PLANET_MAP: Record<string, string[]> = {
  "Aqueous Liquids": ["Barren", "Gas", "Ice", "Oceanic", "Storm", "Temperate"],
  "Autotrophs": ["Temperate"],
  "Base Metals": ["Barren", "Gas", "Lava", "Plasma", "Storm"],
  "Carbon Compounds": ["Barren", "Oceanic", "Temperate"],
  "Complex Organisms": ["Oceanic", "Temperate"],
  "Felsic Magma": ["Lava"],
  "Heavy Metals": ["Ice", "Lava", "Plasma"],
  "Ionic Solutions": ["Gas", "Storm"],
  "Microorganisms": ["Barren", "Ice", "Oceanic", "Temperate"],
  "Noble Gas": ["Gas", "Ice", "Storm"],
  "Noble Metals": ["Barren", "Plasma"],
  "Non-CS Crystals": ["Lava", "Plasma"],
  "Planktic Colonies": ["Ice", "Oceanic"],
  "Reactive Gas": ["Gas"],
  "Suspended Plasma": ["Lava", "Plasma", "Storm"],
};

/**
 * Tier colors matching existing PI components.
 */
export const TIER_COLORS: Record<number, string> = {
  0: '#6b7280', // gray - P0 Raw
  1: '#22c55e', // green - P1 Basic
  2: '#3b82f6', // blue - P2 Refined
  3: '#a855f7', // purple - P3 Specialized
  4: '#f97316', // orange - P4 Advanced
};

/**
 * Tier labels for display.
 */
export const TIER_LABELS: Record<number, string> = {
  0: 'P0 (Raw)',
  1: 'P1 (Basic)',
  2: 'P2 (Refined)',
  3: 'P3 (Specialized)',
  4: 'P4 (Advanced)',
};
