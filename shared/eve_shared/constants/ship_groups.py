"""Ship group constants -- capital ships, categories."""

# Capital ship group IDs (from SDE invGroups)
CAPITAL_GROUP_IDS = (30, 485, 547, 659, 883, 902, 1538, 4594)
# 30 = Titan, 485 = Dreadnought, 547 = Carrier, 659 = Supercarrier,
# 883 = Capital Industrial Ship (Rorqual), 902 = Jump Freighter,
# 1538 = Force Auxiliary, 4594 = Lancer Dreadnought

# Capital group names (for SQL name-based matching)
CAPITAL_GROUP_NAMES = (
    'Carrier', 'Capital Industrial Ship', 'Dreadnought',
    'Force Auxiliary', 'Jump Freighter', 'Lancer Dreadnought',
    'Supercarrier', 'Titan',
)

# Combined mapping: group_id -> group_name
CAPITAL_GROUPS = {
    30: 'Titan',
    485: 'Dreadnought',
    547: 'Carrier',
    659: 'Supercarrier',
    883: 'Capital Industrial Ship',
    902: 'Jump Freighter',
    1538: 'Force Auxiliary',
    4594: 'Lancer Dreadnought',
}
