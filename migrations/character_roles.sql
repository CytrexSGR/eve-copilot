-- Character Role Recommendations
DROP TABLE IF EXISTS character_role_recommendations;
CREATE TABLE character_role_recommendations (
    character_id INTEGER PRIMARY KEY,
    character_name VARCHAR(64),
    total_sp BIGINT,
    primary_role VARCHAR(64),
    secondary_role VARCHAR(64),
    unique_strengths TEXT,
    recommended_ships TEXT,
    best_for TEXT,
    notes TEXT,
    updated_at TIMESTAMP DEFAULT NOW()
);

INSERT INTO character_role_recommendations
    (character_id, character_name, total_sp, primary_role, secondary_role,
     unique_strengths, recommended_ships, best_for, notes)
VALUES
(1117367444, 'Cytrex', 60869680,
 'Combat Pilot', 'Exploration/Scanner',
 'Missiles (11.5M SP, 13 L5), Caldari T3, Scanning, Electronic Warfare',
 'Tengu, Cerberus, Raven Navy, Caracal Navy, Buzzard',
 'Missionen, Exploration, PvP Support',
 'Hauptkampfpilot mit bester Combat-Ausstattung. Caldari Subsystems L5 = perfekter Tengu-Pilot.'),

(110592475, 'Cytricia', 33546217,
 'Miner/Industrialist', 'Drone Combat',
 'Drones (7.2M SP, 10 L5), Mining/Processing, Exhumers L5, Orca',
 'Orca, Hulk, Mackinaw, Porpoise, Dominix, Myrmidon',
 'Mining Ops, Boost, Reactions, AFK Droning',
 'Beste Minerin mit Orca-Boost. Sentry Drone L5 fuer passive Verteidigung. Reactions fuer PI/Industrie.'),

(526379435, 'Artallus', 16536443,
 'Trader/Hauler', 'Industry Support',
 'Trade (2.8M SP, 4 L5), Transport Ships, Advanced Spaceship Command',
 'Occator, Impel, Deep Space Transport, Freighter (bald)',
 'Market Trading, Hauling, Order Management',
 'Trading-Spezialist: Daytrading, Broker Relations. Transport Ships L4 fuer sichere Fracht.');
