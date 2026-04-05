-- migrations/012_panoptikum.sql
-- Panoptikum Target Tracking System

-- Watchlist: Targets to track
CREATE TABLE IF NOT EXISTS panoptikum_watchlist (
    id SERIAL PRIMARY KEY,
    entity_type VARCHAR(20) NOT NULL CHECK (entity_type IN ('character', 'corporation', 'alliance')),
    entity_id BIGINT NOT NULL,
    entity_name VARCHAR(255),
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    added_by VARCHAR(100),
    notes TEXT,
    priority INTEGER DEFAULT 0 CHECK (priority IN (0, 1, 2)),
    alert_enabled BOOLEAN DEFAULT FALSE,
    UNIQUE(entity_type, entity_id)
);

COMMENT ON TABLE panoptikum_watchlist IS 'Tracked entities for Panoptikum target tracking';

CREATE INDEX IF NOT EXISTS idx_panoptikum_watchlist_entity
ON panoptikum_watchlist(entity_type, entity_id);

-- Sightings: References to killmails (no data duplication)
CREATE TABLE IF NOT EXISTS panoptikum_sightings (
    id SERIAL PRIMARY KEY,
    watchlist_id INTEGER NOT NULL REFERENCES panoptikum_watchlist(id) ON DELETE CASCADE,
    killmail_id BIGINT NOT NULL,
    event_type VARCHAR(10) NOT NULL CHECK (event_type IN ('kill', 'loss')),
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(watchlist_id, killmail_id)
);

COMMENT ON TABLE panoptikum_sightings IS 'Killmail references for tracked entities';

CREATE INDEX IF NOT EXISTS idx_panoptikum_sightings_watchlist
ON panoptikum_sightings(watchlist_id);

CREATE INDEX IF NOT EXISTS idx_panoptikum_sightings_detected
ON panoptikum_sightings(detected_at DESC);

CREATE INDEX IF NOT EXISTS idx_panoptikum_sightings_killmail
ON panoptikum_sightings(killmail_id);
