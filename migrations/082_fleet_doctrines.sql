-- Migration 082: Fleet Doctrines
-- Phase 3: SRP & Doctrine Engine - Doctrine storage

CREATE TABLE IF NOT EXISTS fleet_doctrines (
    id              SERIAL PRIMARY KEY,
    corporation_id  INTEGER NOT NULL,
    name            VARCHAR(200) NOT NULL,
    ship_type_id    INTEGER NOT NULL,
    fitting_json    JSONB NOT NULL DEFAULT '{}',
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    base_payout     NUMERIC(20,2),
    created_by      INTEGER,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Query pattern: active doctrines for a corporation
CREATE INDEX IF NOT EXISTS idx_fd_corp_active
    ON fleet_doctrines (corporation_id, is_active)
    WHERE is_active = TRUE;

-- Query pattern: doctrines by ship type (for auto-matching)
CREATE INDEX IF NOT EXISTS idx_fd_ship_type
    ON fleet_doctrines (ship_type_id)
    WHERE is_active = TRUE;
