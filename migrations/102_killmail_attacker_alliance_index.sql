-- Migration 102: Composite index for alliance-based attacker lookups
-- Speeds up offensive queries that filter killmail_attackers by alliance_id + join on killmail_id
-- Mirrors existing idx_km_attackers_corp_id for corporation queries

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_km_attackers_alliance_km
ON killmail_attackers (alliance_id, killmail_id);
