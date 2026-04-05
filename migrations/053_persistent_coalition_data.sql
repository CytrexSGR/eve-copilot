-- Persistent coalition relationship tracking
-- Accumulates data over time instead of time-limited window

-- Table for alliance pair fight history (accumulated)
CREATE TABLE IF NOT EXISTS alliance_fight_together (
    alliance_a BIGINT NOT NULL,
    alliance_b BIGINT NOT NULL,
    fights_together INTEGER DEFAULT 0,
    first_seen TIMESTAMP DEFAULT NOW(),
    last_seen TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (alliance_a, alliance_b),
    CHECK (alliance_a < alliance_b)  -- Normalized order
);

CREATE INDEX IF NOT EXISTS idx_aft_alliance_a ON alliance_fight_together(alliance_a);
CREATE INDEX IF NOT EXISTS idx_aft_alliance_b ON alliance_fight_together(alliance_b);
CREATE INDEX IF NOT EXISTS idx_aft_fights ON alliance_fight_together(fights_together DESC);

-- Table for alliance total activity (accumulated)
CREATE TABLE IF NOT EXISTS alliance_activity_total (
    alliance_id BIGINT PRIMARY KEY,
    total_kills INTEGER DEFAULT 0,
    first_seen TIMESTAMP DEFAULT NOW(),
    last_seen TIMESTAMP DEFAULT NOW()
);

-- Initialize from ALL historical data
INSERT INTO alliance_fight_together (alliance_a, alliance_b, fights_together, first_seen, last_seen)
SELECT 
    LEAST(ka1.alliance_id, ka2.alliance_id) as alliance_a,
    GREATEST(ka1.alliance_id, ka2.alliance_id) as alliance_b,
    COUNT(DISTINCT ka1.killmail_id) as fights_together,
    MIN(k.killmail_time) as first_seen,
    MAX(k.killmail_time) as last_seen
FROM killmail_attackers ka1
JOIN killmail_attackers ka2 
    ON ka1.killmail_id = ka2.killmail_id 
    AND ka1.alliance_id < ka2.alliance_id
JOIN killmails k ON k.killmail_id = ka1.killmail_id
WHERE ka1.alliance_id IS NOT NULL 
  AND ka2.alliance_id IS NOT NULL
GROUP BY LEAST(ka1.alliance_id, ka2.alliance_id), GREATEST(ka1.alliance_id, ka2.alliance_id)
HAVING COUNT(DISTINCT ka1.killmail_id) >= 10
ON CONFLICT (alliance_a, alliance_b) DO UPDATE SET
    fights_together = EXCLUDED.fights_together,
    first_seen = LEAST(alliance_fight_together.first_seen, EXCLUDED.first_seen),
    last_seen = GREATEST(alliance_fight_together.last_seen, EXCLUDED.last_seen);

-- Initialize activity totals
INSERT INTO alliance_activity_total (alliance_id, total_kills, first_seen, last_seen)
SELECT 
    ka.alliance_id,
    COUNT(DISTINCT ka.killmail_id) as total_kills,
    MIN(k.killmail_time) as first_seen,
    MAX(k.killmail_time) as last_seen
FROM killmail_attackers ka
JOIN killmails k ON k.killmail_id = ka.killmail_id
WHERE ka.alliance_id IS NOT NULL
GROUP BY ka.alliance_id
ON CONFLICT (alliance_id) DO UPDATE SET
    total_kills = EXCLUDED.total_kills,
    first_seen = LEAST(alliance_activity_total.first_seen, EXCLUDED.first_seen),
    last_seen = GREATEST(alliance_activity_total.last_seen, EXCLUDED.last_seen);
