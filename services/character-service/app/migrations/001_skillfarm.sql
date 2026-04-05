-- Migration 001: Add is_skillfarm flag to account_characters
ALTER TABLE account_characters ADD COLUMN IF NOT EXISTS is_skillfarm BOOLEAN DEFAULT FALSE;
