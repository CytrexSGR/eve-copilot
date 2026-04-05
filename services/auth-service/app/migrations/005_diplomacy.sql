-- Migration 005: Diplomacy — Alumni Notes
-- Die Tabellen character_standings, character_contacts, character_corporation_history
-- existieren bereits im character-service. Diese Migration fuegt nur die
-- alumni_notes Tabelle hinzu fuer Corp-interne Notizen zu Ex-Membern.

CREATE TABLE IF NOT EXISTS alumni_notes (
    id SERIAL PRIMARY KEY,
    corporation_id BIGINT NOT NULL,
    character_id BIGINT NOT NULL,
    character_name TEXT NOT NULL,
    left_at TIMESTAMPTZ,
    destination_corp_id BIGINT,
    destination_corp_name TEXT,
    note TEXT DEFAULT '',
    noted_by_character_id BIGINT NOT NULL,
    noted_by_name TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(corporation_id, character_id)
);
CREATE INDEX IF NOT EXISTS idx_alumni_notes_corp ON alumni_notes(corporation_id, left_at DESC);
