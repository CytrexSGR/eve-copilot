-- Custom fittings table for user-created fits
CREATE TABLE IF NOT EXISTS custom_fittings (
    id SERIAL PRIMARY KEY,
    creator_character_id INTEGER REFERENCES characters(character_id),
    name VARCHAR(255) NOT NULL,
    description TEXT DEFAULT '',
    ship_type_id INTEGER NOT NULL,
    items JSONB NOT NULL DEFAULT '[]',
    tags TEXT[] DEFAULT '{}',
    is_public BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_cf_ship ON custom_fittings(ship_type_id);
CREATE INDEX idx_cf_public ON custom_fittings(is_public) WHERE is_public;
CREATE INDEX idx_cf_tags ON custom_fittings USING GIN(tags);
CREATE INDEX idx_cf_creator ON custom_fittings(creator_character_id);
