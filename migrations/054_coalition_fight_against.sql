-- Track when alliances fight AGAINST each other (enemies)
-- Used to break coalition relationships

CREATE TABLE IF NOT EXISTS alliance_fight_against (
    alliance_a BIGINT NOT NULL,
    alliance_b BIGINT NOT NULL,
    fights_against INTEGER DEFAULT 0,
    first_seen TIMESTAMP DEFAULT NOW(),
    last_seen TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (alliance_a, alliance_b),
    CHECK (alliance_a < alliance_b)
);

CREATE INDEX IF NOT EXISTS idx_afa_alliance_a ON alliance_fight_against(alliance_a);
CREATE INDEX IF NOT EXISTS idx_afa_alliance_b ON alliance_fight_against(alliance_b);
CREATE INDEX IF NOT EXISTS idx_afa_fights ON alliance_fight_against(fights_against DESC);

-- Initialize from historical data: attacker alliance vs victim alliance
INSERT INTO alliance_fight_against (alliance_a, alliance_b, fights_against, first_seen, last_seen)
SELECT 
    LEAST(ka.alliance_id, k.victim_alliance_id) as alliance_a,
    GREATEST(ka.alliance_id, k.victim_alliance_id) as alliance_b,
    COUNT(DISTINCT k.killmail_id) as fights_against,
    MIN(k.killmail_time) as first_seen,
    MAX(k.killmail_time) as last_seen
FROM killmail_attackers ka
JOIN killmails k ON k.killmail_id = ka.killmail_id
WHERE ka.alliance_id IS NOT NULL 
  AND k.victim_alliance_id IS NOT NULL
  AND ka.alliance_id != k.victim_alliance_id
GROUP BY LEAST(ka.alliance_id, k.victim_alliance_id), GREATEST(ka.alliance_id, k.victim_alliance_id)
HAVING COUNT(DISTINCT k.killmail_id) >= 5
ON CONFLICT (alliance_a, alliance_b) DO UPDATE SET
    fights_against = EXCLUDED.fights_against,
    first_seen = LEAST(alliance_fight_against.first_seen, EXCLUDED.first_seen),
    last_seen = GREATEST(alliance_fight_against.last_seen, EXCLUDED.last_seen);
