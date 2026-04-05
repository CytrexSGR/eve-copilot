"""
Utility functions for War Intel API.
"""

import logging
import time
from typing import Dict, List, Optional, Tuple

from app.database import db_cursor

logger = logging.getLogger(__name__)

# Simple in-memory cache for coalition memberships (expensive query)
_coalition_cache: Tuple[Optional[Dict[int, int]], float] = (None, 0)
_COALITION_CACHE_TTL = 300  # 5 minutes


def calculate_intensity(kills: int) -> str:
    """Calculate battle intensity based on kill count."""
    if kills >= 100:
        return "extreme"
    elif kills >= 50:
        return "high"
    elif kills >= 20:
        return "moderate"
    return "low"


def detect_tactical_shifts(buckets: list, kill_rate_history: list) -> list:
    """Detect tactical shifts from kill patterns."""
    shifts = []
    if len(buckets) < 3:
        return shifts

    window_size = 3
    logi_deaths_consecutive = 0

    for i, bucket in enumerate(buckets):
        ship_cats = bucket.get('ship_categories', [])
        has_logi = any('Logistics' in cat or 'logistics' in cat.lower() for cat in ship_cats if cat)

        if has_logi:
            logi_deaths_consecutive += 1
            if logi_deaths_consecutive >= 2:
                shifts.append({
                    "minute": bucket["minute"],
                    "type": "logi_collapse",
                    "description": f"Logistics ships destroyed ({logi_deaths_consecutive} in sequence)",
                    "severity": "high" if logi_deaths_consecutive >= 3 else "medium"
                })
        else:
            logi_deaths_consecutive = 0

        if i < window_size:
            continue

        prev_avg = sum(kill_rate_history[i-window_size:i]) / window_size
        current = kill_rate_history[i]

        if prev_avg > 0 and current > prev_avg * 3:
            shifts.append({
                "minute": bucket["minute"],
                "type": "kill_spike",
                "description": f"Kill rate spiked to {current} (avg was {prev_avg:.1f})",
                "severity": "medium" if current < 10 else "high"
            })

        if prev_avg > 2 and current < prev_avg * 0.3:
            shifts.append({
                "minute": bucket["minute"],
                "type": "kill_drop",
                "description": f"Kill rate dropped to {current} (avg was {prev_avg:.1f})",
                "severity": "low"
            })

        if bucket["max_kill_value"] > 1_000_000_000:
            shifts.append({
                "minute": bucket["minute"],
                "type": "high_value_kill",
                "description": f"High-value target destroyed ({bucket['max_kill_value'] / 1_000_000_000:.1f}B ISK)",
                "severity": "high"
            })

    return shifts


def get_coalition_memberships() -> Dict[int, int]:
    """
    Get alliance -> coalition_leader mapping from persistent coalition data.
    Results are cached for 5 minutes.

    Algorithm: Uses accumulated historical data with friend/enemy ratio
    - fight_together / fight_against ratio determines if allies or enemies
    - Only groups alliances that fight TOGETHER more than AGAINST each other
    - Coalition leader = most active alliance in the group

    Returns:
        Dict mapping alliance_id to coalition_leader_id
    """
    global _coalition_cache

    # Check cache
    cached_data, cache_time = _coalition_cache
    if cached_data is not None and (time.time() - cache_time) < _COALITION_CACHE_TTL:
        return cached_data

    memberships = {}

    try:
        with db_cursor() as cur:
            # Get pairs from persistent tables with friend/enemy ratio + weighted scores
            cur.execute("""
                SELECT
                    t.alliance_a,
                    t.alliance_b,
                    t.fights_together,
                    COALESCE(t.weighted_together, t.fights_together) as weighted_together,
                    COALESCE(t.recent_together, 0) as recent_together,
                    COALESCE(a.fights_against, 0) as fights_against,
                    COALESCE(a.weighted_against, a.fights_against, 0) as weighted_against,
                    COALESCE(a.recent_against, 0) as recent_against,
                    aa.total_kills as activity_a,
                    ab.total_kills as activity_b
                FROM alliance_fight_together t
                LEFT JOIN alliance_fight_against a
                    ON t.alliance_a = a.alliance_a AND t.alliance_b = a.alliance_b
                LEFT JOIN alliance_activity_total aa ON aa.alliance_id = t.alliance_a
                LEFT JOIN alliance_activity_total ab ON ab.alliance_id = t.alliance_b
                WHERE t.fights_together >= 200
                ORDER BY COALESCE(t.weighted_together, t.fights_together) DESC
            """)

            pairs = cur.fetchall()

            # Track activity levels
            activity = {}

            # Filter to true coalition partners using time-weighted scores
            MIN_TOGETHER_RATIO = 2.0  # Weighted ratio (lower because weighted data is cleaner)
            MIN_FIGHTS = 200
            TREND_RECENT_TOGETHER = 100  # Trend override thresholds
            TREND_RECENT_AGAINST_MAX = 75

            coalition_pairs = []

            for row in pairs:
                a, b = row["alliance_a"], row["alliance_b"]
                together = row["fights_together"]
                w_together = row["weighted_together"]
                w_against = row["weighted_against"]
                recent_t = row["recent_together"]
                recent_a = row["recent_against"]

                activity[a] = row["activity_a"] or 0
                activity[b] = row["activity_b"] or 0

                # Trend override: recent data overwhelmingly positive
                trend_override = (recent_t >= TREND_RECENT_TOGETHER
                                  and recent_a <= TREND_RECENT_AGAINST_MAX)

                # Skip if weighted ratio is too low (unless trend overrides)
                if not trend_override:
                    if w_against > 0 and w_together / w_against < MIN_TOGETHER_RATIO:
                        continue

                # Calculate strength based on how consistently they fight together
                ratio_a = together / activity[a] if activity[a] > 0 else 0
                ratio_b = together / activity[b] if activity[b] > 0 else 0

                # At least one side should have significant co-occurrence (10%+)
                if ratio_a >= 0.10 or ratio_b >= 0.10:
                    strength = together * max(ratio_a, ratio_b)
                    coalition_pairs.append((a, b, strength, together))

            # Use Union-Find to group validated pairs
            parent = {}

            def find(x):
                if x not in parent:
                    parent[x] = x
                if parent[x] != x:
                    parent[x] = find(parent[x])
                return parent[x]

            def union(x, y):
                px, py = find(x), find(y)
                if px != py:
                    # Most active becomes leader
                    if activity.get(px, 0) >= activity.get(py, 0):
                        parent[py] = px
                    else:
                        parent[px] = py

            # Sort by strength and merge
            coalition_pairs.sort(key=lambda x: x[2], reverse=True)
            for a, b, strength, fights in coalition_pairs:
                union(a, b)

            # Build initial memberships from Union-Find
            for alliance_id in parent.keys():
                memberships[alliance_id] = find(alliance_id)

            # Post-processing: Remove alliances that fight against their coalition leader
            # Uses weighted scores and recent activity for trend-awareness
            cur.execute("""
                SELECT alliance_a, alliance_b, fights_against,
                       COALESCE(weighted_against, fights_against) as weighted_against,
                       COALESCE(recent_against, 0) as recent_against
                FROM alliance_fight_against
                WHERE COALESCE(weighted_against, fights_against) >= 15
            """)
            enemy_pairs = {(row["alliance_a"], row["alliance_b"]): row["weighted_against"]
                           for row in cur.fetchall()}

            removed_count = 0
            for alliance_id in list(memberships.keys()):
                leader = memberships[alliance_id]
                if leader == alliance_id:
                    continue  # Skip coalition leaders

                # Check fights_against between this alliance and the leader
                pair = (min(alliance_id, leader), max(alliance_id, leader))
                fights_against = enemy_pairs.get(pair, 0)

                # Also check fights_together for this specific pair
                together_key = (min(alliance_id, leader), max(alliance_id, leader))
                fights_together = 0
                for a, b, _, t in coalition_pairs:
                    if (min(a, b), max(a, b)) == together_key:
                        fights_together = t
                        break

                # If they fight against each other more than together, remove from coalition
                if fights_against > 0 and (fights_together == 0 or fights_together / fights_against < MIN_TOGETHER_RATIO):
                    memberships[alliance_id] = alliance_id  # Make independent
                    removed_count += 1

            logger.info(f"Built coalition memberships for {len(memberships)} alliances "
                       f"({len(coalition_pairs)} validated pairs, {removed_count} removed due to hostility)")

    except Exception as e:
        logger.warning(f"Failed to build coalition memberships: {e}")

    # Update cache
    _coalition_cache = (memberships, time.time())
    return memberships
