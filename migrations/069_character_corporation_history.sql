-- Migration 069: Character Corporation History (SCD Type 2)
-- Tracks which corporation/alliance a character belongs to over time.
-- Enables detection of corp-hopping, defection analysis, and historical lookups.

CREATE TABLE IF NOT EXISTS character_corporation_history (
    id              SERIAL PRIMARY KEY,
    character_id    INTEGER NOT NULL,
    corporation_id  INTEGER NOT NULL,
    alliance_id     INTEGER,
    valid_from      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    valid_to        TIMESTAMPTZ,
    is_current      BOOLEAN NOT NULL DEFAULT TRUE,
    record_source   VARCHAR(32) NOT NULL DEFAULT 'esi_sync',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Fast lookup for current membership
CREATE UNIQUE INDEX IF NOT EXISTS idx_char_corp_hist_current
    ON character_corporation_history (character_id)
    WHERE is_current = TRUE;

-- Historical queries by character
CREATE INDEX IF NOT EXISTS idx_char_corp_hist_char_time
    ON character_corporation_history (character_id, valid_from DESC);

-- Corp member history
CREATE INDEX IF NOT EXISTS idx_char_corp_hist_corp
    ON character_corporation_history (corporation_id, valid_from DESC);

-- Alliance member history
CREATE INDEX IF NOT EXISTS idx_char_corp_hist_alliance
    ON character_corporation_history (alliance_id, valid_from DESC)
    WHERE alliance_id IS NOT NULL;

COMMENT ON TABLE character_corporation_history IS 'SCD Type 2: Character corporation/alliance membership history';
COMMENT ON COLUMN character_corporation_history.valid_from IS 'When this membership started (inclusive)';
COMMENT ON COLUMN character_corporation_history.valid_to IS 'When this membership ended (exclusive). NULL = still current';
COMMENT ON COLUMN character_corporation_history.is_current IS 'TRUE for the active record. Only one per character (enforced by unique index)';
COMMENT ON COLUMN character_corporation_history.record_source IS 'How this record was created: esi_sync, manual, import';

DO $$
BEGIN
    RAISE NOTICE '✅ Migration 069 complete: character_corporation_history table created (SCD Type 2)';
END $$;
