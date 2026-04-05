"""Trade hub constants -- regions, stations, systems."""

# Primary Jita constants
JITA_REGION_ID = 10000002
JITA_STATION_ID = 60003760

# Region name -> region ID
TRADE_HUB_REGIONS = {
    "the_forge": 10000002,     # Jita
    "domain": 10000043,        # Amarr
    "heimatar": 10000030,      # Rens
    "sinq_laison": 10000032,   # Dodixie
    "metropolis": 10000042,    # Hek
}

# Region ID -> primary trade hub station ID
TRADE_HUB_STATIONS = {
    10000002: 60003760,  # Jita IV - Moon 4 - Caldari Navy Assembly Plant
    10000043: 60008494,  # Amarr VIII (Oris) - Emperor Family Academy
    10000030: 60004588,  # Rens VI - Moon 8 - Brutor Tribe Treasury
    10000032: 60011866,  # Dodixie IX - Moon 20 - Federation Navy Assembly Plant
    10000042: 60005686,  # Hek VIII - Moon 12 - Boundless Creation Factory
}

# Trade hub system IDs (solar system, not station)
TRADE_HUB_SYSTEMS = {
    "jita": 30000142,
    "amarr": 30002187,
    "rens": 30002510,
    "dodixie": 30002659,
    "hek": 30002053,
}

# Region ID -> display name
REGION_NAMES = {
    10000002: "The Forge",
    10000043: "Domain",
    10000030: "Heimatar",
    10000032: "Sinq Laison",
    10000042: "Metropolis",
}
