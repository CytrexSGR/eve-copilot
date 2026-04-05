-- Migration 088: Buyback System
-- Phase 5: Logistics & Supply Chain

CREATE TABLE IF NOT EXISTS buyback_configs (
    id              SERIAL PRIMARY KEY,
    corporation_id  BIGINT NOT NULL,
    name            VARCHAR(200) NOT NULL,
    base_discount   NUMERIC(5,2) NOT NULL DEFAULT 10.00,
    ore_modifier    NUMERIC(5,2) NOT NULL DEFAULT 0.00,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    notes           TEXT,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_buyback_configs_corp
    ON buyback_configs (corporation_id);

CREATE TABLE IF NOT EXISTS buyback_requests (
    id              SERIAL PRIMARY KEY,
    character_id    BIGINT NOT NULL,
    character_name  VARCHAR(100),
    corporation_id  BIGINT NOT NULL,
    config_id       INT REFERENCES buyback_configs(id),
    items           JSONB NOT NULL DEFAULT '[]',
    raw_text        TEXT,
    total_jita_value NUMERIC(18,2) NOT NULL DEFAULT 0,
    total_buyback   NUMERIC(18,2) NOT NULL DEFAULT 0,
    status          VARCHAR(20) NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending', 'accepted', 'paid', 'rejected', 'expired')),
    contract_id     BIGINT,
    reviewer_id     BIGINT,
    reviewer_note   TEXT,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_buyback_requests_char
    ON buyback_requests (character_id);
CREATE INDEX IF NOT EXISTS idx_buyback_requests_corp
    ON buyback_requests (corporation_id);
CREATE INDEX IF NOT EXISTS idx_buyback_requests_status
    ON buyback_requests (status) WHERE status IN ('pending', 'accepted');

-- Seed default buyback config for corp 98378388
INSERT INTO buyback_configs (corporation_id, name, base_discount, ore_modifier, notes)
VALUES
    (98378388, 'Standard Buyback', 10.00, 5.00,
     'Default buyback: 90% Jita sell for modules/ships, 85% for ore/minerals'),
    (98378388, 'Director Buyback', 5.00, 0.00,
     'Reduced-fee buyback for directors: 95% Jita sell')
ON CONFLICT DO NOTHING;
