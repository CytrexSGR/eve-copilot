-- Migration 045: Add character names to killmails and attackers
-- Stores character names at time of kill for faster display

-- Add victim name to killmails
ALTER TABLE killmails
ADD COLUMN IF NOT EXISTS victim_character_name VARCHAR(255);

-- Add final blow character name
ALTER TABLE killmails
ADD COLUMN IF NOT EXISTS final_blow_character_name VARCHAR(255);

-- Add attacker character name
ALTER TABLE killmail_attackers
ADD COLUMN IF NOT EXISTS character_name VARCHAR(255);

-- Index for name searches (optional, useful for "who killed X" queries)
CREATE INDEX IF NOT EXISTS idx_killmails_victim_name ON killmails(victim_character_name) WHERE victim_character_name IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_attackers_character_name ON killmail_attackers(character_name) WHERE character_name IS NOT NULL;

-- Note: Existing killmails won't have names - they can be backfilled later if needed
