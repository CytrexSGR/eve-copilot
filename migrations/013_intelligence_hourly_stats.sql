-- Migration: Incremental Intelligence Stats
-- Purpose: Real-time aggregation of alliance combat statistics
-- Updates: Incremented on each killmail via RedisQ listener

-- Drop if exists (for re-running)
DROP VIEW IF EXISTS intelligence_danger_zones CASCADE;
DROP VIEW IF EXISTS intelligence_30d_summary CASCADE;
DROP VIEW IF EXISTS intelligence_7d_summary CASCADE;
DROP TABLE IF EXISTS intelligence_hourly_stats CASCADE;

-- Main aggregation table with hourly buckets
CREATE TABLE intelligence_hourly_stats (
    alliance_id INT NOT NULL,
    hour_bucket TIMESTAMP NOT NULL,  -- Truncated to hour (e.g., 2026-01-16 14:00:00)

    -- Core combat stats (incremented atomically)
    kills INT DEFAULT 0,
    deaths INT DEFAULT 0,
    isk_destroyed BIGINT DEFAULT 0,  -- ISK value of ships killed
    isk_lost BIGINT DEFAULT 0,       -- ISK value of ships lost

    -- Ship breakdown (JSONB: {type_id: count})
    ships_killed JSONB DEFAULT '{}',
    ships_lost JSONB DEFAULT '{}',

    -- System activity (JSONB: {system_id: count})
    systems_kills JSONB DEFAULT '{}',   -- Where alliance got kills
    systems_deaths JSONB DEFAULT '{}',  -- Where alliance lost ships

    -- Enemy tracking (JSONB: {alliance_id: {kills: n, isk: n}})
    enemies_killed JSONB DEFAULT '{}',  -- Enemies this alliance killed
    killed_by JSONB DEFAULT '{}',       -- Who killed this alliance

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    PRIMARY KEY (alliance_id, hour_bucket)
);

-- Index for time-range queries (most common access pattern)
CREATE INDEX idx_intel_hourly_time
ON intelligence_hourly_stats(hour_bucket DESC);

-- Index for alliance lookups with time
CREATE INDEX idx_intel_hourly_alliance_time
ON intelligence_hourly_stats(alliance_id, hour_bucket DESC);

-- Function to merge JSONB counts (for incrementing ship/system counts)
CREATE OR REPLACE FUNCTION jsonb_increment_count(
    existing JSONB,
    new_key TEXT,
    increment INT DEFAULT 1
) RETURNS JSONB AS $$
BEGIN
    RETURN existing || jsonb_build_object(
        new_key,
        COALESCE((existing->>new_key)::INT, 0) + increment
    );
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Function to merge enemy stats
CREATE OR REPLACE FUNCTION jsonb_increment_enemy(
    existing JSONB,
    enemy_id TEXT,
    kill_increment INT DEFAULT 0,
    isk_increment BIGINT DEFAULT 0
) RETURNS JSONB AS $$
DECLARE
    current_kills INT;
    current_isk BIGINT;
BEGIN
    current_kills := COALESCE((existing->enemy_id->>'kills')::INT, 0);
    current_isk := COALESCE((existing->enemy_id->>'isk')::BIGINT, 0);

    RETURN existing || jsonb_build_object(
        enemy_id,
        jsonb_build_object(
            'kills', current_kills + kill_increment,
            'isk', current_isk + isk_increment
        )
    );
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_intel_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS intel_hourly_updated ON intelligence_hourly_stats;
CREATE TRIGGER intel_hourly_updated
    BEFORE UPDATE ON intelligence_hourly_stats
    FOR EACH ROW
    EXECUTE FUNCTION update_intel_timestamp();

-- View for 7-day summary (fast access)
CREATE OR REPLACE VIEW intelligence_7d_summary AS
SELECT
    alliance_id,
    SUM(kills) as kills,
    SUM(deaths) as deaths,
    SUM(isk_destroyed) as isk_destroyed,
    SUM(isk_lost) as isk_lost,
    CASE
        WHEN SUM(isk_destroyed) + SUM(isk_lost) > 0
        THEN ROUND(SUM(isk_destroyed)::NUMERIC / (SUM(isk_destroyed) + SUM(isk_lost)) * 100, 1)
        ELSE 0
    END as efficiency
FROM intelligence_hourly_stats
WHERE hour_bucket >= NOW() - INTERVAL '7 days'
GROUP BY alliance_id;

-- View for 30-day summary
CREATE OR REPLACE VIEW intelligence_30d_summary AS
SELECT
    alliance_id,
    SUM(kills) as kills,
    SUM(deaths) as deaths,
    SUM(isk_destroyed) as isk_destroyed,
    SUM(isk_lost) as isk_lost,
    CASE
        WHEN SUM(isk_destroyed) + SUM(isk_lost) > 0
        THEN ROUND(SUM(isk_destroyed)::NUMERIC / (SUM(isk_destroyed) + SUM(isk_lost)) * 100, 1)
        ELSE 0
    END as efficiency
FROM intelligence_hourly_stats
WHERE hour_bucket >= NOW() - INTERVAL '30 days'
GROUP BY alliance_id;

-- View for danger zones (systems where alliance lost most ships)
CREATE OR REPLACE VIEW intelligence_danger_zones AS
SELECT
    alliance_id,
    system_id::INT,
    death_count::INT,
    s."solarSystemName" as system_name,
    s."regionID" as region_id
FROM (
    SELECT
        alliance_id,
        key as system_id,
        SUM(value::INT) as death_count
    FROM intelligence_hourly_stats,
    LATERAL jsonb_each_text(systems_deaths) as j(key, value)
    WHERE hour_bucket >= NOW() - INTERVAL '7 days'
    GROUP BY alliance_id, key
) zone_stats
LEFT JOIN "mapSolarSystems" s ON zone_stats.system_id::INT = s."solarSystemID"
ORDER BY alliance_id, death_count DESC;

-- Comment on table
COMMENT ON TABLE intelligence_hourly_stats IS
'Incrementally updated alliance combat statistics. Each killmail updates relevant rows via RedisQ listener. Provides near real-time intelligence data.';

-- Grant permissions
GRANT SELECT, INSERT, UPDATE ON intelligence_hourly_stats TO eve;
GRANT SELECT ON intelligence_7d_summary TO eve;
GRANT SELECT ON intelligence_30d_summary TO eve;
GRANT SELECT ON intelligence_danger_zones TO eve;
