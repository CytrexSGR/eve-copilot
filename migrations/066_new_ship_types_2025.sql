-- Migration 066: Add new EVE ship types from Catalyst/Legion expansions (2025)
-- These types are missing from the SDE but appear in killmails.

-- New groups
INSERT INTO "invGroups" ("groupID", "categoryID", "groupName", "published")
VALUES
    (4902, 6, 'Expedition Command Ship', 1),
    (4913, 22, 'Mobile Phase Anchor', 1)
ON CONFLICT ("groupID") DO NOTHING;

-- New types
INSERT INTO "invTypes" ("typeID", "groupID", "typeName", "published")
VALUES
    (89607, 4902, 'Odysseus', 1),             -- Expedition Command Ship (Catalyst expansion)
    (89647, 420, 'Pioneer Consortium Issue', 1), -- Destroyer (mining variant)
    (89648, 25, 'Venture Consortium Issue', 1),  -- Frigate (mining variant)
    (89649, 1534, 'Outrider', 1),              -- Command Destroyer
    (90037, 4913, 'Mobile Phase Anchor', 1),   -- Deployable
    (91174, 420, 'Perseverance', 1)            -- Destroyer
ON CONFLICT ("typeID") DO NOTHING;
