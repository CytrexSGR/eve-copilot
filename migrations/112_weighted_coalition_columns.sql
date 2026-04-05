-- Migration 112: Add time-weighted columns for coalition detection
-- Exponential decay with half-life 14 days: weight = 2^(-age_days/14)
-- Keeps existing raw counts for backwards compatibility

-- Step 1: Add weighted columns
ALTER TABLE alliance_fight_together
    ADD COLUMN IF NOT EXISTS weighted_together DOUBLE PRECISION DEFAULT 0,
    ADD COLUMN IF NOT EXISTS recent_together INTEGER DEFAULT 0;

ALTER TABLE alliance_fight_against
    ADD COLUMN IF NOT EXISTS weighted_against DOUBLE PRECISION DEFAULT 0,
    ADD COLUMN IF NOT EXISTS recent_against INTEGER DEFAULT 0;

ALTER TABLE alliance_activity_total
    ADD COLUMN IF NOT EXISTS weighted_kills DOUBLE PRECISION DEFAULT 0;

-- Step 2: Backfill weighted fight_together data
UPDATE alliance_fight_together t
SET weighted_together = sub.w, recent_together = sub.r
FROM (
    SELECT
        alliance_a, alliance_b,
        SUM(w) as w,
        SUM(CASE WHEN killmail_time >= NOW() - INTERVAL '14 days' THEN 1 ELSE 0 END) as r
    FROM (
        SELECT DISTINCT
            LEAST(ka1.alliance_id, ka2.alliance_id) as alliance_a,
            GREATEST(ka1.alliance_id, ka2.alliance_id) as alliance_b,
            ka1.killmail_id,
            k.killmail_time,
            POWER(2.0, -EXTRACT(EPOCH FROM (NOW() - k.killmail_time)) / (14.0 * 86400)) as w
        FROM killmail_attackers ka1
        JOIN killmail_attackers ka2
            ON ka1.killmail_id = ka2.killmail_id
            AND ka1.alliance_id < ka2.alliance_id
        JOIN killmails k ON k.killmail_id = ka1.killmail_id
        WHERE ka1.alliance_id IS NOT NULL
          AND ka2.alliance_id IS NOT NULL
          AND k.killmail_time >= NOW() - INTERVAL '90 days'
    ) distinct_pairs
    GROUP BY alliance_a, alliance_b
) sub
WHERE t.alliance_a = sub.alliance_a AND t.alliance_b = sub.alliance_b;

-- Step 3: Backfill weighted fight_against data
UPDATE alliance_fight_against a
SET weighted_against = sub.w, recent_against = sub.r
FROM (
    SELECT
        alliance_a, alliance_b,
        SUM(w) as w,
        SUM(CASE WHEN killmail_time >= NOW() - INTERVAL '14 days' THEN 1 ELSE 0 END) as r
    FROM (
        SELECT DISTINCT
            LEAST(ka.alliance_id, k.victim_alliance_id) as alliance_a,
            GREATEST(ka.alliance_id, k.victim_alliance_id) as alliance_b,
            k.killmail_id,
            k.killmail_time,
            POWER(2.0, -EXTRACT(EPOCH FROM (NOW() - k.killmail_time)) / (14.0 * 86400)) as w
        FROM killmail_attackers ka
        JOIN killmails k ON k.killmail_id = ka.killmail_id
        WHERE ka.alliance_id IS NOT NULL
          AND k.victim_alliance_id IS NOT NULL
          AND ka.alliance_id <> k.victim_alliance_id
          AND k.killmail_time >= NOW() - INTERVAL '90 days'
    ) distinct_pairs
    GROUP BY alliance_a, alliance_b
) sub
WHERE a.alliance_a = sub.alliance_a AND a.alliance_b = sub.alliance_b;

-- Step 4: Backfill weighted activity totals
UPDATE alliance_activity_total act
SET weighted_kills = sub.w
FROM (
    SELECT
        alliance_id,
        SUM(w) as w
    FROM (
        SELECT DISTINCT
            ka.alliance_id,
            ka.killmail_id,
            POWER(2.0, -EXTRACT(EPOCH FROM (NOW() - k.killmail_time)) / (14.0 * 86400)) as w
        FROM killmail_attackers ka
        JOIN killmails k ON k.killmail_id = ka.killmail_id
        WHERE ka.alliance_id IS NOT NULL
          AND k.killmail_time >= NOW() - INTERVAL '90 days'
    ) distinct_kills
    GROUP BY alliance_id
) sub
WHERE act.alliance_id = sub.alliance_id;
