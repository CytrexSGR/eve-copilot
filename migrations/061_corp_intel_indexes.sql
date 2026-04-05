-- Corporation Intelligence Performance Indexes
-- Support for hourly aggregation, weapon analysis, and temporal queries

-- Hourly aggregation optimization for Peak Hunting Hours / Safe-Danger Hours
-- Note: killmail_time is already stored in UTC
CREATE INDEX CONCURRENTLY idx_killmails_time_hour
ON killmails(DATE_TRUNC('hour', killmail_time));

-- Weapon analysis optimization for Damage Dealt/Taken and E-War analysis
CREATE INDEX CONCURRENTLY idx_killmail_attackers_weapon
ON killmail_attackers(weapon_type_id) WHERE weapon_type_id IS NOT NULL;

-- Victim corporation temporal optimization (verify if not exists)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_killmails_victim_corp_time
ON killmails(victim_corporation_id, killmail_time DESC);
