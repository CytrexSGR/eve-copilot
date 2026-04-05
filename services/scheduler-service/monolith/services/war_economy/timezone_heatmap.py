# services/war_economy/timezone_heatmap.py
"""
Timezone Heatmap Service - Aggregates killmail activity by hour (UTC).
Identifies peak activity times and defensive gaps for alliance intelligence.
"""
from typing import Dict, List, Any, Optional


class TimezoneHeatmapService:
    """Aggregates killmail timestamps into 24-hour activity heatmap."""

    def __init__(self, conn):
        self.conn = conn

    def get_hourly_activity(
        self,
        days_back: int = 7,
        alliance_id: Optional[int] = None,
        region_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get hourly kill activity aggregated across the time period.

        Args:
            days_back: Number of days to analyze (default 7)
            alliance_id: Filter to specific alliance (optional)
            region_id: Filter to specific region (optional)

        Returns:
            Dict with hours array (0-23), peak_hours, defensive_gaps, summary
        """
        if days_back <= 0:
            days_back = 7  # Default fallback

        # Build query with optional filters
        query = """
            SELECT
                EXTRACT(HOUR FROM killmail_time)::int as hour_utc,
                COUNT(*) as kills,
                COALESCE(SUM(ship_value), 0) as isk_destroyed
            FROM killmails
            WHERE killmail_time >= NOW() - INTERVAL '%s days'
        """
        params = [days_back]

        if alliance_id:
            query += " AND victim_alliance_id = %s"
            params.append(alliance_id)

        if region_id:
            query += " AND region_id = %s"
            params.append(region_id)

        query += """
            GROUP BY EXTRACT(HOUR FROM killmail_time)
            ORDER BY hour_utc
        """

        with self.conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()

        # Initialize all 24 hours with zeros
        hourly_data = {h: {"hour_utc": h, "kills": 0, "isk_destroyed": 0} for h in range(24)}

        # Fill in actual data
        for row in rows:
            hour, kills, isk = row
            hourly_data[hour] = {
                "hour_utc": hour,
                "kills": kills,
                "isk_destroyed": float(isk) if isk else 0
            }

        hours_list = [hourly_data[h] for h in range(24)]

        # Calculate peak hours (top 3 by kills)
        sorted_by_kills = sorted(hours_list, key=lambda x: x["kills"], reverse=True)
        peak_hours = [h["hour_utc"] for h in sorted_by_kills[:3] if h["kills"] > 0]

        # Find defensive gaps (3+ consecutive hours with < 10% of peak activity)
        defensive_gaps = self._find_defensive_gaps(hours_list)

        # Summary stats
        total_kills = sum(h["kills"] for h in hours_list)
        total_isk = sum(h["isk_destroyed"] for h in hours_list)

        return {
            "hours": hours_list,
            "peak_hours": peak_hours,
            "defensive_gaps": defensive_gaps,
            "summary": {
                "total_kills": total_kills,
                "total_isk_destroyed": total_isk,
                "peak_hour_utc": peak_hours[0] if peak_hours else None,
                "peak_kills": sorted_by_kills[0]["kills"] if sorted_by_kills else 0,
                "days_analyzed": days_back
            }
        }

    def _find_defensive_gaps(self, hours_list: List[Dict]) -> List[List[int]]:
        """
        Find windows of 3+ consecutive hours with low activity.
        Low = less than 10% of the peak hour's activity.
        """
        if not hours_list:
            return []

        peak_kills = max(h["kills"] for h in hours_list)
        if peak_kills == 0:
            return []

        threshold = peak_kills * 0.1

        gaps = []
        current_gap = []

        # Check all 24 hours, wrapping around
        for i in range(24):
            if hours_list[i]["kills"] < threshold:
                current_gap.append(i)
            else:
                if len(current_gap) >= 3:
                    gaps.append(current_gap)
                current_gap = []

        # Check if gap wraps around midnight
        if len(current_gap) >= 3:
            gaps.append(current_gap)

        return gaps

    def get_alliance_comparison(
        self,
        alliance_ids: List[int],
        days_back: int = 7
    ) -> Dict[str, Any]:
        """
        Compare timezone activity between multiple alliances.
        Useful for finding optimal attack windows.
        """
        results = {}

        for alliance_id in alliance_ids:
            results[str(alliance_id)] = self.get_hourly_activity(
                days_back=days_back,
                alliance_id=alliance_id
            )

        return {
            "alliances": results,
            "days_analyzed": days_back
        }
