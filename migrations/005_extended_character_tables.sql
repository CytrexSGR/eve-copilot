-- Migration: 005_extended_character_tables.sql
-- Description: Create tables for extended character data from new ESI scopes
-- This enables tracking of location, online status, clones, implants, fatigue,
-- loyalty points, contacts, standings, fittings, killmails, contracts, and corp assets

-- ============================================================================
-- Table 1: character_location - Current character location
-- ============================================================================
CREATE TABLE IF NOT EXISTS character_location (
    character_id INTEGER PRIMARY KEY REFERENCES characters(character_id) ON DELETE CASCADE,
    solar_system_id INTEGER,                      -- Current solar system
    station_id BIGINT,                            -- Current station (if docked)
    structure_id BIGINT,                          -- Current structure (if in player structure)
    last_updated TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_character_location_solar_system_id
    ON character_location(solar_system_id);

COMMENT ON TABLE character_location IS 'Current location for each character';
COMMENT ON COLUMN character_location.solar_system_id IS 'Solar system where character is located';
COMMENT ON COLUMN character_location.station_id IS 'NPC station ID if docked in station';
COMMENT ON COLUMN character_location.structure_id IS 'Player structure ID if docked in structure';

-- ============================================================================
-- Table 2: character_online_status - Online history tracking
-- ============================================================================
CREATE TABLE IF NOT EXISTS character_online_status (
    id SERIAL PRIMARY KEY,
    character_id INTEGER NOT NULL REFERENCES characters(character_id) ON DELETE CASCADE,
    is_online BOOLEAN NOT NULL,                   -- Current online status
    last_login TIMESTAMP WITHOUT TIME ZONE,       -- Last login timestamp
    last_logout TIMESTAMP WITHOUT TIME ZONE,      -- Last logout timestamp
    logins INTEGER,                               -- Total login count
    recorded_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_character_online_status_character_id
    ON character_online_status(character_id);
CREATE INDEX IF NOT EXISTS idx_character_online_status_recorded_at
    ON character_online_status(recorded_at);

COMMENT ON TABLE character_online_status IS 'Online status history for characters';
COMMENT ON COLUMN character_online_status.logins IS 'Total number of logins since character creation';

-- ============================================================================
-- Table 3: character_ship - Current ship tracking
-- ============================================================================
CREATE TABLE IF NOT EXISTS character_ship (
    character_id INTEGER PRIMARY KEY REFERENCES characters(character_id) ON DELETE CASCADE,
    ship_item_id BIGINT NOT NULL,                 -- Unique item instance ID of the ship
    ship_type_id INTEGER NOT NULL,                -- EVE type_id of the ship
    ship_name VARCHAR(255),                       -- Player-given ship name
    ship_type_name VARCHAR(255),                  -- Ship type name (e.g., 'Rifter')
    last_updated TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_character_ship_ship_type_id
    ON character_ship(ship_type_id);

COMMENT ON TABLE character_ship IS 'Currently active ship for each character';
COMMENT ON COLUMN character_ship.ship_item_id IS 'Unique item instance ID of the active ship';
COMMENT ON COLUMN character_ship.ship_name IS 'Custom name given to the ship by the player';

-- ============================================================================
-- Table 4: character_clones - Jump clones tracking
-- ============================================================================
CREATE TABLE IF NOT EXISTS character_clones (
    id SERIAL PRIMARY KEY,
    character_id INTEGER NOT NULL REFERENCES characters(character_id) ON DELETE CASCADE,
    jump_clone_id INTEGER NOT NULL,               -- ESI jump clone ID
    location_id BIGINT NOT NULL,                  -- Station/structure where clone is located
    location_type VARCHAR(32),                    -- 'station' or 'structure'
    implants JSONB,                               -- Array of implant type_ids installed
    last_synced TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),

    -- Each jump clone is unique per character
    CONSTRAINT character_clones_unique UNIQUE (character_id, jump_clone_id)
);

CREATE INDEX IF NOT EXISTS idx_character_clones_character_id
    ON character_clones(character_id);
CREATE INDEX IF NOT EXISTS idx_character_clones_location_id
    ON character_clones(location_id);

COMMENT ON TABLE character_clones IS 'Jump clones owned by each character';
COMMENT ON COLUMN character_clones.implants IS 'JSON array of implant type_ids installed in this clone';

-- ============================================================================
-- Table 5: character_implants - Active implants in current clone
-- ============================================================================
CREATE TABLE IF NOT EXISTS character_implants (
    id SERIAL PRIMARY KEY,
    character_id INTEGER NOT NULL REFERENCES characters(character_id) ON DELETE CASCADE,
    implant_type_id INTEGER NOT NULL,             -- EVE type_id of the implant
    implant_name VARCHAR(255),                    -- Cached implant name
    slot INTEGER,                                 -- Implant slot (1-10)

    -- Each implant type is unique per character (current clone)
    CONSTRAINT character_implants_unique UNIQUE (character_id, implant_type_id)
);

CREATE INDEX IF NOT EXISTS idx_character_implants_character_id
    ON character_implants(character_id);
CREATE INDEX IF NOT EXISTS idx_character_implants_implant_type_id
    ON character_implants(implant_type_id);

COMMENT ON TABLE character_implants IS 'Active implants in the current clone for each character';
COMMENT ON COLUMN character_implants.slot IS 'Implant slot number (1-10)';

-- ============================================================================
-- Table 6: character_fatigue - Jump fatigue tracking
-- ============================================================================
CREATE TABLE IF NOT EXISTS character_fatigue (
    character_id INTEGER PRIMARY KEY REFERENCES characters(character_id) ON DELETE CASCADE,
    jump_fatigue_expire_date TIMESTAMP WITHOUT TIME ZONE, -- When fatigue expires
    last_jump_date TIMESTAMP WITHOUT TIME ZONE,           -- Last jump gate/bridge use
    last_update_date TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE character_fatigue IS 'Jump fatigue status for each character';
COMMENT ON COLUMN character_fatigue.jump_fatigue_expire_date IS 'When jump fatigue will expire';
COMMENT ON COLUMN character_fatigue.last_jump_date IS 'Last time character used a jump gate or bridge';

-- ============================================================================
-- Table 7: character_loyalty_points - LP by corporation
-- ============================================================================
CREATE TABLE IF NOT EXISTS character_loyalty_points (
    id SERIAL PRIMARY KEY,
    character_id INTEGER NOT NULL REFERENCES characters(character_id) ON DELETE CASCADE,
    corporation_id INTEGER NOT NULL,              -- Corporation that granted LP
    corporation_name VARCHAR(255),                -- Cached corporation name
    loyalty_points INTEGER NOT NULL DEFAULT 0,    -- LP balance

    -- Each corporation LP balance is unique per character
    CONSTRAINT character_loyalty_points_unique UNIQUE (character_id, corporation_id)
);

CREATE INDEX IF NOT EXISTS idx_character_loyalty_points_character_id
    ON character_loyalty_points(character_id);
CREATE INDEX IF NOT EXISTS idx_character_loyalty_points_corporation_id
    ON character_loyalty_points(corporation_id);

COMMENT ON TABLE character_loyalty_points IS 'Loyalty point balances by corporation for each character';
COMMENT ON COLUMN character_loyalty_points.loyalty_points IS 'Current LP balance with this corporation';

-- ============================================================================
-- Table 8: character_contacts - Contact list
-- ============================================================================
CREATE TABLE IF NOT EXISTS character_contacts (
    id SERIAL PRIMARY KEY,
    character_id INTEGER NOT NULL REFERENCES characters(character_id) ON DELETE CASCADE,
    contact_id INTEGER NOT NULL,                  -- Character/Corp/Alliance ID of contact
    contact_type VARCHAR(32) NOT NULL,            -- 'character', 'corporation', 'alliance', 'faction'
    contact_name VARCHAR(255),                    -- Cached contact name
    standing NUMERIC(4, 2) NOT NULL,              -- Standing value (-10.0 to 10.0)
    is_blocked BOOLEAN NOT NULL DEFAULT FALSE,    -- Contact is blocked
    is_watched BOOLEAN NOT NULL DEFAULT FALSE,    -- Contact is watched
    label_ids JSONB,                              -- Array of label IDs

    -- Each contact is unique per character
    CONSTRAINT character_contacts_unique UNIQUE (character_id, contact_id)
);

CREATE INDEX IF NOT EXISTS idx_character_contacts_character_id
    ON character_contacts(character_id);
CREATE INDEX IF NOT EXISTS idx_character_contacts_contact_id
    ON character_contacts(contact_id);
CREATE INDEX IF NOT EXISTS idx_character_contacts_standing
    ON character_contacts(standing);

COMMENT ON TABLE character_contacts IS 'Contact list for each character';
COMMENT ON COLUMN character_contacts.standing IS 'Standing value from -10.0 (enemy) to 10.0 (excellent)';
COMMENT ON COLUMN character_contacts.label_ids IS 'JSON array of label IDs applied to this contact';

-- ============================================================================
-- Table 9: character_standings - NPC standings
-- ============================================================================
CREATE TABLE IF NOT EXISTS character_standings (
    id SERIAL PRIMARY KEY,
    character_id INTEGER NOT NULL REFERENCES characters(character_id) ON DELETE CASCADE,
    from_id INTEGER NOT NULL,                     -- Faction/Corp/Agent ID
    from_type VARCHAR(32) NOT NULL,               -- 'faction', 'npc_corp', 'agent'
    standing NUMERIC(5, 2) NOT NULL,              -- Standing value (-10.0 to 10.0)

    -- Each standing source is unique per character
    CONSTRAINT character_standings_unique UNIQUE (character_id, from_id)
);

CREATE INDEX IF NOT EXISTS idx_character_standings_character_id
    ON character_standings(character_id);
CREATE INDEX IF NOT EXISTS idx_character_standings_from_id
    ON character_standings(from_id);
CREATE INDEX IF NOT EXISTS idx_character_standings_standing
    ON character_standings(standing);

COMMENT ON TABLE character_standings IS 'NPC standings for each character';
COMMENT ON COLUMN character_standings.from_type IS 'Source type: faction, npc_corp, or agent';
COMMENT ON COLUMN character_standings.standing IS 'Standing value from -10.0 to 10.0';

-- ============================================================================
-- Table 10: character_fittings - Saved ship fittings
-- ============================================================================
CREATE TABLE IF NOT EXISTS character_fittings (
    id SERIAL PRIMARY KEY,
    character_id INTEGER NOT NULL REFERENCES characters(character_id) ON DELETE CASCADE,
    fitting_id INTEGER NOT NULL,                  -- ESI fitting ID
    name VARCHAR(255) NOT NULL,                   -- Fitting name
    description TEXT,                             -- Fitting description
    ship_type_id INTEGER NOT NULL,                -- EVE type_id of the ship
    items JSONB NOT NULL,                         -- Array of fitted items

    -- Each fitting is unique per character
    CONSTRAINT character_fittings_unique UNIQUE (character_id, fitting_id)
);

CREATE INDEX IF NOT EXISTS idx_character_fittings_character_id
    ON character_fittings(character_id);
CREATE INDEX IF NOT EXISTS idx_character_fittings_ship_type_id
    ON character_fittings(ship_type_id);

COMMENT ON TABLE character_fittings IS 'Saved ship fittings for each character';
COMMENT ON COLUMN character_fittings.items IS 'JSON array of fitted items with type_id, flag, quantity';

-- ============================================================================
-- Table 11: character_killmails - Kill history
-- ============================================================================
CREATE TABLE IF NOT EXISTS character_killmails (
    id SERIAL PRIMARY KEY,
    character_id INTEGER NOT NULL REFERENCES characters(character_id) ON DELETE CASCADE,
    killmail_id INTEGER NOT NULL,                 -- ESI killmail ID
    killmail_time TIMESTAMP WITHOUT TIME ZONE NOT NULL, -- When kill occurred
    solar_system_id INTEGER NOT NULL,             -- System where kill occurred
    victim_ship_type_id INTEGER,                  -- Ship type that was destroyed
    is_victim BOOLEAN NOT NULL DEFAULT FALSE,     -- True if character was the victim
    is_final_blow BOOLEAN NOT NULL DEFAULT FALSE, -- True if character got final blow
    damage_done INTEGER,                          -- Damage dealt (if attacker)
    zkb_hash VARCHAR(64),                         -- zKillboard hash for linking
    zkb_total_value NUMERIC(20, 2),               -- Total ISK value from zKillboard

    -- Each killmail is unique per character
    CONSTRAINT character_killmails_unique UNIQUE (character_id, killmail_id)
);

CREATE INDEX IF NOT EXISTS idx_character_killmails_character_id
    ON character_killmails(character_id);
CREATE INDEX IF NOT EXISTS idx_character_killmails_killmail_id
    ON character_killmails(killmail_id);
CREATE INDEX IF NOT EXISTS idx_character_killmails_killmail_time
    ON character_killmails(killmail_time);
CREATE INDEX IF NOT EXISTS idx_character_killmails_solar_system_id
    ON character_killmails(solar_system_id);

COMMENT ON TABLE character_killmails IS 'Kill history for each character (both as attacker and victim)';
COMMENT ON COLUMN character_killmails.is_victim IS 'True if character was destroyed in this killmail';
COMMENT ON COLUMN character_killmails.zkb_total_value IS 'Total ISK value from zKillboard';

-- ============================================================================
-- Table 12: character_contracts - Contract history
-- ============================================================================
CREATE TABLE IF NOT EXISTS character_contracts (
    id SERIAL PRIMARY KEY,
    character_id INTEGER NOT NULL REFERENCES characters(character_id) ON DELETE CASCADE,
    contract_id INTEGER NOT NULL,                 -- ESI contract ID
    type VARCHAR(32) NOT NULL,                    -- 'unknown', 'item_exchange', 'auction', 'courier', 'loan'
    status VARCHAR(32) NOT NULL,                  -- Contract status
    title VARCHAR(255),                           -- Contract title
    price NUMERIC(20, 2),                         -- Price for item exchange/auction
    reward NUMERIC(20, 2),                        -- Reward for courier contracts
    collateral NUMERIC(20, 2),                    -- Collateral for courier contracts
    volume NUMERIC(20, 4),                        -- Volume in m3
    issuer_id INTEGER NOT NULL,                   -- Character who created contract
    issuer_corporation_id INTEGER NOT NULL,       -- Corporation of issuer
    acceptor_id INTEGER,                          -- Who accepted the contract
    assignee_id INTEGER,                          -- Who contract is assigned to
    availability VARCHAR(32),                     -- 'public', 'personal', 'corporation', 'alliance'
    start_location_id BIGINT,                     -- Start location for courier
    end_location_id BIGINT,                       -- End location for courier
    days_to_complete INTEGER,                     -- Days to complete courier
    date_issued TIMESTAMP WITHOUT TIME ZONE,      -- When contract was created
    date_expired TIMESTAMP WITHOUT TIME ZONE,     -- When contract expires
    date_accepted TIMESTAMP WITHOUT TIME ZONE,    -- When contract was accepted
    date_completed TIMESTAMP WITHOUT TIME ZONE,   -- When contract was completed
    for_corporation BOOLEAN DEFAULT FALSE,        -- True if corporation contract

    -- Each contract is unique per character
    CONSTRAINT character_contracts_unique UNIQUE (character_id, contract_id)
);

CREATE INDEX IF NOT EXISTS idx_character_contracts_character_id
    ON character_contracts(character_id);
CREATE INDEX IF NOT EXISTS idx_character_contracts_contract_id
    ON character_contracts(contract_id);
CREATE INDEX IF NOT EXISTS idx_character_contracts_type
    ON character_contracts(type);
CREATE INDEX IF NOT EXISTS idx_character_contracts_status
    ON character_contracts(status);
CREATE INDEX IF NOT EXISTS idx_character_contracts_date_issued
    ON character_contracts(date_issued);

COMMENT ON TABLE character_contracts IS 'Contract history for each character';
COMMENT ON COLUMN character_contracts.type IS 'Contract type: item_exchange, auction, courier, loan';
COMMENT ON COLUMN character_contracts.status IS 'Current contract status';

-- ============================================================================
-- Table 13: corporation_assets - Corporation inventory
-- ============================================================================
CREATE TABLE IF NOT EXISTS corporation_assets (
    id SERIAL PRIMARY KEY,
    corporation_id INTEGER NOT NULL,              -- Corporation ID
    item_id BIGINT NOT NULL,                      -- Unique item instance ID
    type_id INTEGER NOT NULL,                     -- EVE type_id of the item
    type_name VARCHAR(255),                       -- Cached item name
    location_id BIGINT NOT NULL,                  -- Station/structure/container ID
    location_name VARCHAR(255),                   -- Cached location name
    location_flag VARCHAR(64),                    -- Slot/location within container
    location_type VARCHAR(32),                    -- 'station', 'solar_system', 'item', 'other'
    quantity INTEGER NOT NULL DEFAULT 1,          -- Stack size
    is_singleton BOOLEAN NOT NULL DEFAULT FALSE,  -- True if item is assembled
    is_blueprint_copy BOOLEAN,                    -- True if item is a BPC
    last_synced TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),

    -- Each item instance is unique per corporation
    CONSTRAINT corporation_assets_unique UNIQUE (corporation_id, item_id)
);

CREATE INDEX IF NOT EXISTS idx_corporation_assets_corporation_id
    ON corporation_assets(corporation_id);
CREATE INDEX IF NOT EXISTS idx_corporation_assets_type_id
    ON corporation_assets(type_id);
CREATE INDEX IF NOT EXISTS idx_corporation_assets_location_id
    ON corporation_assets(location_id);

COMMENT ON TABLE corporation_assets IS 'All items owned by corporations across all locations';
COMMENT ON COLUMN corporation_assets.is_singleton IS 'True for assembled ships/modules that cannot be stacked';

-- ============================================================================
-- Update character_sync_status with new sync tracking columns
-- ============================================================================
ALTER TABLE character_sync_status
ADD COLUMN IF NOT EXISTS location_synced_at TIMESTAMP WITHOUT TIME ZONE,
ADD COLUMN IF NOT EXISTS online_status_synced_at TIMESTAMP WITHOUT TIME ZONE,
ADD COLUMN IF NOT EXISTS ship_synced_at TIMESTAMP WITHOUT TIME ZONE,
ADD COLUMN IF NOT EXISTS clones_synced_at TIMESTAMP WITHOUT TIME ZONE,
ADD COLUMN IF NOT EXISTS implants_synced_at TIMESTAMP WITHOUT TIME ZONE,
ADD COLUMN IF NOT EXISTS fatigue_synced_at TIMESTAMP WITHOUT TIME ZONE,
ADD COLUMN IF NOT EXISTS loyalty_points_synced_at TIMESTAMP WITHOUT TIME ZONE,
ADD COLUMN IF NOT EXISTS contacts_synced_at TIMESTAMP WITHOUT TIME ZONE,
ADD COLUMN IF NOT EXISTS standings_synced_at TIMESTAMP WITHOUT TIME ZONE,
ADD COLUMN IF NOT EXISTS fittings_synced_at TIMESTAMP WITHOUT TIME ZONE,
ADD COLUMN IF NOT EXISTS killmails_synced_at TIMESTAMP WITHOUT TIME ZONE,
ADD COLUMN IF NOT EXISTS contracts_synced_at TIMESTAMP WITHOUT TIME ZONE;

COMMENT ON COLUMN character_sync_status.location_synced_at IS 'Last successful location sync';
COMMENT ON COLUMN character_sync_status.online_status_synced_at IS 'Last successful online status sync';
COMMENT ON COLUMN character_sync_status.ship_synced_at IS 'Last successful current ship sync';
COMMENT ON COLUMN character_sync_status.clones_synced_at IS 'Last successful jump clones sync';
COMMENT ON COLUMN character_sync_status.implants_synced_at IS 'Last successful implants sync';
COMMENT ON COLUMN character_sync_status.fatigue_synced_at IS 'Last successful jump fatigue sync';
COMMENT ON COLUMN character_sync_status.loyalty_points_synced_at IS 'Last successful LP sync';
COMMENT ON COLUMN character_sync_status.contacts_synced_at IS 'Last successful contacts sync';
COMMENT ON COLUMN character_sync_status.standings_synced_at IS 'Last successful standings sync';
COMMENT ON COLUMN character_sync_status.fittings_synced_at IS 'Last successful fittings sync';
COMMENT ON COLUMN character_sync_status.killmails_synced_at IS 'Last successful killmails sync';
COMMENT ON COLUMN character_sync_status.contracts_synced_at IS 'Last successful contracts sync';

-- ============================================================================
-- Summary of created tables:
-- 1. character_location - Current location (character_id PK)
-- 2. character_online_status - Online history
-- 3. character_ship - Current ship (character_id PK)
-- 4. character_clones - Jump clones
-- 5. character_implants - Active implants
-- 6. character_fatigue - Jump fatigue (character_id PK)
-- 7. character_loyalty_points - LP by corporation
-- 8. character_contacts - Contact list
-- 9. character_standings - NPC standings
-- 10. character_fittings - Saved fittings
-- 11. character_killmails - Kill history
-- 12. character_contracts - Contract history
-- 13. corporation_assets - Corp inventory
--
-- Also updated character_sync_status with 12 new sync tracking columns
-- ============================================================================
