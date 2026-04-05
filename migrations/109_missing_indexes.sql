-- Migration 109: Add missing indexes on high-seq-scan tables
-- Addresses CPU peaks from full table scans on SDE + operational tables
-- All CREATE INDEX CONCURRENTLY to avoid blocking writes

-- 1. industryActivityMaterials — 3.2M seq scans, 0 idx scans, 116B rows read
--    Every query filters on (typeID, activityID)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_iam_typeid_activityid
    ON "industryActivityMaterials" ("typeID", "activityID");

-- 2. industryActivityProducts — 7.3M seq scans, 0 idx scans, 27B rows read
--    Most queries filter on (productTypeID, activityID)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_iap_producttypeid_activityid
    ON "industryActivityProducts" ("productTypeID", "activityID");

--    Some queries filter on (typeID, activityID)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_iap_typeid_activityid
    ON "industryActivityProducts" ("typeID", "activityID");

-- 3. battles — 2.3M seq scans despite 7 existing indexes
--    battle_tracker queries: WHERE solar_system_id = X AND status = 'active' AND last_kill_at > NOW() - INTERVAL
--    Existing idx_battles_active is partial (WHERE status='active') but lacks last_kill_at
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_battles_system_status_lastkill
    ON battles (solar_system_id, status, last_kill_at DESC);

-- 4. alliance_name_cache — 4.5M seq scans, PK on alliance_id exists
--    dotlan scraper does reverse lookup: WHERE alliance_name = %s
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_alliance_name_cache_name
    ON alliance_name_cache (alliance_name);

-- 5. planetSchematicsTypeMap — 129K seq scans, 0 idx scans
--    Queries filter on (typeID, isInput)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_pstm_typeid_isinput
    ON "planetSchematicsTypeMap" ("typeID", "isInput");

-- 6. certMasteries — 53K seq scans, 0 idx scans
--    Queries filter on (typeID, masteryLevel)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_certmasteries_typeid
    ON "certMasteries" ("typeID", "masteryLevel");

-- 7. certSkills — 53K seq scans, 0 idx scans
--    Queries JOIN/filter on (certID, certLevelInt)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_certskills_certid
    ON "certSkills" ("certID", "certLevelInt");
