-- Migration 079: Mining Observer Ledger
-- Phase 2: Finance Module - Mining observer structures and raw ledger data

CREATE TABLE IF NOT EXISTS mining_observers (
    observer_id     BIGINT PRIMARY KEY,
    corporation_id  INTEGER NOT NULL,
    observer_type   VARCHAR(20) NOT NULL DEFAULT 'structure',
    last_updated    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mining_obs_corp
    ON mining_observers (corporation_id);

-- Raw mining ledger from ESI observers
-- Composite key for deduplification per spec Section 4.1
CREATE TABLE IF NOT EXISTS mining_observer_ledger (
    observer_id     BIGINT NOT NULL,
    character_id    INTEGER NOT NULL,
    type_id         INTEGER NOT NULL,
    last_updated    DATE NOT NULL,
    quantity        BIGINT NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (observer_id, character_id, type_id, last_updated)
);

-- Query pattern: ledger by corporation (via observer join)
CREATE INDEX IF NOT EXISTS idx_mol_character
    ON mining_observer_ledger (character_id, last_updated DESC);

CREATE INDEX IF NOT EXISTS idx_mol_type
    ON mining_observer_ledger (type_id);
