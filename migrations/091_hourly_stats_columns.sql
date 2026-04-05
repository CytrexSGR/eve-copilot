-- Migration 091: Add missing columns to hourly stats tables
-- B1: solo_kills + solo_ratio for alliance hourly stats
-- B2: avg_kill_value + max_kill_value for corporation hourly stats

-- Alliance hourly stats: add solo_kills and solo_ratio
ALTER TABLE intelligence_hourly_stats
    ADD COLUMN IF NOT EXISTS solo_kills INT DEFAULT 0,
    ADD COLUMN IF NOT EXISTS solo_ratio DOUBLE PRECISION DEFAULT 0.0;

-- Corporation hourly stats: add avg_kill_value and max_kill_value
ALTER TABLE corporation_hourly_stats
    ADD COLUMN IF NOT EXISTS avg_kill_value BIGINT DEFAULT 0,
    ADD COLUMN IF NOT EXISTS max_kill_value BIGINT DEFAULT 0;
