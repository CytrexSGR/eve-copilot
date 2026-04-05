-- Migration 072: Vetting Reports
-- HR Module - Automated vetting results with risk scores and flags

CREATE TABLE IF NOT EXISTS vetting_reports (
    id              SERIAL PRIMARY KEY,
    character_id    BIGINT NOT NULL,
    character_name  VARCHAR(255),
    risk_score      SMALLINT NOT NULL DEFAULT 0 CHECK (risk_score BETWEEN 0 AND 100),
    flags           JSONB NOT NULL DEFAULT '{}',
    red_list_hits   JSONB NOT NULL DEFAULT '[]',
    wallet_flags    JSONB NOT NULL DEFAULT '[]',
    skill_flags     JSONB NOT NULL DEFAULT '[]',
    checked_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    checked_by      VARCHAR(255),
    notes           TEXT
);

-- Latest report per character (fast lookup)
CREATE INDEX idx_vetting_character_latest
    ON vetting_reports (character_id, checked_at DESC);

-- Risk score filtering (high-risk first)
CREATE INDEX idx_vetting_risk_score
    ON vetting_reports (risk_score DESC, checked_at DESC);

-- GIN index on flags JSONB for filtering
CREATE INDEX idx_vetting_flags_gin
    ON vetting_reports USING GIN (flags);

COMMENT ON TABLE vetting_reports IS 'Automated vetting results per applicant';
COMMENT ON COLUMN vetting_reports.risk_score IS '0=clean, 100=confirmed hostile';
COMMENT ON COLUMN vetting_reports.flags IS 'Key-value flags from vetting checks (e.g. {"sp_injection": true})';
COMMENT ON COLUMN vetting_reports.red_list_hits IS 'Array of matched red list entries [{entity_id, severity, reason}]';
