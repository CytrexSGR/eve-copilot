-- Migration 060: Add alliance_id to corporations table
-- Part of the "3 Truths" system: Track which corporations belong to which alliance

-- Add alliance_id column
ALTER TABLE corporations
ADD COLUMN IF NOT EXISTS alliance_id BIGINT;

-- Add member_count for tracking corporation size
ALTER TABLE corporations
ADD COLUMN IF NOT EXISTS member_count INTEGER DEFAULT 0;

-- Add updated_at for tracking freshness
ALTER TABLE corporations
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW();

-- Create index for efficient queries by alliance
CREATE INDEX IF NOT EXISTS idx_corporations_alliance_id ON corporations(alliance_id);

-- Add comment explaining the table's purpose
COMMENT ON TABLE corporations IS 'Corporation data synced from ESI. Part of Truth #1 (structural membership) for coalition detection.';
COMMENT ON COLUMN corporations.alliance_id IS 'Current alliance membership from ESI. NULL if not in an alliance.';
