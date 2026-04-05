-- Migration 084: Item Prices + SRP Config
-- Phase 3: SRP & Doctrine Engine - Pricing data and SRP configuration

CREATE TABLE IF NOT EXISTS item_prices (
    type_id         INTEGER PRIMARY KEY,
    type_name       VARCHAR(200),
    group_id        INTEGER,
    meta_level      INTEGER DEFAULT 0,
    jita_buy        NUMERIC(20,2) DEFAULT 0,
    jita_sell       NUMERIC(20,2) DEFAULT 0,
    jita_split      NUMERIC(20,2) DEFAULT 0,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Query pattern: price lookups by group for fuzzy matching
CREATE INDEX IF NOT EXISTS idx_ip_group
    ON item_prices (group_id);

-- SRP configuration per corporation
CREATE TABLE IF NOT EXISTS srp_config (
    corporation_id          INTEGER PRIMARY KEY,
    pricing_mode            VARCHAR(20) NOT NULL DEFAULT 'jita_split'
                            CHECK (pricing_mode IN ('jita_buy', 'jita_sell', 'jita_split')),
    default_insurance_level VARCHAR(20) NOT NULL DEFAULT 'none'
                            CHECK (default_insurance_level IN ('none', 'basic', 'standard', 'bronze', 'silver', 'gold', 'platinum')),
    auto_approve_threshold  NUMERIC(5,2) DEFAULT 0.90,
    max_payout              NUMERIC(20,2),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
