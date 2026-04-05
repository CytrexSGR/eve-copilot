-- Migration 006: Bulletin Board — Corp Announcements
CREATE TABLE IF NOT EXISTS bulletin_posts (
    id SERIAL PRIMARY KEY,
    corporation_id BIGINT NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    priority TEXT DEFAULT 'normal',
    is_pinned BOOLEAN DEFAULT FALSE,
    author_character_id BIGINT NOT NULL,
    author_name TEXT NOT NULL,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_bulletin_corp ON bulletin_posts(corporation_id, is_pinned DESC, created_at DESC);
