-- ============================================================
-- Migration 058: Doctrine Unique Constraint
-- ============================================================
-- Description: Adds unique constraint on (doctrine_name, region_id)
-- Must be run AFTER cleanup_doctrine_duplicates.py
-- ============================================================

BEGIN;

-- Add unique constraint to prevent future duplicates
ALTER TABLE doctrine_templates
ADD CONSTRAINT uq_doctrine_name_region
UNIQUE (doctrine_name, region_id);

COMMENT ON CONSTRAINT uq_doctrine_name_region ON doctrine_templates IS
    'Prevents duplicate doctrines with same name in same region';

COMMIT;
