-- Migration 096: HR Application Portal

CREATE TABLE IF NOT EXISTS hr_applications (
    id SERIAL PRIMARY KEY,
    character_id BIGINT NOT NULL,
    character_name VARCHAR(200) NOT NULL,
    corporation_id BIGINT,          -- Target corporation
    status VARCHAR(30) DEFAULT 'pending',  -- pending, reviewing, approved, rejected, withdrawn
    motivation TEXT,
    recruiter_id BIGINT,            -- Assigned recruiter character_id
    recruiter_notes TEXT,
    vetting_report_id INT,          -- FK to vetting_reports
    submitted_at TIMESTAMPTZ DEFAULT NOW(),
    reviewed_at TIMESTAMPTZ,
    decided_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_hr_applications_char ON hr_applications(character_id);
CREATE INDEX IF NOT EXISTS idx_hr_applications_status ON hr_applications(status);
CREATE INDEX IF NOT EXISTS idx_hr_applications_corp ON hr_applications(corporation_id);
