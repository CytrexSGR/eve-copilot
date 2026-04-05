-- ============================================================
-- Migration 006: Doctrine Detection Engine
-- ============================================================
-- Description: Creates tables for automatic doctrine detection
-- via DBSCAN clustering of zkillboard fleet compositions.
-- Replaces old doctrine_templates schema with DBSCAN approach.
-- ============================================================

BEGIN;

-- Drop old tables if they exist (from 005_doctrine_detection.sql)
DROP TABLE IF EXISTS fleet_compositions CASCADE;
DROP TABLE IF EXISTS detected_doctrines CASCADE;
DROP TABLE IF EXISTS doctrine_items_of_interest CASCADE;
DROP TABLE IF EXISTS doctrine_templates CASCADE;

-- Fleet Snapshots (raw data collection)
CREATE TABLE IF NOT EXISTS doctrine_fleet_snapshots (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    system_id INTEGER NOT NULL,
    region_id INTEGER NOT NULL,
    ships JSONB NOT NULL,  -- [{"type_id": 11190, "count": 12}, ...]
    total_pilots INTEGER NOT NULL,
    killmail_ids INTEGER[] NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Doctrine Templates (clustered results)
CREATE TABLE IF NOT EXISTS doctrine_templates (
    id SERIAL PRIMARY KEY,
    doctrine_name VARCHAR(100) DEFAULT 'Unnamed Doctrine',
    alliance_id INTEGER,
    region_id INTEGER,
    composition JSONB NOT NULL,  -- {"11190": 0.4, "638": 0.3, ...}
    confidence_score FLOAT NOT NULL DEFAULT 0.0,
    observation_count INTEGER NOT NULL DEFAULT 0,
    first_seen TIMESTAMP NOT NULL,
    last_seen TIMESTAMP NOT NULL,
    total_pilots_avg INTEGER,
    primary_doctrine_type VARCHAR(50),  -- 'subcap', 'capital', 'supercap'
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Items of Interest (derived from doctrines)
CREATE TABLE IF NOT EXISTS doctrine_items_of_interest (
    id SERIAL PRIMARY KEY,
    doctrine_id INTEGER REFERENCES doctrine_templates(id) ON DELETE CASCADE,
    type_id INTEGER NOT NULL,
    item_name VARCHAR(200),
    item_category VARCHAR(50) NOT NULL,  -- 'ammunition', 'fuel', 'module'
    consumption_rate FLOAT,
    priority INTEGER NOT NULL DEFAULT 2,  -- 1=critical, 2=high, 3=medium
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(doctrine_id, type_id)
);

-- ============================================================
-- Indices
-- ============================================================

-- Fleet snapshots - temporal queries
CREATE INDEX IF NOT EXISTS idx_snapshots_timestamp
    ON doctrine_fleet_snapshots(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_snapshots_region
    ON doctrine_fleet_snapshots(region_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_snapshots_system
    ON doctrine_fleet_snapshots(system_id, timestamp DESC);

-- Doctrine templates - discovery queries
CREATE INDEX IF NOT EXISTS idx_templates_alliance
    ON doctrine_templates(alliance_id, last_seen DESC);
CREATE INDEX IF NOT EXISTS idx_templates_region
    ON doctrine_templates(region_id, last_seen DESC);
CREATE INDEX IF NOT EXISTS idx_templates_last_seen
    ON doctrine_templates(last_seen DESC);
CREATE INDEX IF NOT EXISTS idx_templates_confidence
    ON doctrine_templates(confidence_score DESC);
CREATE INDEX IF NOT EXISTS idx_templates_type
    ON doctrine_templates(primary_doctrine_type, last_seen DESC);

-- Items of interest - doctrine lookup
CREATE INDEX IF NOT EXISTS idx_items_doctrine
    ON doctrine_items_of_interest(doctrine_id);
CREATE INDEX IF NOT EXISTS idx_items_type
    ON doctrine_items_of_interest(type_id);
CREATE INDEX IF NOT EXISTS idx_items_priority
    ON doctrine_items_of_interest(priority, doctrine_id);

-- ============================================================
-- Comments
-- ============================================================

COMMENT ON TABLE doctrine_fleet_snapshots IS
    'Aggregated fleet compositions from zkillboard kills within 5-minute windows';
COMMENT ON TABLE doctrine_templates IS
    'Detected doctrine patterns via DBSCAN clustering with cosine similarity';
COMMENT ON TABLE doctrine_items_of_interest IS
    'Market items auto-derived from doctrine ship compositions';

COMMENT ON COLUMN doctrine_templates.composition IS
    'Normalized ship type distribution as JSONB: {"type_id": ratio}';
COMMENT ON COLUMN doctrine_templates.confidence_score IS
    'Clustering confidence (0.0-1.0) based on observation count and consistency';

COMMIT;

-- Verify tables created
\dt doctrine_*
