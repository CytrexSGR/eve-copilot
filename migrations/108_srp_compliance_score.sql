-- Migration 108: Add Dogma-based compliance score to SRP requests
-- Alongside existing fuzzy match_score, stores Dogma Engine stats-based score

ALTER TABLE srp_requests ADD COLUMN IF NOT EXISTS compliance_score NUMERIC(5,3);
ALTER TABLE srp_requests ADD COLUMN IF NOT EXISTS scoring_method VARCHAR(20) DEFAULT 'fuzzy';

COMMENT ON COLUMN srp_requests.compliance_score IS 'Dogma Engine stats-based compliance score (0-1)';
COMMENT ON COLUMN srp_requests.scoring_method IS 'fuzzy = KillmailMatcher, dogma = Doctrine Engine';
