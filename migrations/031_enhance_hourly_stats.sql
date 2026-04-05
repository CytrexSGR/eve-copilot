-- Migration 031: Enhance intelligence_hourly_stats with pre-aggregated fields
-- Purpose: Add JSONB columns for damage types, ship effectiveness, ewar threats, expensive losses
-- Impact: Enables Phase 3 query migration from killmails table scans to hourly_stats

-- Add new JSONB columns for pre-aggregated data
ALTER TABLE intelligence_hourly_stats
ADD COLUMN IF NOT EXISTS damage_types JSONB DEFAULT '{}'::jsonb,
ADD COLUMN IF NOT EXISTS ship_effectiveness JSONB DEFAULT '{}'::jsonb,
ADD COLUMN IF NOT EXISTS ewar_threats JSONB DEFAULT '{}'::jsonb,
ADD COLUMN IF NOT EXISTS expensive_losses JSONB DEFAULT '[]'::jsonb;

-- Add GIN indexes for JSONB query performance
CREATE INDEX IF NOT EXISTS idx_intel_hourly_damage_types
ON intelligence_hourly_stats USING gin (damage_types);

CREATE INDEX IF NOT EXISTS idx_intel_hourly_ship_effectiveness
ON intelligence_hourly_stats USING gin (ship_effectiveness);

CREATE INDEX IF NOT EXISTS idx_intel_hourly_ewar_threats
ON intelligence_hourly_stats USING gin (ewar_threats);

-- Helper function to merge JSONB counts (increment existing keys or add new ones)
CREATE OR REPLACE FUNCTION jsonb_merge_increment(a jsonb, b jsonb)
RETURNS jsonb AS $$
DECLARE
    result jsonb := a;
    k text;
    v jsonb;
BEGIN
    -- Iterate over all keys in b
    FOR k, v IN SELECT * FROM jsonb_each(b) LOOP
        IF result ? k THEN
            -- Key exists - increment the count
            result := jsonb_set(result, ARRAY[k],
                to_jsonb((result->>k)::int + (v->>0)::int));
        ELSE
            -- Key doesn't exist - add it
            result := result || jsonb_build_object(k, v);
        END IF;
    END LOOP;
    RETURN result;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Add column comments for documentation
COMMENT ON COLUMN intelligence_hourly_stats.damage_types IS
'JSONB: {"em": count, "thermal": count, "kinetic": count, "explosive": count}
Damage type distribution inferred from attacker ship races.
Used by get_damage_taken() to analyze vulnerability patterns.';

COMMENT ON COLUMN intelligence_hourly_stats.ship_effectiveness IS
'JSONB: {"groupName": {"deaths": count, "isk_lost": value}}
Ship class effectiveness tracking (victim ships by group).
Used by get_ship_effectiveness() to identify bleeding ship classes.';

COMMENT ON COLUMN intelligence_hourly_stats.ewar_threats IS
'JSONB: {"groupName": {"count": attacks, "ewar_type": "ecm|dampener|bubble"}}
Electronic warfare threat detection from attacker ship groups.
Used by get_ewar_threats() to identify common ewar attackers.';

COMMENT ON COLUMN intelligence_hourly_stats.expensive_losses IS
'JSONB: [{"killmail_id": id, "ship_type_id": type, "ship_value": isk, "system_id": sys}]
Top 5 most expensive losses per hour (only if ship_value > 100M ISK).
Used by get_expensive_losses() for high-value loss tracking.';

-- Verification query (after zkillboard backfill)
-- SELECT
--   COUNT(*) as total_rows,
--   COUNT(*) FILTER (WHERE damage_types != '{}') as with_damage,
--   COUNT(*) FILTER (WHERE ship_effectiveness != '{}') as with_effectiveness,
--   COUNT(*) FILTER (WHERE ewar_threats != '{}') as with_ewar,
--   COUNT(*) FILTER (WHERE expensive_losses != '[]') as with_expensive
-- FROM intelligence_hourly_stats
-- WHERE hour_bucket >= NOW() - INTERVAL '24 hours';
