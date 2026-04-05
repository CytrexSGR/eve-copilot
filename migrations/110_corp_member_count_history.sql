-- Migration 110: Corporation Member Count History
-- Track daily member count snapshots for growth/attrition analysis

CREATE TABLE IF NOT EXISTS corporation_member_count_history (
    corporation_id BIGINT NOT NULL,
    snapshot_date DATE NOT NULL,
    member_count INTEGER NOT NULL,
    alliance_id BIGINT,
    PRIMARY KEY (corporation_id, snapshot_date)
);

CREATE INDEX IF NOT EXISTS idx_cmch_date ON corporation_member_count_history(snapshot_date DESC);

-- Seed initial snapshot from current corporations data
INSERT INTO corporation_member_count_history (corporation_id, snapshot_date, member_count, alliance_id)
SELECT corporation_id, CURRENT_DATE, member_count, alliance_id
FROM corporations
WHERE member_count > 0
ON CONFLICT DO NOTHING;
