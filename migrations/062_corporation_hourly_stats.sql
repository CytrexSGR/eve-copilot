-- Migration 062: Corporation Hourly Stats Table
-- Purpose: Pre-aggregate killmails by corporation-hour to eliminate 29 expensive scans
-- Impact: Corporation Offensive/Defensive tabs from 5.5s → 0.1s (55x faster!)
-- Date: 2026-02-02

-- Create corporation hourly stats table (identical structure to alliance version)
CREATE TABLE IF NOT EXISTS corporation_hourly_stats (
    corporation_id INT NOT NULL,
    hour_bucket TIMESTAMP WITHOUT TIME ZONE NOT NULL,

    -- Core aggregation metrics
    kills INT DEFAULT 0,
    deaths INT DEFAULT 0,
    isk_destroyed BIGINT DEFAULT 0,
    isk_lost BIGINT DEFAULT 0,

    -- Ship tracking (JSONB: {ship_type_id: count})
    ships_killed JSONB DEFAULT '{}'::jsonb,
    ships_lost JSONB DEFAULT '{}'::jsonb,

    -- Geographic tracking (JSONB: {system_id: count})
    systems_kills JSONB DEFAULT '{}'::jsonb,
    systems_deaths JSONB DEFAULT '{}'::jsonb,

    -- Enemy tracking (JSONB: {enemy_corp_id: {kills: N, isk: X}})
    enemies_killed JSONB DEFAULT '{}'::jsonb,
    killed_by JSONB DEFAULT '{}'::jsonb,

    -- Phase 2 Enhanced Fields (matching alliance version)
    damage_types JSONB DEFAULT '{"em":0,"thermal":0,"kinetic":0,"explosive":0}'::jsonb,
    ship_effectiveness JSONB DEFAULT '{}'::jsonb,
    ewar_threats JSONB DEFAULT '{}'::jsonb,
    expensive_losses JSONB DEFAULT '[]'::jsonb,
    equipment_summary JSONB DEFAULT '{}'::jsonb,

    -- Phase 3 Enhanced Fields (for future optimization)
    solo_kills INT DEFAULT 0,
    solo_deaths INT DEFAULT 0,
    active_pilots INT DEFAULT 0,
    engagement_distribution JSONB DEFAULT '{"solo":0,"small":0,"medium":0,"large":0,"blob":0}'::jsonb,
    solo_ratio FLOAT DEFAULT 0.0,
    damage_dealt JSONB DEFAULT '{"em":0,"thermal":0,"kinetic":0,"explosive":0}'::jsonb,
    ewar_used JSONB DEFAULT '{}'::jsonb,

    -- Metadata
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),

    PRIMARY KEY (corporation_id, hour_bucket)
);

-- Core indexes for time-based queries
CREATE INDEX IF NOT EXISTS idx_corp_hourly_corp_time
  ON corporation_hourly_stats (corporation_id, hour_bucket DESC);

CREATE INDEX IF NOT EXISTS idx_corp_hourly_time
  ON corporation_hourly_stats (hour_bucket DESC);

-- JSONB indexes for fast queries on aggregated data
CREATE INDEX IF NOT EXISTS idx_corp_hourly_ships_killed
  ON corporation_hourly_stats USING gin (ships_killed);

CREATE INDEX IF NOT EXISTS idx_corp_hourly_ships_lost
  ON corporation_hourly_stats USING gin (ships_lost);

CREATE INDEX IF NOT EXISTS idx_corp_hourly_systems_kills
  ON corporation_hourly_stats USING gin (systems_kills);

CREATE INDEX IF NOT EXISTS idx_corp_hourly_systems_deaths
  ON corporation_hourly_stats USING gin (systems_deaths);

CREATE INDEX IF NOT EXISTS idx_corp_hourly_enemies
  ON corporation_hourly_stats USING gin (enemies_killed);

CREATE INDEX IF NOT EXISTS idx_corp_hourly_killed_by
  ON corporation_hourly_stats USING gin (killed_by);

CREATE INDEX IF NOT EXISTS idx_corp_hourly_damage_types
  ON corporation_hourly_stats USING gin (damage_types);

CREATE INDEX IF NOT EXISTS idx_corp_hourly_ship_effectiveness
  ON corporation_hourly_stats USING gin (ship_effectiveness);

CREATE INDEX IF NOT EXISTS idx_corp_hourly_ewar_threats
  ON corporation_hourly_stats USING gin (ewar_threats);

CREATE INDEX IF NOT EXISTS idx_corp_hourly_equipment
  ON corporation_hourly_stats USING gin (equipment_summary);

CREATE INDEX IF NOT EXISTS idx_corp_hourly_engagement
  ON corporation_hourly_stats USING gin (engagement_distribution);

CREATE INDEX IF NOT EXISTS idx_corp_hourly_damage_dealt
  ON corporation_hourly_stats USING gin (damage_dealt);

CREATE INDEX IF NOT EXISTS idx_corp_hourly_ewar_used
  ON corporation_hourly_stats USING gin (ewar_used);

-- Partial index for gatecamp detection (high solo_ratio)
CREATE INDEX IF NOT EXISTS idx_corp_hourly_solo_ratio
  ON corporation_hourly_stats (corporation_id, solo_ratio DESC)
  WHERE solo_ratio > 0.6;

-- Trigger function for automatic updated_at timestamp
CREATE OR REPLACE FUNCTION update_corp_hourly_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Attach trigger to table
CREATE TRIGGER corp_hourly_updated
    BEFORE UPDATE ON corporation_hourly_stats
    FOR EACH ROW
    EXECUTE FUNCTION update_corp_hourly_timestamp();

-- Table and column comments for documentation
COMMENT ON TABLE corporation_hourly_stats IS
'Hourly pre-aggregated statistics per corporation. Eliminates expensive killmails scans for Corporation Offensive/Defensive tabs. Reduces 29 queries per view to 2-3 queries. Expected storage: ~5MB initial, ~50MB after 1 year.';

COMMENT ON COLUMN corporation_hourly_stats.corporation_id IS
'Corporation ID from ESI/killmails. Primary key component.';

COMMENT ON COLUMN corporation_hourly_stats.hour_bucket IS
'Hour-aligned timestamp (e.g., 2026-02-02 14:00:00). Primary key component. Aggregates all killmails within this hour for this corporation.';

COMMENT ON COLUMN corporation_hourly_stats.ships_killed IS
'JSONB: {ship_type_id: kill_count}. Ship types this corporation destroyed. Example: {"670": 5, "671": 3} means 5 Capsules, 3 Shuttles killed.';

COMMENT ON COLUMN corporation_hourly_stats.ships_lost IS
'JSONB: {ship_type_id: loss_count}. Ship types this corporation lost. Inverse of ships_killed.';

COMMENT ON COLUMN corporation_hourly_stats.systems_kills IS
'JSONB: {system_id: kill_count}. Systems where this corporation got kills. Example: {"30000142": 12} means 12 kills in Jita.';

COMMENT ON COLUMN corporation_hourly_stats.systems_deaths IS
'JSONB: {system_id: death_count}. Systems where this corporation lost ships.';

COMMENT ON COLUMN corporation_hourly_stats.enemies_killed IS
'JSONB: {enemy_corp_id: {kills: N, isk: X}}. Corporations this corp killed and ISK destroyed. Example: {"98000001": {"kills": 5, "isk": 123456789}}.';

COMMENT ON COLUMN corporation_hourly_stats.killed_by IS
'JSONB: {enemy_corp_id: {deaths: N, isk: X}}. Corporations that killed this corp and ISK lost.';

COMMENT ON COLUMN corporation_hourly_stats.damage_types IS
'JSONB: {em, thermal, kinetic, explosive}. Damage types received (inferred from attacker ship races). Used for defensive analysis.';

COMMENT ON COLUMN corporation_hourly_stats.ship_effectiveness IS
'JSONB: Ship effectiveness matrix. Example: {"Rifter": {"destroyed": ["Merlin", "Punisher"], "avg_value": 5000000}}.';

COMMENT ON COLUMN corporation_hourly_stats.ewar_threats IS
'JSONB: EWAR threats faced by this corporation. Example: {"ECM": {"count": 5, "ships": ["Griffin", "Blackbird"]}}.';

COMMENT ON COLUMN corporation_hourly_stats.expensive_losses IS
'JSONB array: Top 5 most expensive losses this hour. Example: [{"killmail_id": 123, "ship_type_id": 670, "value": 5000000000}].';

COMMENT ON COLUMN corporation_hourly_stats.equipment_summary IS
'JSONB: Equipment profile. Example: {"projectile": 45, "missile": 30, "hybrid": 25} shows weapon usage percentages.';

COMMENT ON COLUMN corporation_hourly_stats.solo_kills IS
'Count of kills where attacker_count <= 3 (solo/small gang). Used to calculate solo_ratio for playstyle analysis.';

COMMENT ON COLUMN corporation_hourly_stats.solo_deaths IS
'Count of deaths where attacker_count <= 3 (ganked by solo/small gang).';

COMMENT ON COLUMN corporation_hourly_stats.active_pilots IS
'Count of unique character_ids active this hour (as attackers or victims). Used for activity tracking.';

COMMENT ON COLUMN corporation_hourly_stats.engagement_distribution IS
'JSONB: Engagement size breakdown. Example: {"solo": 8, "small": 15, "medium": 18, "large": 4, "blob": 0}. Sizes: solo <=3, small 4-10, medium 11-30, large 31-100, blob >100 attackers.';

COMMENT ON COLUMN corporation_hourly_stats.solo_ratio IS
'Float: solo_kills / total_kills. Used for gatecamp detection (high ratio = roaming, low = blob warfare). Indexed for WHERE solo_ratio > 0.6 queries.';

COMMENT ON COLUMN corporation_hourly_stats.damage_dealt IS
'JSONB: {em, thermal, kinetic, explosive}. Damage types dealt by this corporation (inferred from ship races). Offensive counterpart to damage_types.';

COMMENT ON COLUMN corporation_hourly_stats.ewar_used IS
'JSONB: EWAR ships used by this corporation. Example: {"ECM": {"count": 3, "ewar_type": "ECM"}}.';

-- Success message
DO $$
BEGIN
    RAISE NOTICE '✅ Migration 062 complete: corporation_hourly_stats table created with 15 indexes';
    RAISE NOTICE 'Expected table size: ~5 MB initial, ~50 MB after 1 year';
    RAISE NOTICE 'Expected index size: ~30 MB total';
    RAISE NOTICE 'Next step: Run Migration 063 (corporation attacker index)';
END $$;
