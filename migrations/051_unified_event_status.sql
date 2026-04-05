-- Migration: 051_unified_event_status.sql
-- Description: Add status_level field to battles table for unified event system

-- Add status_level column
ALTER TABLE battles ADD COLUMN IF NOT EXISTS status_level TEXT
  DEFAULT 'gank'
  CHECK (status_level IN ('gank', 'brawl', 'battle', 'hellcamp'));

-- Update existing battles based on total_kills
UPDATE battles SET status_level = CASE
  WHEN total_kills >= 200 THEN 'hellcamp'
  WHEN total_kills >= 50 THEN 'battle'
  WHEN total_kills >= 10 THEN 'brawl'
  ELSE 'gank'
END
WHERE status_level IS NULL OR status_level = 'gank';

-- Create index for filtering by status_level
CREATE INDEX IF NOT EXISTS idx_battles_status_level ON battles(status_level);

-- Verify migration
SELECT status_level, COUNT(*) FROM battles GROUP BY status_level ORDER BY status_level;
