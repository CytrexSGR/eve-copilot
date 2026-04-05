-- Migration 003: Doctrine Management Extensions
-- Adds category column and doctrine_changelog table

-- 1. Add category column to fleet_doctrines
ALTER TABLE fleet_doctrines ADD COLUMN IF NOT EXISTS category TEXT DEFAULT 'general';
CREATE INDEX IF NOT EXISTS idx_fleet_doctrines_category ON fleet_doctrines(corporation_id, category);

-- 2. Doctrine Changelog
CREATE TABLE IF NOT EXISTS doctrine_changelog (
    id BIGSERIAL PRIMARY KEY,
    doctrine_id INTEGER NOT NULL REFERENCES fleet_doctrines(id) ON DELETE CASCADE,
    corporation_id BIGINT NOT NULL,
    actor_character_id BIGINT NOT NULL,
    actor_name TEXT NOT NULL,
    action TEXT NOT NULL,
    changes JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_doctrine_changelog_doctrine ON doctrine_changelog(doctrine_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_doctrine_changelog_corp ON doctrine_changelog(corporation_id, created_at DESC);
