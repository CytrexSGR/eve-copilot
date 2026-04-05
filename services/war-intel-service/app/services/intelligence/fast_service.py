"""
Fast Intelligence Service - Uses pre-aggregated hourly stats.

This service provides near real-time intelligence data by reading
from the intelligence_hourly_stats table which is incrementally
updated on each killmail.

Response times: ~10-50ms (vs 30-60s for on-demand calculation)
"""

import logging
from datetime import datetime
from typing import Dict, List, Any

from app.database import db_cursor
from app.services.intelligence.esi_utils import batch_resolve_alliance_names
from app.services.intelligence.equipment_service import equipment_intel_service

logger = logging.getLogger(__name__)


class IntelligenceFastService:
    """Fast intelligence service using pre-aggregated stats."""

    def __init__(self):
        self.equipment = equipment_intel_service

    def get_summary(self, alliance_id: int, days: int = 7) -> Dict[str, Any]:
        """
        Get combat summary for an alliance.

        Returns kills, deaths, ISK stats, and efficiency in ~10ms.
        """
        with db_cursor() as cur:
            cur.execute("""
                SELECT
                    COALESCE(SUM(kills), 0) as kills,
                    COALESCE(SUM(deaths), 0) as deaths,
                    COALESCE(SUM(isk_destroyed), 0) as isk_destroyed,
                    COALESCE(SUM(isk_lost), 0) as isk_lost
                FROM intelligence_hourly_stats
                WHERE alliance_id = %s
                  AND hour_bucket >= NOW() - INTERVAL '%s days'
            """, (alliance_id, days))
            row = cur.fetchone()

            kills = row['kills'] or 0
            deaths = row['deaths'] or 0
            isk_destroyed = row['isk_destroyed'] or 0
            isk_lost = row['isk_lost'] or 0

            total_isk = isk_destroyed + isk_lost
            efficiency = round((isk_destroyed / total_isk) * 100, 1) if total_isk > 0 else 0

            return {
                "alliance_id": alliance_id,
                "period_days": days,
                "kills": kills,
                "deaths": deaths,
                "isk_destroyed": isk_destroyed,
                "isk_lost": isk_lost,
                "efficiency": efficiency,
                "kd_ratio": round(kills / deaths, 2) if deaths > 0 else kills
            }

    def get_danger_zones(self, alliance_id: int, days: int = 7, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get most dangerous systems for an alliance (where they lose ships).
        """
        with db_cursor() as cur:
            cur.execute("""
                SELECT
                    system_id::INT as system_id,
                    death_count::INT as death_count,
                    s."solarSystemName" as system_name,
                    s."regionID" as region_id,
                    r."regionName" as region_name
                FROM (
                    SELECT
                        key as system_id,
                        SUM(value::INT) as death_count
                    FROM intelligence_hourly_stats,
                    LATERAL jsonb_each_text(systems_deaths) as j(key, value)
                    WHERE alliance_id = %s
                      AND hour_bucket >= NOW() - INTERVAL '%s days'
                      AND systems_deaths != '{}'
                    GROUP BY key
                ) zone_stats
                LEFT JOIN "mapSolarSystems" s ON zone_stats.system_id::INT = s."solarSystemID"
                LEFT JOIN "mapRegions" r ON s."regionID" = r."regionID"
                ORDER BY death_count DESC
                LIMIT %s
            """, (alliance_id, days, limit))

            return [
                {
                    "system_id": row['system_id'],
                    "deaths": row['death_count'],
                    "system_name": row['system_name'] or f"System {row['system_id']}",
                    "region_id": row['region_id'],
                    "region_name": row['region_name'] or "Unknown"
                }
                for row in cur.fetchall()
            ]

    def get_ships_lost(self, alliance_id: int, days: int = 7, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get most commonly lost ship types for an alliance WITH ISK values.
        Uses killmails table for accurate ISK data.
        """
        with db_cursor() as cur:
            cur.execute("""
                SELECT
                    k.ship_type_id,
                    COUNT(*) as ship_count,
                    COALESCE(SUM(k.ship_value), 0) as total_isk_lost,
                    t."typeName" as ship_name,
                    g."groupName" as ship_class
                FROM killmails k
                LEFT JOIN "invTypes" t ON k.ship_type_id = t."typeID"
                LEFT JOIN "invGroups" g ON t."groupID" = g."groupID"
                WHERE k.victim_alliance_id = %s
                  AND k.killmail_time >= NOW() - INTERVAL '%s days'
                GROUP BY k.ship_type_id, t."typeName", g."groupName"
                ORDER BY ship_count DESC
                LIMIT %s
            """, (alliance_id, days, limit))

            return [
                {
                    "type_id": row['ship_type_id'],
                    "count": row['ship_count'],
                    "isk_lost": row['total_isk_lost'] or 0,
                    "ship_name": row['ship_name'] or f"Unknown ({row['ship_type_id']})",
                    "ship_class": row['ship_class'] or "Unknown"
                }
                for row in cur.fetchall()
            ]

    def get_top_enemies(self, alliance_id: int, days: int = 7, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get alliances that kill this alliance the most.
        Counts all kills where the enemy alliance participated (not just final blow).
        """
        with db_cursor() as cur:
            cur.execute("""
                SELECT
                    ka.alliance_id as enemy_id,
                    COUNT(DISTINCT k.killmail_id) as kills,
                    COALESCE(SUM(k.ship_value), 0) as isk_destroyed
                FROM killmails k
                JOIN killmail_attackers ka ON k.killmail_id = ka.killmail_id
                WHERE k.victim_alliance_id = %s
                  AND k.killmail_time >= NOW() - INTERVAL '%s days'
                  AND ka.alliance_id IS NOT NULL
                  AND ka.alliance_id <> %s
                GROUP BY ka.alliance_id
                ORDER BY kills DESC
                LIMIT %s
            """, (alliance_id, days, alliance_id, limit))

            rows = cur.fetchall()

            # Batch resolve alliance names
            enemy_ids = [row['enemy_id'] for row in rows if row['enemy_id']]
            names = batch_resolve_alliance_names(enemy_ids) if enemy_ids else {}

            return [
                {
                    "alliance_id": row['enemy_id'],
                    "alliance_name": names.get(row['enemy_id'], f"Alliance {row['enemy_id']}"),
                    "kills": row['kills'],
                    "isk_destroyed": row['isk_destroyed']
                }
                for row in rows
            ]

    def get_hourly_activity(self, alliance_id: int, days: int = 7) -> Dict[str, Any]:
        """
        Get hourly activity distribution (24h breakdown) WITH peak/safe hour analysis.
        """
        with db_cursor() as cur:
            cur.execute("""
                SELECT
                    EXTRACT(HOUR FROM hour_bucket)::INT as hour,
                    SUM(kills) as kills,
                    SUM(deaths) as deaths
                FROM intelligence_hourly_stats
                WHERE alliance_id = %s
                  AND hour_bucket >= NOW() - INTERVAL '%s days'
                GROUP BY EXTRACT(HOUR FROM hour_bucket)
                ORDER BY hour
            """, (alliance_id, days))

            # Initialize 24 hours
            kills_by_hour = [0] * 24
            deaths_by_hour = [0] * 24

            for row in cur.fetchall():
                hour = int(row['hour'])
                kills_by_hour[hour] = row['kills'] or 0
                deaths_by_hour[hour] = row['deaths'] or 0

            # Calculate peak danger hours (top 25% of deaths)
            max_deaths = max(deaths_by_hour) if deaths_by_hour else 0
            threshold = max_deaths * 0.5  # 50% of max

            peak_hours = [h for h, d in enumerate(deaths_by_hour) if d >= threshold and d > 0]
            safe_hours = [h for h, d in enumerate(deaths_by_hour) if d < threshold * 0.3]

            # Find contiguous peak window
            peak_start = min(peak_hours) if peak_hours else 18
            peak_end = max(peak_hours) if peak_hours else 22

            # Find safest window (lowest consecutive deaths)
            safe_start = min(safe_hours) if safe_hours else 4
            safe_end = max(safe_hours) if safe_hours else 10

            return {
                "kills_by_hour": kills_by_hour,
                "deaths_by_hour": deaths_by_hour,
                "peak_danger_start": peak_start,
                "peak_danger_end": peak_end,
                "safe_start": safe_start,
                "safe_end": safe_end
            }

    def get_economics(self, alliance_id: int, days: int = 7) -> Dict[str, Any]:
        """
        Get economic analysis: ISK balance, cost per kill, efficiency trends.
        """
        with db_cursor() as cur:
            cur.execute("""
                SELECT
                    COALESCE(SUM(kills), 0) as kills,
                    COALESCE(SUM(deaths), 0) as deaths,
                    COALESCE(SUM(isk_destroyed), 0) as isk_destroyed,
                    COALESCE(SUM(isk_lost), 0) as isk_lost
                FROM intelligence_hourly_stats
                WHERE alliance_id = %s
                  AND hour_bucket >= NOW() - INTERVAL '%s days'
            """, (alliance_id, days))
            row = cur.fetchone()

            kills = row['kills'] or 0
            deaths = row['deaths'] or 0
            isk_destroyed = row['isk_destroyed'] or 0
            isk_lost = row['isk_lost'] or 0

            isk_balance = isk_destroyed - isk_lost
            cost_per_kill = round(isk_lost / kills, 0) if kills > 0 else 0
            cost_per_death = round(isk_lost / deaths, 0) if deaths > 0 else 0

            return {
                "isk_destroyed": isk_destroyed,
                "isk_lost": isk_lost,
                "isk_balance": isk_balance,
                "cost_per_kill": cost_per_kill,
                "cost_per_death": cost_per_death,
                "profitable": isk_balance > 0
            }

    def get_expensive_losses(self, alliance_id: int, days: int = 7, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get most expensive individual ship losses.
        """
        with db_cursor() as cur:
            cur.execute("""
                SELECT
                    k.killmail_id,
                    k.ship_type_id,
                    t."typeName" as ship_name,
                    g."groupName" as ship_class,
                    k.ship_value,
                    k.killmail_time,
                    s."solarSystemName" as system_name
                FROM killmails k
                LEFT JOIN "invTypes" t ON k.ship_type_id = t."typeID"
                LEFT JOIN "invGroups" g ON t."groupID" = g."groupID"
                LEFT JOIN "mapSolarSystems" s ON k.solar_system_id = s."solarSystemID"
                WHERE k.victim_alliance_id = %s
                  AND k.killmail_time >= NOW() - INTERVAL '%s days'
                  AND k.ship_value > 0
                ORDER BY k.ship_value DESC
                LIMIT %s
            """, (alliance_id, days, limit))

            return [
                {
                    "killmail_id": row['killmail_id'],
                    "type_id": row['ship_type_id'],
                    "ship_name": row['ship_name'] or f"Unknown ({row['ship_type_id']})",
                    "ship_class": row['ship_class'] or "Unknown",
                    "isk_lost": row['ship_value'] or 0,
                    "time": row['killmail_time'].isoformat() if row['killmail_time'] else None,
                    "system_name": row['system_name'] or "Unknown"
                }
                for row in cur.fetchall()
            ]

    def get_ship_effectiveness(self, alliance_id: int, days: int = 7) -> List[Dict[str, Any]]:
        """
        Get ship class effectiveness: kills vs deaths per ship class.
        """
        with db_cursor() as cur:
            cur.execute("""
                SELECT
                    g."groupName" as ship_class,
                    COUNT(*) as deaths,
                    COALESCE(SUM(k.ship_value), 0) as isk_lost
                FROM killmails k
                LEFT JOIN "invTypes" t ON k.ship_type_id = t."typeID"
                LEFT JOIN "invGroups" g ON t."groupID" = g."groupID"
                WHERE k.victim_alliance_id = %s
                  AND k.killmail_time >= NOW() - INTERVAL '%s days'
                GROUP BY g."groupName"
                HAVING COUNT(*) >= 3
                ORDER BY COUNT(*) DESC
                LIMIT 10
            """, (alliance_id, days))

            results = []
            for row in cur.fetchall():
                ship_class = row['ship_class'] or "Unknown"
                deaths = row['deaths'] or 0
                isk_lost = row['isk_lost'] or 0

                # Determine verdict based on death rate
                if deaths > 50:
                    verdict = "bleeding"
                elif deaths > 20:
                    verdict = "moderate"
                else:
                    verdict = "acceptable"

                results.append({
                    "ship_class": ship_class,
                    "deaths": deaths,
                    "isk_lost": isk_lost,
                    "verdict": verdict
                })

            return results

    def get_production_needs(self, alliance_id: int, days: int = 7, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Calculate production/replacement needs based on ship losses.
        """
        with db_cursor() as cur:
            cur.execute("""
                SELECT
                    k.ship_type_id,
                    t."typeName" as ship_name,
                    g."groupName" as ship_class,
                    COUNT(*) as losses_period,
                    COALESCE(SUM(k.ship_value), 0) as total_isk_lost,
                    COALESCE(AVG(k.ship_value), 0) as avg_ship_value
                FROM killmails k
                LEFT JOIN "invTypes" t ON k.ship_type_id = t."typeID"
                LEFT JOIN "invGroups" g ON t."groupID" = g."groupID"
                WHERE k.victim_alliance_id = %s
                  AND k.killmail_time >= NOW() - INTERVAL '%s days'
                  AND k.ship_type_id NOT IN (670, 33328)  -- Exclude capsules/pods
                GROUP BY k.ship_type_id, t."typeName", g."groupName"
                HAVING COUNT(*) >= 3
                ORDER BY COUNT(*) DESC
                LIMIT %s
            """, (alliance_id, days, limit))

            results = []
            for row in cur.fetchall():
                losses = row['losses_period'] or 0
                losses_per_day = losses / days
                weekly_replacement = int(losses_per_day * 7)
                avg_value = row['avg_ship_value'] or 0

                # Determine priority based on loss rate and value
                if losses_per_day >= 10:
                    priority = "critical"
                elif losses_per_day >= 5:
                    priority = "high"
                elif losses_per_day >= 2:
                    priority = "medium"
                elif avg_value > 100_000_000:  # > 100M ISK
                    priority = "high"
                else:
                    priority = "low"

                results.append({
                    "ship_type_id": row['ship_type_id'],
                    "ship_name": row['ship_name'] or f"Unknown ({row['ship_type_id']})",
                    "ship_class": row['ship_class'] or "Unknown",
                    "losses_period": losses,
                    "losses_per_day": round(losses_per_day, 1),
                    "weekly_replacement": weekly_replacement,
                    "estimated_cost": int(weekly_replacement * avg_value),
                    "priority": priority
                })

            return results

    def get_damage_taken(self, alliance_id: int, days: int = 7) -> List[Dict[str, Any]]:
        """
        Analyze damage types taken based on attacker ship races.
        Uses race → damage type mappings from EVE lore.

        Race damage profiles:
        - Caldari (1): Kinetic/Thermal (missiles, hybrid turrets)
        - Minmatar (2): Explosive/Kinetic (projectile turrets)
        - Amarr (4): EM/Thermal (laser turrets)
        - Gallente (8): Thermal/Kinetic (hybrid turrets, drones)
        """
        with db_cursor() as cur:
            cur.execute("""
                SELECT
                    t."raceID" as race_id,
                    COUNT(*) as attack_count
                FROM killmails k
                JOIN killmail_attackers ka ON k.killmail_id = ka.killmail_id
                JOIN "invTypes" t ON ka.ship_type_id = t."typeID"
                WHERE k.victim_alliance_id = %s
                  AND k.killmail_time >= NOW() - INTERVAL '%s days'
                  AND ka.ship_type_id IS NOT NULL
                GROUP BY t."raceID"
            """, (alliance_id, days))

            # Race to damage type mapping based on EVE faction weapon systems
            RACE_DAMAGE = {
                1: {"kinetic": 0.55, "thermal": 0.45},   # Caldari - missiles/hybrid
                2: {"explosive": 0.55, "kinetic": 0.45}, # Minmatar - projectile
                4: {"em": 0.55, "thermal": 0.45},        # Amarr - laser
                8: {"thermal": 0.55, "kinetic": 0.45},   # Gallente - hybrid/drone
            }

            damage_counts = {"em": 0.0, "thermal": 0.0, "kinetic": 0.0, "explosive": 0.0}
            total = 0

            for row in cur.fetchall():
                count = row['attack_count'] or 0
                race_id = row['race_id']
                total += count

                if race_id in RACE_DAMAGE:
                    for dt, ratio in RACE_DAMAGE[race_id].items():
                        damage_counts[dt] += count * ratio
                else:
                    # Pirate/other factions - mixed damage profiles
                    # Distribute with slight emphasis on thermal (most common)
                    damage_counts["thermal"] += count * 0.3
                    damage_counts["kinetic"] += count * 0.3
                    damage_counts["em"] += count * 0.2
                    damage_counts["explosive"] += count * 0.2

            if total == 0:
                return []

            # Calculate percentages from weighted counts
            total_weighted = sum(damage_counts.values())
            return [
                {
                    "damage_type": dt,
                    "percentage": round((count / total_weighted) * 100, 1) if total_weighted > 0 else 0
                }
                for dt, count in sorted(damage_counts.items(), key=lambda x: -x[1])
            ]

    def get_ewar_threats(self, alliance_id: int, days: int = 7) -> List[Dict[str, Any]]:
        """
        Detect EWAR threats based on attacker ship types.
        """
        # EWAR ship groups and their primary EWAR type
        EWAR_SHIPS = {
            "Electronic Attack Ship": "ecm",
            "Force Recon Ship": "dampener",
            "Combat Recon Ship": "neut",
            "Interdictor": "bubble",
            "Heavy Interdictor": "bubble",
            "Logistics": "remote_rep",
            "Logistics Frigate": "remote_rep",
        }

        with db_cursor() as cur:
            cur.execute("""
                SELECT
                    g."groupName" as ship_class,
                    COUNT(DISTINCT k.killmail_id) as kills_affected
                FROM killmails k
                JOIN killmail_attackers ka ON k.killmail_id = ka.killmail_id
                LEFT JOIN "invTypes" t ON ka.ship_type_id = t."typeID"
                LEFT JOIN "invGroups" g ON t."groupID" = g."groupID"
                WHERE k.victim_alliance_id = %s
                  AND k.killmail_time >= NOW() - INTERVAL '%s days'
                  AND g."groupName" IN %s
                GROUP BY g."groupName"
                ORDER BY COUNT(DISTINCT k.killmail_id) DESC
            """, (alliance_id, days, tuple(EWAR_SHIPS.keys())))

            total_kills = self.get_summary(alliance_id, days).get("deaths", 1)

            return [
                {
                    "ewar_type": EWAR_SHIPS.get(row['ship_class'], "unknown"),
                    "ship_class": row['ship_class'],
                    "kills_affected": row['kills_affected'],
                    "percentage": round((row['kills_affected'] / total_kills) * 100, 1) if total_kills > 0 else 0
                }
                for row in cur.fetchall()
            ]

    def get_enemy_vulnerabilities(self, alliance_id: int, days: int = 7, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Find enemy vulnerabilities: when and where WE kill THEM.
        """
        with db_cursor() as cur:
            cur.execute("""
                SELECT
                    k.victim_alliance_id as enemy_id,
                    COUNT(*) as kills,
                    array_agg(DISTINCT s."solarSystemName") as systems,
                    array_agg(EXTRACT(HOUR FROM k.killmail_time)::INT) as hours
                FROM killmails k
                JOIN killmail_attackers ka ON k.killmail_id = ka.killmail_id
                LEFT JOIN "mapSolarSystems" s ON k.solar_system_id = s."solarSystemID"
                WHERE ka.alliance_id = %s
                  AND ka.is_final_blow = true
                  AND k.killmail_time >= NOW() - INTERVAL '%s days'
                  AND k.victim_alliance_id IS NOT NULL
                  AND k.victim_alliance_id != %s
                GROUP BY k.victim_alliance_id
                ORDER BY COUNT(*) DESC
                LIMIT %s
            """, (alliance_id, days, alliance_id, limit))

            rows = cur.fetchall()

            # Batch resolve alliance names
            enemy_ids = [row['enemy_id'] for row in rows if row['enemy_id']]
            names = batch_resolve_alliance_names(enemy_ids) if enemy_ids else {}

            results = []
            for row in rows:
                hours = row['hours'] or []
                systems = [s for s in (row['systems'] or []) if s][:3]

                # Find peak vulnerability hours
                if hours:
                    hour_counts = {}
                    for h in hours:
                        hour_counts[h] = hour_counts.get(h, 0) + 1
                    sorted_hours = sorted(hour_counts.items(), key=lambda x: -x[1])
                    weak_hour_start = sorted_hours[0][0] if sorted_hours else 18
                    weak_hour_end = (weak_hour_start + 2) % 24
                else:
                    weak_hour_start, weak_hour_end = 18, 20

                results.append({
                    "alliance_id": row['enemy_id'],
                    "alliance_name": names.get(row['enemy_id'], f"Alliance {row['enemy_id']}"),
                    "losses_to_us": row['kills'],
                    "weak_systems": systems,
                    "weak_hours": [weak_hour_start, weak_hour_end]
                })

            return results

    def generate_recommendations(self, alliance_id: int, days: int = 7) -> List[Dict[str, Any]]:
        """
        Generate tactical recommendations based on all data.
        """
        recommendations = []
        priority = 1

        # Get data for analysis
        danger_zones = self.get_danger_zones(alliance_id, days, limit=3)
        hourly = self.get_hourly_activity(alliance_id, days)
        damage = self.get_damage_taken(alliance_id, days)
        enemies = self.get_enemy_vulnerabilities(alliance_id, days, limit=3)
        ships = self.get_ships_lost(alliance_id, days, limit=5)

        # Avoid recommendation - danger zones
        if danger_zones and danger_zones[0]["deaths"] > 20:
            top_zone = danger_zones[0]
            recommendations.append({
                "priority": priority,
                "category": "avoid",
                "text": f"Avoid {top_zone['system_name']} ({top_zone['region_name']}) - {top_zone['deaths']} deaths in {days}d"
            })
            priority += 1

        # Timing recommendation
        peak_start = hourly.get("peak_danger_start", 18)
        peak_end = hourly.get("peak_danger_end", 22)
        safe_start = hourly.get("safe_start", 6)
        safe_end = hourly.get("safe_end", 12)
        recommendations.append({
            "priority": priority,
            "category": "avoid",
            "text": f"Peak danger: {peak_start}:00-{peak_end}:00 UTC. Safer: {safe_start}:00-{safe_end}:00 UTC"
        })
        priority += 1

        # Tank recommendation - based on damage taken
        if damage:
            top_damage = damage[0]
            recommendations.append({
                "priority": priority,
                "category": "fit",
                "text": f"Prioritize {top_damage['damage_type'].upper()} resist - {top_damage['percentage']}% of incoming damage"
            })
            priority += 1

        # Attack recommendation - enemy vulnerabilities
        if enemies:
            enemy = enemies[0]
            hours = enemy.get("weak_hours", [18, 20])
            recommendations.append({
                "priority": priority,
                "category": "attack",
                "text": f"Strike {enemy['alliance_name']} at {hours[0]}:00-{hours[1]}:00 UTC - {enemy['losses_to_us']} kills achieved"
            })
            priority += 1

        # Doctrine recommendation - ship losses
        if ships and len(ships) >= 2:
            top_ship = ships[0]
            if top_ship["count"] > 30:
                recommendations.append({
                    "priority": priority,
                    "category": "doctrine",
                    "text": f"High {top_ship['ship_name']} losses ({top_ship['count']}x) - consider doctrine review"
                })

        return recommendations

    # Equipment intel methods - delegated to equipment service
    def get_weapons_lost(self, alliance_id: int, days: int = 7, limit: int = 20) -> Dict[str, Any]:
        """Analyze weapon systems lost. Delegated to equipment service."""
        return self.equipment.get_weapons_lost(alliance_id, days, limit)

    def get_tank_profile(self, alliance_id: int, days: int = 7, limit: int = 20) -> Dict[str, Any]:
        """Analyze tank modules lost. Delegated to equipment service."""
        return self.equipment.get_tank_profile(alliance_id, days, limit)

    def get_cargo_intel(self, alliance_id: int, days: int = 7, limit: int = 50) -> Dict[str, Any]:
        """Analyze cargo hold contents lost. Delegated to equipment service."""
        return self.equipment.get_cargo_intel(alliance_id, days, limit)

    def get_equipment_intel(self, alliance_id: int, days: int = 7) -> Dict[str, Any]:
        """Comprehensive equipment intelligence. Delegated to equipment service."""
        return self.equipment.get_equipment_intel(alliance_id, days)

    def get_dashboard(self, alliance_id: int, days: int = 7) -> Dict[str, Any]:
        """
        Get complete dashboard data in a single call.

        Combines all metrics into one response for the frontend.
        """
        summary = self.get_summary(alliance_id, days)
        danger_zones = self.get_danger_zones(alliance_id, days, limit=5)
        ships_lost = self.get_ships_lost(alliance_id, days, limit=10)
        top_enemies = self.get_top_enemies(alliance_id, days, limit=5)
        hourly = self.get_hourly_activity(alliance_id, days)
        economics = self.get_economics(alliance_id, days)
        expensive_losses = self.get_expensive_losses(alliance_id, days, limit=5)
        ship_effectiveness = self.get_ship_effectiveness(alliance_id, days)
        production_needs = self.get_production_needs(alliance_id, days, limit=10)
        damage_taken = self.get_damage_taken(alliance_id, days)
        ewar_threats = self.get_ewar_threats(alliance_id, days)
        enemy_vulnerabilities = self.get_enemy_vulnerabilities(alliance_id, days, limit=5)
        recommendations = self.generate_recommendations(alliance_id, days)
        equipment_intel = self.get_equipment_intel(alliance_id, days)

        # Add activity levels to danger zones
        if danger_zones:
            max_deaths = max(z["deaths"] for z in danger_zones)
            for zone in danger_zones:
                ratio = zone["deaths"] / max_deaths if max_deaths > 0 else 0
                if ratio >= 0.8:
                    zone["activity_level"] = "CRITICAL"
                elif ratio >= 0.5:
                    zone["activity_level"] = "HIGH"
                elif ratio >= 0.25:
                    zone["activity_level"] = "MEDIUM"
                else:
                    zone["activity_level"] = "LOW"

        # Calculate total weekly production cost
        total_weekly_cost = sum(p.get("estimated_cost", 0) for p in production_needs)

        return {
            "alliance_id": alliance_id,
            "period_days": days,
            "generated_at": datetime.now().isoformat(),
            "summary": summary,
            "economics": economics,
            "danger_zones": danger_zones,
            "ships_lost": ships_lost,
            "top_enemies": top_enemies,
            "hourly_activity": hourly,
            "expensive_losses": expensive_losses,
            "ship_effectiveness": ship_effectiveness,
            "production_needs": production_needs,
            "total_weekly_production_cost": total_weekly_cost,
            "damage_taken": damage_taken,
            "ewar_threats": ewar_threats,
            "enemy_vulnerabilities": enemy_vulnerabilities,
            "recommendations": recommendations,
            "equipment_intel": equipment_intel
        }

    def get_all_alliances_summary(self, days: int = 7, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get summary for all tracked alliances, sorted by activity.
        """
        with db_cursor() as cur:
            cur.execute("""
                SELECT
                    alliance_id,
                    SUM(kills) as kills,
                    SUM(deaths) as deaths,
                    SUM(isk_destroyed) as isk_destroyed,
                    SUM(isk_lost) as isk_lost
                FROM intelligence_hourly_stats
                WHERE hour_bucket >= NOW() - INTERVAL '%s days'
                GROUP BY alliance_id
                HAVING SUM(kills) + SUM(deaths) >= 10
                ORDER BY SUM(kills) + SUM(deaths) DESC
                LIMIT %s
            """, (days, limit))

            return [
                {
                    "alliance_id": row['alliance_id'],
                    "alliance_name": f"Alliance {row['alliance_id']}",  # Name lookup deferred
                    "kills": row['kills'] or 0,
                    "deaths": row['deaths'] or 0,
                    "isk_destroyed": row['isk_destroyed'] or 0,
                    "isk_lost": row['isk_lost'] or 0,
                    "efficiency": round((row['isk_destroyed'] / (row['isk_destroyed'] + row['isk_lost'])) * 100, 1) if (row['isk_destroyed'] or 0) + (row['isk_lost'] or 0) > 0 else 0
                }
                for row in cur.fetchall()
            ]


# Singleton instance
intelligence_fast_service = IntelligenceFastService()
