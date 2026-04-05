-- ============================================================
-- Migration 008: Detected Doctrines Table
-- ============================================================
-- Description: Restores the detected_doctrines table for
-- per-alliance doctrine tracking used by the intelligence service.
-- This table was dropped in migration 006 but is still needed
-- by the DoctrineRepository for alliance intelligence.
-- ============================================================

BEGIN;

-- Detected doctrines by alliance (from zkillboard analysis)
CREATE TABLE IF NOT EXISTS detected_doctrines (
    id SERIAL PRIMARY KEY,
    alliance_id INT NOT NULL,
    doctrine_name VARCHAR(100),
    is_known_doctrine BOOLEAN DEFAULT TRUE,
    ship_type_id INT NOT NULL,
    fit_hash VARCHAR(64),
    sightings INT DEFAULT 1,
    first_seen TIMESTAMP NOT NULL,
    last_seen TIMESTAMP NOT NULL,
    avg_dps NUMERIC(8,2),
    tank_type VARCHAR(20),
    weapon_type VARCHAR(50),
    engagement_range VARCHAR(20),
    example_fitting JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(alliance_id, fit_hash)
);

-- Indices for efficient queries
CREATE INDEX IF NOT EXISTS idx_dd_alliance ON detected_doctrines(alliance_id);
CREATE INDEX IF NOT EXISTS idx_dd_last_seen ON detected_doctrines(last_seen);
CREATE INDEX IF NOT EXISTS idx_dd_ship_type ON detected_doctrines(ship_type_id);

COMMENT ON TABLE detected_doctrines IS
    'Alliance doctrine detections from zkillboard killmail analysis';

COMMIT;
