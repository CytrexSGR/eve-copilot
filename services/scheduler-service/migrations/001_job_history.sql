-- 001_job_history.sql
-- Persistent job execution history for scheduler-service

CREATE TABLE IF NOT EXISTS scheduler_job_history (
    id SERIAL PRIMARY KEY,
    job_id VARCHAR(100) NOT NULL,
    job_name VARCHAR(255),
    status VARCHAR(20) NOT NULL,  -- pending, running, success, failed, skipped
    started_at TIMESTAMP NOT NULL,
    finished_at TIMESTAMP,
    duration_ms INTEGER,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_job_history_job_id ON scheduler_job_history(job_id);
CREATE INDEX IF NOT EXISTS idx_job_history_status ON scheduler_job_history(status);
CREATE INDEX IF NOT EXISTS idx_job_history_started ON scheduler_job_history(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_job_history_job_status ON scheduler_job_history(job_id, status);

-- Composite index for dashboard queries
CREATE INDEX IF NOT EXISTS idx_job_history_recent ON scheduler_job_history(job_id, started_at DESC);

-- Cleanup old history (keep 30 days)
CREATE OR REPLACE FUNCTION cleanup_old_job_history() RETURNS void AS $$
BEGIN
    DELETE FROM scheduler_job_history
    WHERE created_at < NOW() - INTERVAL '30 days';
END;
$$ LANGUAGE plpgsql;
