-- Migration 093: Contract status change history
-- Tracks status transitions for corp contracts to detect changes over time

CREATE TABLE IF NOT EXISTS contract_status_history (
    id SERIAL PRIMARY KEY,
    contract_id BIGINT NOT NULL,
    old_status VARCHAR(30),
    new_status VARCHAR(30) NOT NULL,
    changed_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_contract_status_history_contract ON contract_status_history(contract_id);
CREATE INDEX IF NOT EXISTS idx_contract_status_history_changed ON contract_status_history(changed_at DESC);
