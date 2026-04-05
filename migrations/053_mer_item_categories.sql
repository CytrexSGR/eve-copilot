-- migrations/053_mer_item_categories.sql
-- MER Item Categories for Station Trading filters

CREATE TABLE IF NOT EXISTS mer_item_categories (
    type_id INTEGER PRIMARY KEY,
    primary_index VARCHAR(50) NOT NULL,
    sub_index VARCHAR(50) NOT NULL,
    category_name VARCHAR(100),
    imported_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mer_primary_index ON mer_item_categories(primary_index);
CREATE INDEX IF NOT EXISTS idx_mer_sub_index ON mer_item_categories(sub_index);

COMMENT ON TABLE mer_item_categories IS 'Item categories from EVE Monthly Economic Report (MER)';
