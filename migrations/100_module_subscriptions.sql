-- Migration 100: Module-based feature gating tables
-- Replaces tier-based gating with per-module subscriptions.

-- Module subscriptions (individual feature purchases)
CREATE TABLE module_subscriptions (
    id SERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES platform_accounts(id) ON DELETE CASCADE,
    module_name VARCHAR(50) NOT NULL,
    scope JSONB DEFAULT '{}',
    expires_at TIMESTAMPTZ NOT NULL,
    trial_used BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_module_subs_account ON module_subscriptions(account_id);
CREATE INDEX idx_module_subs_module ON module_subscriptions(account_id, module_name);
CREATE INDEX idx_module_subs_active ON module_subscriptions(account_id, expires_at);

-- Organization plans (seat-based)
CREATE TABLE org_plans (
    id SERIAL PRIMARY KEY,
    org_type VARCHAR(20) NOT NULL CHECK (org_type IN ('corporation', 'alliance')),
    org_id BIGINT NOT NULL,
    plan_name VARCHAR(50) NOT NULL,
    heavy_seats INTEGER NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_org_plans_lookup ON org_plans(org_type, org_id);
CREATE INDEX idx_org_plans_active ON org_plans(org_type, org_id, expires_at);

-- Seat assignments for heavy features
CREATE TABLE org_seat_assignments (
    id SERIAL PRIMARY KEY,
    org_plan_id INTEGER NOT NULL REFERENCES org_plans(id) ON DELETE CASCADE,
    character_id BIGINT NOT NULL,
    assigned_by BIGINT NOT NULL,
    assigned_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_org_seats_unique ON org_seat_assignments(org_plan_id, character_id);

-- Module pricing reference table
CREATE TABLE module_pricing (
    module_name VARCHAR(50) PRIMARY KEY,
    display_name VARCHAR(100) NOT NULL,
    category VARCHAR(20) NOT NULL CHECK (category IN ('intel', 'personal', 'entity', 'bundle')),
    base_price_isk BIGINT NOT NULL,
    duration_days INTEGER NOT NULL DEFAULT 30,
    is_active BOOLEAN DEFAULT TRUE
);

-- Seed pricing data
INSERT INTO module_pricing (module_name, display_name, category, base_price_isk) VALUES
    ('warfare_intel', 'Warfare Intel', 'intel', 100000000),
    ('war_economy', 'War Economy', 'intel', 100000000),
    ('wormhole_intel', 'Wormhole Intel', 'intel', 100000000),
    ('doctrine_intel', 'Doctrine Intel', 'intel', 100000000),
    ('battle_analysis', 'Battle Analysis', 'intel', 100000000),
    ('character_suite', 'Character Suite', 'personal', 150000000),
    ('market_analysis', 'Market Analysis', 'personal', 150000000),
    ('corp_intel_1', 'Corp Intel (1 Entity)', 'entity', 50000000),
    ('corp_intel_5', 'Corp Intel (5 Entities)', 'entity', 150000000),
    ('corp_intel_unlimited', 'Corp Intel (Unlimited)', 'entity', 200000000),
    ('alliance_intel_1', 'Alliance Intel (1 Entity)', 'entity', 75000000),
    ('alliance_intel_5', 'Alliance Intel (5 Entities)', 'entity', 200000000),
    ('alliance_intel_unlimited', 'Alliance Intel (Unlimited)', 'entity', 250000000),
    ('powerbloc_intel_1', 'PowerBloc Intel (1 Entity)', 'entity', 100000000),
    ('powerbloc_intel_5', 'PowerBloc Intel (5 Entities)', 'entity', 250000000),
    ('powerbloc_intel_unlimited', 'PowerBloc Intel (Unlimited)', 'entity', 300000000),
    ('intel_pack', 'Intel Pack', 'bundle', 350000000),
    ('entity_pack', 'Entity Pack', 'bundle', 550000000),
    ('pilot_complete', 'Pilot Complete', 'bundle', 1000000000);

-- Extend tier_payments for module codes
ALTER TABLE tier_payments ADD COLUMN IF NOT EXISTS module_name VARCHAR(50);
ALTER TABLE tier_payments ADD COLUMN IF NOT EXISTS scope JSONB;
ALTER TABLE tier_payments ADD COLUMN IF NOT EXISTS is_trial BOOLEAN DEFAULT FALSE;
