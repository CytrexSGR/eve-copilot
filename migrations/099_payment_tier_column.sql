-- Migration 099: Add tier column to tier_payments for subscription activation
ALTER TABLE tier_payments ADD COLUMN IF NOT EXISTS tier TEXT;
ALTER TABLE tier_payments ADD COLUMN IF NOT EXISTS corporation_id BIGINT;
ALTER TABLE tier_payments ADD COLUMN IF NOT EXISTS alliance_id BIGINT;
