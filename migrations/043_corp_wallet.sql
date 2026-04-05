-- Migration: 043_corp_wallet.sql
-- Description: Corporation wallet analysis and tracking
-- Date: 2026-01-23

-- Corporation wallet divisions
CREATE TABLE IF NOT EXISTS corp_wallet_divisions (
    id SERIAL PRIMARY KEY,
    corporation_id INTEGER NOT NULL,
    division INTEGER NOT NULL,  -- 1-7
    name VARCHAR(100),
    balance NUMERIC(20, 2),
    purpose VARCHAR(50),  -- 'srp', 'tax', 'industry', 'market', 'general', etc.
    last_synced TIMESTAMP WITH TIME ZONE,

    UNIQUE(corporation_id, division)
);

CREATE INDEX IF NOT EXISTS idx_corp_wallet_corp ON corp_wallet_divisions(corporation_id);

-- Wallet journal entries
CREATE TABLE IF NOT EXISTS corp_wallet_journal (
    id BIGINT PRIMARY KEY,  -- ESI journal entry ID
    corporation_id INTEGER NOT NULL,
    division INTEGER NOT NULL,

    -- Transaction details
    amount NUMERIC(20, 2) NOT NULL,
    balance NUMERIC(20, 2),
    context_id BIGINT,
    context_id_type VARCHAR(50),
    date TIMESTAMP WITH TIME ZONE NOT NULL,
    description TEXT,
    first_party_id INTEGER,
    second_party_id INTEGER,
    reason TEXT,
    ref_type VARCHAR(100) NOT NULL,
    tax NUMERIC(20, 2),
    tax_receiver_id INTEGER,

    -- Metadata
    synced_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_journal_corp ON corp_wallet_journal(corporation_id, division);
CREATE INDEX IF NOT EXISTS idx_journal_date ON corp_wallet_journal(date);
CREATE INDEX IF NOT EXISTS idx_journal_ref_type ON corp_wallet_journal(ref_type);
CREATE INDEX IF NOT EXISTS idx_journal_amount ON corp_wallet_journal(amount);

-- Common wallet ref_types for categorization
-- bounty_prizes, agent_mission_reward, corporate_reward_tax,
-- market_escrow, market_transaction, industry_job_tax,
-- structure_gate_jump, jump_clone_activation_fee, etc.

-- View for income analysis
CREATE OR REPLACE VIEW v_corp_wallet_income AS
SELECT
    corporation_id,
    division,
    ref_type,
    DATE_TRUNC('day', date) as day,
    SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as income,
    SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as expenses,
    COUNT(*) as transaction_count
FROM corp_wallet_journal
WHERE date > NOW() - INTERVAL '30 days'
GROUP BY corporation_id, division, ref_type, DATE_TRUNC('day', date);

-- View for tax income tracking
CREATE OR REPLACE VIEW v_corp_tax_income AS
SELECT
    corporation_id,
    DATE_TRUNC('day', date) as day,
    SUM(CASE WHEN ref_type = 'corporate_reward_tax' THEN amount ELSE 0 END) as bounty_tax,
    SUM(CASE WHEN ref_type = 'industry_job_tax' THEN amount ELSE 0 END) as industry_tax,
    SUM(CASE WHEN ref_type = 'office_rental_fee' THEN ABS(amount) ELSE 0 END) as office_fees,
    SUM(amount) as net_change
FROM corp_wallet_journal
WHERE date > NOW() - INTERVAL '30 days'
GROUP BY corporation_id, DATE_TRUNC('day', date)
ORDER BY day DESC;

-- Large transactions tracker
CREATE OR REPLACE VIEW v_large_transactions AS
SELECT
    j.id,
    j.corporation_id,
    j.division,
    j.amount,
    j.date,
    j.ref_type,
    j.description,
    j.first_party_id,
    j.second_party_id,
    ABS(j.amount) as abs_amount
FROM corp_wallet_journal j
WHERE ABS(j.amount) > 100000000  -- Over 100M ISK
ORDER BY j.date DESC;

COMMENT ON TABLE corp_wallet_divisions IS 'Corporation wallet divisions with balances';
COMMENT ON TABLE corp_wallet_journal IS 'Corporation wallet journal entries';
COMMENT ON VIEW v_corp_wallet_income IS 'Daily income/expense by ref_type';
COMMENT ON VIEW v_corp_tax_income IS 'Daily tax income breakdown';
