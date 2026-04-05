"""Coalition detection constants for time-weighted power bloc algorithm."""

# Exponential decay half-life in days (for documentation; actual calc is in SQL)
DECAY_HALF_LIFE_DAYS = 14

# Weighted ratio threshold: weighted_together / weighted_against must exceed this
WEIGHTED_TOGETHER_RATIO = 2.0

# Weighted enemy threshold (replaces fights_against >= 100)
WEIGHTED_ENEMY_THRESHOLD = 30.0

# Trend override: if recent 14-day data is overwhelmingly positive,
# override old hostility and allow merge
TREND_OVERRIDE_RECENT_TOGETHER = 100  # At least 100 joint kills in last 14 days
TREND_OVERRIDE_RECENT_AGAINST_MAX = 75  # At most 75 hostile kills in last 14 days (accounts for incidental fights in large coalitions)

# Minimum raw fights_together to consider a pair
MIN_FIGHTS_TOGETHER = 200

# Minimum activity for an alliance to appear in power blocs
MIN_ACTIVITY_TOTAL = 50
