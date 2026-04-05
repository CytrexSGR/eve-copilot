-- Migration 052: Alliance Doctrine Fingerprints
-- Creates table for tracking what ships each alliance flies
-- Data populated by scheduler job from killmail_attackers

-- Alliance-level doctrine fingerprints
CREATE TABLE IF NOT EXISTS alliance_doctrine_fingerprints (
    alliance_id BIGINT PRIMARY KEY,
    alliance_name VARCHAR(255),

    -- Usage statistics
    total_uses INT NOT NULL DEFAULT 0,           -- Total ship deployments
    unique_ships INT NOT NULL DEFAULT 0,         -- Distinct ship types

    -- Top ships as JSONB array
    -- [{type_id, type_name, uses, percentage, ship_class}, ...]
    ship_fingerprint JSONB NOT NULL DEFAULT '[]'::JSONB,

    -- Detected primary doctrine type
    primary_doctrine VARCHAR(50),                -- "HAC", "Battleship", "Bomber", etc.

    -- Coalition membership (from mv_coalition_pairs Union-Find)
    coalition_id BIGINT,                         -- Leader alliance_id of bloc

    -- Metadata
    data_period_days INT NOT NULL DEFAULT 30,
    last_updated TIMESTAMP NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Index for coalition/bloc queries
CREATE INDEX IF NOT EXISTS idx_adf_coalition ON alliance_doctrine_fingerprints(coalition_id);
CREATE INDEX IF NOT EXISTS idx_adf_updated ON alliance_doctrine_fingerprints(last_updated);

-- Comments
COMMENT ON TABLE alliance_doctrine_fingerprints IS 'Alliance ship usage fingerprints derived from killmail_attackers';
COMMENT ON COLUMN alliance_doctrine_fingerprints.ship_fingerprint IS 'Top 10 ships: [{type_id, type_name, uses, percentage, ship_class}, ...]';
COMMENT ON COLUMN alliance_doctrine_fingerprints.coalition_id IS 'Coalition leader alliance_id from Union-Find grouping';
