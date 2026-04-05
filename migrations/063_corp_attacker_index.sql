-- Migration 063: Corporation Attacker Performance Index
-- Purpose: Optimize Corporation Offensive/Defensive queries (20-30% speedup)
-- Impact: Eliminates full table scan on killmail_attackers for corporation queries
-- Date: 2026-02-02

-- Create composite index for corporation-based queries
-- CONCURRENTLY prevents table locking during index creation (production-safe)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_km_attackers_corp_km
  ON killmail_attackers (corporation_id, killmail_id)
  WHERE corporation_id IS NOT NULL;

-- Index statistics
COMMENT ON INDEX idx_km_attackers_corp_km IS
'Optimizes Corporation Offensive/Defensive queries. Allows PostgreSQL to use corporation_id filter before joining to killmails table, avoiding full table scans on 2.8M attacker rows. Expected size: ~50MB. Query pattern: SELECT ... FROM killmail_attackers WHERE corporation_id = X AND killmail_id IN (...)';

-- Success message
DO $$
BEGIN
    RAISE NOTICE '✅ Migration 063 complete: idx_km_attackers_corp_km index created';
    RAISE NOTICE 'Expected index size: ~50 MB';
    RAISE NOTICE 'Expected speedup: 20-30%% for corporation queries';
    RAISE NOTICE 'Next step: Apply migrations to database';
END $$;
