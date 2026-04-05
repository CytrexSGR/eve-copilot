-- Migration 059: Deprecate mv_coalition_pairs materialized view
--
-- The mv_coalition_pairs view is DEPRECATED in favor of the alliance_fight_together
-- and alliance_fight_against tables which provide more accurate coalition detection
-- by considering both ally relationships (fighting together) AND enemy relationships
-- (fighting against each other).
--
-- The new system uses a friend/enemy ratio (fights_together / fights_against >= 3.0)
-- to determine coalition membership, which correctly separates enemy blocs like
-- Imperium vs PandaFam.
--
-- Coalition membership is now calculated dynamically at runtime by:
-- war-intel-service/app/routers/war/utils.py::get_coalition_memberships()
--
-- The alliance_doctrine_fingerprints.coalition_id column is no longer populated
-- by the scheduler job and should not be relied upon.

-- Note: We keep the mv_coalition_pairs view for now as it may be referenced
-- by other systems. It will be fully removed in a future migration.

-- Add a comment to the view marking it as deprecated
COMMENT ON MATERIALIZED VIEW mv_coalition_pairs IS
'DEPRECATED: Use alliance_fight_together/against tables instead.
Coalition membership calculated by war-intel-service/utils.py::get_coalition_memberships()';

-- Add comment to the deprecated column
COMMENT ON COLUMN alliance_doctrine_fingerprints.coalition_id IS
'DEPRECATED: No longer populated. Coalition membership is calculated dynamically.';
