-- Migration 076: Corp Wallet Journal
-- Phase 2: Finance Module - Core wallet transaction archive

CREATE TABLE IF NOT EXISTS corp_wallet_journal (
    transaction_id  BIGINT PRIMARY KEY,
    corporation_id  INTEGER NOT NULL,
    division_id     INTEGER NOT NULL DEFAULT 1 CHECK (division_id BETWEEN 1 AND 7),
    date            TIMESTAMPTZ NOT NULL,
    ref_type        VARCHAR(100) NOT NULL,
    first_party_id  INTEGER,
    second_party_id INTEGER,
    amount          NUMERIC(20,2) NOT NULL DEFAULT 0,
    balance         NUMERIC(20,2) NOT NULL DEFAULT 0,
    reason          TEXT,
    extra_info      JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Query pattern: fetch journal for a corp+division, ordered by date
CREATE INDEX IF NOT EXISTS idx_cwj_corp_div_date
    ON corp_wallet_journal (corporation_id, division_id, date DESC);

-- Query pattern: gap-filling algorithm needs max transaction_id per corp+division
CREATE INDEX IF NOT EXISTS idx_cwj_corp_div_txid
    ON corp_wallet_journal (corporation_id, division_id, transaction_id DESC);

-- Query pattern: financial reports filter by ref_type
CREATE INDEX IF NOT EXISTS idx_cwj_ref_type
    ON corp_wallet_journal (ref_type);

-- Query pattern: payment matching by party
CREATE INDEX IF NOT EXISTS idx_cwj_first_party
    ON corp_wallet_journal (first_party_id) WHERE first_party_id IS NOT NULL;

-- High water mark tracking for gap-filling algorithm
CREATE TABLE IF NOT EXISTS wallet_sync_state (
    corporation_id  INTEGER NOT NULL,
    division_id     INTEGER NOT NULL CHECK (division_id BETWEEN 1 AND 7),
    high_water_mark BIGINT NOT NULL DEFAULT 0,
    last_sync_at    TIMESTAMPTZ,
    pages_fetched   INTEGER DEFAULT 0,
    entries_added   INTEGER DEFAULT 0,
    PRIMARY KEY (corporation_id, division_id)
);
