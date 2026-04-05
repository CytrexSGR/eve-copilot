-- migrations/025_reactions.sql
-- Reaction formulas and moon material prices

CREATE TABLE IF NOT EXISTS reaction_formulas (
    id SERIAL PRIMARY KEY,
    reaction_type_id INTEGER NOT NULL UNIQUE,
    reaction_name VARCHAR(255),
    product_type_id INTEGER NOT NULL,
    product_name VARCHAR(255),
    product_quantity INTEGER NOT NULL,
    reaction_time INTEGER NOT NULL,
    reaction_category VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS reaction_formula_inputs (
    id SERIAL PRIMARY KEY,
    reaction_type_id INTEGER REFERENCES reaction_formulas(reaction_type_id) ON DELETE CASCADE,
    input_type_id INTEGER NOT NULL,
    input_name VARCHAR(255),
    quantity INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS moon_material_prices (
    type_id INTEGER PRIMARY KEY,
    type_name VARCHAR(255),
    jita_sell BIGINT,
    jita_buy BIGINT,
    amarr_sell BIGINT,
    amarr_buy BIGINT,
    volume_daily BIGINT,
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_reaction_product ON reaction_formulas(product_type_id);
CREATE INDEX IF NOT EXISTS idx_reaction_category ON reaction_formulas(reaction_category);
CREATE INDEX IF NOT EXISTS idx_reaction_inputs_type ON reaction_formula_inputs(reaction_type_id);

COMMENT ON TABLE reaction_formulas IS 'EVE reaction formulas from SDE (activityID=11)';
COMMENT ON TABLE reaction_formula_inputs IS 'Input materials for each reaction formula';
COMMENT ON TABLE moon_material_prices IS 'Cached moon material prices for profitability calculations';
