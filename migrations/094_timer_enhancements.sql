-- Migration 094: Timer enhancements — jitter window and state transitions

ALTER TABLE structure_timers
    ADD COLUMN IF NOT EXISTS jitter_minutes INT DEFAULT 0,
    ADD COLUMN IF NOT EXISTS timer_window_start TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS timer_window_end TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS state VARCHAR(30) DEFAULT 'pending',
    ADD COLUMN IF NOT EXISTS last_state_change TIMESTAMPTZ DEFAULT NOW();

-- Valid states: pending, reinforced, vulnerable, active, completed, expired
COMMENT ON COLUMN structure_timers.state IS 'pending→reinforced→vulnerable→active→completed|expired';
