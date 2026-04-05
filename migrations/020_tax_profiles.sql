-- migrations/020_tax_profiles.sql
-- Tax & Fee Profiles for Production Cost Calculation

-- Tax Profiles for Broker/Sales Tax
CREATE TABLE IF NOT EXISTS tax_profiles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    character_id BIGINT,  -- NULL = global profile
    broker_fee_buy DECIMAL(5,2) DEFAULT 3.00,
    broker_fee_sell DECIMAL(5,2) DEFAULT 3.00,
    sales_tax DECIMAL(5,2) DEFAULT 3.60,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Only one default per character (or global)
CREATE UNIQUE INDEX IF NOT EXISTS idx_tax_profiles_default
ON tax_profiles(character_id, is_default)
WHERE is_default = TRUE;

CREATE INDEX IF NOT EXISTS idx_tax_profiles_character ON tax_profiles(character_id);

-- Insert default profile
INSERT INTO tax_profiles (name, broker_fee_buy, broker_fee_sell, sales_tax, is_default)
VALUES ('Default (No Skills)', 3.00, 3.00, 3.60, TRUE)
ON CONFLICT DO NOTHING;

COMMENT ON TABLE tax_profiles IS 'Player tax profiles for production cost calculations';
