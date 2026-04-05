-- Migration 078: Wallet Divisions
-- Phase 2: Finance Module - Corp wallet division names

CREATE TABLE IF NOT EXISTS wallet_divisions (
    corporation_id  INTEGER NOT NULL,
    division_id     INTEGER NOT NULL CHECK (division_id BETWEEN 1 AND 7),
    name            VARCHAR(100) NOT NULL DEFAULT 'Division',
    cached_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (corporation_id, division_id)
);
