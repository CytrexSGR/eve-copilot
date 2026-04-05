-- Corporation name cache (similar to alliance_name_cache)
-- Used for displaying corporation names in kill tooltips

CREATE TABLE IF NOT EXISTS corp_name_cache (
    corporation_id BIGINT PRIMARY KEY,
    corporation_name VARCHAR(255) NOT NULL,
    ticker VARCHAR(10),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_corp_name_cache_name ON corp_name_cache(corporation_name);

-- Insert any existing corporations we have
INSERT INTO corp_name_cache (corporation_id, corporation_name, ticker)
SELECT corporation_id, corporation_name, ticker
FROM corporations
ON CONFLICT (corporation_id) DO NOTHING;
