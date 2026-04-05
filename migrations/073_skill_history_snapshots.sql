-- Migration 073: Skill History Snapshots
-- HR Module - SP tracking for skill injector detection

CREATE TABLE IF NOT EXISTS skill_history_snapshots (
    id              SERIAL PRIMARY KEY,
    character_id    BIGINT NOT NULL,
    total_sp        BIGINT NOT NULL,
    unallocated_sp  BIGINT NOT NULL DEFAULT 0,
    snapshot_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Time-series index for SP delta analysis
CREATE INDEX idx_skill_history_character_time
    ON skill_history_snapshots (character_id, snapshot_at DESC);

-- Prevent exact duplicate snapshots (same character, same timestamp)
CREATE UNIQUE INDEX idx_skill_history_unique
    ON skill_history_snapshots (character_id, snapshot_at);

COMMENT ON TABLE skill_history_snapshots IS 'SP snapshots for injector detection via delta analysis';
COMMENT ON COLUMN skill_history_snapshots.total_sp IS 'Total skillpoints at snapshot time';
COMMENT ON COLUMN skill_history_snapshots.unallocated_sp IS 'Unallocated SP (from extractors/injectors)';
