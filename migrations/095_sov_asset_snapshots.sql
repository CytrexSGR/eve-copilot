-- Migration 095: Sovereignty asset snapshots for delta analysis

CREATE TABLE IF NOT EXISTS sov_asset_snapshots (
    id SERIAL PRIMARY KEY,
    system_id INT NOT NULL,
    structure_type VARCHAR(50) NOT NULL,  -- skyhook, metenox, ihub, tcu
    structure_id BIGINT,
    snapshot_data JSONB NOT NULL DEFAULT '{}',
    snapshot_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sov_snapshots_system ON sov_asset_snapshots(system_id);
CREATE INDEX IF NOT EXISTS idx_sov_snapshots_time ON sov_asset_snapshots(snapshot_at DESC);
CREATE INDEX IF NOT EXISTS idx_sov_snapshots_type ON sov_asset_snapshots(structure_type);

-- Metenox fuel tracking for TTF (Time-to-Full) calculation
ALTER TABLE metenox_drills
    ADD COLUMN IF NOT EXISTS last_fuel_check TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS fuel_consumption_rate FLOAT DEFAULT 0;
