-- Migration: Create materialized view for coalition pairs
-- This replaces the expensive self-join query in get_coalition_memberships()
-- Refresh every 15 minutes via scheduler job

-- Index for faster self-join (if not exists)
CREATE INDEX IF NOT EXISTS idx_killmail_attackers_km_alliance
ON killmail_attackers(killmail_id, alliance_id)
WHERE alliance_id IS NOT NULL;

-- Materialized view for coalition pairs
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_coalition_pairs AS
WITH recent_kills AS (
    SELECT killmail_id FROM killmails
    WHERE killmail_time >= NOW() - INTERVAL '7 days'
),
alliance_pairs AS (
    SELECT
        ka1.alliance_id as alliance_a,
        ka2.alliance_id as alliance_b,
        COUNT(DISTINCT ka1.killmail_id) as fights_together
    FROM killmail_attackers ka1
    JOIN killmail_attackers ka2
        ON ka1.killmail_id = ka2.killmail_id
        AND ka1.alliance_id < ka2.alliance_id
    WHERE ka1.killmail_id IN (SELECT killmail_id FROM recent_kills)
      AND ka1.alliance_id IS NOT NULL
      AND ka2.alliance_id IS NOT NULL
    GROUP BY ka1.alliance_id, ka2.alliance_id
    HAVING COUNT(DISTINCT ka1.killmail_id) >= 10
),
alliance_activity AS (
    SELECT alliance_id, COUNT(*) as activity
    FROM (
        SELECT ka.alliance_id FROM killmail_attackers ka
        JOIN killmails k ON k.killmail_id = ka.killmail_id
        WHERE k.killmail_time >= NOW() - INTERVAL '7 days'
          AND ka.alliance_id IS NOT NULL
    ) sub
    GROUP BY alliance_id
)
SELECT
    ap.alliance_a,
    ap.alliance_b,
    ap.fights_together,
    COALESCE(aa.activity, 0) as activity_a,
    COALESCE(ab.activity, 0) as activity_b
FROM alliance_pairs ap
LEFT JOIN alliance_activity aa ON aa.alliance_id = ap.alliance_a
LEFT JOIN alliance_activity ab ON ab.alliance_id = ap.alliance_b
ORDER BY fights_together DESC;

-- Indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_mv_coalition_pairs_a ON mv_coalition_pairs(alliance_a);
CREATE INDEX IF NOT EXISTS idx_mv_coalition_pairs_b ON mv_coalition_pairs(alliance_b);

-- To refresh (run via scheduler every 15 min):
-- REFRESH MATERIALIZED VIEW CONCURRENTLY mv_coalition_pairs;
-- Note: CONCURRENTLY requires a unique index, so we use regular refresh
