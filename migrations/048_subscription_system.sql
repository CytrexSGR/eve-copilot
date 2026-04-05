-- Subscription System Tables
-- Migration: 048_subscription_system.sql

-- Customers (EVE Character = Account)
CREATE TABLE IF NOT EXISTS customers (
    character_id BIGINT PRIMARY KEY,
    character_name VARCHAR(255) NOT NULL,
    corporation_id BIGINT,
    alliance_id BIGINT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_login TIMESTAMPTZ
);

-- Products (flexible pricing)
CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    slug VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    price_isk BIGINT NOT NULL,
    duration_days INT DEFAULT 30,
    is_active BOOLEAN DEFAULT true,
    features JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Subscriptions
CREATE TABLE IF NOT EXISTS subscriptions (
    id SERIAL PRIMARY KEY,
    character_id BIGINT NOT NULL REFERENCES customers(character_id),
    product_id INT NOT NULL REFERENCES products(id),
    starts_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    payment_id INT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_subscriptions_character ON subscriptions(character_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_expires ON subscriptions(expires_at);

-- Service Wallets (ISK receiver characters)
CREATE TABLE IF NOT EXISTS service_wallets (
    id SERIAL PRIMARY KEY,
    character_id BIGINT NOT NULL,
    character_name VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    last_journal_ref_id BIGINT DEFAULT 0
);

-- Payments
CREATE TABLE IF NOT EXISTS payments (
    id SERIAL PRIMARY KEY,
    journal_ref_id BIGINT UNIQUE NOT NULL,
    from_character_id BIGINT NOT NULL,
    from_character_name VARCHAR(255),
    amount BIGINT NOT NULL,
    reason TEXT,
    received_at TIMESTAMPTZ NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    matched_customer_id BIGINT REFERENCES customers(character_id),
    payment_code VARCHAR(20),
    processed_at TIMESTAMPTZ,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);
CREATE INDEX IF NOT EXISTS idx_payments_from ON payments(from_character_id);
CREATE INDEX IF NOT EXISTS idx_payments_code ON payments(payment_code);

-- Payment Codes (fallback matching)
CREATE TABLE IF NOT EXISTS payment_codes (
    code VARCHAR(20) PRIMARY KEY,
    character_id BIGINT REFERENCES customers(character_id),
    product_id INT REFERENCES products(id),
    amount_expected BIGINT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_payment_codes_expires ON payment_codes(expires_at);

-- Feature Flags (route → feature mapping)
CREATE TABLE IF NOT EXISTS feature_flags (
    slug VARCHAR(100) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    route_patterns JSONB DEFAULT '[]'::jsonb,
    is_public BOOLEAN DEFAULT false
);

-- System Config (kill-switches)
CREATE TABLE IF NOT EXISTS system_config (
    key VARCHAR(100) PRIMARY KEY,
    value TEXT NOT NULL,
    description TEXT
);

-- Initial config values (all disabled)
INSERT INTO system_config (key, value, description) VALUES
    ('subscription_enabled', 'false', 'Paywall active?'),
    ('login_enabled', 'false', 'Show login button on public site?'),
    ('wallet_poll_enabled', 'false', 'Check for ISK payments?'),
    ('billing_character_id', '', 'Character ID receiving ISK')
ON CONFLICT (key) DO NOTHING;

-- Initial feature flags for public frontend
INSERT INTO feature_flags (slug, name, route_patterns, is_public) VALUES
    ('alliance-intel', 'Alliance Intelligence', '["/api/wars/*", "/api/intel/*"]', false),
    ('battle-reports', 'Battle Reports', '["/api/battles/*", "/api/reports/*"]', false),
    ('war-economy', 'War Economy Analysis', '["/api/economy/*"]', false),
    ('doctrines', 'Doctrine Analysis', '["/api/doctrines/*"]', true),
    ('panoptikum', 'Panoptikum Overview', '["/api/panoptikum/*"]', false)
ON CONFLICT (slug) DO NOTHING;
