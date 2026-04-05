-- Migration 003: character_scope_consents
-- Tracks granted and requested ESI scopes per character

CREATE TABLE IF NOT EXISTS character_scope_consents (
    character_id BIGINT PRIMARY KEY,
    granted_scopes TEXT[] NOT NULL DEFAULT '{}',
    requested_scopes TEXT[] NOT NULL DEFAULT '{}',
    last_auth_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    revoked_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT fk_scope_char_tokens FOREIGN KEY (character_id)
        REFERENCES character_tokens(character_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_scope_consents_revoked
    ON character_scope_consents(revoked_at) WHERE revoked_at IS NOT NULL;
