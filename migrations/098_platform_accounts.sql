-- Migration 098: Platform Accounts for SaaS
-- Links EVE characters to a platform account for multi-char support.

-- Core account table (1 account = 1 user)
CREATE TABLE IF NOT EXISTS platform_accounts (
    id                   SERIAL PRIMARY KEY,
    primary_character_id BIGINT NOT NULL UNIQUE,
    primary_character_name TEXT NOT NULL DEFAULT '',
    effective_tier       TEXT NOT NULL DEFAULT 'free',
    corporation_id       BIGINT,
    alliance_id          BIGINT,
    created_at           TIMESTAMPTZ DEFAULT now(),
    last_login           TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_platform_accounts_tier
    ON platform_accounts(effective_tier);

-- Link multiple characters to one account
CREATE TABLE IF NOT EXISTS account_characters (
    account_id      INTEGER NOT NULL REFERENCES platform_accounts(id) ON DELETE CASCADE,
    character_id    BIGINT NOT NULL UNIQUE,
    character_name  TEXT NOT NULL DEFAULT '',
    is_primary      BOOLEAN DEFAULT false,
    added_at        TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (account_id, character_id)
);

CREATE INDEX IF NOT EXISTS idx_account_characters_char
    ON account_characters(character_id);
