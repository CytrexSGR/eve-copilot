-- Migration 081: Tax Invoices
-- Phase 2: Finance Module - Mining tax invoicing and payment tracking

CREATE TABLE IF NOT EXISTS tax_invoices (
    id                  SERIAL PRIMARY KEY,
    corporation_id      INTEGER NOT NULL,
    character_id        INTEGER NOT NULL,
    period_start        DATE NOT NULL,
    period_end          DATE NOT NULL,
    total_mined_value   NUMERIC(20,2) NOT NULL DEFAULT 0,
    tax_rate            NUMERIC(5,4) NOT NULL DEFAULT 0.10,
    amount_due          NUMERIC(20,2) NOT NULL DEFAULT 0,
    amount_paid         NUMERIC(20,2) NOT NULL DEFAULT 0,
    remaining_balance   NUMERIC(20,2) NOT NULL DEFAULT 0,
    credit              NUMERIC(20,2) NOT NULL DEFAULT 0,
    status              VARCHAR(20) NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'partial', 'paid', 'overdue')),
    ledger_entries_ref  JSONB DEFAULT '[]',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Query pattern: invoices for a character
CREATE INDEX IF NOT EXISTS idx_ti_character
    ON tax_invoices (character_id, status);

-- Query pattern: invoices for a corporation
CREATE INDEX IF NOT EXISTS idx_ti_corp_period
    ON tax_invoices (corporation_id, period_start DESC);

-- Query pattern: open invoices for payment matching
CREATE INDEX IF NOT EXISTS idx_ti_open
    ON tax_invoices (status, corporation_id)
    WHERE status IN ('pending', 'partial');

-- Payment matching log: tracks which wallet transactions matched to which invoices
CREATE TABLE IF NOT EXISTS invoice_payment_matches (
    id              SERIAL PRIMARY KEY,
    invoice_id      INTEGER NOT NULL REFERENCES tax_invoices(id),
    transaction_id  BIGINT NOT NULL,
    amount          NUMERIC(20,2) NOT NULL,
    matched_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    match_method    VARCHAR(30) NOT NULL DEFAULT 'auto'
                    CHECK (match_method IN ('auto', 'manual', 'reason_keyword', 'amount_match'))
);

CREATE INDEX IF NOT EXISTS idx_ipm_invoice
    ON invoice_payment_matches (invoice_id);

CREATE UNIQUE INDEX IF NOT EXISTS idx_ipm_transaction
    ON invoice_payment_matches (transaction_id);
