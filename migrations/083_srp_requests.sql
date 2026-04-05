-- Migration 083: SRP Requests
-- Phase 3: SRP & Doctrine Engine - Ship Replacement Program workflow

CREATE TABLE IF NOT EXISTS srp_requests (
    id              SERIAL PRIMARY KEY,
    corporation_id  INTEGER NOT NULL,
    character_id    INTEGER NOT NULL,
    character_name  VARCHAR(200),
    killmail_id     BIGINT NOT NULL,
    killmail_hash   VARCHAR(64) NOT NULL,
    ship_type_id    INTEGER,
    ship_name       VARCHAR(200),
    doctrine_id     INTEGER REFERENCES fleet_doctrines(id),
    payout_amount   NUMERIC(20,2) NOT NULL DEFAULT 0,
    fitting_value   NUMERIC(20,2) NOT NULL DEFAULT 0,
    insurance_payout NUMERIC(20,2) NOT NULL DEFAULT 0,
    status          VARCHAR(20) NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending', 'approved', 'rejected', 'paid')),
    match_result    JSONB DEFAULT '{}',
    match_score     NUMERIC(5,2) DEFAULT 0,
    submitted_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reviewed_by     INTEGER,
    reviewed_at     TIMESTAMPTZ,
    review_note     TEXT,
    paid_at         TIMESTAMPTZ
);

-- Prevent duplicate submissions for the same killmail
CREATE UNIQUE INDEX IF NOT EXISTS idx_srp_killmail
    ON srp_requests (killmail_id);

-- Query pattern: requests by corporation + status
CREATE INDEX IF NOT EXISTS idx_srp_corp_status
    ON srp_requests (corporation_id, status, submitted_at DESC);

-- Query pattern: requests by character
CREATE INDEX IF NOT EXISTS idx_srp_character
    ON srp_requests (character_id, submitted_at DESC);

-- Query pattern: approved unpaid requests for payout list
CREATE INDEX IF NOT EXISTS idx_srp_approved
    ON srp_requests (corporation_id, status)
    WHERE status = 'approved';
