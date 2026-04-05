-- Migration: 044_corp_contracts.sql
-- Description: Corporation contract monitoring
-- Date: 2026-01-23

-- Corporation contracts cache
CREATE TABLE IF NOT EXISTS corp_contracts (
    contract_id BIGINT PRIMARY KEY,
    corporation_id INTEGER NOT NULL,

    -- Contract details
    acceptor_id INTEGER,
    assignee_id INTEGER,
    availability VARCHAR(50),  -- 'public', 'personal', 'corporation', 'alliance'
    buyout NUMERIC(20, 2),
    collateral NUMERIC(20, 2),
    date_accepted TIMESTAMP WITH TIME ZONE,
    date_completed TIMESTAMP WITH TIME ZONE,
    date_expired TIMESTAMP WITH TIME ZONE,
    date_issued TIMESTAMP WITH TIME ZONE NOT NULL,
    days_to_complete INTEGER,
    end_location_id BIGINT,
    for_corporation BOOLEAN DEFAULT FALSE,
    issuer_corporation_id INTEGER,
    issuer_id INTEGER,
    price NUMERIC(20, 2),
    reward NUMERIC(20, 2),
    start_location_id BIGINT,
    status VARCHAR(50) NOT NULL,  -- 'outstanding', 'in_progress', 'finished', 'finished_issuer', etc.
    title TEXT,
    type VARCHAR(50) NOT NULL,  -- 'courier', 'item_exchange', 'auction'
    volume FLOAT,

    -- Metadata
    synced_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_corp_contracts_corp ON corp_contracts(corporation_id);
CREATE INDEX IF NOT EXISTS idx_corp_contracts_status ON corp_contracts(status);
CREATE INDEX IF NOT EXISTS idx_corp_contracts_type ON corp_contracts(type);
CREATE INDEX IF NOT EXISTS idx_corp_contracts_issuer ON corp_contracts(issuer_id);
CREATE INDEX IF NOT EXISTS idx_corp_contracts_acceptor ON corp_contracts(acceptor_id);

-- Contract items (for item_exchange contracts)
CREATE TABLE IF NOT EXISTS corp_contract_items (
    id SERIAL PRIMARY KEY,
    contract_id BIGINT NOT NULL REFERENCES corp_contracts(contract_id) ON DELETE CASCADE,
    type_id INTEGER NOT NULL,
    quantity BIGINT NOT NULL,
    is_included BOOLEAN NOT NULL,
    is_singleton BOOLEAN DEFAULT FALSE,

    UNIQUE(contract_id, type_id, is_included, is_singleton)
);

CREATE INDEX IF NOT EXISTS idx_contract_items_contract ON corp_contract_items(contract_id);

-- View for courier contract analysis
CREATE OR REPLACE VIEW v_corp_courier_contracts AS
SELECT
    c.contract_id,
    c.corporation_id,
    c.issuer_id,
    c.acceptor_id,
    c.status,
    c.reward,
    c.collateral,
    c.volume,
    c.date_issued,
    c.date_accepted,
    c.date_completed,
    c.date_expired,
    c.days_to_complete,
    c.start_location_id,
    c.end_location_id,
    -- Calculate ISK/m3
    CASE WHEN c.volume > 0 THEN c.reward / c.volume ELSE 0 END as isk_per_m3,
    -- Calculate completion time in hours
    CASE
        WHEN c.date_completed IS NOT NULL AND c.date_accepted IS NOT NULL
        THEN EXTRACT(EPOCH FROM (c.date_completed - c.date_accepted)) / 3600
        ELSE NULL
    END as completion_hours
FROM corp_contracts c
WHERE c.type = 'courier';

-- View for contract statistics
CREATE OR REPLACE VIEW v_corp_contract_stats AS
SELECT
    c.corporation_id,
    c.type,
    c.status,
    COUNT(*) as count,
    SUM(COALESCE(c.price, 0) + COALESCE(c.reward, 0)) as total_value,
    AVG(COALESCE(c.price, 0) + COALESCE(c.reward, 0)) as avg_value
FROM corp_contracts c
WHERE c.date_issued > NOW() - INTERVAL '30 days'
GROUP BY c.corporation_id, c.type, c.status;

COMMENT ON TABLE corp_contracts IS 'Corporation contracts cache';
COMMENT ON TABLE corp_contract_items IS 'Items in corporation contracts';
COMMENT ON VIEW v_corp_courier_contracts IS 'Courier contract analysis';
