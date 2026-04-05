-- Add charges column to custom_fittings table
-- Stores map of slot flag to charge type_id: {"27": 12345, "28": 12345}
ALTER TABLE custom_fittings
ADD COLUMN IF NOT EXISTS charges JSONB DEFAULT '{}';
