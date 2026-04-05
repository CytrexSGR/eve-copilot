"""Power Bloc wormhole intelligence endpoint."""

import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Query

from app.database import db_cursor
from app.services.intelligence.esi_utils import batch_resolve_alliance_info
from ._shared import _get_coalition_members
from eve_shared.utils.error_handling import handle_endpoint_errors

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/{leader_id}/wormhole")
@handle_endpoint_errors()
def get_powerbloc_wormhole(
    leader_id: int,
    days: int = Query(30, ge=1, le=90)
) -> Dict[str, Any]:
    """Wormhole intelligence aggregated across coalition."""
    with db_cursor() as cur:
        member_ids, coalition_name, name_map, ticker_map = _get_coalition_members(leader_id, cur)

        # Controlled WH systems
        controlled_systems = []
        try:
            cur.execute("""
                SELECT wr.system_id, wr.alliance_id, wr.corporation_id,
                       wr.kills, wr.losses, wr.last_seen,
                       wse.effect_name, wse.effect_description,
                       mlwc."wormholeClassID" as wh_class
                FROM wormhole_residents wr
                LEFT JOIN wormhole_system_effects wse ON wr.system_id = wse.system_id
                LEFT JOIN "mapLocationWormholeClasses" mlwc ON wr.system_id = mlwc."locationID"
                WHERE wr.alliance_id = ANY(%s)
                ORDER BY wr.kills DESC
            """, (member_ids,))
            for r in cur.fetchall():
                system_id = r["system_id"]
                # Get system name
                cur.execute('SELECT "solarSystemName" FROM "mapSolarSystems" WHERE "solarSystemID" = %s', (system_id,))
                sys_row = cur.fetchone()
                sys_name = sys_row["solarSystemName"] if sys_row else f"J{system_id}"

                # Get statics
                statics = []
                try:
                    cur.execute("""
                        SELECT wss.static_type, wte.in_class, wte.max_mass, wte.max_jump_mass, wte.lifetime
                        FROM wormhole_system_statics wss
                        LEFT JOIN wormhole_type_extended wte ON wss.static_type = wte.type_code
                        WHERE wss.system_id = %s
                    """, (system_id,))
                    statics = [
                        {"type": s["static_type"], "destination_class": s.get("in_class"),
                         "max_mass": s.get("max_mass"), "max_jump_mass": s.get("max_jump_mass"),
                         "lifetime": s.get("lifetime")}
                        for s in cur.fetchall()
                    ]
                except Exception:
                    cur.connection.rollback()

                # Economic potential
                wh_class = r.get("wh_class")
                econ_map = {1: 700, 2: 1200, 3: 2000, 4: 3300, 5: 7000, 6: 12000,
                            13: 2500, 14: 0, 15: 15000, 16: 15000, 17: 15000, 18: 15000}
                isk_per_month = econ_map.get(wh_class, 0)

                controlled_systems.append({
                    "system_id": system_id, "system_name": sys_name,
                    "wh_class": wh_class,
                    "alliance_id": r["alliance_id"],
                    "alliance_name": name_map.get(r["alliance_id"], f"Alliance {r['alliance_id']}"),
                    "kills": r["kills"], "losses": r["losses"],
                    "last_seen": r["last_seen"].isoformat() if r["last_seen"] else None,
                    "effect_name": r.get("effect_name"),
                    "statics": statics,
                    "isk_per_month_m": isk_per_month,
                })
        except Exception as ex:
            logger.warning(f"WH residents query failed: {ex}")

        # Visitors in coalition WH space
        visitors = []
        if controlled_systems:
            wh_system_ids = [s["system_id"] for s in controlled_systems]
            try:
                cur.execute("""
                    SELECT wr.alliance_id, wr.system_id, wr.kills, wr.losses, wr.last_seen
                    FROM wormhole_residents wr
                    WHERE wr.system_id = ANY(%s)
                      AND wr.alliance_id != ALL(%s)
                      AND wr.alliance_id IS NOT NULL
                    ORDER BY wr.kills DESC LIMIT 20
                """, (wh_system_ids, member_ids))
                visitor_rows = cur.fetchall()
                visitor_ids = list(set(r["alliance_id"] for r in visitor_rows))
                visitor_names = {}
                if visitor_ids:
                    cur.execute("SELECT alliance_id, alliance_name FROM alliance_name_cache WHERE alliance_id = ANY(%s)", (visitor_ids,))
                    for r in cur.fetchall():
                        visitor_names[r['alliance_id']] = r['alliance_name']
                visitors = [
                    {"alliance_id": r["alliance_id"],
                     "alliance_name": visitor_names.get(r["alliance_id"], f"Alliance {r['alliance_id']}"),
                     "system_id": r["system_id"], "kills": r["kills"], "losses": r["losses"],
                     "threat_level": "high" if r["kills"] >= 10 else "medium" if r["kills"] >= 3 else "low"}
                    for r in visitor_rows
                ]
            except Exception:
                cur.connection.rollback()

        # SOV Threats
        sov_threats = []
        try:
            cur.execute("""
                SELECT alliance_id, total_wh_systems, total_kills, total_isk_destroyed,
                       critical_systems, high_systems, moderate_systems, low_systems,
                       top_attackers, top_regions, us_prime_pct, eu_prime_pct, au_prime_pct,
                       top_wh_systems, attacker_doctrines
                FROM wh_sov_threats
                WHERE alliance_id = ANY(%s)
            """, (member_ids,))
            for r in cur.fetchall():
                sov_threats.append({
                    "alliance_id": r["alliance_id"],
                    "alliance_name": name_map.get(r["alliance_id"], f"Alliance {r['alliance_id']}"),
                    "total_wh_systems": r["total_wh_systems"],
                    "total_kills": r["total_kills"],
                    "total_isk_destroyed": float(r["total_isk_destroyed"] or 0),
                    "threat_breakdown": {
                        "critical": r["critical_systems"], "high": r["high_systems"],
                        "moderate": r["moderate_systems"], "low": r["low_systems"],
                    },
                    "top_attackers": r.get("top_attackers") or [],
                    "top_regions": r.get("top_regions") or [],
                    "timezone": {
                        "us": float(r["us_prime_pct"] or 0),
                        "eu": float(r["eu_prime_pct"] or 0),
                        "au": float(r["au_prime_pct"] or 0),
                    },
                    "top_wh_systems": r.get("top_wh_systems") or [],
                    "attacker_doctrines": r.get("attacker_doctrines") or [],
                })
        except Exception:
            cur.connection.rollback()

        # Summary
        total_systems = len(controlled_systems)
        total_isk_potential = sum(s["isk_per_month_m"] for s in controlled_systems)
        class_breakdown = {}
        for s in controlled_systems:
            cls = s.get("wh_class") or 0
            class_breakdown[f"C{cls}"] = class_breakdown.get(f"C{cls}", 0) + 1

        return {
            "coalition_name": coalition_name,
            "member_count": len(member_ids),
            "summary": {
                "total_systems": total_systems,
                "total_isk_potential_m": total_isk_potential,
                "class_breakdown": class_breakdown,
            },
            "controlled_systems": controlled_systems,
            "visitors": visitors,
            "sov_threats": sov_threats,
        }
