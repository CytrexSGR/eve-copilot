-- Migration 077: Reference Types + Seed Data
-- Phase 2: Finance Module - Wallet journal ref_type mapping

CREATE TABLE IF NOT EXISTS ref_types (
    ref_type_id  INTEGER PRIMARY KEY,
    name         VARCHAR(100) NOT NULL,
    label_de     VARCHAR(100),
    category     VARCHAR(50)
);

-- Seed critical ref_types for financial analysis
INSERT INTO ref_types (ref_type_id, name, label_de, category) VALUES
    (1,  'player_trading',              'Spielerhandel',          'market'),
    (2,  'market_transaction',          'Markttransaktion',       'market'),
    (10, 'player_donation',             'Spende / Transfer',      'transfer'),
    (17, 'bounty_prize',                'Kopfgeld-Auszahlung',    'ratting'),
    (33, 'mission_reward',              'Missionsbelohnung',      'ratting'),
    (34, 'mission_time_bonus_reward',   'Missions-Zeitbonus',     'ratting'),
    (35, 'agent_mission_reward',        'Agenten-Belohnung',      'ratting'),
    (37, 'corporation_account_withdrawal', 'Konto-Abhebung',     'admin'),
    (42, 'market_escrow',               'Markt-Treuhand',         'market'),
    (46, 'brokers_fee',                 'Maklergebühr',           'market_cost'),
    (54, 'transaction_tax',             'Verkaufssteuer',         'market_cost'),
    (56, 'manufacturing',               'Produktion',             'industry'),
    (85, 'bounty_prizes',               'Ratting-Steuer (Corp)',  'corp_tax'),
    (96, 'planetary_import_tax',        'PI Import-Zoll',         'pi'),
    (97, 'planetary_export_tax',        'PI Export-Zoll',         'pi'),
    (117, 'structure_gate_jump',        'Struktur-Gate Jump',     'infrastructure'),
    (125, 'project_discovery_reward',   'Project Discovery',      'ratting'),
    (128, 'reprocessing_tax',           'Reprocessing-Steuer',    'corp_tax'),
    (10009, 'ess_escrow_transfer',      'ESS Transfer',           'ratting')
ON CONFLICT (ref_type_id) DO UPDATE SET
    name = EXCLUDED.name,
    label_de = EXCLUDED.label_de,
    category = EXCLUDED.category;
