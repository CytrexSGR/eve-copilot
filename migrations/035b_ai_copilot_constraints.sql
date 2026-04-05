-- migrations/035b_ai_copilot_constraints.sql
-- Additional constraints and columns for AI Copilot tables

-- Add CHECK constraints for data validation
ALTER TABLE ai_plans ADD CONSTRAINT check_progress_pct_range
    CHECK (progress_pct >= 0 AND progress_pct <= 100);

ALTER TABLE ai_context ADD CONSTRAINT check_confidence_range
    CHECK (confidence >= 0 AND confidence <= 1);

-- Add updated_at column to ai_plan_milestones
ALTER TABLE ai_plan_milestones ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW();
