-- Migration: 004_character_data_tables.sql
-- Description: Create tables for comprehensive character data persistence
-- This enables tracking of wallets, skills, assets, orders, industry jobs, blueprints, and SP history

-- ============================================================================
-- Table 1: character_wallets - Wallet balance history tracking
-- ============================================================================
CREATE TABLE IF NOT EXISTS character_wallets (
    id SERIAL PRIMARY KEY,
    character_id INTEGER NOT NULL REFERENCES characters(character_id) ON DELETE CASCADE,
    balance NUMERIC(20, 2) NOT NULL,  -- ISK balance (supports up to quintillions)
    recorded_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),

    -- Index for efficient queries by character and time
    CONSTRAINT character_wallets_unique_snapshot UNIQUE (character_id, recorded_at)
);

CREATE INDEX IF NOT EXISTS idx_character_wallets_character_id
    ON character_wallets(character_id);
CREATE INDEX IF NOT EXISTS idx_character_wallets_recorded_at
    ON character_wallets(recorded_at);

COMMENT ON TABLE character_wallets IS 'Historical wallet balance snapshots for characters';
COMMENT ON COLUMN character_wallets.balance IS 'ISK balance at the recorded timestamp';

-- ============================================================================
-- Table 2: character_skills - Current skill snapshots
-- ============================================================================
CREATE TABLE IF NOT EXISTS character_skills (
    id SERIAL PRIMARY KEY,
    character_id INTEGER NOT NULL REFERENCES characters(character_id) ON DELETE CASCADE,
    skill_id INTEGER NOT NULL,                    -- EVE type_id for the skill
    skill_name VARCHAR(255),                       -- Cached skill name
    active_skill_level INTEGER NOT NULL DEFAULT 0, -- Current active level (0-5)
    trained_skill_level INTEGER NOT NULL DEFAULT 0, -- Trained level (may differ with implants)
    skillpoints_in_skill BIGINT NOT NULL DEFAULT 0, -- SP in this specific skill
    last_synced TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),

    -- Each character can only have one entry per skill
    CONSTRAINT character_skills_unique UNIQUE (character_id, skill_id)
);

CREATE INDEX IF NOT EXISTS idx_character_skills_character_id
    ON character_skills(character_id);
CREATE INDEX IF NOT EXISTS idx_character_skills_skill_id
    ON character_skills(skill_id);

COMMENT ON TABLE character_skills IS 'Current skill levels and skillpoints for each character';
COMMENT ON COLUMN character_skills.active_skill_level IS 'Effective skill level (affected by implants)';
COMMENT ON COLUMN character_skills.trained_skill_level IS 'Base trained level without modifiers';

-- ============================================================================
-- Table 3: character_skill_queue - Training queue tracking
-- ============================================================================
CREATE TABLE IF NOT EXISTS character_skill_queue (
    id SERIAL PRIMARY KEY,
    character_id INTEGER NOT NULL REFERENCES characters(character_id) ON DELETE CASCADE,
    queue_position INTEGER NOT NULL,              -- Position in queue (0 = currently training)
    skill_id INTEGER NOT NULL,                    -- EVE type_id for the skill
    skill_name VARCHAR(255),                       -- Cached skill name
    finished_level INTEGER NOT NULL,              -- Level being trained to (1-5)
    start_date TIMESTAMP WITHOUT TIME ZONE,       -- When training started/will start
    finish_date TIMESTAMP WITHOUT TIME ZONE,      -- When training will complete
    training_start_sp BIGINT,                     -- SP when training started
    level_start_sp BIGINT,                        -- SP required to start this level
    level_end_sp BIGINT,                          -- SP required to complete this level
    last_synced TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),

    -- Each character can only have one skill at each queue position
    CONSTRAINT character_skill_queue_unique UNIQUE (character_id, queue_position)
);

CREATE INDEX IF NOT EXISTS idx_character_skill_queue_character_id
    ON character_skill_queue(character_id);
CREATE INDEX IF NOT EXISTS idx_character_skill_queue_finish_date
    ON character_skill_queue(finish_date);

COMMENT ON TABLE character_skill_queue IS 'Current skill training queue for each character';
COMMENT ON COLUMN character_skill_queue.queue_position IS '0 = currently training, 1+ = queued';

-- ============================================================================
-- Table 4: character_assets - Item inventory tracking
-- ============================================================================
CREATE TABLE IF NOT EXISTS character_assets (
    id SERIAL PRIMARY KEY,
    character_id INTEGER NOT NULL REFERENCES characters(character_id) ON DELETE CASCADE,
    item_id BIGINT NOT NULL,                      -- Unique item instance ID
    type_id INTEGER NOT NULL,                     -- EVE type_id of the item
    type_name VARCHAR(255),                        -- Cached item name
    location_id BIGINT NOT NULL,                  -- Station/structure/container ID
    location_name VARCHAR(255),                    -- Cached location name
    location_flag VARCHAR(64),                    -- Slot/location within container (e.g., 'Hangar', 'Cargo')
    location_type VARCHAR(32),                    -- 'station', 'solar_system', 'item', 'other'
    quantity INTEGER NOT NULL DEFAULT 1,          -- Stack size
    is_singleton BOOLEAN NOT NULL DEFAULT FALSE,  -- True if item is assembled/not stackable
    is_blueprint_copy BOOLEAN,                    -- True if item is a BPC (only for blueprints)
    last_synced TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),

    -- Each item instance is unique per character
    CONSTRAINT character_assets_unique UNIQUE (character_id, item_id)
);

CREATE INDEX IF NOT EXISTS idx_character_assets_character_id
    ON character_assets(character_id);
CREATE INDEX IF NOT EXISTS idx_character_assets_type_id
    ON character_assets(type_id);
CREATE INDEX IF NOT EXISTS idx_character_assets_location_id
    ON character_assets(location_id);

COMMENT ON TABLE character_assets IS 'All items owned by characters across all locations';
COMMENT ON COLUMN character_assets.is_singleton IS 'True for assembled ships/modules that cannot be stacked';

-- ============================================================================
-- Table 5: character_orders - Market orders tracking
-- ============================================================================
CREATE TABLE IF NOT EXISTS character_orders (
    id SERIAL PRIMARY KEY,
    character_id INTEGER NOT NULL REFERENCES characters(character_id) ON DELETE CASCADE,
    order_id BIGINT NOT NULL,                     -- Unique market order ID
    type_id INTEGER NOT NULL,                     -- EVE type_id of item being traded
    type_name VARCHAR(255),                        -- Cached item name
    location_id BIGINT NOT NULL,                  -- Station/structure where order is placed
    location_name VARCHAR(255),                    -- Cached location name
    region_id INTEGER NOT NULL,                   -- Region where order is valid
    is_buy_order BOOLEAN NOT NULL,                -- True = buy order, False = sell order
    price NUMERIC(20, 2) NOT NULL,                -- Price per unit
    volume_total INTEGER NOT NULL,                -- Original volume
    volume_remain INTEGER NOT NULL,               -- Remaining volume
    min_volume INTEGER DEFAULT 1,                 -- Minimum volume per transaction
    range VARCHAR(32),                            -- Order range (for buy orders)
    duration INTEGER,                             -- Order duration in days
    escrow NUMERIC(20, 2),                        -- ISK in escrow (for buy orders)
    is_corporation BOOLEAN DEFAULT FALSE,         -- True if corporation order
    issued TIMESTAMP WITHOUT TIME ZONE,           -- When order was placed
    state VARCHAR(32) DEFAULT 'active',           -- 'active', 'expired', 'cancelled'
    last_synced TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),

    -- Each order is unique
    CONSTRAINT character_orders_unique UNIQUE (character_id, order_id)
);

CREATE INDEX IF NOT EXISTS idx_character_orders_character_id
    ON character_orders(character_id);
CREATE INDEX IF NOT EXISTS idx_character_orders_type_id
    ON character_orders(type_id);
CREATE INDEX IF NOT EXISTS idx_character_orders_location_id
    ON character_orders(location_id);
CREATE INDEX IF NOT EXISTS idx_character_orders_state
    ON character_orders(state);

COMMENT ON TABLE character_orders IS 'Active and historical market orders for characters';
COMMENT ON COLUMN character_orders.escrow IS 'ISK held in escrow for buy orders';

-- ============================================================================
-- Table 6: character_industry_jobs - Industry jobs tracking
-- ============================================================================
CREATE TABLE IF NOT EXISTS character_industry_jobs (
    id SERIAL PRIMARY KEY,
    character_id INTEGER NOT NULL REFERENCES characters(character_id) ON DELETE CASCADE,
    job_id BIGINT NOT NULL,                       -- Unique industry job ID
    installer_id INTEGER NOT NULL,                -- Character who started the job
    facility_id BIGINT NOT NULL,                  -- Station/structure where job runs
    facility_name VARCHAR(255),                    -- Cached facility name
    activity_id INTEGER NOT NULL,                 -- 1=Manufacturing, 3=TE Research, 4=ME Research, 5=Copying, 8=Invention
    activity_name VARCHAR(64),                    -- Cached activity name
    blueprint_id BIGINT NOT NULL,                 -- Item ID of the blueprint used
    blueprint_type_id INTEGER NOT NULL,           -- Type ID of the blueprint
    blueprint_type_name VARCHAR(255),              -- Cached blueprint name
    blueprint_location_id BIGINT,                 -- Where blueprint is stored
    output_location_id BIGINT,                    -- Where output will be delivered
    product_type_id INTEGER,                      -- Type ID of the product (for manufacturing/invention)
    product_type_name VARCHAR(255),                -- Cached product name
    runs INTEGER NOT NULL,                        -- Number of runs
    cost NUMERIC(20, 2),                          -- Job installation cost
    licensed_runs INTEGER,                        -- Runs available on BPC (for copying)
    probability NUMERIC(5, 4),                    -- Success probability (for invention)
    status VARCHAR(32) NOT NULL,                  -- 'active', 'paused', 'ready', 'delivered', 'cancelled', 'reverted'
    start_date TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    end_date TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    pause_date TIMESTAMP WITHOUT TIME ZONE,       -- When job was paused (if applicable)
    completed_date TIMESTAMP WITHOUT TIME ZONE,   -- When job was delivered
    completed_character_id INTEGER,               -- Who delivered the job
    successful_runs INTEGER,                      -- Successful runs (for invention)
    last_synced TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),

    -- Each job is unique
    CONSTRAINT character_industry_jobs_unique UNIQUE (character_id, job_id)
);

CREATE INDEX IF NOT EXISTS idx_character_industry_jobs_character_id
    ON character_industry_jobs(character_id);
CREATE INDEX IF NOT EXISTS idx_character_industry_jobs_status
    ON character_industry_jobs(status);
CREATE INDEX IF NOT EXISTS idx_character_industry_jobs_end_date
    ON character_industry_jobs(end_date);
CREATE INDEX IF NOT EXISTS idx_character_industry_jobs_activity_id
    ON character_industry_jobs(activity_id);

COMMENT ON TABLE character_industry_jobs IS 'Manufacturing, research, copying, and invention jobs';
COMMENT ON COLUMN character_industry_jobs.activity_id IS '1=Manufacturing, 3=TE, 4=ME, 5=Copying, 8=Invention';

-- ============================================================================
-- Table 7: character_blueprints - Blueprint library tracking
-- ============================================================================
CREATE TABLE IF NOT EXISTS character_blueprints (
    id SERIAL PRIMARY KEY,
    character_id INTEGER NOT NULL REFERENCES characters(character_id) ON DELETE CASCADE,
    item_id BIGINT NOT NULL,                      -- Unique item instance ID
    type_id INTEGER NOT NULL,                     -- EVE type_id of the blueprint
    type_name VARCHAR(255),                        -- Cached blueprint name
    location_id BIGINT NOT NULL,                  -- Station/structure/container ID
    location_name VARCHAR(255),                    -- Cached location name
    location_flag VARCHAR(64),                    -- Slot/location within container
    quantity INTEGER NOT NULL DEFAULT -1,         -- -1 = original (BPO), -2 = copy (BPC)
    time_efficiency INTEGER NOT NULL DEFAULT 0,   -- TE research level (0-20)
    material_efficiency INTEGER NOT NULL DEFAULT 0, -- ME research level (0-10)
    runs INTEGER NOT NULL DEFAULT -1,             -- -1 for BPO, positive for BPC remaining runs
    last_synced TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),

    -- Each blueprint instance is unique per character
    CONSTRAINT character_blueprints_unique UNIQUE (character_id, item_id)
);

CREATE INDEX IF NOT EXISTS idx_character_blueprints_character_id
    ON character_blueprints(character_id);
CREATE INDEX IF NOT EXISTS idx_character_blueprints_type_id
    ON character_blueprints(type_id);
CREATE INDEX IF NOT EXISTS idx_character_blueprints_location_id
    ON character_blueprints(location_id);

COMMENT ON TABLE character_blueprints IS 'Blueprint originals and copies owned by characters';
COMMENT ON COLUMN character_blueprints.quantity IS '-1 = BPO, -2 = BPC (EVE convention)';
COMMENT ON COLUMN character_blueprints.runs IS '-1 for BPO (unlimited), positive for BPC remaining runs';

-- ============================================================================
-- Table 8: character_sp_history - Skillpoint tracking over time
-- ============================================================================
CREATE TABLE IF NOT EXISTS character_sp_history (
    id SERIAL PRIMARY KEY,
    character_id INTEGER NOT NULL REFERENCES characters(character_id) ON DELETE CASCADE,
    total_sp BIGINT NOT NULL,                     -- Total skillpoints
    unallocated_sp BIGINT NOT NULL DEFAULT 0,     -- Unallocated SP from extractors/injectors
    recorded_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),

    -- Unique snapshot per character per timestamp
    CONSTRAINT character_sp_history_unique UNIQUE (character_id, recorded_at)
);

CREATE INDEX IF NOT EXISTS idx_character_sp_history_character_id
    ON character_sp_history(character_id);
CREATE INDEX IF NOT EXISTS idx_character_sp_history_recorded_at
    ON character_sp_history(recorded_at);

COMMENT ON TABLE character_sp_history IS 'Historical skillpoint totals for tracking SP growth';
COMMENT ON COLUMN character_sp_history.unallocated_sp IS 'Free SP from skill extractors or daily rewards';

-- ============================================================================
-- Table 9: character_sync_status - Sync tracking for each data type
-- ============================================================================
CREATE TABLE IF NOT EXISTS character_sync_status (
    character_id INTEGER PRIMARY KEY REFERENCES characters(character_id) ON DELETE CASCADE,
    wallets_synced_at TIMESTAMP WITHOUT TIME ZONE,
    skills_synced_at TIMESTAMP WITHOUT TIME ZONE,
    skill_queue_synced_at TIMESTAMP WITHOUT TIME ZONE,
    assets_synced_at TIMESTAMP WITHOUT TIME ZONE,
    orders_synced_at TIMESTAMP WITHOUT TIME ZONE,
    industry_jobs_synced_at TIMESTAMP WITHOUT TIME ZONE,
    blueprints_synced_at TIMESTAMP WITHOUT TIME ZONE,
    sp_history_synced_at TIMESTAMP WITHOUT TIME ZONE,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE character_sync_status IS 'Tracks last sync time for each character data type';
COMMENT ON COLUMN character_sync_status.wallets_synced_at IS 'Last successful wallet balance sync';
COMMENT ON COLUMN character_sync_status.skills_synced_at IS 'Last successful skills sync';
COMMENT ON COLUMN character_sync_status.assets_synced_at IS 'Last successful assets sync';

-- ============================================================================
-- Summary of created tables:
-- 1. character_wallets - Wallet balance history
-- 2. character_skills - Current skill snapshots
-- 3. character_skill_queue - Training queue
-- 4. character_assets - Item inventory
-- 5. character_orders - Market orders
-- 6. character_industry_jobs - Industry jobs
-- 7. character_blueprints - Blueprint library
-- 8. character_sp_history - SP tracking over time
-- 9. character_sync_status - Sync status tracking
-- ============================================================================
