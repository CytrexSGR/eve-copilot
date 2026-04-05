"""Hunting Opportunity Score calculator — multi-factor system assessment."""


def calculate_hunting_score(
    adm_military: float,
    npc_kills_per_day: float,
    player_deaths_per_week: float,
    avg_kill_value: float,
    jumps_to_staging: int,
    capital_presence: bool,
    adm_industry: float = 0,
) -> float:
    """Calculate hunting opportunity score 0-100 for a system.

    Score = Target Density + Kill Activity + Value - Risk

    Components:
      - Target Density (0-35): NPC kills + ADM indicate PvE targets
      - Kill Activity (0-25): Recent deaths confirm catchable targets
      - Value (0-25): Average ISK per kill
      - Risk (0-15): Capital umbrella + distance penalty
    """
    # Target Density (0-35): PvE activity = potential targets
    npc_normalized = min(1.0, npc_kills_per_day / 500)
    adm_normalized = min(1.0, adm_military / 5.0)
    if npc_kills_per_day > 0:
        density = (npc_normalized * 0.7 + adm_normalized * 0.3) * 35
    else:
        # No NPC data — rely on ADM alone
        density = adm_normalized * 35

    # Kill Activity (0-25): Recent kills prove targets exist and can be caught
    death_normalized = min(1.0, player_deaths_per_week / 15)
    kill_activity = death_normalized * 25

    # Value (0-25): Average ISK at risk per kill
    value_normalized = min(1.0, avg_kill_value / 500_000_000)  # 500M cap
    value = value_normalized * 25

    # Risk penalty (0-15): Danger to the hunter
    distance_penalty = min(5, jumps_to_staging * 0.25)
    capital_penalty = 10 if capital_presence else 0
    risk = distance_penalty + capital_penalty

    score = density + kill_activity + value - risk
    return max(0, min(100, score))
