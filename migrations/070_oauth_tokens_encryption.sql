-- Migration 070: OAuth Token Encryption Support
-- Adds encrypted refresh token column and character owner hash tracking.
-- Enables Fernet encryption for refresh_tokens and character transfer detection.

-- Add encrypted refresh token column (BYTEA for Fernet ciphertext)
ALTER TABLE oauth_tokens
    ADD COLUMN IF NOT EXISTS refresh_token_encrypted BYTEA;

-- Add character owner hash for detecting account transfers
-- EVE SSO returns CharacterOwnerHash in the verify response
ALTER TABLE oauth_tokens
    ADD COLUMN IF NOT EXISTS character_owner_hash VARCHAR(128);

-- Track encryption status
ALTER TABLE oauth_tokens
    ADD COLUMN IF NOT EXISTS is_encrypted BOOLEAN NOT NULL DEFAULT FALSE;

COMMENT ON COLUMN oauth_tokens.refresh_token_encrypted IS 'Fernet-encrypted refresh_token. When populated, refresh_token column contains a placeholder.';
COMMENT ON COLUMN oauth_tokens.character_owner_hash IS 'EVE SSO CharacterOwnerHash — changes when character is transferred to a different account';
COMMENT ON COLUMN oauth_tokens.is_encrypted IS 'TRUE when refresh_token_encrypted contains the actual token';

DO $$
BEGIN
    RAISE NOTICE '✅ Migration 070 complete: oauth_tokens encryption columns added';
END $$;
