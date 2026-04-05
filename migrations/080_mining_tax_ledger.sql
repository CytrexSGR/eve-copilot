-- Migration 080: Mining Tax Ledger
-- Phase 2: Finance Module - Computed tax amounts from delta calculation

CREATE TABLE IF NOT EXISTS mining_tax_ledger (
    id              SERIAL PRIMARY KEY,
    observer_id     BIGINT NOT NULL,
    character_id    INTEGER NOT NULL,
    type_id         INTEGER NOT NULL,
    date            DATE NOT NULL,
    quantity        BIGINT NOT NULL DEFAULT 0,
    delta_quantity  BIGINT NOT NULL DEFAULT 0,
    isk_value       NUMERIC(20,2) NOT NULL DEFAULT 0,
    tax_amount      NUMERIC(20,2) NOT NULL DEFAULT 0,
    tax_rate        NUMERIC(5,4) NOT NULL DEFAULT 0.10,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Unique constraint: one tax entry per observer+character+type+date
CREATE UNIQUE INDEX IF NOT EXISTS idx_mtl_composite
    ON mining_tax_ledger (observer_id, character_id, type_id, date);

-- Query pattern: tax summary per character
CREATE INDEX IF NOT EXISTS idx_mtl_character_date
    ON mining_tax_ledger (character_id, date DESC);

-- Query pattern: tax summary per corporation (via observer)
CREATE INDEX IF NOT EXISTS idx_mtl_observer
    ON mining_tax_ledger (observer_id, date DESC);

-- Ore market prices for reprocessed value calculation
CREATE TABLE IF NOT EXISTS ore_market_prices (
    type_id         INTEGER PRIMARY KEY,
    type_name       VARCHAR(200),
    jita_buy        NUMERIC(20,2) DEFAULT 0,
    jita_sell       NUMERIC(20,2) DEFAULT 0,
    jita_split      NUMERIC(20,2) DEFAULT 0,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Mining tax configuration per corporation
CREATE TABLE IF NOT EXISTS mining_tax_config (
    corporation_id      INTEGER PRIMARY KEY,
    tax_rate            NUMERIC(5,4) NOT NULL DEFAULT 0.10,
    reprocessing_yield  NUMERIC(5,4) NOT NULL DEFAULT 0.85,
    pricing_mode        VARCHAR(20) NOT NULL DEFAULT 'jita_split'
                        CHECK (pricing_mode IN ('jita_buy', 'jita_sell', 'jita_split')),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by          INTEGER
);
