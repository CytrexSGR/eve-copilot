-- 034_trading_goals.sql
-- Trading goals system for daily/weekly/monthly targets

-- Trading goals configuration per character
CREATE TABLE IF NOT EXISTS trading_goals (
    id SERIAL PRIMARY KEY,
    character_id BIGINT NOT NULL,

    -- Goal configuration
    goal_type VARCHAR(20) NOT NULL,  -- daily, weekly, monthly
    target_type VARCHAR(30) NOT NULL,  -- profit, volume, trades, roi

    -- Target values
    target_value DECIMAL(20,2) NOT NULL,  -- Target ISK or count or percentage

    -- Optional filters
    type_id INTEGER,  -- Specific item type (NULL = all items)
    type_name VARCHAR(255),  -- Cached type name

    -- State
    is_active BOOLEAN DEFAULT TRUE,
    notify_on_progress BOOLEAN DEFAULT TRUE,  -- Alert at 50%, 80%, 100%
    notify_on_completion BOOLEAN DEFAULT TRUE,  -- Alert when goal reached

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- Unique constraint per character/period/target type
    UNIQUE(character_id, goal_type, target_type, type_id)
);

CREATE INDEX IF NOT EXISTS idx_trading_goals_character ON trading_goals(character_id);
CREATE INDEX IF NOT EXISTS idx_trading_goals_active ON trading_goals(character_id, is_active) WHERE is_active = TRUE;

-- Goal progress tracking (historical snapshots)
CREATE TABLE IF NOT EXISTS trading_goal_progress (
    id SERIAL PRIMARY KEY,
    goal_id INTEGER NOT NULL REFERENCES trading_goals(id) ON DELETE CASCADE,

    -- Period info
    period_start DATE NOT NULL,  -- Start of the period (day/week/month start)
    period_end DATE NOT NULL,    -- End of the period

    -- Progress values
    current_value DECIMAL(20,2) NOT NULL DEFAULT 0,
    target_value DECIMAL(20,2) NOT NULL,
    progress_percent DECIMAL(5,2) NOT NULL DEFAULT 0,

    -- Completion tracking
    is_completed BOOLEAN DEFAULT FALSE,
    completed_at TIMESTAMP,

    -- Notification tracking
    notified_50 BOOLEAN DEFAULT FALSE,
    notified_80 BOOLEAN DEFAULT FALSE,
    notified_100 BOOLEAN DEFAULT FALSE,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- One progress record per goal per period
    UNIQUE(goal_id, period_start)
);

CREATE INDEX IF NOT EXISTS idx_trading_goal_progress_goal ON trading_goal_progress(goal_id);
CREATE INDEX IF NOT EXISTS idx_trading_goal_progress_period ON trading_goal_progress(period_start, period_end);

-- Goal achievements (completed goals history)
CREATE TABLE IF NOT EXISTS trading_goal_achievements (
    id SERIAL PRIMARY KEY,
    character_id BIGINT NOT NULL,
    goal_id INTEGER REFERENCES trading_goals(id) ON DELETE SET NULL,

    -- Goal details (snapshot for history even if goal deleted)
    goal_type VARCHAR(20) NOT NULL,
    target_type VARCHAR(30) NOT NULL,
    target_value DECIMAL(20,2) NOT NULL,
    achieved_value DECIMAL(20,2) NOT NULL,

    -- Period
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,

    -- Achievement details
    exceeded_by_percent DECIMAL(5,2),  -- How much over target
    achievement_date TIMESTAMP NOT NULL DEFAULT NOW(),

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_trading_goal_achievements_char ON trading_goal_achievements(character_id);
CREATE INDEX IF NOT EXISTS idx_trading_goal_achievements_date ON trading_goal_achievements(achievement_date DESC);

-- Function to auto-update updated_at
CREATE OR REPLACE FUNCTION update_trading_goals_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers for auto-update
DROP TRIGGER IF EXISTS trading_goals_updated ON trading_goals;
CREATE TRIGGER trading_goals_updated
    BEFORE UPDATE ON trading_goals
    FOR EACH ROW
    EXECUTE FUNCTION update_trading_goals_timestamp();

DROP TRIGGER IF EXISTS trading_goal_progress_updated ON trading_goal_progress;
CREATE TRIGGER trading_goal_progress_updated
    BEFORE UPDATE ON trading_goal_progress
    FOR EACH ROW
    EXECUTE FUNCTION update_trading_goals_timestamp();

-- Comments
COMMENT ON TABLE trading_goals IS 'Trading goal configuration (daily/weekly/monthly targets)';
COMMENT ON TABLE trading_goal_progress IS 'Current period progress tracking for active goals';
COMMENT ON TABLE trading_goal_achievements IS 'Historical record of completed goals';
COMMENT ON COLUMN trading_goals.target_type IS 'profit = ISK profit, volume = items traded, trades = number of transactions, roi = return on investment %';
