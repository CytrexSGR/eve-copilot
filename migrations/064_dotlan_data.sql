-- DOTLAN Scraping Service - Data tables
-- Stores scraped data from evemaps.dotlan.net that is NOT available via ESI

-- =============================================================
-- DOTLAN System Activity (hourly snapshots)
-- NPC kills, ship kills, pod kills, jumps per system
-- =============================================================
CREATE TABLE IF NOT EXISTS dotlan_system_activity (
    solar_system_id   INTEGER NOT NULL,
    timestamp         TIMESTAMP NOT NULL,
    npc_kills         INTEGER DEFAULT 0,
    ship_kills        INTEGER DEFAULT 0,
    pod_kills         INTEGER DEFAULT 0,
    jumps             INTEGER DEFAULT 0,
    scraped_at        TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (solar_system_id, timestamp)
);

CREATE INDEX IF NOT EXISTS idx_dotlan_activity_ts
    ON dotlan_system_activity (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_dotlan_activity_system_ts
    ON dotlan_system_activity (solar_system_id, timestamp DESC);

-- Partial indexes for "hot systems" queries
CREATE INDEX IF NOT EXISTS idx_dotlan_activity_npc_kills
    ON dotlan_system_activity (timestamp DESC, npc_kills DESC)
    WHERE npc_kills > 0;
CREATE INDEX IF NOT EXISTS idx_dotlan_activity_ship_kills
    ON dotlan_system_activity (timestamp DESC, ship_kills DESC)
    WHERE ship_kills > 0;

-- =============================================================
-- DOTLAN Sovereignty Campaigns (active contests)
-- =============================================================
CREATE TABLE IF NOT EXISTS dotlan_sov_campaigns (
    campaign_id       INTEGER PRIMARY KEY,
    solar_system_id   INTEGER NOT NULL,
    region_id         INTEGER,
    structure_type    VARCHAR(20) NOT NULL,
    defender_name     VARCHAR(255),
    defender_id       INTEGER,
    score             FLOAT,
    status            VARCHAR(20) DEFAULT 'active',
    first_seen        TIMESTAMP DEFAULT NOW(),
    last_updated      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dotlan_sov_campaigns_status
    ON dotlan_sov_campaigns (status) WHERE status = 'active';
CREATE INDEX IF NOT EXISTS idx_dotlan_sov_campaigns_system
    ON dotlan_sov_campaigns (solar_system_id);

-- =============================================================
-- DOTLAN Sovereignty Changes (historical)
-- =============================================================
CREATE TABLE IF NOT EXISTS dotlan_sov_changes (
    id                SERIAL PRIMARY KEY,
    solar_system_id   INTEGER NOT NULL,
    region_id         INTEGER,
    change_type       VARCHAR(20) NOT NULL,
    old_alliance_name VARCHAR(255),
    new_alliance_name VARCHAR(255),
    old_alliance_id   INTEGER,
    new_alliance_id   INTEGER,
    changed_at        TIMESTAMP NOT NULL,
    scraped_at        TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dotlan_sov_changes_time
    ON dotlan_sov_changes (changed_at DESC);
CREATE INDEX IF NOT EXISTS idx_dotlan_sov_changes_alliance
    ON dotlan_sov_changes (new_alliance_id, changed_at DESC);

-- Prevent duplicate entries
CREATE UNIQUE INDEX IF NOT EXISTS idx_dotlan_sov_changes_unique
    ON dotlan_sov_changes (solar_system_id, change_type, changed_at);

-- =============================================================
-- DOTLAN Alliance Statistics (daily snapshots)
-- =============================================================
CREATE TABLE IF NOT EXISTS dotlan_alliance_stats (
    alliance_name     VARCHAR(255) NOT NULL,
    alliance_slug     VARCHAR(255) NOT NULL,
    alliance_id       INTEGER,
    systems_count     INTEGER DEFAULT 0,
    member_count      INTEGER DEFAULT 0,
    corp_count        INTEGER DEFAULT 0,
    rank_by_systems   INTEGER,
    snapshot_date     DATE NOT NULL DEFAULT CURRENT_DATE,
    scraped_at        TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (alliance_slug, snapshot_date)
);

CREATE INDEX IF NOT EXISTS idx_dotlan_alliance_stats_date
    ON dotlan_alliance_stats (snapshot_date DESC);
CREATE INDEX IF NOT EXISTS idx_dotlan_alliance_stats_id
    ON dotlan_alliance_stats (alliance_id, snapshot_date DESC);

-- =============================================================
-- DOTLAN ADM History (sovereignty strength trends)
-- =============================================================
CREATE TABLE IF NOT EXISTS dotlan_adm_history (
    solar_system_id   INTEGER NOT NULL,
    timestamp         TIMESTAMP NOT NULL,
    adm_level         FLOAT NOT NULL,
    scraped_at        TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (solar_system_id, timestamp)
);

CREATE INDEX IF NOT EXISTS idx_dotlan_adm_history_ts
    ON dotlan_adm_history (timestamp DESC);

-- =============================================================
-- Scraper Execution Log (monitoring)
-- =============================================================
CREATE TABLE IF NOT EXISTS dotlan_scraper_log (
    id                SERIAL PRIMARY KEY,
    scraper_name      VARCHAR(50) NOT NULL,
    started_at        TIMESTAMP NOT NULL,
    finished_at       TIMESTAMP,
    status            VARCHAR(20) DEFAULT 'running',
    regions_scraped   INTEGER DEFAULT 0,
    systems_scraped   INTEGER DEFAULT 0,
    rows_inserted     INTEGER DEFAULT 0,
    error_message     TEXT,
    duration_seconds  FLOAT
);

CREATE INDEX IF NOT EXISTS idx_dotlan_scraper_log_name
    ON dotlan_scraper_log (scraper_name, started_at DESC);
