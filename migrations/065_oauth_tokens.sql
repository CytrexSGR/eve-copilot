-- Migration 065: OAuth token storage in PostgreSQL
-- Replaces file-based tokens.json with proper DB storage
-- Supports concurrent access, atomic updates, and scales to many users

CREATE TABLE IF NOT EXISTS oauth_tokens (
    character_id INTEGER PRIMARY KEY,
    character_name VARCHAR(255) NOT NULL,
    access_token TEXT NOT NULL,
    refresh_token TEXT NOT NULL,
    scopes TEXT[] NOT NULL DEFAULT '{}',
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS oauth_states (
    state VARCHAR(255) PRIMARY KEY,
    code_verifier VARCHAR(255) NOT NULL,
    redirect_url TEXT,
    created_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_oauth_states_expires ON oauth_states(expires_at);
