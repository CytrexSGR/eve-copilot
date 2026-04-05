"""Power Bloc capsuleer intelligence endpoint."""

import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Query

from app.database import db_cursor
from app.services.intelligence.esi_utils import batch_resolve_alliance_info
from ._shared import _get_coalition_members
from eve_shared.utils.error_handling import handle_endpoint_errors

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/{leader_id}/capsuleers")
@handle_endpoint_errors()
def get_powerbloc_capsuleers(
    leader_id: int,
    days: int = Query(7, ge=1, le=30)
) -> Dict[str, Any]:
    """Capsuleer intelligence aggregated across coalition."""
    with db_cursor() as cur:
        member_ids, coalition_name, name_map, ticker_map = _get_coalition_members(leader_id, cur)

        # Active pilots = attackers + victims (all PvP participants)
        cur.execute("""
            SELECT COUNT(DISTINCT character_id) as active_pilots
            FROM (
                SELECT ka.character_id
                FROM killmail_attackers ka
                JOIN killmails k ON ka.killmail_id = k.killmail_id
                WHERE ka.alliance_id = ANY(%(ids)s)
                  AND k.killmail_time >= NOW() - make_interval(days => %(days)s)
                  AND ka.character_id IS NOT NULL
                UNION
                SELECT k.victim_character_id
                FROM killmails k
                WHERE k.victim_alliance_id = ANY(%(ids)s)
                  AND k.killmail_time >= NOW() - make_interval(days => %(days)s)
                  AND k.victim_character_id IS NOT NULL
            ) all_pilots
        """, {"ids": member_ids, "days": days})
        active_pilots = cur.fetchone()["active_pilots"] or 0

        # Kill stats (deduplicated by killmail_id for correct ISK)
        cur.execute("""
            WITH unique_kills AS (
                SELECT DISTINCT ka.killmail_id, k.ship_value
                FROM killmail_attackers ka
                JOIN killmails k ON ka.killmail_id = k.killmail_id
                WHERE ka.alliance_id = ANY(%(ids)s)
                  AND k.killmail_time >= NOW() - make_interval(days => %(days)s)
            )
            SELECT COUNT(*) as total_kills,
                   COALESCE(SUM(ship_value), 0) as total_isk_destroyed
            FROM unique_kills
        """, {"ids": member_ids, "days": days})
        kill_stats = cur.fetchone()

        cur.execute("""
            SELECT COUNT(DISTINCT victim_character_id) as pilots_lost,
                   COUNT(*) as total_deaths,
                   COALESCE(SUM(ship_value), 0) as total_isk_lost,
                   COUNT(*) FILTER (WHERE ship_type_id = 670) as pod_deaths
            FROM killmails
            WHERE victim_alliance_id = ANY(%(ids)s)
              AND killmail_time >= NOW() - make_interval(days => %(days)s)
              AND victim_character_id IS NOT NULL
        """, {"ids": member_ids, "days": days})
        death_stats = cur.fetchone()

        total_kills = kill_stats["total_kills"] if kill_stats else 0
        total_isk_destroyed = float(kill_stats["total_isk_destroyed"]) if kill_stats else 0
        total_deaths = death_stats["total_deaths"] if death_stats else 0
        total_isk_lost = float(death_stats["total_isk_lost"]) if death_stats else 0
        pod_deaths = death_stats["pod_deaths"] if death_stats else 0
        pod_survival = round((1 - pod_deaths / max(total_deaths, 1)) * 100, 1)

        # ISK-based efficiency (consistent with Alliance capsuleers)
        total_isk = total_isk_destroyed + total_isk_lost
        efficiency = round(total_isk_destroyed / total_isk * 100, 1) if total_isk > 0 else 0

        summary = {
            "active_pilots": active_pilots,
            "total_kills": total_kills,
            "total_deaths": total_deaths,
            "efficiency": efficiency,
            "isk_destroyed": total_isk_destroyed,
            "isk_lost": total_isk_lost,
            "pod_deaths": pod_deaths,
            "pod_survival_rate": pod_survival,
            "kd_ratio": round(total_kills / max(total_deaths, 1), 2),
        }

        # Alliance Rankings (deduplicated ISK)
        cur.execute("""
            WITH unique_alliance_kills AS (
                SELECT DISTINCT ka.alliance_id, ka.killmail_id, k.ship_value
                FROM killmail_attackers ka
                JOIN killmails k ON ka.killmail_id = k.killmail_id
                WHERE ka.alliance_id = ANY(%(ids)s)
                  AND k.killmail_time >= NOW() - make_interval(days => %(days)s)
            ),
            alliance_kill_stats AS (
                SELECT alliance_id,
                       COUNT(*) as kills,
                       COALESCE(SUM(ship_value), 0) as isk_destroyed
                FROM unique_alliance_kills
                GROUP BY alliance_id
            ),
            alliance_pilot_counts AS (
                SELECT ka.alliance_id,
                       COUNT(DISTINCT ka.character_id) as pilots
                FROM killmail_attackers ka
                JOIN killmails k ON ka.killmail_id = k.killmail_id
                WHERE ka.alliance_id = ANY(%(ids)s)
                  AND k.killmail_time >= NOW() - make_interval(days => %(days)s)
                GROUP BY ka.alliance_id
            )
            SELECT aks.alliance_id,
                   COALESCE(ap.pilots, 0) as pilots,
                   aks.kills,
                   aks.isk_destroyed
            FROM alliance_kill_stats aks
            LEFT JOIN alliance_pilot_counts ap ON aks.alliance_id = ap.alliance_id
            ORDER BY aks.kills DESC
        """, {"ids": member_ids, "days": days})
        alliance_kill_rows = cur.fetchall()

        # Get deaths per alliance
        cur.execute("""
            SELECT victim_alliance_id as alliance_id,
                   COUNT(*) as deaths,
                   COALESCE(SUM(ship_value), 0) as isk_lost
            FROM killmails
            WHERE victim_alliance_id = ANY(%s)
              AND killmail_time >= NOW() - INTERVAL '%s days'
            GROUP BY victim_alliance_id
        """, (member_ids, days))
        alliance_death_map = {r["alliance_id"]: r for r in cur.fetchall()}

        alliance_rankings = []
        for r in alliance_kill_rows:
            aid = r["alliance_id"]
            deaths_data = alliance_death_map.get(aid, {"deaths": 0, "isk_lost": 0})
            kills = r["kills"]
            deaths = deaths_data["deaths"]
            isk_d = float(r["isk_destroyed"] or 0)
            isk_l = float(deaths_data["isk_lost"] or 0)
            eff = round(isk_d / max(isk_d + isk_l, 1) * 100, 1)
            alliance_rankings.append({
                "alliance_id": aid,
                "alliance_name": name_map.get(aid, f"Alliance {aid}"),
                "ticker": ticker_map.get(aid, ""),
                "pilots": r["pilots"], "kills": kills, "deaths": deaths,
                "efficiency": eff,
                "kd_ratio": round(kills / max(deaths, 1), 2),
                "isk_destroyed": isk_d,
                "isk_lost": isk_l,
            })

        # Top Pilots — deduplicated, with final_blows and ISK
        cur.execute("""
            WITH unique_pilot_kills AS (
                SELECT DISTINCT ka.character_id, ka.alliance_id, ka.corporation_id,
                       ka.killmail_id, k.ship_value, ka.is_final_blow
                FROM killmail_attackers ka
                JOIN killmails k ON ka.killmail_id = k.killmail_id
                WHERE ka.alliance_id = ANY(%s)
                  AND k.killmail_time >= NOW() - INTERVAL '%s days'
                  AND ka.character_id IS NOT NULL
            )
            SELECT character_id, alliance_id, corporation_id,
                   COUNT(*) as kills,
                   SUM(CASE WHEN is_final_blow THEN 1 ELSE 0 END) as final_blows,
                   SUM(ship_value) as isk_destroyed
            FROM unique_pilot_kills
            GROUP BY character_id, alliance_id, corporation_id
            ORDER BY kills DESC LIMIT 50
        """, (member_ids, days))
        pilot_rows = cur.fetchall()

        # Get pilot deaths
        pilot_ids = [r["character_id"] for r in pilot_rows]
        pilot_deaths_map = {}
        if pilot_ids:
            cur.execute("""
                SELECT victim_character_id as character_id,
                       COUNT(*) as deaths,
                       COALESCE(SUM(ship_value), 0) as isk_lost,
                       COUNT(*) FILTER (WHERE ship_type_id = 670) as pod_deaths
                FROM killmails
                WHERE victim_character_id = ANY(%s)
                  AND killmail_time >= NOW() - INTERVAL '%s days'
                GROUP BY victim_character_id
            """, (pilot_ids, days))
            for r in cur.fetchall():
                pilot_deaths_map[r["character_id"]] = r

        # Resolve pilot names
        pilot_name_map = {}
        if pilot_ids:
            cur.execute("SELECT character_id, character_name FROM character_name_cache WHERE character_id = ANY(%s)", (pilot_ids,))
            for r in cur.fetchall():
                pilot_name_map[r["character_id"]] = r["character_name"]

        # Resolve corp names/tickers for pilots
        pilot_corp_ids = list(set(r["corporation_id"] for r in pilot_rows if r["corporation_id"]))
        pilot_corp_map = {}
        if pilot_corp_ids:
            cur.execute("SELECT corporation_id, corporation_name, ticker FROM corporations WHERE corporation_id = ANY(%s)", (pilot_corp_ids,))
            for r in cur.fetchall():
                pilot_corp_map[r["corporation_id"]] = {"name": r["corporation_name"], "ticker": r["ticker"]}

        top_pilots = []
        for r in pilot_rows:
            cid = r["character_id"]
            deaths_data = pilot_deaths_map.get(cid, {"deaths": 0, "isk_lost": 0, "pod_deaths": 0})
            kills = r["kills"]
            deaths = deaths_data["deaths"]
            isk_d = float(r["isk_destroyed"] or 0)
            isk_l = float(deaths_data.get("isk_lost", 0) or 0)
            eff = round(isk_d / max(isk_d + isk_l, 1) * 100, 1)
            corp_data = pilot_corp_map.get(r["corporation_id"], {"name": "Unknown", "ticker": "???"})
            top_pilots.append({
                "character_id": cid,
                "character_name": pilot_name_map.get(cid, "Unknown"),
                "alliance_id": r["alliance_id"],
                "alliance_name": name_map.get(r["alliance_id"], f"Alliance {r['alliance_id']}"),
                "corp_id": r["corporation_id"],
                "corp_name": corp_data["name"],
                "ticker": corp_data["ticker"] or "???",
                "kills": kills, "deaths": deaths, "efficiency": eff,
                "final_blows": r["final_blows"] or 0,
                "isk_destroyed": isk_d,
                "isk_lost": isk_l,
                "pod_deaths": deaths_data["pod_deaths"],
            })

        # Corp Rankings — deduplicated with deaths, ISK, ticker
        cur.execute("""
            WITH unique_corp_kills AS (
                SELECT DISTINCT ka.corporation_id, ka.killmail_id, k.ship_value
                FROM killmail_attackers ka
                JOIN killmails k ON ka.killmail_id = k.killmail_id
                WHERE ka.alliance_id = ANY(%(ids)s)
                  AND k.killmail_time >= NOW() - make_interval(days => %(days)s)
                  AND ka.corporation_id IS NOT NULL
            ),
            corp_kill_stats AS (
                SELECT corporation_id,
                       COUNT(*) as kills,
                       SUM(ship_value) as isk_destroyed
                FROM unique_corp_kills GROUP BY corporation_id
            ),
            corp_pilot_counts AS (
                SELECT ka.corporation_id,
                       COUNT(DISTINCT ka.character_id) as pilots
                FROM killmail_attackers ka
                JOIN killmails k ON ka.killmail_id = k.killmail_id
                WHERE ka.alliance_id = ANY(%(ids)s)
                  AND k.killmail_time >= NOW() - make_interval(days => %(days)s)
                  AND ka.corporation_id IS NOT NULL
                GROUP BY ka.corporation_id
            ),
            corp_death_stats AS (
                SELECT victim_corporation_id as corporation_id,
                       COUNT(*) as deaths,
                       SUM(ship_value) as isk_lost
                FROM killmails
                WHERE victim_alliance_id = ANY(%(ids)s)
                  AND killmail_time >= NOW() - make_interval(days => %(days)s)
                GROUP BY victim_corporation_id
            )
            SELECT ck.corporation_id,
                   COALESCE(cp.pilots, 0) as pilots,
                   ck.kills,
                   COALESCE(cd.deaths, 0) as deaths,
                   ck.isk_destroyed,
                   COALESCE(cd.isk_lost, 0) as isk_lost
            FROM corp_kill_stats ck
            LEFT JOIN corp_pilot_counts cp ON ck.corporation_id = cp.corporation_id
            LEFT JOIN corp_death_stats cd ON ck.corporation_id = cd.corporation_id
            ORDER BY ck.kills DESC LIMIT 20
        """, {"ids": member_ids, "days": days})
        corp_kill_rows = cur.fetchall()
        corp_ids = [r["corporation_id"] for r in corp_kill_rows]
        corp_info_map = {}
        if corp_ids:
            cur.execute("SELECT corporation_id, corporation_name, ticker FROM corporations WHERE corporation_id = ANY(%s)", (corp_ids,))
            for r in cur.fetchall():
                corp_info_map[r["corporation_id"]] = {"name": r["corporation_name"], "ticker": r["ticker"]}

        total_alliance_kills = total_kills if total_kills > 0 else 1
        corp_rankings = []
        for r in corp_kill_rows:
            cid = r["corporation_id"]
            ci = corp_info_map.get(cid, {"name": f"Corp {cid}", "ticker": "???"})
            kills = r["kills"]
            deaths = r["deaths"]
            isk_d = float(r["isk_destroyed"] or 0)
            isk_l = float(r["isk_lost"] or 0)
            eff = round(isk_d / max(isk_d + isk_l, 1) * 100, 1)
            corp_rankings.append({
                "corp_id": cid,
                "corp_name": ci["name"],
                "ticker": ci["ticker"] or "???",
                "active_pilots": r["pilots"],
                "kills": kills,
                "deaths": deaths,
                "efficiency": eff,
                "isk_destroyed": isk_d,
                "activity_share": round(kills / total_alliance_kills * 100, 1),
            })

        return {
            "coalition_name": coalition_name,
            "member_count": len(member_ids),
            "summary": summary,
            "alliance_rankings": alliance_rankings,
            "corp_rankings": corp_rankings,
            "top_pilots": top_pilots,
        }
