"""Power Bloc hunting intelligence endpoint."""

import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Query

from app.database import db_cursor
from app.services.intelligence.esi_utils import batch_resolve_alliance_info
from ._shared import _get_coalition_members
from eve_shared.utils.error_handling import handle_endpoint_errors
from app.utils.cache import get_cached, set_cached

logger = logging.getLogger(__name__)
router = APIRouter()

HUNTING_CACHE_TTL = 300  # 5 minutes


@router.get("/{leader_id}/hunting")
@handle_endpoint_errors()
def get_powerbloc_hunting(
    leader_id: int,
    days: int = Query(30, ge=1, le=90)
) -> Dict[str, Any]:
    """Hunting intelligence aggregated across all coalition members.

    Results are cached for 5 minutes.
    """
    cache_key = f"pb-hunting:{leader_id}:{days}"
    cached = get_cached(cache_key, HUNTING_CACHE_TTL)
    if cached:
        logger.debug(f"Hunting cache hit for PowerBloc {leader_id}")
        return cached

    with db_cursor() as cur:
        member_ids, coalition_name, name_map, ticker_map = _get_coalition_members(leader_id, cur)

        # Hot Zones - split into kills and deaths queries for performance
        cur.execute("""
            SELECT k.solar_system_id as system_id, COUNT(*) as deaths,
                   s."solarSystemName" as system_name, r."regionName" as region_name
            FROM killmails k
            LEFT JOIN "mapSolarSystems" s ON k.solar_system_id = s."solarSystemID"
            LEFT JOIN "mapRegions" r ON s."regionID" = r."regionID"
            WHERE k.killmail_time >= NOW() - INTERVAL '%s days'
              AND k.victim_alliance_id = ANY(%s)
            GROUP BY k.solar_system_id, s."solarSystemName", r."regionName"
        """, (days, member_ids))
        death_by_system = {}
        system_info = {}
        for r in cur.fetchall():
            sid = r["system_id"]
            death_by_system[sid] = r["deaths"]
            system_info[sid] = (r.get("system_name") or f"System {sid}", r.get("region_name") or "Unknown")

        cur.execute("""
            SELECT k.solar_system_id as system_id,
                   COUNT(DISTINCT k.killmail_id) as kills
            FROM killmails k
            JOIN killmail_attackers ka ON k.killmail_id = ka.killmail_id
            WHERE k.killmail_time >= NOW() - INTERVAL '%s days'
              AND ka.alliance_id = ANY(%s)
            GROUP BY k.solar_system_id
        """, (days, member_ids))
        kill_by_system = {}
        for r in cur.fetchall():
            kill_by_system[r["system_id"]] = r["kills"]

        # Resolve names for kill-only systems
        kill_only_systems = [sid for sid in kill_by_system if sid not in system_info]
        if kill_only_systems:
            cur.execute("""
                SELECT s."solarSystemID" as system_id, s."solarSystemName" as system_name,
                       r."regionName" as region_name
                FROM "mapSolarSystems" s
                LEFT JOIN "mapRegions" r ON s."regionID" = r."regionID"
                WHERE s."solarSystemID" = ANY(%s)
            """, (kill_only_systems,))
            for r in cur.fetchall():
                system_info[r["system_id"]] = (r["system_name"], r.get("region_name") or "Unknown")

        all_systems = set(death_by_system.keys()) | set(kill_by_system.keys())
        hot_zone_list = []
        for sid in all_systems:
            kills = kill_by_system.get(sid, 0)
            deaths = death_by_system.get(sid, 0)
            sname, rname = system_info.get(sid, (f"System {sid}", "Unknown"))
            hot_zone_list.append({"system_id": sid, "system_name": sname, "region_name": rname,
                                  "kills": kills, "deaths": deaths, "total_activity": kills + deaths})
        hot_zone_list.sort(key=lambda x: x["total_activity"], reverse=True)
        hot_zones = hot_zone_list[:20]

        # Strike Window - split queries
        cur.execute("""
            SELECT EXTRACT(HOUR FROM killmail_time)::INT as hour,
                   COUNT(*) as our_deaths
            FROM killmails
            WHERE killmail_time >= NOW() - INTERVAL '%s days'
              AND victim_alliance_id = ANY(%s)
            GROUP BY EXTRACT(HOUR FROM killmail_time)
        """, (days, member_ids))
        deaths_by_hour = {r["hour"]: r["our_deaths"] for r in cur.fetchall()}

        cur.execute("""
            SELECT EXTRACT(HOUR FROM k.killmail_time)::INT as hour,
                   COUNT(DISTINCT k.killmail_id) as our_kills
            FROM killmails k
            JOIN killmail_attackers ka ON k.killmail_id = ka.killmail_id
            WHERE k.killmail_time >= NOW() - INTERVAL '%s days'
              AND ka.alliance_id = ANY(%s)
            GROUP BY EXTRACT(HOUR FROM k.killmail_time)
        """, (days, member_ids))
        kills_by_hour = {r["hour"]: r["our_kills"] for r in cur.fetchall()}
        all_hours = set(deaths_by_hour.keys()) | set(kills_by_hour.keys())
        activity_by_hour = []
        for h in sorted(all_hours):
            kills = kills_by_hour.get(h, 0)
            deaths = deaths_by_hour.get(h, 0)
            activity_by_hour.append({"hour": h, "activity": kills + deaths,
                                      "our_deaths": deaths, "our_kills": kills})

        if activity_by_hour:
            sorted_by_activity = sorted(activity_by_hour, key=lambda x: x["activity"], reverse=True)
            total_activity = sum(h["activity"] for h in activity_by_hour)
            peak_hours = sorted_by_activity[:4]
            weak_hours = sorted_by_activity[-4:]
            peak_start = min(h["hour"] for h in peak_hours)
            peak_end = max(h["hour"] for h in peak_hours) + 1
            weak_start = min(h["hour"] for h in weak_hours)
            weak_end = max(h["hour"] for h in weak_hours) + 1
            peak_pct = round(sum(h["activity"] for h in peak_hours) / max(total_activity, 1) * 100)
            weak_pct = round(sum(h["activity"] for h in weak_hours) / max(total_activity, 1) * 100)
        else:
            peak_start = peak_end = weak_start = weak_end = peak_pct = weak_pct = 0

        strike_window = {
            "activity_by_hour": activity_by_hour,
            "peak_hours": f"{peak_start}:00-{peak_end}:00 UTC ({peak_pct}%)",
            "weak_hours": f"{weak_start}:00-{weak_end}:00 UTC ({weak_pct}%)",
            "peak_start": peak_start, "peak_end": peak_end,
            "weak_start": weak_start, "weak_end": weak_end,
        }

        # Last 24h stats
        cur.execute("""
            SELECT COUNT(DISTINCT k.killmail_id) as kills,
                   COUNT(DISTINCT CASE WHEN ka.ship_type_id IN (
                       SELECT "typeID" FROM "invTypes" t
                       JOIN "invGroups" g ON t."groupID" = g."groupID"
                       WHERE g."categoryID" = 6 AND g."groupID" IN (547, 485, 659, 883, 1538)
                   ) THEN k.killmail_id END) as capital_kills
            FROM killmails k
            JOIN killmail_attackers ka ON k.killmail_id = ka.killmail_id
            WHERE k.killmail_time >= NOW() - INTERVAL '24 hours'
              AND ka.alliance_id = ANY(%s)
        """, (member_ids,))
        last_24h = cur.fetchone()
        strike_window["last_24h"] = {
            "kills": last_24h["kills"] if last_24h else 0,
            "capital_deployments": last_24h["capital_kills"] if last_24h else 0
        }

        # Priority Targets
        cur.execute("""
            WITH pilot_deaths AS (
                SELECT victim_character_id as character_id, COUNT(*) as deaths,
                       AVG(ship_value) as avg_ship_value, SUM(ship_value) as total_isk_lost,
                       MAX(killmail_time) as last_death
                FROM killmails
                WHERE victim_alliance_id = ANY(%s)
                  AND killmail_time >= NOW() - INTERVAL '%s days'
                  AND victim_character_id IS NOT NULL AND ship_value > 10000000
                GROUP BY victim_character_id HAVING COUNT(*) >= 2
            ),
            pilot_kills AS (
                SELECT ka.character_id, COUNT(DISTINCT k.killmail_id) as kills
                FROM killmails k JOIN killmail_attackers ka ON k.killmail_id = ka.killmail_id
                WHERE ka.alliance_id = ANY(%s)
                  AND k.killmail_time >= NOW() - INTERVAL '%s days'
                GROUP BY ka.character_id
            )
            SELECT pd.character_id, c.character_name, pd.deaths,
                   COALESCE(pk.kills, 0) as kills,
                   pd.avg_ship_value, pd.total_isk_lost, pd.last_death
            FROM pilot_deaths pd
            LEFT JOIN pilot_kills pk ON pd.character_id = pk.character_id
            LEFT JOIN character_name_cache c ON pd.character_id = c.character_id
            ORDER BY (pd.avg_ship_value / 1000000000.0 * pd.deaths) DESC
            LIMIT 10
        """, (member_ids, days, member_ids, days))
        priority_targets = []
        for r in cur.fetchall():
            kills = r["kills"] or 0
            deaths = r["deaths"]
            eff = round(kills / max(kills + deaths, 1) * 100, 1)
            whale_score = int((float(r["avg_ship_value"]) / 1e9 * deaths) / (eff / 100 + 0.1))
            priority_targets.append({
                "character_id": r["character_id"],
                "character_name": r["character_name"] or "Unknown",
                "whale_score": min(whale_score, 100),
                "deaths": deaths, "kills": kills, "efficiency": eff,
                "isk_per_death": round(float(r["avg_ship_value"])),
                "total_isk_lost": round(float(r["total_isk_lost"])),
                "last_active": r["last_death"].isoformat() if r["last_death"] else None,
            })

        # Counter Doctrine
        cur.execute("""
            SELECT t."typeName" as ship_name, t."typeID" as type_id,
                   g."groupName" as ship_class,
                   COUNT(*) as usage_count,
                   ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) as pct
            FROM killmail_attackers ka
            JOIN killmails k ON ka.killmail_id = k.killmail_id
            LEFT JOIN "invTypes" t ON ka.ship_type_id = t."typeID"
            LEFT JOIN "invGroups" g ON t."groupID" = g."groupID"
            WHERE ka.alliance_id = ANY(%s)
              AND k.killmail_time >= NOW() - INTERVAL '%s days'
              AND ka.ship_type_id IS NOT NULL
            GROUP BY t."typeName", t."typeID", g."groupName"
            ORDER BY usage_count DESC LIMIT 10
        """, (member_ids, days))
        their_meta = [{"ship": r["ship_name"], "type_id": r["type_id"],
                       "ship_class": r["ship_class"], "pct": float(r["pct"]),
                       "count": r["usage_count"]} for r in cur.fetchall()]

        damage_counts = {"kinetic": 0, "thermal": 0, "em": 0, "explosive": 0}
        for ship in their_meta:
            name = (ship["ship"] or "").lower()
            count = ship["count"]
            if any(x in name for x in ["cerberus", "caracal", "drake", "tengu", "osprey", "raven", "leviathan", "phoenix"]):
                damage_counts["kinetic"] += count
            elif any(x in name for x in ["zealot", "omen", "harbinger", "legion", "guardian", "apocalypse", "avatar", "revelation"]):
                damage_counts["em"] += count
            elif any(x in name for x in ["muninn", "hurricane", "sleipnir", "loki", "maelstrom", "ragnarok", "naglfar"]):
                damage_counts["explosive"] += count
            elif any(x in name for x in ["ishtar", "vexor", "myrmidon", "proteus", "dominix", "erebus", "moros"]):
                damage_counts["thermal"] += count
            else:
                damage_counts["thermal"] += count // 2
                damage_counts["kinetic"] += count // 2

        total_dmg = sum(damage_counts.values()) or 1
        damage_profile = {k: round(v / total_dmg * 100) for k, v in damage_counts.items()}
        primary_damage = max(damage_counts, key=damage_counts.get)

        tank_recs = {
            "kinetic": "Shield Tank with Kinetic Hardeners",
            "thermal": "Armor Tank with Thermal Hardeners",
            "em": "Shield Tank with EM Hardeners",
            "explosive": "Armor Tank with Explosive Hardeners",
        }

        counter_doctrine = {
            "their_meta": their_meta,
            "damage_profile": damage_profile,
            "primary_damage_type": primary_damage,
            "tank_recommendation": tank_recs.get(primary_damage, "Balanced Tank"),
        }

        # Gatecamp Alerts - recent kills in coalition-active systems
        # Step 1: Get systems with coalition activity in last 7 days
        cur.execute("""
            SELECT DISTINCT solar_system_id FROM killmails
            WHERE victim_alliance_id = ANY(%s)
              AND killmail_time >= NOW() - INTERVAL '7 days'
        """, (member_ids,))
        coalition_systems = [r["solar_system_id"] for r in cur.fetchall()]

        cur.execute("""
            SELECT DISTINCT k.solar_system_id
            FROM killmails k
            JOIN killmail_attackers ka ON k.killmail_id = ka.killmail_id
            WHERE ka.alliance_id = ANY(%s)
              AND k.killmail_time >= NOW() - INTERVAL '7 days'
        """, (member_ids,))
        coalition_systems = list(set(coalition_systems + [r["solar_system_id"] for r in cur.fetchall()]))

        # Step 2: Get recent activity in those systems
        if coalition_systems:
            cur.execute("""
                SELECT k.solar_system_id, s."solarSystemName" as system_name,
                       r."regionName" as region_name,
                       ROUND(s."security"::numeric, 1) as security_status,
                       COUNT(*) as kills,
                       COUNT(*) FILTER (WHERE k.ship_type_id = 670) as pod_kills,
                       MIN(k.killmail_time) as first_kill, MAX(k.killmail_time) as last_kill,
                       SUM(k.ship_value) as total_isk
                FROM killmails k
                LEFT JOIN "mapSolarSystems" s ON k.solar_system_id = s."solarSystemID"
                LEFT JOIN "mapRegions" r ON s."regionID" = r."regionID"
                WHERE k.killmail_time >= NOW() - INTERVAL '60 minutes'
                  AND k.solar_system_id = ANY(%s)
                GROUP BY k.solar_system_id, s."solarSystemName", r."regionName", s."security"
                HAVING COUNT(*) >= 3
                ORDER BY COUNT(*) DESC LIMIT 10
            """, (coalition_systems,))

        gatecamp_alerts = []
        for r in (cur.fetchall() if coalition_systems else []):
            kills = r["kills"]
            severity = "critical" if kills >= 10 else "high" if kills >= 5 else "medium"
            duration = int((r["last_kill"] - r["first_kill"]).total_seconds()) if r["last_kill"] and r["first_kill"] else 0
            gatecamp_alerts.append({
                "system_id": r["solar_system_id"], "system_name": r["system_name"] or "Unknown",
                "region_name": r["region_name"] or "Unknown",
                "security_status": float(r["security_status"]) if r["security_status"] else 0,
                "kills": kills, "pod_kills": r["pod_kills"],
                "total_isk": float(r["total_isk"] or 0),
                "duration_seconds": duration, "severity": severity,
            })

        # Enemy Damage Profiles
        cur.execute("""
            WITH top_enemies AS (
                SELECT ka.alliance_id as enemy_id, COUNT(DISTINCT k.killmail_id) as kills
                FROM killmails k
                JOIN killmail_attackers ka ON k.killmail_id = ka.killmail_id
                WHERE k.victim_alliance_id = ANY(%s)
                  AND k.killmail_time >= NOW() - INTERVAL '%s days'
                  AND ka.alliance_id IS NOT NULL AND ka.alliance_id != ALL(%s)
                GROUP BY ka.alliance_id ORDER BY kills DESC LIMIT 5
            )
            SELECT te.enemy_id, te.kills, t."typeName" as ship_name,
                   g."groupName" as ship_class, COUNT(*) as usage_count
            FROM top_enemies te
            JOIN killmail_attackers ka ON ka.alliance_id = te.enemy_id
            JOIN killmails k ON ka.killmail_id = k.killmail_id
            LEFT JOIN "invTypes" t ON ka.ship_type_id = t."typeID"
            LEFT JOIN "invGroups" g ON t."groupID" = g."groupID"
            WHERE k.victim_alliance_id = ANY(%s)
              AND k.killmail_time >= NOW() - INTERVAL '%s days'
              AND ka.ship_type_id IS NOT NULL
            GROUP BY te.enemy_id, te.kills, t."typeName", g."groupName"
            ORDER BY te.kills DESC, usage_count DESC
        """, (member_ids, days, member_ids, member_ids, days))
        enemy_rows = cur.fetchall()
        enemy_profiles_map: Dict[int, Dict] = {}
        for r in enemy_rows:
            eid = r["enemy_id"]
            if eid not in enemy_profiles_map:
                enemy_profiles_map[eid] = {"alliance_id": eid, "kills": r["kills"], "top_ships": []}
            if len(enemy_profiles_map[eid]["top_ships"]) < 3:
                enemy_profiles_map[eid]["top_ships"].append({
                    "ship": r["ship_name"], "ship_class": r["ship_class"], "count": r["usage_count"]
                })

        # Resolve enemy names from cache first, then ESI
        enemy_ids = list(enemy_profiles_map.keys())
        if enemy_ids:
            cur.execute("""
                SELECT alliance_id, alliance_name, ticker FROM alliance_name_cache
                WHERE alliance_id = ANY(%s)
            """, (enemy_ids,))
            for r in cur.fetchall():
                if r['alliance_id'] in enemy_profiles_map:
                    enemy_profiles_map[r['alliance_id']]["alliance_name"] = r['alliance_name']
                    enemy_profiles_map[r['alliance_id']]["ticker"] = r.get('ticker', '')
            # Fill remaining from ESI
            missing = [eid for eid in enemy_ids if "alliance_name" not in enemy_profiles_map[eid]]
            if missing:
                esi_info = batch_resolve_alliance_info(missing)
                for eid, info in esi_info.items():
                    if eid in enemy_profiles_map:
                        enemy_profiles_map[eid]["alliance_name"] = info.get("name", f"Alliance {eid}")
                        enemy_profiles_map[eid]["ticker"] = info.get("ticker", "")
        enemy_damage_profiles = list(enemy_profiles_map.values())

        # System Danger Radar
        cur.execute("""
            SELECT k.solar_system_id as system_id, s."solarSystemName" as system_name,
                   r."regionName" as region_name,
                   ROUND(s."security"::numeric, 1) as security,
                   COUNT(*) as total_deaths,
                   COUNT(*) FILTER (WHERE k.ship_type_id = 670) as pod_deaths,
                   SUM(k.ship_value) as isk_lost
            FROM killmails k
            LEFT JOIN "mapSolarSystems" s ON k.solar_system_id = s."solarSystemID"
            LEFT JOIN "mapRegions" r ON s."regionID" = r."regionID"
            WHERE k.victim_alliance_id = ANY(%s)
              AND k.killmail_time >= NOW() - INTERVAL '%s days'
            GROUP BY k.solar_system_id, s."solarSystemName", r."regionName", s."security"
            ORDER BY COUNT(*) DESC LIMIT 10
        """, (member_ids, days))
        system_dangers = []
        for r in cur.fetchall():
            deaths = r["total_deaths"]
            danger = "critical" if deaths >= 50 else "high" if deaths >= 20 else "medium" if deaths >= 5 else "low"
            system_dangers.append({
                "system_id": r["system_id"], "system_name": r["system_name"] or "Unknown",
                "region_name": r["region_name"] or "Unknown",
                "security": float(r["security"]) if r["security"] else 0,
                "total_deaths": deaths, "pod_deaths": r["pod_deaths"],
                "isk_lost": float(r["isk_lost"] or 0), "danger_level": danger,
            })

        result = {
            "coalition_name": coalition_name,
            "member_count": len(member_ids),
            "hot_zones": hot_zones,
            "strike_window": strike_window,
            "priority_targets": priority_targets,
            "counter_doctrine": counter_doctrine,
            "gatecamp_alerts": gatecamp_alerts,
            "enemy_damage_profiles": enemy_damage_profiles,
            "system_dangers": system_dangers,
        }

        # Cache the result
        set_cached(cache_key, result, HUNTING_CACHE_TTL)
        logger.debug(f"Hunting cached for PowerBloc {leader_id}")

        return result
