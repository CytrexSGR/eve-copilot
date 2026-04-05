-- ============================================================
-- Migration 057: Doctrine Deduplication Constraints
-- ============================================================
-- Description: Adds unique constraints and processed markers
-- to prevent duplicate doctrines and re-processing of snapshots.
-- ============================================================

BEGIN;

-- ============================================================
-- Step 1: Add processed flag to snapshots
-- ============================================================

ALTER TABLE doctrine_fleet_snapshots
ADD COLUMN IF NOT EXISTS processed BOOLEAN DEFAULT FALSE;

-- Index for finding unprocessed snapshots
CREATE INDEX IF NOT EXISTS idx_snapshots_unprocessed
    ON doctrine_fleet_snapshots(processed, timestamp DESC)
    WHERE processed = FALSE;

COMMENT ON COLUMN doctrine_fleet_snapshots.processed IS
    'True if this snapshot has been processed by the clustering job';

-- ============================================================
-- Step 2: Add unique constraint to snapshots (prevent duplicates)
-- ============================================================

-- First, delete duplicate snapshots keeping only the first one per (timestamp, system_id)
DELETE FROM doctrine_fleet_snapshots a
USING doctrine_fleet_snapshots b
WHERE a.id > b.id
  AND a.timestamp = b.timestamp
  AND a.system_id = b.system_id;

-- Now add the unique constraint
ALTER TABLE doctrine_fleet_snapshots
ADD CONSTRAINT uq_snapshot_time_system
UNIQUE (timestamp, system_id);

-- ============================================================
-- Step 3: Prepare for unique doctrine constraint
-- ============================================================
-- Note: We don't add UNIQUE(doctrine_name, region_id) here because
-- the cleanup in Task 3 needs to run first. The constraint will be
-- added after the cleanup via a separate migration or manual step.

COMMIT;
