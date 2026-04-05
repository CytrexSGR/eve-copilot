"""Alliance Insights Endpoints - Corp Heatmap, Participation Trends, Gatecamp Alerts, Enemy Damage,
   Burnout Index, Attrition Tracker, Survival Trainer, System Danger Radar."""

import logging
from typing import Dict, Any, List
from fastapi import APIRouter, Query

from app.database import db_cursor
from app.services.intelligence.esi_utils import batch_resolve_alliance_info
from eve_shared.utils.error_handling import handle_endpoint_errors

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/fast/{alliance_id}/corp-activity-heatmap")
@handle_endpoint_errors()
def get_corp_activity_heatmap(
    alliance_id: int,
    days: int = Query(7, ge=1, le=30)
) -> Dict[str, Any]:
    """
    Get per-corporation activity breakdown by hour (24h × top corps).
    Shows when each corp is most active based on killmail timestamps.
    """
    with db_cursor() as cur:
        # Get top 10 active corps with hourly breakdown
        cur.execute("""
            WITH corp_kills AS (
                SELECT
                    ka.corporation_id,
                    EXTRACT(HOUR FROM k.killmail_time)::INT as hour,
                    COUNT(DISTINCT k.killmail_id) as kills
                FROM killmail_attackers ka
                JOIN killmails k ON ka.killmail_id = k.killmail_id
                WHERE ka.alliance_id = %s
                  AND k.killmail_time >= NOW() - INTERVAL '%s days'
                  AND ka.corporation_id IS NOT NULL
                GROUP BY ka.corporation_id, EXTRACT(HOUR FROM k.killmail_time)
            ),
            corp_deaths AS (
                SELECT
                    victim_corporation_id as corporation_id,
                    EXTRACT(HOUR FROM killmail_time)::INT as hour,
                    COUNT(*) as deaths
                FROM killmails
                WHERE victim_alliance_id = %s
                  AND killmail_time >= NOW() - INTERVAL '%s days'
                  AND victim_corporation_id IS NOT NULL
                GROUP BY victim_corporation_id, EXTRACT(HOUR FROM killmail_time)
            ),
            corp_totals AS (
                SELECT
                    COALESCE(ck.corporation_id, cd.corporation_id) as corporation_id,
                    SUM(COALESCE(ck.kills, 0) + COALESCE(cd.deaths, 0)) as total_activity
                FROM corp_kills ck
                FULL OUTER JOIN corp_deaths cd
                    ON ck.corporation_id = cd.corporation_id AND ck.hour = cd.hour
                GROUP BY COALESCE(ck.corporation_id, cd.corporation_id)
                ORDER BY total_activity DESC
                LIMIT 10
            )
            SELECT
                ct.corporation_id,
                c.corporation_name,
                c.ticker,
                COALESCE(ck.hour, cd.hour) as hour,
                COALESCE(ck.kills, 0) as kills,
                COALESCE(cd.deaths, 0) as deaths
            FROM corp_totals ct
            LEFT JOIN corp_kills ck ON ct.corporation_id = ck.corporation_id
            FULL OUTER JOIN corp_deaths cd
                ON ct.corporation_id = cd.corporation_id
                AND COALESCE(ck.hour, -1) = COALESCE(cd.hour, -1)
            LEFT JOIN corporations c ON ct.corporation_id = c.corporation_id
            WHERE COALESCE(ck.hour, cd.hour) IS NOT NULL
            ORDER BY ct.corporation_id, COALESCE(ck.hour, cd.hour)
        """, (alliance_id, days, alliance_id, days))

        rows = cur.fetchall()

        # Build corp → hourly data map
        corps_map: Dict[int, Dict] = {}
        for row in rows:
            corp_id = row["corporation_id"]
            if corp_id not in corps_map:
                corps_map[corp_id] = {
                    "corp_id": corp_id,
                    "corp_name": row["corporation_name"] or f"Corp {corp_id}",
                    "ticker": row["ticker"] or "???",
                    "hours": [0] * 24,
                    "total": 0
                }
            hour = row["hour"]
            if hour is not None and 0 <= hour < 24:
                activity = (row["kills"] or 0) + (row["deaths"] or 0)
                corps_map[corp_id]["hours"][hour] += activity
                corps_map[corp_id]["total"] += activity

        # Sort by total activity
        corps = sorted(corps_map.values(), key=lambda x: x["total"], reverse=True)

        return {
            "alliance_id": alliance_id,
            "period_days": days,
            "corps": corps
        }

@router.get("/fast/{alliance_id}/participation-trends")
@handle_endpoint_errors()
def get_participation_trends(
    alliance_id: int,
    days: int = Query(14, ge=7, le=90)
) -> Dict[str, Any]:
    """
    Get daily participation trends showing if alliance activity is rising or falling.
    Includes active pilot count, kills, deaths per day and trend direction.
    """
    with db_cursor() as cur:
        # Daily activity breakdown
        cur.execute("""
            WITH daily_kills AS (
                SELECT
                    DATE(k.killmail_time) as day,
                    COUNT(DISTINCT k.killmail_id) as kills,
                    COUNT(DISTINCT ka.character_id) as active_attackers,
                    SUM(k.ship_value) as isk_destroyed
                FROM killmail_attackers ka
                JOIN killmails k ON ka.killmail_id = k.killmail_id
                WHERE ka.alliance_id = %s
                  AND k.killmail_time >= NOW() - INTERVAL '%s days'
                GROUP BY DATE(k.killmail_time)
            ),
            daily_deaths AS (
                SELECT
                    DATE(killmail_time) as day,
                    COUNT(*) as deaths,
                    COUNT(DISTINCT victim_character_id) as pilots_lost,
                    SUM(ship_value) as isk_lost
                FROM killmails
                WHERE victim_alliance_id = %s
                  AND killmail_time >= NOW() - INTERVAL '%s days'
                GROUP BY DATE(killmail_time)
            )
            SELECT
                COALESCE(dk.day, dd.day) as day,
                COALESCE(dk.kills, 0) as kills,
                COALESCE(dd.deaths, 0) as deaths,
                COALESCE(dk.active_attackers, 0) as active_pilots,
                COALESCE(dk.isk_destroyed, 0) as isk_destroyed,
                COALESCE(dd.isk_lost, 0) as isk_lost
            FROM daily_kills dk
            FULL OUTER JOIN daily_deaths dd ON dk.day = dd.day
            ORDER BY COALESCE(dk.day, dd.day)
        """, (alliance_id, days, alliance_id, days))

        daily_data = []
        for row in cur.fetchall():
            daily_data.append({
                "day": row["day"].isoformat() if row["day"] else None,
                "kills": row["kills"],
                "deaths": row["deaths"],
                "active_pilots": row["active_pilots"],
                "isk_destroyed": float(row["isk_destroyed"] or 0),
                "isk_lost": float(row["isk_lost"] or 0)
            })

        # Calculate trend (compare last half vs first half)
        if len(daily_data) >= 4:
            mid = len(daily_data) // 2
            first_half = daily_data[:mid]
            second_half = daily_data[mid:]

            first_avg_kills = sum(d["kills"] for d in first_half) / len(first_half)
            second_avg_kills = sum(d["kills"] for d in second_half) / len(second_half)

            first_avg_pilots = sum(d["active_pilots"] for d in first_half) / len(first_half)
            second_avg_pilots = sum(d["active_pilots"] for d in second_half) / len(second_half)

            kills_trend_pct = 0.0
            if first_avg_kills > 0:
                kills_trend_pct = round((second_avg_kills - first_avg_kills) / first_avg_kills * 100, 1)

            pilots_trend_pct = 0.0
            if first_avg_pilots > 0:
                pilots_trend_pct = round((second_avg_pilots - first_avg_pilots) / first_avg_pilots * 100, 1)

            trend_direction = "rising" if kills_trend_pct > 5 else "falling" if kills_trend_pct < -5 else "stable"
        else:
            kills_trend_pct = 0.0
            pilots_trend_pct = 0.0
            trend_direction = "insufficient_data"

        return {
            "alliance_id": alliance_id,
            "period_days": days,
            "daily": daily_data,
            "trend": {
                "direction": trend_direction,
                "kills_change_pct": kills_trend_pct,
                "pilots_change_pct": pilots_trend_pct
            }
        }

@router.get("/fast/{alliance_id}/hunting/gatecamp-alerts")
@handle_endpoint_errors()
def get_gatecamp_alerts(
    alliance_id: int,
    minutes: int = Query(60, ge=10, le=360)
) -> List[Dict[str, Any]]:
    """
    Detect probable gatecamps or kill hotspots in systems where the alliance
    operates. A system with 3+ kills within the time window is flagged.
    """
    with db_cursor() as cur:
        cur.execute("""
            SELECT
                k.solar_system_id,
                s."solarSystemName" as system_name,
                r."regionName" as region_name,
                ROUND(s."security"::numeric, 1) as security_status,
                COUNT(*) as kills,
                COUNT(*) FILTER (WHERE k.ship_type_id = 670) as pod_kills,
                COUNT(DISTINCT k.victim_alliance_id) FILTER (WHERE k.victim_alliance_id IS NOT NULL) as victim_alliances,
                MIN(k.killmail_time) as first_kill,
                MAX(k.killmail_time) as last_kill,
                SUM(k.ship_value) as total_isk,
                ARRAY_AGG(DISTINCT ka_top.alliance_id) FILTER (WHERE ka_top.alliance_id IS NOT NULL AND ka_top.alliance_id != %s) as attacker_alliances
            FROM killmails k
            LEFT JOIN "mapSolarSystems" s ON k.solar_system_id = s."solarSystemID"
            LEFT JOIN "mapRegions" r ON s."regionID" = r."regionID"
            LEFT JOIN LATERAL (
                SELECT DISTINCT ka.alliance_id
                FROM killmail_attackers ka
                WHERE ka.killmail_id = k.killmail_id
                  AND ka.alliance_id IS NOT NULL
                LIMIT 3
            ) ka_top ON true
            WHERE k.killmail_time >= NOW() - INTERVAL '%s minutes'
              AND k.solar_system_id IN (
                  -- Systems where alliance is active (kills or losses last 7d)
                  SELECT DISTINCT solar_system_id FROM killmails
                  WHERE (victim_alliance_id = %s OR killmail_id IN (
                      SELECT killmail_id FROM killmail_attackers WHERE alliance_id = %s
                  ))
                  AND killmail_time >= NOW() - INTERVAL '7 days'
              )
            GROUP BY k.solar_system_id, s."solarSystemName", r."regionName", s."security"
            HAVING COUNT(*) >= 3
            ORDER BY COUNT(*) DESC
            LIMIT 10
        """, (alliance_id, minutes, alliance_id, alliance_id))

        results = []
        for row in cur.fetchall():
            kills = row["kills"]
            pod_kills = row["pod_kills"] or 0
            duration_sec = 0
            if row["first_kill"] and row["last_kill"]:
                duration_sec = int((row["last_kill"] - row["first_kill"]).total_seconds())

            # Classify alert severity
            if kills >= 10 or pod_kills >= 5:
                severity = "critical"
            elif kills >= 6:
                severity = "high"
            else:
                severity = "medium"

            # Determine camp type
            if pod_kills > kills * 0.4:
                camp_type = "gatecamp"
            elif row["victim_alliances"] <= 2 and kills >= 5:
                camp_type = "targeted_hunt"
            else:
                camp_type = "hotspot"

            results.append({
                "system_id": row["solar_system_id"],
                "system_name": row["system_name"] or f"System {row['solar_system_id']}",
                "region_name": row["region_name"] or "Unknown",
                "security_status": float(row["security_status"] or 0),
                "kills": kills,
                "pod_kills": pod_kills,
                "total_isk": float(row["total_isk"] or 0),
                "duration_seconds": duration_sec,
                "severity": severity,
                "camp_type": camp_type,
                "victim_alliances": row["victim_alliances"] or 0,
                "attacker_alliance_ids": [a for a in (row["attacker_alliances"] or []) if a] [:5]
            })

        return results

@router.get("/fast/{alliance_id}/hunting/enemy-damage-profiles")
@handle_endpoint_errors()
def get_enemy_damage_profiles(
    alliance_id: int,
    days: int = Query(30, ge=1, le=90),
    limit: int = Query(5, ge=1, le=10)
) -> List[Dict[str, Any]]:
    """
    Get damage type profile for each top enemy alliance.
    Shows what damage type each specific enemy deals, enabling targeted fitting.
    """
    with db_cursor() as cur:
        # Get top enemy alliances and their ship usage
        cur.execute("""
            WITH top_enemies AS (
                SELECT
                    ka.alliance_id as enemy_id,
                    COUNT(DISTINCT k.killmail_id) as kills
                FROM killmails k
                JOIN killmail_attackers ka ON k.killmail_id = ka.killmail_id
                WHERE k.victim_alliance_id = %s
                  AND k.killmail_time >= NOW() - INTERVAL '%s days'
                  AND ka.alliance_id IS NOT NULL
                  AND ka.alliance_id != %s
                GROUP BY ka.alliance_id
                ORDER BY kills DESC
                LIMIT %s
            )
            SELECT
                te.enemy_id,
                te.kills,
                ka.ship_type_id,
                t."typeName" as ship_name,
                g."groupName" as ship_class,
                COUNT(*) as usage_count,
                CASE
                    WHEN t."typeName" IN ('Cerberus', 'Caracal', 'Drake', 'Ferox', 'Raven', 'Rokh',
                                           'Cormorant', 'Naga', 'Osprey Navy Issue', 'Tengu')
                        THEN 'kinetic'
                    WHEN t."typeName" IN ('Vagabond', 'Muninn', 'Hurricane', 'Maelstrom', 'Tornado',
                                           'Svipul', 'Loki', 'Typhoon', 'Tempest')
                        THEN 'explosive'
                    WHEN t."typeName" IN ('Zealot', 'Sacrilege', 'Harbinger', 'Abaddon', 'Oracle',
                                           'Retribution', 'Legion', 'Confessor', 'Apocalypse',
                                           'Nightmare', 'Paladin')
                        THEN 'em'
                    WHEN t."typeName" IN ('Ishtar', 'Deimos', 'Myrmidon', 'Megathron', 'Talos',
                                           'Proteus', 'Hecate', 'Brutix', 'Dominix', 'Kronos')
                        THEN 'thermal'
                    ELSE 'mixed'
                END as primary_damage
            FROM top_enemies te
            JOIN killmail_attackers ka ON ka.alliance_id = te.enemy_id
            JOIN killmails k ON ka.killmail_id = k.killmail_id
            LEFT JOIN "invTypes" t ON ka.ship_type_id = t."typeID"
            LEFT JOIN "invGroups" g ON t."groupID" = g."groupID"
            WHERE k.victim_alliance_id = %s
              AND k.killmail_time >= NOW() - INTERVAL '%s days'
              AND ka.ship_type_id IS NOT NULL
            GROUP BY te.enemy_id, te.kills, ka.ship_type_id, t."typeName", g."groupName"
            ORDER BY te.kills DESC, usage_count DESC
        """, (alliance_id, days, alliance_id, limit, alliance_id, days))

        rows = cur.fetchall()

    # Build enemy profiles
    enemies_map: Dict[int, Dict] = {}
    for row in rows:
        eid = row["enemy_id"]
        if eid not in enemies_map:
            enemies_map[eid] = {
                "alliance_id": eid,
                "kills": row["kills"],
                "top_ships": [],
                "damage_counts": {"kinetic": 0, "thermal": 0, "em": 0, "explosive": 0, "mixed": 0}
            }
        enemies_map[eid]["damage_counts"][row["primary_damage"]] += row["usage_count"]
        if len(enemies_map[eid]["top_ships"]) < 3:
            enemies_map[eid]["top_ships"].append({
                "ship": row["ship_name"] or "Unknown",
                "ship_class": row["ship_class"] or "Unknown",
                "count": row["usage_count"]
            })

    # Resolve alliance names
    enemy_ids = list(enemies_map.keys())
    alliance_info = batch_resolve_alliance_info(enemy_ids)

    # Calculate damage profiles
    results = []
    for eid, data in enemies_map.items():
        total = sum(data["damage_counts"].values()) or 1
        profile = {
            k: round(v / total * 100)
            for k, v in data["damage_counts"].items()
            if k != "mixed"
        }
        # Distribute 'mixed' evenly
        mixed_pct = round(data["damage_counts"]["mixed"] / total * 100)
        if mixed_pct > 0:
            for k in profile:
                profile[k] += mixed_pct // 4

        primary_type = max(profile, key=profile.get)

        tank_recs = {
            "kinetic": "Kinetic Hardeners",
            "thermal": "Thermal Hardeners",
            "em": "EM Hardeners",
            "explosive": "Explosive Hardeners"
        }

        results.append({
            "alliance_id": eid,
            "alliance_name": alliance_info.get(eid, {}).get("name", f"Alliance {eid}"),
            "ticker": alliance_info.get(eid, {}).get("ticker", "???"),
            "kills": data["kills"],
            "top_ships": data["top_ships"],
            "damage_profile": profile,
            "primary_damage": primary_type,
            "tank_recommendation": tank_recs.get(primary_type, "Omni Tank")
        })

    results.sort(key=lambda x: x["kills"], reverse=True)
    return results

@router.get("/fast/{alliance_id}/burnout-index")
@handle_endpoint_errors()
def get_burnout_index(
    alliance_id: int,
    days: int = Query(14, ge=7, le=90)
) -> Dict[str, Any]:
    """
    Burnout Index: kills per active pilot over time.
    If kills/pilot rises while pilot count drops, the remaining core is overworked.
    """
    with db_cursor() as cur:
        cur.execute("""
            WITH daily AS (
                SELECT
                    DATE(k.killmail_time) as day,
                    COUNT(DISTINCT k.killmail_id) as kills,
                    COUNT(DISTINCT ka.character_id) as active_pilots
                FROM killmail_attackers ka
                JOIN killmails k ON ka.killmail_id = k.killmail_id
                WHERE ka.alliance_id = %s
                  AND k.killmail_time >= NOW() - INTERVAL '%s days'
                  AND ka.character_id IS NOT NULL
                GROUP BY DATE(k.killmail_time)
                ORDER BY day
            )
            SELECT
                day,
                kills,
                active_pilots,
                CASE WHEN active_pilots > 0
                     THEN ROUND(kills::numeric / active_pilots, 2)
                     ELSE 0 END as kills_per_pilot
            FROM daily
        """, (alliance_id, days))

        daily = []
        for row in cur.fetchall():
            daily.append({
                "day": row["day"].isoformat() if row["day"] else None,
                "kills": row["kills"],
                "active_pilots": row["active_pilots"],
                "kills_per_pilot": float(row["kills_per_pilot"])
            })

        # Burnout detection: compare halves
        burnout_risk = "low"
        kpp_trend = 0.0
        pilot_trend = 0.0
        if len(daily) >= 4:
            mid = len(daily) // 2
            first = daily[:mid]
            second = daily[mid:]

            first_avg_kpp = sum(d["kills_per_pilot"] for d in first) / len(first)
            second_avg_kpp = sum(d["kills_per_pilot"] for d in second) / len(second)
            first_avg_pilots = sum(d["active_pilots"] for d in first) / len(first)
            second_avg_pilots = sum(d["active_pilots"] for d in second) / len(second)

            if first_avg_kpp > 0:
                kpp_trend = round((second_avg_kpp - first_avg_kpp) / first_avg_kpp * 100, 1)
            if first_avg_pilots > 0:
                pilot_trend = round((second_avg_pilots - first_avg_pilots) / first_avg_pilots * 100, 1)

            # Burnout = workload rising + pilots declining
            if kpp_trend > 15 and pilot_trend < -10:
                burnout_risk = "critical"
            elif kpp_trend > 10 and pilot_trend < -5:
                burnout_risk = "high"
            elif kpp_trend > 5 and pilot_trend < 0:
                burnout_risk = "moderate"

        # Current averages
        total_kills = sum(d["kills"] for d in daily)
        total_pilots = sum(d["active_pilots"] for d in daily)
        avg_kpp = round(total_kills / max(total_pilots, 1), 2)

        return {
            "alliance_id": alliance_id,
            "period_days": days,
            "daily": daily,
            "summary": {
                "avg_kills_per_pilot": avg_kpp,
                "kpp_trend_pct": kpp_trend,
                "pilot_trend_pct": pilot_trend,
                "burnout_risk": burnout_risk
            }
        }

@router.get("/fast/{alliance_id}/attrition-tracker")
@handle_endpoint_errors()
def get_attrition_tracker(
    alliance_id: int,
    days: int = Query(30, ge=14, le=90)
) -> Dict[str, Any]:
    """
    Attrition Tracker: find pilots who were active for this alliance in the past
    but now appear on killmails for other alliances. Shows where they went.
    """
    with db_cursor() as cur:
        # Find pilots who were active for this alliance in the first half of the period
        # but are now appearing for different alliances in the recent half
        half_days = days // 2
        cur.execute("""
            WITH old_pilots AS (
                -- Pilots active for this alliance in the older period
                SELECT DISTINCT ka.character_id
                FROM killmail_attackers ka
                JOIN killmails k ON ka.killmail_id = k.killmail_id
                WHERE ka.alliance_id = %s
                  AND k.killmail_time >= NOW() - INTERVAL '%s days'
                  AND k.killmail_time < NOW() - INTERVAL '%s days'
                  AND ka.character_id IS NOT NULL
            ),
            current_pilots AS (
                -- Pilots still active for this alliance recently
                SELECT DISTINCT ka.character_id
                FROM killmail_attackers ka
                JOIN killmails k ON ka.killmail_id = k.killmail_id
                WHERE ka.alliance_id = %s
                  AND k.killmail_time >= NOW() - INTERVAL '%s days'
                  AND ka.character_id IS NOT NULL
            ),
            departed AS (
                -- Pilots who left: were active before but NOT recently for this alliance
                SELECT character_id FROM old_pilots
                EXCEPT
                SELECT character_id FROM current_pilots
            ),
            new_homes AS (
                -- Where did they go? Check recent killmails for their new alliance
                SELECT
                    d.character_id,
                    ka.alliance_id as new_alliance_id,
                    COUNT(*) as activity_count,
                    ROW_NUMBER() OVER (PARTITION BY d.character_id ORDER BY COUNT(*) DESC) as rn
                FROM departed d
                JOIN killmail_attackers ka ON d.character_id = ka.character_id
                JOIN killmails k ON ka.killmail_id = k.killmail_id
                WHERE k.killmail_time >= NOW() - INTERVAL '%s days'
                  AND ka.alliance_id IS NOT NULL
                  AND ka.alliance_id != %s
                GROUP BY d.character_id, ka.alliance_id
            )
            SELECT
                nh.new_alliance_id,
                COUNT(DISTINCT nh.character_id) as pilot_count,
                SUM(nh.activity_count) as total_activity
            FROM new_homes nh
            WHERE nh.rn = 1
            GROUP BY nh.new_alliance_id
            ORDER BY pilot_count DESC
            LIMIT 10
        """, (alliance_id, days, half_days, alliance_id, half_days, half_days, alliance_id))

        destinations = cur.fetchall()

        # Also get total departed count
        cur.execute("""
            WITH old_pilots AS (
                SELECT DISTINCT ka.character_id
                FROM killmail_attackers ka
                JOIN killmails k ON ka.killmail_id = k.killmail_id
                WHERE ka.alliance_id = %s
                  AND k.killmail_time >= NOW() - INTERVAL '%s days'
                  AND k.killmail_time < NOW() - INTERVAL '%s days'
                  AND ka.character_id IS NOT NULL
            ),
            current_pilots AS (
                SELECT DISTINCT ka.character_id
                FROM killmail_attackers ka
                JOIN killmails k ON ka.killmail_id = k.killmail_id
                WHERE ka.alliance_id = %s
                  AND k.killmail_time >= NOW() - INTERVAL '%s days'
                  AND ka.character_id IS NOT NULL
            )
            SELECT
                (SELECT COUNT(*) FROM old_pilots) as old_count,
                (SELECT COUNT(*) FROM current_pilots) as current_count,
                (SELECT COUNT(*) FROM (SELECT character_id FROM old_pilots EXCEPT SELECT character_id FROM current_pilots) x) as departed_count
        """, (alliance_id, days, half_days, alliance_id, half_days))
        summary_row = cur.fetchone()

    # Resolve alliance names for destinations
    dest_ids = [d["new_alliance_id"] for d in destinations]
    alliance_info = batch_resolve_alliance_info(dest_ids)

    dest_list = []
    for d in destinations:
        aid = d["new_alliance_id"]
        info = alliance_info.get(aid, {})
        dest_list.append({
            "alliance_id": aid,
            "alliance_name": info.get("name", f"Alliance {aid}"),
            "ticker": info.get("ticker", "???"),
            "pilot_count": d["pilot_count"],
            "total_activity": d["total_activity"]
        })

    old_count = summary_row["old_count"] if summary_row else 0
    current_count = summary_row["current_count"] if summary_row else 0
    departed_count = summary_row["departed_count"] if summary_row else 0
    retention_rate = round((1 - departed_count / max(old_count, 1)) * 100, 1)

    return {
        "alliance_id": alliance_id,
        "period_days": days,
        "summary": {
            "old_active_pilots": old_count,
            "current_active_pilots": current_count,
            "departed_pilots": departed_count,
            "retention_rate": retention_rate,
            "tracked_destinations": sum(d["pilot_count"] for d in dest_list)
        },
        "destinations": dest_list
    }

@router.get("/fast/{alliance_id}/survival-trainer")
@handle_endpoint_errors()
def get_survival_trainer(
    alliance_id: int,
    days: int = Query(30, ge=7, le=90),
    limit: int = Query(20, ge=5, le=50)
) -> Dict[str, Any]:
    """
    Survival Trainer: identify pilots with poor pod survival rates.
    Ranks pilots by pod loss rate and provides per-pilot stats for targeted training.
    """
    with db_cursor() as cur:
        cur.execute("""
            WITH pilot_losses AS (
                SELECT
                    victim_character_id as character_id,
                    COUNT(*) as total_deaths,
                    COUNT(*) FILTER (WHERE ship_type_id = 670) as pod_deaths,
                    COUNT(*) FILTER (WHERE ship_type_id != 670) as ship_deaths,
                    SUM(ship_value) FILTER (WHERE ship_type_id = 670) as pod_isk_lost,
                    SUM(ship_value) FILTER (WHERE ship_type_id != 670) as ship_isk_lost,
                    MAX(killmail_time) as last_death
                FROM killmails
                WHERE victim_alliance_id = %s
                  AND killmail_time >= NOW() - INTERVAL '%s days'
                  AND victim_character_id IS NOT NULL
                GROUP BY victim_character_id
                HAVING COUNT(*) FILTER (WHERE ship_type_id != 670) >= 3  -- At least 3 ship losses
            )
            SELECT
                pl.character_id,
                COALESCE(cn.character_name, CONCAT('Pilot ', pl.character_id)) as character_name,
                c.corporation_name as corp_name,
                c.ticker,
                pl.total_deaths,
                pl.pod_deaths,
                pl.ship_deaths,
                COALESCE(pl.pod_isk_lost, 0) as pod_isk_lost,
                COALESCE(pl.ship_isk_lost, 0) as ship_isk_lost,
                CASE WHEN pl.ship_deaths > 0
                     THEN ROUND((1 - pl.pod_deaths::numeric / pl.ship_deaths) * 100, 1)
                     ELSE 100 END as survival_rate,
                pl.last_death
            FROM pilot_losses pl
            LEFT JOIN character_name_cache cn ON pl.character_id = cn.character_id
            LEFT JOIN killmails k_latest ON pl.character_id = k_latest.victim_character_id
                AND k_latest.killmail_time = pl.last_death
            LEFT JOIN corporations c ON k_latest.victim_corporation_id = c.corporation_id
            ORDER BY
                -- Sort by worst survival rate first, with enough data
                CASE WHEN pl.ship_deaths > 0
                     THEN pl.pod_deaths::numeric / pl.ship_deaths
                     ELSE 0 END DESC,
                pl.pod_deaths DESC
            LIMIT %s
        """, (alliance_id, days, limit))

        pilots = []
        for row in cur.fetchall():
            survival_rate = float(row["survival_rate"])
            if survival_rate >= 80:
                risk_level = "good"
            elif survival_rate >= 50:
                risk_level = "at_risk"
            else:
                risk_level = "critical"

            # Training tips based on survival rate
            if survival_rate < 30:
                tip = "Needs Insta-Warp bookmark training. Set up tactical bookmarks at gates."
            elif survival_rate < 50:
                tip = "Practice pre-aligning to celestials during combat. Consider Warp Core Stabilizers."
            elif survival_rate < 70:
                tip = "Good basics, refine awareness. Use D-Scan and check local before warping."
            else:
                tip = "Strong survival instincts. Keep it up."

            pilots.append({
                "character_id": row["character_id"],
                "character_name": row["character_name"],
                "corp_name": row["corp_name"] or "Unknown",
                "ticker": row["ticker"] or "???",
                "total_deaths": row["total_deaths"],
                "pod_deaths": row["pod_deaths"],
                "ship_deaths": row["ship_deaths"],
                "pod_isk_lost": float(row["pod_isk_lost"]),
                "ship_isk_lost": float(row["ship_isk_lost"]),
                "survival_rate": survival_rate,
                "risk_level": risk_level,
                "training_tip": tip
            })

        # Alliance-wide stats
        total_ship_deaths = sum(p["ship_deaths"] for p in pilots)
        total_pod_deaths = sum(p["pod_deaths"] for p in pilots)
        alliance_survival = round((1 - total_pod_deaths / max(total_ship_deaths, 1)) * 100, 1)
        critical_count = sum(1 for p in pilots if p["risk_level"] == "critical")
        at_risk_count = sum(1 for p in pilots if p["risk_level"] == "at_risk")

        return {
            "alliance_id": alliance_id,
            "period_days": days,
            "summary": {
                "alliance_survival_rate": alliance_survival,
                "pilots_analyzed": len(pilots),
                "critical_pilots": critical_count,
                "at_risk_pilots": at_risk_count,
                "total_pod_isk_wasted": sum(p["pod_isk_lost"] for p in pilots)
            },
            "pilots": pilots
        }

@router.get("/fast/{alliance_id}/hunting/system-danger-radar")
@handle_endpoint_errors()
def get_system_danger_radar(
    alliance_id: int,
    days: int = Query(7, ge=1, le=30),
    limit: int = Query(10, ge=3, le=20)
) -> List[Dict[str, Any]]:
    """
    System Danger Radar: persistent danger analysis for the deadliest systems.
    Shows kill history, peak danger hours, top attackers per system.
    """
    with db_cursor() as cur:
        # Get top death systems with detailed breakdown
        cur.execute("""
            WITH system_deaths AS (
                SELECT
                    k.solar_system_id,
                    s."solarSystemName" as system_name,
                    r."regionName" as region_name,
                    ROUND(s."security"::numeric, 1) as security,
                    COUNT(*) as total_deaths,
                    COUNT(*) FILTER (WHERE k.ship_type_id = 670) as pod_deaths,
                    SUM(k.ship_value) as isk_lost,
                    COUNT(DISTINCT DATE(k.killmail_time)) as active_days,
                    COUNT(DISTINCT k.victim_character_id) as unique_victims
                FROM killmails k
                LEFT JOIN "mapSolarSystems" s ON k.solar_system_id = s."solarSystemID"
                LEFT JOIN "mapRegions" r ON s."regionID" = r."regionID"
                WHERE k.victim_alliance_id = %s
                  AND k.killmail_time >= NOW() - INTERVAL '%s days'
                GROUP BY k.solar_system_id, s."solarSystemName", r."regionName", s."security"
                ORDER BY total_deaths DESC
                LIMIT %s
            )
            SELECT * FROM system_deaths
        """, (alliance_id, days, limit))

        systems = cur.fetchall()
        system_ids = [s["solar_system_id"] for s in systems]

        if not system_ids:
            return []

        # Get hourly danger distribution per system
        cur.execute("""
            SELECT
                k.solar_system_id,
                EXTRACT(HOUR FROM k.killmail_time)::INT as hour,
                COUNT(*) as deaths
            FROM killmails k
            WHERE k.victim_alliance_id = %s
              AND k.killmail_time >= NOW() - INTERVAL '%s days'
              AND k.solar_system_id = ANY(%s)
            GROUP BY k.solar_system_id, EXTRACT(HOUR FROM k.killmail_time)
        """, (alliance_id, days, system_ids))

        hourly_map: Dict[int, List[int]] = {sid: [0] * 24 for sid in system_ids}
        for row in cur.fetchall():
            sid = row["solar_system_id"]
            if sid in hourly_map:
                hourly_map[sid][row["hour"]] = row["deaths"]

        # Get top attackers per system
        cur.execute("""
            SELECT
                k.solar_system_id,
                ka.alliance_id as attacker_alliance_id,
                COUNT(DISTINCT k.killmail_id) as kills
            FROM killmails k
            JOIN killmail_attackers ka ON k.killmail_id = ka.killmail_id
            WHERE k.victim_alliance_id = %s
              AND k.killmail_time >= NOW() - INTERVAL '%s days'
              AND k.solar_system_id = ANY(%s)
              AND ka.alliance_id IS NOT NULL
              AND ka.alliance_id != %s
            GROUP BY k.solar_system_id, ka.alliance_id
            ORDER BY k.solar_system_id, kills DESC
        """, (alliance_id, days, system_ids, alliance_id))

        attacker_map: Dict[int, List[Dict]] = {sid: [] for sid in system_ids}
        for row in cur.fetchall():
            sid = row["solar_system_id"]
            if sid in attacker_map and len(attacker_map[sid]) < 3:
                attacker_map[sid].append({
                    "alliance_id": row["attacker_alliance_id"],
                    "kills": row["kills"]
                })

    # Resolve attacker alliance names
    all_attacker_ids = set()
    for attackers in attacker_map.values():
        for a in attackers:
            all_attacker_ids.add(a["alliance_id"])
    alliance_info = batch_resolve_alliance_info(list(all_attacker_ids))

    results = []
    for sys in systems:
        sid = sys["solar_system_id"]
        hours = hourly_map.get(sid, [0] * 24)
        peak_hour = hours.index(max(hours)) if max(hours) > 0 else 0
        deaths_per_day = round(sys["total_deaths"] / max(sys["active_days"], 1), 1)

        # Danger level
        if sys["total_deaths"] >= 50:
            danger_level = "critical"
        elif sys["total_deaths"] >= 20:
            danger_level = "high"
        elif sys["total_deaths"] >= 10:
            danger_level = "medium"
        else:
            danger_level = "low"

        attackers = []
        for a in attacker_map.get(sid, []):
            info = alliance_info.get(a["alliance_id"], {})
            attackers.append({
                "alliance_id": a["alliance_id"],
                "alliance_name": info.get("name", f"Alliance {a['alliance_id']}"),
                "ticker": info.get("ticker", "???"),
                "kills": a["kills"]
            })

        results.append({
            "system_id": sid,
            "system_name": sys["system_name"] or f"System {sid}",
            "region_name": sys["region_name"] or "Unknown",
            "security": float(sys["security"] or 0),
            "total_deaths": sys["total_deaths"],
            "pod_deaths": sys["pod_deaths"] or 0,
            "isk_lost": float(sys["isk_lost"] or 0),
            "unique_victims": sys["unique_victims"] or 0,
            "active_days": sys["active_days"] or 0,
            "deaths_per_day": deaths_per_day,
            "danger_level": danger_level,
            "peak_hour": peak_hour,
            "hourly_deaths": hours,
            "top_attackers": attackers
        })

    return results

@router.get("/fast/{alliance_id}/defence/chokepoints")
@handle_endpoint_errors()
def get_defence_chokepoints(
    alliance_id: int,
    days: int = Query(30, ge=7, le=90)
) -> Dict[str, Any]:
    """
    Chokepoint Analysis: find systems that sit on the shortest paths between
    enemy staging (top danger zones) and alliance sovereignty space.
    Systems appearing on many routes are strategic bottlenecks.
    """
    with db_cursor() as cur:
        # 1. Get alliance sov systems
        cur.execute("""
            SELECT solar_system_id
            FROM sovereignty_map_cache
            WHERE alliance_id = %s
        """, (alliance_id,))
        sov_systems = [r["solar_system_id"] for r in cur.fetchall()]

        if not sov_systems:
            return {
                "alliance_id": alliance_id,
                "chokepoints": [],
                "sov_system_count": 0,
                "danger_zone_count": 0
            }

        # 2. Get top 10 danger zones (systems where alliance dies most)
        cur.execute("""
            SELECT solar_system_id, COUNT(*) as deaths
            FROM killmails
            WHERE victim_alliance_id = %s
              AND killmail_time >= NOW() - INTERVAL '%s days'
              AND solar_system_id IS NOT NULL
            GROUP BY solar_system_id
            ORDER BY deaths DESC
            LIMIT 10
        """, (alliance_id, days))
        danger_zones = [r["solar_system_id"] for r in cur.fetchall()]

        if not danger_zones:
            return {
                "alliance_id": alliance_id,
                "chokepoints": [],
                "sov_system_count": len(sov_systems),
                "danger_zone_count": 0
            }

        # 3. Build adjacency map from mapSolarSystemJumps
        cur.execute("""
            SELECT "fromSolarSystemID", "toSolarSystemID"
            FROM "mapSolarSystemJumps"
        """)
        adj: Dict[int, List[int]] = {}
        for row in cur.fetchall():
            f, t = row["fromSolarSystemID"], row["toSolarSystemID"]
            adj.setdefault(f, []).append(t)
            adj.setdefault(t, []).append(f)

        # 4. BFS shortest paths from each danger zone to each sov system
        from collections import deque

        intermediate_counts: Dict[int, int] = {}
        total_routes = 0

        # Limit to first 5 sov systems and all danger zones for performance
        sov_sample = sov_systems[:5]

        for dz in danger_zones:
            for sv in sov_sample:
                if dz == sv:
                    continue
                # BFS to find shortest path
                queue = deque([(dz, [dz])])
                visited = {dz}
                found_path: List[int] = []
                while queue:
                    node, path = queue.popleft()
                    if node == sv:
                        found_path = path
                        break
                    if len(path) > 30:  # max path length
                        break
                    for nb in adj.get(node, []):
                        if nb not in visited:
                            visited.add(nb)
                            queue.append((nb, path + [nb]))
                if found_path and len(found_path) > 2:
                    total_routes += 1
                    for sys_id in found_path[1:-1]:  # exclude start/end
                        intermediate_counts[sys_id] = intermediate_counts.get(sys_id, 0) + 1

        if not intermediate_counts or total_routes == 0:
            return {
                "alliance_id": alliance_id,
                "chokepoints": [],
                "sov_system_count": len(sov_systems),
                "danger_zone_count": len(danger_zones)
            }

        # 5. Top chokepoints by route count
        top_systems = sorted(intermediate_counts.items(), key=lambda x: x[1], reverse=True)[:15]
        top_ids = [s[0] for s in top_systems]

        # 6. Enrich with system info and kill data
        cur.execute("""
            SELECT
                s."solarSystemID" as system_id,
                s."solarSystemName" as system_name,
                r."regionName" as region_name,
                ROUND(s."security"::numeric, 1) as security
            FROM "mapSolarSystems" s
            LEFT JOIN "mapRegions" r ON s."regionID" = r."regionID"
            WHERE s."solarSystemID" = ANY(%s)
        """, (top_ids,))
        sys_info = {r["system_id"]: r for r in cur.fetchall()}

        # Deaths in chokepoint systems
        cur.execute("""
            SELECT solar_system_id, COUNT(*) as deaths
            FROM killmails
            WHERE victim_alliance_id = %s
              AND killmail_time >= NOW() - INTERVAL '7 days'
              AND solar_system_id = ANY(%s)
            GROUP BY solar_system_id
        """, (alliance_id, top_ids))
        deaths_map = {r["solar_system_id"]: r["deaths"] for r in cur.fetchall()}

        # Jumps to nearest sov for each chokepoint
        sov_set = set(sov_systems)
        chokepoints = []
        for sys_id, route_count in top_systems:
            info = sys_info.get(sys_id, {})
            score = round(route_count / total_routes * 100)

            # Quick BFS to nearest sov
            jumps = 0
            q = deque([(sys_id, 0)])
            vis = {sys_id}
            while q:
                n, d = q.popleft()
                if n in sov_set:
                    jumps = d
                    break
                if d > 15:
                    jumps = 99
                    break
                for nb in adj.get(n, []):
                    if nb not in vis:
                        vis.add(nb)
                        q.append((nb, d + 1))

            chokepoints.append({
                "system_id": sys_id,
                "system_name": info.get("system_name") or f"System {sys_id}",
                "region_name": info.get("region_name") or "Unknown",
                "security": float(info.get("security") or 0),
                "route_count": route_count,
                "total_routes": total_routes,
                "chokepoint_score": score,
                "deaths_7d": deaths_map.get(sys_id, 0),
                "jumps_to_nearest_sov": jumps,
            })

        return {
            "alliance_id": alliance_id,
            "chokepoints": chokepoints,
            "sov_system_count": len(sov_systems),
            "danger_zone_count": len(danger_zones),
        }

@router.get("/fast/{alliance_id}/defence/allied-sync")
@handle_endpoint_errors()
def get_defence_allied_sync(
    alliance_id: int,
    days: int = Query(30, ge=7, le=90)
) -> Dict[str, Any]:
    """
    Allied Activity Sync: show coalition partner timezone coverage.
    Identify gaps where no allied coverage exists.
    """
    with db_cursor() as cur:
        # 1. Find coalition partners (fight together ≥50 times, ratio ≥1.5)
        cur.execute("""
            WITH together AS (
                SELECT
                    CASE WHEN alliance_a = %s THEN alliance_b ELSE alliance_a END as ally_id,
                    fights_together
                FROM alliance_fight_together
                WHERE (alliance_a = %s OR alliance_b = %s)
                  AND fights_together >= 50
            ),
            against AS (
                SELECT
                    CASE WHEN alliance_a = %s THEN alliance_b ELSE alliance_a END as enemy_id,
                    fights_together as fights_against
                FROM alliance_fight_together aft
                WHERE FALSE  -- placeholder; we use the fight_together ratio approach
            )
            SELECT t.ally_id, t.fights_together
            FROM together t
            ORDER BY t.fights_together DESC
            LIMIT 10
        """, (alliance_id, alliance_id, alliance_id, alliance_id))
        allies_raw = cur.fetchall()

        if not allies_raw:
            return {
                "alliance_id": alliance_id,
                "allies": [],
                "own_hourly": [0] * 24,
                "coverage": {"covered_hours": 0, "gap_hours": list(range(24)), "coverage_pct": 0},
            }

        ally_ids = [r["ally_id"] for r in allies_raw]
        ally_fights = {r["ally_id"]: r["fights_together"] for r in allies_raw}

        # 2. Own hourly activity
        cur.execute("""
            SELECT EXTRACT(HOUR FROM k.killmail_time)::INT as hour, COUNT(*) as cnt
            FROM killmail_attackers ka
            JOIN killmails k ON ka.killmail_id = k.killmail_id
            WHERE ka.alliance_id = %s
              AND k.killmail_time >= NOW() - INTERVAL '%s days'
            GROUP BY EXTRACT(HOUR FROM k.killmail_time)
        """, (alliance_id, days))
        own_hourly = [0] * 24
        for r in cur.fetchall():
            own_hourly[r["hour"]] = r["cnt"]

        # 3. Ally hourly activity
        cur.execute("""
            SELECT ka.alliance_id, EXTRACT(HOUR FROM k.killmail_time)::INT as hour, COUNT(*) as cnt
            FROM killmail_attackers ka
            JOIN killmails k ON ka.killmail_id = k.killmail_id
            WHERE ka.alliance_id = ANY(%s)
              AND k.killmail_time >= NOW() - INTERVAL '%s days'
            GROUP BY ka.alliance_id, EXTRACT(HOUR FROM k.killmail_time)
        """, (ally_ids, days))
        ally_hourly_map: Dict[int, List[int]] = {aid: [0] * 24 for aid in ally_ids}
        for r in cur.fetchall():
            ally_hourly_map[r["alliance_id"]][r["hour"]] = r["cnt"]

    # Resolve ally names
    ally_info = batch_resolve_alliance_info(ally_ids)

    # 4. Build ally list and coverage
    allies_out = []
    for aid in ally_ids:
        hourly = ally_hourly_map.get(aid, [0] * 24)
        total = sum(hourly)
        if total == 0:
            continue
        max_val = max(hourly) if hourly else 1
        threshold = max_val * 0.3
        peak_hours = [h for h in range(24) if hourly[h] >= threshold]

        # Classify timezone
        eu_count = sum(hourly[h] for h in range(16, 23))
        us_count = sum(hourly[h] for h in range(0, 7)) + sum(hourly[h] for h in range(23, 24))
        au_count = sum(hourly[h] for h in range(7, 13))
        cn_count = sum(hourly[h] for h in range(10, 16))
        tz_map = {"EU": eu_count, "US": us_count, "AU": au_count, "CN": cn_count}
        tz = max(tz_map, key=tz_map.get)

        info = ally_info.get(aid, {})
        allies_out.append({
            "alliance_id": aid,
            "alliance_name": info.get("name", f"Alliance {aid}"),
            "ticker": info.get("ticker", "???"),
            "fights_together": ally_fights.get(aid, 0),
            "hourly_activity": hourly,
            "peak_hours": peak_hours,
            "timezone": tz,
        })

    # 5. Calculate coverage
    own_max = max(own_hourly) if own_hourly else 1
    own_threshold = own_max * 0.15
    covered_hours = set()
    for h in range(24):
        if own_hourly[h] >= own_threshold:
            covered_hours.add(h)
        for ally in allies_out:
            ally_max = max(ally["hourly_activity"]) if ally["hourly_activity"] else 1
            if ally["hourly_activity"][h] >= ally_max * 0.15:
                covered_hours.add(h)

    gap_hours = sorted([h for h in range(24) if h not in covered_hours])
    coverage_pct = round(len(covered_hours) / 24 * 100, 1)

    return {
        "alliance_id": alliance_id,
        "allies": allies_out,
        "own_hourly": own_hourly,
        "coverage": {
            "covered_hours": len(covered_hours),
            "gap_hours": gap_hours,
            "coverage_pct": coverage_pct,
        },
    }

@router.get("/fast/{alliance_id}/defence/loss-velocity")
@handle_endpoint_errors()
def get_defence_loss_velocity(
    alliance_id: int,
    days: int = Query(14, ge=4, le=90)
) -> Dict[str, Any]:
    """
    Loss Velocity Monitor: track how fast each doctrine/ship class is losing ships.
    Compare current half vs previous half of period. Rising = ESCALATING.
    """
    half = days // 2
    with db_cursor() as cur:
        cur.execute("""
            WITH losses AS (
                SELECT
                    g."groupName" as ship_class,
                    k.ship_value,
                    CASE
                        WHEN k.killmail_time >= NOW() - INTERVAL '%s days' THEN 'recent'
                        ELSE 'previous'
                    END as period
                FROM killmails k
                LEFT JOIN "invTypes" t ON k.ship_type_id = t."typeID"
                LEFT JOIN "invGroups" g ON t."groupID" = g."groupID"
                WHERE k.victim_alliance_id = %s
                  AND k.killmail_time >= NOW() - INTERVAL '%s days'
                  AND k.ship_type_id IS NOT NULL
                  AND k.ship_type_id != 670
                  AND g."groupName" IS NOT NULL
            )
            SELECT
                ship_class,
                COUNT(*) FILTER (WHERE period = 'recent') as recent_deaths,
                COALESCE(SUM(ship_value) FILTER (WHERE period = 'recent'), 0) as recent_isk,
                COUNT(*) FILTER (WHERE period = 'previous') as previous_deaths,
                COALESCE(SUM(ship_value) FILTER (WHERE period = 'previous'), 0) as previous_isk
            FROM losses
            GROUP BY ship_class
            HAVING COUNT(*) >= 3
            ORDER BY COUNT(*) FILTER (WHERE period = 'recent') DESC
            LIMIT 20
        """, (half, alliance_id, days))

        rows = cur.fetchall()

    doctrines = []
    for r in rows:
        recent_d = r["recent_deaths"]
        prev_d = r["previous_deaths"]
        recent_rate = recent_d / max(half, 1)
        prev_rate = prev_d / max(half, 1)

        if prev_rate > 0:
            velocity_pct = round((recent_rate - prev_rate) / prev_rate * 100, 1)
        elif recent_d > 0:
            velocity_pct = 100.0
        else:
            velocity_pct = 0.0

        if velocity_pct > 25:
            status = "ESCALATING"
        elif velocity_pct < -25:
            status = "STABILIZING"
        else:
            status = "STEADY"

        doctrines.append({
            "ship_class": r["ship_class"],
            "recent_deaths": recent_d,
            "recent_isk": float(r["recent_isk"]),
            "previous_deaths": prev_d,
            "previous_isk": float(r["previous_isk"]),
            "velocity_pct": velocity_pct,
            "status": status,
            "deaths_per_day_recent": round(recent_rate, 1),
            "deaths_per_day_previous": round(prev_rate, 1),
        })

    return {
        "alliance_id": alliance_id,
        "period_days": days,
        "doctrines": doctrines,
    }
