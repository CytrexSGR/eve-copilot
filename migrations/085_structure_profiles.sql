-- Migration 085: Structure Profiles Enhancement
-- Phase 4: Industry Calculation Engine - Engineering Complex rig bonuses

-- Add missing columns for rig bonuses and security scaling
ALTER TABLE facility_profiles
    ADD COLUMN IF NOT EXISTS security VARCHAR(10) DEFAULT 'high',
    ADD COLUMN IF NOT EXISTS rig_type_id INTEGER,
    ADD COLUMN IF NOT EXISTS rig_me_bonus NUMERIC(5,4) DEFAULT 0,
    ADD COLUMN IF NOT EXISTS rig_te_bonus NUMERIC(5,4) DEFAULT 0;

-- Seed common Engineering Complex profiles
-- Structure base bonuses (from game mechanics):
--   EC (Raitaru/Azbel/Sotiyo): 1% ME, 15% TE, variable tax
--   Refinery (Athanor/Tatara): reaction bonuses only
--   NPC Station: 0% structure bonus, 10% tax

-- Update existing NPC Station entry
UPDATE facility_profiles
SET structure_type = 'station', security = 'high'
WHERE name = 'NPC Station (Default)';

-- Raitaru (Small EC) - Nullsec with T2 ME rig
INSERT INTO facility_profiles
    (name, system_id, structure_type, security, me_bonus, te_bonus, cost_bonus,
     facility_tax, rig_type_id, rig_me_bonus, rig_te_bonus)
VALUES
    ('Raitaru (Nullsec, T2 ME Rig)', 0, 'raitaru', 'null',
     1.00, 15.00, 0.00, 0.25,
     NULL, 4.20, 0.00),
    ('Raitaru (Highsec, T1 ME Rig)', 0, 'raitaru', 'high',
     1.00, 15.00, 0.00, 0.25,
     NULL, 2.00, 0.00),
    ('Azbel (Nullsec, T2 ME Rig)', 0, 'azbel', 'null',
     1.00, 15.00, 0.00, 0.25,
     NULL, 4.20, 0.00),
    ('Sotiyo (Nullsec, T2 ME Rig)', 0, 'sotiyo', 'null',
     1.00, 15.00, 0.00, 0.25,
     NULL, 4.20, 0.00),
    ('Sotiyo (Nullsec, T2 ME Rig, Capitals)', 0, 'sotiyo', 'null',
     1.00, 15.00, 0.00, 0.25,
     NULL, 4.20, 0.00),
    ('Tatara (Nullsec, T2 Reaction Rig)', 0, 'tatara', 'null',
     0.00, 0.00, 0.00, 0.25,
     NULL, 0.00, 0.00),
    ('Athanor (Nullsec)', 0, 'athanor', 'null',
     0.00, 0.00, 0.00, 0.25,
     NULL, 0.00, 0.00)
ON CONFLICT DO NOTHING;

-- Security scaling reference (stored as comments, applied in code):
-- Highsec:  rig_bonus * 1.0
-- Lowsec:   rig_bonus * 1.9
-- Nullsec:  rig_bonus * 2.1
-- Wormhole: rig_bonus * 2.1
