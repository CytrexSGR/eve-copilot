-- Migration: Add equipment_summary and coalition_allies to intelligence_hourly_stats
-- Purpose: Eliminate 4.4s bottleneck in Alliance /complete endpoint
-- Pattern: Same as damage_types, ship_effectiveness, ewar_threats (Phase 2-4)

-- Add new JSONB columns for pre-aggregated equipment and coalition data
ALTER TABLE intelligence_hourly_stats
ADD COLUMN IF NOT EXISTS equipment_summary JSONB DEFAULT '{}'::jsonb,
ADD COLUMN IF NOT EXISTS coalition_allies JSONB DEFAULT '[]'::jsonb;

-- Add GIN indexes for efficient JSONB queries
CREATE INDEX IF NOT EXISTS idx_intel_hourly_equipment
ON intelligence_hourly_stats USING gin (equipment_summary);

CREATE INDEX IF NOT EXISTS idx_intel_hourly_coalition
ON intelligence_hourly_stats USING gin (coalition_allies);

-- Add metadata comments
COMMENT ON COLUMN intelligence_hourly_stats.equipment_summary IS
'JSONB: Pre-aggregated equipment analysis from killmail_items
{
  "weapons": {
    "laser": {"count": N, "isk": X},
    "projectile": {"count": N, "isk": X},
    "hybrid": {"count": N, "isk": X},
    "missile": {"count": N, "isk": X}
  },
  "tank": {
    "shield_pct": X.X,
    "armor_pct": X.X,
    "resist_gap": "em|thermal|kinetic|explosive",
    "doctrine": "heavy_shield|shield_leaning|mixed|armor_leaning|heavy_armor"
  },
  "cargo_categories": {
    "fuel": ISK_value,
    "minerals": ISK_value,
    "moon_materials": ISK_value,
    "construction": ISK_value,
    "ships": ISK_value
  }
}';

COMMENT ON COLUMN intelligence_hourly_stats.coalition_allies IS
'JSONB: Co-attacker alliances detected on same killmails (coalition members)
[
  {"alliance_id": ID, "joint_kills": count},
  {"alliance_id": ID, "joint_kills": count}
]
Filtered to alliances with >=10 joint kills and cooperation > 3x conflict';

-- Grant permissions
GRANT SELECT ON intelligence_hourly_stats TO eve;
