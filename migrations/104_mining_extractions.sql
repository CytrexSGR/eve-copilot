-- Migration 104: Moon extraction schedule tracking
-- Used by finance-service to store ESI extraction data for the Moon Mining dashboard

CREATE TABLE IF NOT EXISTS mining_extractions (
    structure_id BIGINT NOT NULL,
    corporation_id INT NOT NULL,
    moon_id INT NOT NULL,
    extraction_start_time TIMESTAMPTZ NOT NULL,
    chunk_arrival_time TIMESTAMPTZ NOT NULL,
    natural_decay_time TIMESTAMPTZ NOT NULL,
    synced_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (structure_id, extraction_start_time)
);

CREATE INDEX IF NOT EXISTS idx_mining_ext_corp ON mining_extractions(corporation_id);
CREATE INDEX IF NOT EXISTS idx_mining_ext_arrival ON mining_extractions(chunk_arrival_time);
