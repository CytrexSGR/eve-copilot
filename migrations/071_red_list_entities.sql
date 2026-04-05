-- Migration 071: Red List Entities
-- HR Module - Red list of hostile/banned entities for vetting intersection

CREATE TABLE IF NOT EXISTS red_list_entities (
    id              SERIAL PRIMARY KEY,
    entity_id       BIGINT NOT NULL,
    entity_name     VARCHAR(255),
    category        VARCHAR(20) NOT NULL CHECK (category IN ('character', 'corporation', 'alliance')),
    severity        SMALLINT NOT NULL DEFAULT 1 CHECK (severity BETWEEN 1 AND 5),
    reason          TEXT,
    added_by        VARCHAR(255),
    added_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    active          BOOLEAN NOT NULL DEFAULT TRUE
);

-- Unique constraint: one active entry per entity+category
CREATE UNIQUE INDEX idx_red_list_entity_active
    ON red_list_entities (entity_id, category)
    WHERE active = TRUE;

-- Fast lookup by entity_id (for SQL JOIN intersection)
CREATE INDEX idx_red_list_entity_id ON red_list_entities (entity_id) WHERE active = TRUE;

-- Filter by category
CREATE INDEX idx_red_list_category ON red_list_entities (category) WHERE active = TRUE;

-- Filter by severity (high-severity first)
CREATE INDEX idx_red_list_severity ON red_list_entities (severity DESC) WHERE active = TRUE;

COMMENT ON TABLE red_list_entities IS 'Hostile/banned entities for vetting intersection checks';
COMMENT ON COLUMN red_list_entities.severity IS '1=low, 5=critical (known spy, awoxer)';
COMMENT ON COLUMN red_list_entities.category IS 'character, corporation, or alliance';
