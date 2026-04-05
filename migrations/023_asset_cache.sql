-- migrations/023_asset_cache.sql
-- Character Asset Cache for shopping list integration

CREATE TABLE IF NOT EXISTS character_asset_cache (
    id SERIAL PRIMARY KEY,
    character_id BIGINT NOT NULL,
    type_id INTEGER NOT NULL,
    type_name VARCHAR(255),
    quantity BIGINT NOT NULL,
    location_id BIGINT,
    location_name VARCHAR(255),
    location_type VARCHAR(50),  -- 'station', 'structure', 'container', 'ship'
    cached_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(character_id, type_id, location_id)
);

CREATE INDEX IF NOT EXISTS idx_asset_cache_character ON character_asset_cache(character_id);
CREATE INDEX IF NOT EXISTS idx_asset_cache_type ON character_asset_cache(type_id);
CREATE INDEX IF NOT EXISTS idx_asset_cache_location ON character_asset_cache(location_id);

-- Add quantity_in_assets column to shopping_list_items if not exists
ALTER TABLE shopping_list_items
ADD COLUMN IF NOT EXISTS quantity_in_assets INTEGER DEFAULT 0;

COMMENT ON TABLE character_asset_cache IS 'Cached character assets from ESI for shopping list deduction';
