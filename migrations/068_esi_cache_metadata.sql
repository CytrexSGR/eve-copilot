-- Migration 068: ESI Cache Metadata
-- Tracks ETag cache entries for monitoring and cleanup.
-- Actual cache data lives in Redis; this table provides observability.

CREATE TABLE IF NOT EXISTS esi_cache_metadata (
    endpoint       TEXT PRIMARY KEY,
    etag           TEXT NOT NULL,
    last_fetched   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_modified  TIMESTAMPTZ,
    expires_at     TIMESTAMPTZ,
    hit_count      INTEGER NOT NULL DEFAULT 0,
    byte_size      INTEGER,
    service_name   VARCHAR(64)
);

CREATE INDEX IF NOT EXISTS idx_esi_cache_expires
    ON esi_cache_metadata (expires_at)
    WHERE expires_at IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_esi_cache_service
    ON esi_cache_metadata (service_name);

COMMENT ON TABLE esi_cache_metadata IS 'Observability table for ESI ETag cache entries stored in Redis';
COMMENT ON COLUMN esi_cache_metadata.endpoint IS 'ESI endpoint path (e.g. /characters/12345/wallet/)';
COMMENT ON COLUMN esi_cache_metadata.hit_count IS 'Number of 304 Not Modified responses served from cache';

DO $$
BEGIN
    RAISE NOTICE '✅ Migration 068 complete: esi_cache_metadata table created';
END $$;
