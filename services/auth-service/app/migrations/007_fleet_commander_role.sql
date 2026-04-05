-- Fleet commander role migration
-- No schema changes needed: roles are TEXT in platform_roles,
-- permissions are code-defined in org_store.py DEFAULT_PERMISSIONS.
-- This migration serves as a versioning marker.
SELECT 1;
