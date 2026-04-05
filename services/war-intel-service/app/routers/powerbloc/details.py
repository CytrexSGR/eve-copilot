"""Power Bloc details intelligence endpoint."""

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

DETAILS_CACHE_TTL = 300  # 5 minutes


@router.get("/{leader_id}/details")
@handle_endpoint_errors()
def get_powerbloc_details(
    leader_id: int,
    days: int = Query(7, ge=1, le=30)
) -> Dict[str, Any]:
    """Details intelligence aggregated across all coalition members.

    Results are cached for 5 minutes.
    """
    cache_key = f"pb-details:{leader_id}:{days}"
    cached = get_cached(cache_key, DETAILS_CACHE_TTL)
    if cached:
        logger.debug(f"Details cache hit for PowerBloc {leader_id}")
        return cached

    with db_cursor() as cur:
        member_ids, coalition_name, name_map, ticker_map = _get_coalition_members(leader_id, cur)

        # Danger Zones - top systems by deaths
        cur.execute("""
            SELECT k.solar_system_id as system_id,
                   s."solarSystemName" as system_name,
                   r."regionName" as region_name,
                   COUNT(*) as deaths,
                   COALESCE(SUM(k.ship_value), 0) as isk_lost
            FROM killmails k
            LEFT JOIN "mapSolarSystems" s ON k.solar_system_id = s."solarSystemID"
            LEFT JOIN "mapRegions" r ON s."regionID" = r."regionID"
            WHERE k.victim_alliance_id = ANY(%s)
              AND k.killmail_time >= NOW() - INTERVAL '%s days'
            GROUP BY k.solar_system_id, s."solarSystemName", r."regionName"
            ORDER BY COUNT(*) DESC LIMIT 10
        """, (member_ids, days))
        danger_zones = [
            {"system_id": r["system_id"], "system_name": r.get("system_name") or "Unknown",
             "region_name": r.get("region_name") or "Unknown",
             "deaths": r["deaths"], "isk_lost": float(r["isk_lost"] or 0)}
            for r in cur.fetchall()
        ]

        # Top Enemies - exclude coalition members, final blow only for consistent attribution
        cur.execute("""
            SELECT ka.alliance_id as enemy_id,
                   COUNT(DISTINCT k.killmail_id) as kills,
                   COALESCE(SUM(k.ship_value), 0) as isk_destroyed
            FROM killmails k
            JOIN killmail_attackers ka ON k.killmail_id = ka.killmail_id AND ka.is_final_blow = TRUE
            WHERE k.victim_alliance_id = ANY(%s)
              AND k.killmail_time >= NOW() - INTERVAL '%s days'
              AND ka.alliance_id IS NOT NULL
              AND ka.alliance_id != ALL(%s)
            GROUP BY ka.alliance_id
            ORDER BY kills DESC LIMIT 10
        """, (member_ids, days, member_ids))
        enemy_rows = cur.fetchall()
        enemy_ids = [r["enemy_id"] for r in enemy_rows]
        enemy_name_map = {}
        enemy_ticker_map = {}
        if enemy_ids:
            cur.execute("SELECT alliance_id, alliance_name, ticker FROM alliance_name_cache WHERE alliance_id = ANY(%s)", (enemy_ids,))
            for r in cur.fetchall():
                enemy_name_map[r['alliance_id']] = r['alliance_name']
                enemy_ticker_map[r['alliance_id']] = r.get('ticker', '')
            missing = [eid for eid in enemy_ids if eid not in enemy_name_map]
            if missing:
                esi_info = batch_resolve_alliance_info(missing)
                for eid, info in esi_info.items():
                    enemy_name_map[eid] = info.get("name", f"Alliance {eid}")
                    enemy_ticker_map[eid] = info.get("ticker", "")
        top_enemies = [
            {"alliance_id": r["enemy_id"],
             "alliance_name": enemy_name_map.get(r["enemy_id"], f"Alliance {r['enemy_id']}"),
             "ticker": enemy_ticker_map.get(r["enemy_id"], ""),
             "kills": r["kills"], "isk_destroyed": float(r["isk_destroyed"] or 0)}
            for r in enemy_rows
        ]

        # Coalition Allies - the members themselves
        coalition_allies = [
            {"alliance_id": aid, "alliance_name": name_map.get(aid, f"Alliance {aid}"),
             "ticker": ticker_map.get(aid, "")}
            for aid in member_ids
        ]

        # Ships Killed
        cur.execute("""
            SELECT t."typeName" as ship_name, t."typeID" as type_id,
                   g."groupName" as ship_class,
                   COUNT(DISTINCT k.killmail_id) as count,
                   COALESCE(SUM(k.ship_value), 0) as isk
            FROM killmails k
            JOIN killmail_attackers ka ON k.killmail_id = ka.killmail_id
            LEFT JOIN "invTypes" t ON k.ship_type_id = t."typeID"
            LEFT JOIN "invGroups" g ON t."groupID" = g."groupID"
            WHERE ka.alliance_id = ANY(%s)
              AND k.killmail_time >= NOW() - INTERVAL '%s days'
              AND k.victim_alliance_id != ALL(%s)
            GROUP BY t."typeName", t."typeID", g."groupName"
            ORDER BY count DESC LIMIT 10
        """, (member_ids, days, member_ids))
        ships_killed = [
            {"type_id": r["type_id"], "ship_name": r.get("ship_name") or "Unknown",
             "ship_class": r.get("ship_class") or "Unknown",
             "count": r["count"], "isk": float(r["isk"] or 0)}
            for r in cur.fetchall()
        ]

        # Ships Lost
        cur.execute("""
            SELECT t."typeName" as ship_name, t."typeID" as type_id,
                   g."groupName" as ship_class,
                   COUNT(*) as count,
                   COALESCE(SUM(k.ship_value), 0) as isk
            FROM killmails k
            LEFT JOIN "invTypes" t ON k.ship_type_id = t."typeID"
            LEFT JOIN "invGroups" g ON t."groupID" = g."groupID"
            WHERE k.victim_alliance_id = ANY(%s)
              AND k.killmail_time >= NOW() - INTERVAL '%s days'
            GROUP BY t."typeName", t."typeID", g."groupName"
            ORDER BY count DESC LIMIT 10
        """, (member_ids, days))
        ships_lost = [
            {"type_id": r["type_id"], "ship_name": r.get("ship_name") or "Unknown",
             "ship_class": r.get("ship_class") or "Unknown",
             "count": r["count"], "isk": float(r["isk"] or 0)}
            for r in cur.fetchall()
        ]

        # Hunting Grounds - top regions by kills
        cur.execute("""
            SELECT r."regionName" as region_name,
                   COUNT(DISTINCT k.killmail_id) as kills,
                   COALESCE(SUM(k.ship_value), 0) as isk
            FROM killmails k
            JOIN killmail_attackers ka ON k.killmail_id = ka.killmail_id
            LEFT JOIN "mapSolarSystems" s ON k.solar_system_id = s."solarSystemID"
            LEFT JOIN "mapRegions" r ON s."regionID" = r."regionID"
            WHERE ka.alliance_id = ANY(%s)
              AND k.killmail_time >= NOW() - INTERVAL '%s days'
            GROUP BY r."regionName"
            ORDER BY kills DESC LIMIT 10
        """, (member_ids, days))
        hunting_grounds = [
            {"region_name": r.get("region_name") or "Unknown",
             "kills": r["kills"], "isk": float(r["isk"] or 0)}
            for r in cur.fetchall()
        ]

        # Hourly Activity Heatmap (from intelligence_hourly_stats for consistency)
        cur.execute("""
            SELECT EXTRACT(HOUR FROM hour_bucket)::INT as hour,
                   COALESCE(SUM(kills), 0) as kills,
                   COALESCE(SUM(deaths), 0) as deaths
            FROM intelligence_hourly_stats
            WHERE alliance_id = ANY(%s)
              AND hour_bucket >= NOW() - INTERVAL '%s days'
            GROUP BY EXTRACT(HOUR FROM hour_bucket)
            ORDER BY hour
        """, (member_ids, days))
        hourly_data = {r["hour"]: r for r in cur.fetchall()}
        hours = []
        for h in range(24):
            data = hourly_data.get(h, {"kills": 0, "deaths": 0})
            hours.append({"hour": h, "kills": data["kills"] or 0, "deaths": data["deaths"] or 0})

        max_deaths = max((h["deaths"] for h in hours), default=0)
        threshold = max_deaths * 0.5
        peak_hours_list = [h["hour"] for h in hours if h["deaths"] >= threshold and h["deaths"] > 0]
        safe_hours_list = [h["hour"] for h in hours if h["deaths"] < threshold * 0.3]

        hourly_activity = {
            "hours": hours,
            "peak_start": min(peak_hours_list) if peak_hours_list else 18,
            "safe_start": min(safe_hours_list) if safe_hours_list else 6,
        }

        # Economics (from intelligence_hourly_stats for consistency with reports.py)
        cur.execute("""
            SELECT
                COALESCE(SUM(kills), 0) as total_kills,
                COALESCE(SUM(deaths), 0) as total_losses,
                COALESCE(SUM(isk_destroyed), 0) as isk_destroyed,
                COALESCE(SUM(isk_lost), 0) as isk_lost
            FROM intelligence_hourly_stats
            WHERE alliance_id = ANY(%s)
              AND hour_bucket >= NOW() - INTERVAL '%s days'
        """, (member_ids, days))
        econ_row = cur.fetchone()

        isk_destroyed = float(econ_row["isk_destroyed"]) if econ_row else 0
        isk_lost = float(econ_row["isk_lost"]) if econ_row else 0
        total_kills = econ_row["total_kills"] if econ_row else 0
        total_losses = econ_row["total_losses"] if econ_row else 0

        economics = {
            "isk_destroyed": isk_destroyed,
            "isk_lost": isk_lost,
            "efficiency": round(isk_destroyed / max(isk_destroyed + isk_lost, 1) * 100, 1),
            "cost_per_kill": round(isk_destroyed / max(total_kills, 1)),
            "cost_per_death": round(isk_lost / max(total_losses, 1)),
        }

        # Participation Trends - daily
        cur.execute("""
            WITH daily_kills AS (
                SELECT DATE(k.killmail_time) as day,
                       COUNT(DISTINCT k.killmail_id) as kills,
                       COUNT(DISTINCT ka.character_id) as active_pilots
                FROM killmails k
                JOIN killmail_attackers ka ON k.killmail_id = ka.killmail_id
                WHERE ka.alliance_id = ANY(%s)
                  AND k.killmail_time >= NOW() - INTERVAL '%s days'
                GROUP BY DATE(k.killmail_time)
            ),
            daily_deaths AS (
                SELECT DATE(killmail_time) as day, COUNT(*) as deaths
                FROM killmails
                WHERE victim_alliance_id = ANY(%s)
                  AND killmail_time >= NOW() - INTERVAL '%s days'
                GROUP BY DATE(killmail_time)
            )
            SELECT COALESCE(dk.day, dd.day) as day,
                   COALESCE(dk.kills, 0) as kills,
                   COALESCE(dd.deaths, 0) as deaths,
                   COALESCE(dk.active_pilots, 0) as active_pilots
            FROM daily_kills dk
            FULL OUTER JOIN daily_deaths dd ON dk.day = dd.day
            ORDER BY day
        """, (member_ids, days, member_ids, days))
        daily = [
            {"day": r["day"].isoformat() if r["day"] else None,
             "kills": r["kills"], "deaths": r["deaths"],
             "active_pilots": r["active_pilots"]}
            for r in cur.fetchall()
        ]

        # Trend summary
        if len(daily) >= 2:
            mid = len(daily) // 2
            first_half_kills = sum(d["kills"] for d in daily[:mid])
            second_half_kills = sum(d["kills"] for d in daily[mid:])
            kill_trend = "up" if second_half_kills > first_half_kills * 1.1 else "down" if second_half_kills < first_half_kills * 0.9 else "stable"
        else:
            kill_trend = "stable"

        participation_trends = {
            "daily": daily,
            "trend": {"kills": kill_trend}
        }

        # Burnout Index
        burnout_daily = []
        for d in daily:
            kpp = round(d["kills"] / max(d["active_pilots"], 1), 2)
            burnout_daily.append({"day": d["day"], "kills_per_pilot": kpp, "active_pilots": d["active_pilots"]})

        avg_kpp = round(sum(b["kills_per_pilot"] for b in burnout_daily) / max(len(burnout_daily), 1), 2)
        burnout_index = {
            "daily": burnout_daily,
            "summary": {"avg_kills_per_pilot": avg_kpp,
                         "status": "healthy" if avg_kpp >= 2 else "moderate" if avg_kpp >= 1 else "low"}
        }

        # Attrition
        cur.execute("""
            WITH first_half AS (
                SELECT DISTINCT ka.character_id
                FROM killmail_attackers ka
                JOIN killmails k ON ka.killmail_id = k.killmail_id
                WHERE ka.alliance_id = ANY(%s)
                  AND k.killmail_time >= NOW() - INTERVAL '%s days'
                  AND k.killmail_time < NOW() - INTERVAL '%s days'
            ),
            second_half AS (
                SELECT DISTINCT ka.character_id
                FROM killmail_attackers ka
                JOIN killmails k ON ka.killmail_id = k.killmail_id
                WHERE ka.alliance_id = ANY(%s)
                  AND k.killmail_time >= NOW() - INTERVAL '%s days'
            )
            SELECT
                (SELECT COUNT(*) FROM first_half) as first_half_pilots,
                (SELECT COUNT(*) FROM second_half) as second_half_pilots,
                (SELECT COUNT(*) FROM first_half fh WHERE fh.character_id IN (SELECT character_id FROM second_half)) as retained
        """, (member_ids, days, days // 2, member_ids, days // 2))
        attr_row = cur.fetchone()
        first_half_p = attr_row["first_half_pilots"] if attr_row else 0
        second_half_p = attr_row["second_half_pilots"] if attr_row else 0
        retained = attr_row["retained"] if attr_row else 0
        retention_rate = round(retained / max(first_half_p, 1) * 100, 1)

        attrition = {
            "summary": {
                "first_half_pilots": first_half_p,
                "second_half_pilots": second_half_p,
                "retained": retained,
                "retention_rate": retention_rate,
                "status": "healthy" if retention_rate >= 70 else "concerning" if retention_rate >= 50 else "critical"
            }
        }

        # Alliance Activity Heatmap (from intelligence_hourly_stats for consistency)
        cur.execute("""
            SELECT alliance_id,
                   EXTRACT(HOUR FROM hour_bucket)::INT as hour,
                   COALESCE(SUM(kills), 0) as kills
            FROM intelligence_hourly_stats
            WHERE alliance_id = ANY(%s)
              AND hour_bucket >= NOW() - INTERVAL '%s days'
            GROUP BY alliance_id, EXTRACT(HOUR FROM hour_bucket)
            ORDER BY alliance_id, hour
        """, (member_ids, days))
        heatmap_data: Dict[int, List[int]] = {}
        for r in cur.fetchall():
            aid = r["alliance_id"]
            if aid not in heatmap_data:
                heatmap_data[aid] = [0] * 24
            heatmap_data[aid][r["hour"]] = r["kills"]

        alliance_heatmap = [
            {"alliance_id": aid, "name": name_map.get(aid, f"Alliance {aid}"),
             "ticker": ticker_map.get(aid, ""), "hours": heatmap_data[aid]}
            for aid in member_ids if aid in heatmap_data
        ]

        # Recommendations
        recommendations = []
        if danger_zones:
            dz = danger_zones[0]
            recommendations.append({
                "priority": 1, "category": "avoid",
                "text": f"Avoid {dz['system_name']} ({dz['region_name']}) - {dz['deaths']} deaths in {days}d"
            })
        peak_s = hourly_activity["peak_start"]
        safe_s = hourly_activity["safe_start"]
        recommendations.append({
            "priority": 2, "category": "timing",
            "text": f"Peak danger: {peak_s}:00 UTC. Safer operations: {safe_s}:00 UTC"
        })
        if top_enemies:
            recommendations.append({
                "priority": 3, "category": "threat",
                "text": f"Primary threat: {top_enemies[0]['alliance_name']} with {top_enemies[0]['kills']} kills"
            })

        result = {
            "coalition_name": coalition_name,
            "member_count": len(member_ids),
            "danger_zones": danger_zones,
            "top_enemies": top_enemies,
            "coalition_allies": coalition_allies,
            "ships_killed": ships_killed,
            "ships_lost": ships_lost,
            "hunting_grounds": hunting_grounds,
            "hourly_activity": hourly_activity,
            "economics": economics,
            "recommendations": recommendations,
            "participation_trends": participation_trends,
            "burnout_index": burnout_index,
            "attrition": attrition,
            "alliance_heatmap": alliance_heatmap,
        }

        # Cache the result
        set_cached(cache_key, result, DETAILS_CACHE_TTL)
        logger.debug(f"Details cached for PowerBloc {leader_id}")

        return result
