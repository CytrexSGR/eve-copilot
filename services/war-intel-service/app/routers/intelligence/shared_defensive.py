"""Shared defensive intelligence queries for Alliance, Corporation, and PowerBloc.

All 16 sections are identical across entity types except for WHERE clause filters.
Uses tuple cursor (cursor_factory=None) and named parameters.
"""

import logging
from collections import defaultdict
from typing import Optional

from .entity_context import EntityContext, EntityType
from .corp_sql_helpers import classify_ship_group
from ._shared_filters import _victim_filter, _attacker_filter, _params, _params_with_days

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Section helpers — each computes one part of the defensive intel result.
# All take tuple-cursor `cur`, EntityContext `ctx`, and `days` period.
# ---------------------------------------------------------------------------


def _build_summary(cur, ctx: EntityContext, days: int, vf: str, af: str, p: dict) -> dict:
    """Section 1: Enhanced summary (kills, deaths, ISK, efficiency, capitals)."""
    sql = f"""
        WITH unique_kills AS (
            SELECT DISTINCT km.killmail_id
            FROM killmails km
            JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
            WHERE {af}
                AND km.killmail_time >= NOW() - INTERVAL '{days} days'
        ),
        entity_kills AS (
            SELECT COUNT(*) AS total_kills FROM unique_kills
        ),
        entity_deaths AS (
            SELECT
                COUNT(*) AS total_deaths,
                SUM(km.ship_value) AS isk_lost,
                AVG(km.ship_value) AS avg_loss_value,
                MAX(km.ship_value) AS max_loss_value
            FROM killmails km
            WHERE {vf}
                AND km.killmail_time >= NOW() - INTERVAL '{days} days'
        ),
        solo_deaths AS (
            SELECT COUNT(*) AS solo_death_count
            FROM killmails km
            WHERE {vf}
                AND km.killmail_time >= NOW() - INTERVAL '{days} days'
                AND (SELECT COUNT(*) FROM killmail_attackers ka2 WHERE ka2.killmail_id = km.killmail_id) <= 3
        ),
        capital_deaths AS (
            SELECT COUNT(*) AS capital_loss_count
            FROM killmails km
            JOIN "invTypes" it ON km.ship_type_id = it."typeID"
            JOIN "invGroups" ig ON it."groupID" = ig."groupID"
            WHERE {vf}
                AND ig."groupName" IN ('Carrier', 'Dreadnought', 'Force Auxiliary', 'Supercarrier', 'Titan')
                AND km.killmail_time >= NOW() - INTERVAL '{days} days'
        )
        SELECT
            cd.total_deaths, cd.isk_lost, cd.avg_loss_value, cd.max_loss_value,
            ck.total_kills,
            ROUND(100.0 * ck.total_kills / NULLIF(ck.total_kills + cd.total_deaths, 0), 1) AS efficiency,
            ROUND(ck.total_kills::numeric / NULLIF(cd.total_deaths, 0), 2) AS kd_ratio,
            ROUND(100.0 * sd.solo_death_count / NULLIF(cd.total_deaths, 0), 1) AS solo_death_pct,
            COALESCE(capd.capital_loss_count, 0) AS capital_losses
        FROM entity_deaths cd, entity_kills ck, solo_deaths sd, capital_deaths capd
    """
    cur.execute(sql, p)
    sr = cur.fetchone()
    if sr:
        return {
            "total_deaths": sr[0] or 0, "isk_lost": sr[1] or 0.0,
            "avg_loss_value": sr[2] or 0.0, "max_loss_value": sr[3] or 0.0,
            "total_kills": sr[4] or 0, "efficiency": float(sr[5] or 0),
            "kd_ratio": float(sr[6] or 0), "solo_death_pct": float(sr[7] or 0),
            "capital_losses": sr[8] or 0,
        }
    return {
        "total_deaths": 0, "isk_lost": 0.0, "avg_loss_value": 0.0, "max_loss_value": 0.0,
        "total_kills": 0, "efficiency": 0.0, "kd_ratio": 0.0, "solo_death_pct": 0.0, "capital_losses": 0
    }


def _build_threat_profile(cur, ctx: EntityContext, days: int, vf: str, p: dict) -> dict:
    """Section 2: Threat profile (engagement size distribution)."""
    sql = f"""
        WITH attacker_counts AS (
            SELECT km.killmail_id, COUNT(ka.character_id) AS attacker_count
            FROM killmails km
            LEFT JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
            WHERE {vf} AND km.killmail_time >= NOW() - INTERVAL '{days} days'
            GROUP BY km.killmail_id
        )
        SELECT
            CASE
                WHEN attacker_count <= 3 THEN 'solo_ganked'
                WHEN attacker_count <= 10 THEN 'small'
                WHEN attacker_count <= 30 THEN 'medium'
                WHEN attacker_count <= 100 THEN 'large'
                ELSE 'blob'
            END AS engagement_type,
            COUNT(*) AS deaths,
            ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS percentage
        FROM attacker_counts GROUP BY engagement_type
    """
    cur.execute(sql, p)
    tp_raw = {}
    for et, deaths, pct in cur.fetchall():
        tp_raw[et] = {"deaths": deaths, "percentage": float(pct or 0)}
    return {k: tp_raw.get(k, {"deaths": 0, "percentage": 0.0})
            for k in ("solo_ganked", "small", "medium", "large", "blob")}


def _build_death_prone_pilots(cur, ctx: EntityContext, days: int, vf: str, af: str, p: dict) -> list:
    """Section 3: Death-prone pilots (high death-count characters)."""
    sql = f"""
        WITH pilot_activity AS (
            SELECT
                COALESCE(ka.character_id, km.victim_character_id) AS character_id,
                cn.character_name,
                COUNT(CASE WHEN {af} THEN 1 END) AS kills,
                COUNT(CASE WHEN {vf} THEN 1 END) AS deaths,
                AVG(CASE WHEN {vf} THEN km.ship_value END) AS avg_loss_value
            FROM killmails km
            LEFT JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id AND {af}
            LEFT JOIN character_name_cache cn ON COALESCE(ka.character_id, km.victim_character_id) = cn.character_id
            WHERE ({af} OR {vf})
                AND km.killmail_time >= NOW() - INTERVAL '{days} days'
            GROUP BY COALESCE(ka.character_id, km.victim_character_id), cn.character_name
        ),
        pilot_last_ship AS (
            SELECT DISTINCT ON (km.victim_character_id)
                km.victim_character_id, it."typeName" AS last_ship_lost
            FROM killmails km
            JOIN "invTypes" it ON km.ship_type_id = it."typeID"
            WHERE {vf} AND km.killmail_time >= NOW() - INTERVAL '{days} days'
            ORDER BY km.victim_character_id, km.killmail_time DESC
        )
        SELECT pa.character_id, pa.character_name, pa.deaths, pa.kills,
            ROUND(100.0 * pa.deaths / NULLIF(pa.kills + pa.deaths, 0), 1) AS death_pct,
            pa.avg_loss_value, pls.last_ship_lost
        FROM pilot_activity pa
        LEFT JOIN pilot_last_ship pls ON pa.character_id = pls.victim_character_id
        WHERE pa.deaths >= 5 ORDER BY pa.deaths DESC LIMIT 20
    """
    cur.execute(sql, p)
    return [
        {"character_id": cid, "character_name": cn, "deaths": d, "kills": k,
         "death_pct": float(dp or 0), "avg_loss_value": float(av or 0), "last_ship_lost": ls}
        for cid, cn, d, k, dp, av, ls in cur.fetchall()
    ]


def _build_ship_losses(cur, ctx: EntityContext, days: int, vf: str, p: dict) -> list:
    """Section 4: Ship losses by class (Python-side classification)."""
    sql = f"""
        SELECT it."typeID", ig."groupName", COUNT(*) AS count
        FROM killmails km
        JOIN "invTypes" it ON km.ship_type_id = it."typeID"
        JOIN "invGroups" ig ON it."groupID" = ig."groupID"
        WHERE {vf} AND km.killmail_time >= NOW() - INTERVAL '{days} days'
        GROUP BY it."typeID", ig."groupName"
    """
    cur.execute(sql, p)
    ship_class_counts: dict[str, int] = defaultdict(int)
    for type_id, group_name, count in cur.fetchall():
        ship_class_counts[classify_ship_group(group_name)] += count
    total_ships = sum(ship_class_counts.values())
    return [
        {"ship_class": sc, "count": c, "percentage": round(100.0 * c / total_ships, 1) if total_ships > 0 else 0.0}
        for sc, c in sorted(ship_class_counts.items(), key=lambda x: x[1], reverse=True)
    ]


def _build_doctrine_weakness(cur, ctx: EntityContext, days: int, vf: str, p: dict) -> list:
    """Section 5: Doctrine weakness (top lost ship types, excluding pods/shuttles)."""
    sql = f"""
        SELECT it."typeName" AS ship_name, ig."groupName" AS ship_group,
            COUNT(*) AS count,
            ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS percentage
        FROM killmails km
        JOIN "invTypes" it ON km.ship_type_id = it."typeID"
        JOIN "invGroups" ig ON it."groupID" = ig."groupID"
        WHERE {vf} AND km.killmail_time >= NOW() - INTERVAL '{days} days'
            AND ig."groupName" NOT IN ('Capsule', 'Shuttle', 'Rookie ship', 'Corvette')
        GROUP BY it."typeName", ig."groupName" ORDER BY count DESC LIMIT 15
    """
    cur.execute(sql, p)
    return [
        {"ship_name": sn, "ship_group": sg, "count": c, "percentage": float(pct or 0)}
        for sn, sg, c, pct in cur.fetchall()
    ]


def _build_loss_analysis(cur, ctx: EntityContext, days: int, vf: str, p: dict, capital_losses: int) -> dict:
    """Section 6: Loss analysis (PvP vs PvE, solo deaths, attacker counts)."""
    sql = f"""
        WITH death_details AS (
            SELECT km.killmail_id, km.ship_value,
                (SELECT COUNT(*) FROM killmail_attackers ka2 WHERE ka2.killmail_id = km.killmail_id) AS attacker_count,
                (SELECT COUNT(*) FROM killmail_attackers ka3
                 JOIN "invTypes" it3 ON ka3.ship_type_id = it3."typeID"
                 JOIN "invGroups" ig3 ON it3."groupID" = ig3."groupID"
                 WHERE ka3.killmail_id = km.killmail_id AND ig3."categoryID" = 6) AS combat_ship_attackers
            FROM killmails km
            WHERE {vf} AND km.killmail_time >= NOW() - INTERVAL '{days} days'
        )
        SELECT COUNT(*) AS total_deaths,
            COUNT(CASE WHEN combat_ship_attackers > 0 THEN 1 END) AS pvp_deaths,
            COUNT(CASE WHEN attacker_count <= 3 THEN 1 END) AS solo_deaths,
            AVG(attacker_count) AS avg_attacker_count,
            AVG(ship_value) AS avg_death_value
        FROM death_details
    """
    cur.execute(sql, p)
    lr = cur.fetchone()
    if lr:
        total_ld = lr[0] or 0
        pvp_d = lr[1] or 0
        return {
            "total_deaths": total_ld, "pvp_deaths": pvp_d, "pve_deaths": total_ld - pvp_d,
            "solo_deaths": lr[2] or 0, "avg_attacker_count": float(lr[3] or 0),
            "avg_death_value": float(lr[4] or 0), "capital_losses": capital_losses,
        }
    return {"total_deaths": 0, "pvp_deaths": 0, "pve_deaths": 0,
            "solo_deaths": 0, "avg_attacker_count": 0.0, "avg_death_value": 0.0, "capital_losses": 0}


def _build_death_heatmap(cur, ctx: EntityContext, days: int, vf: str, p: dict) -> list:
    """Section 7: Death heatmap (top systems by death count)."""
    sql = f"""
        WITH system_deaths AS (
            SELECT ms."solarSystemID" AS system_id, ms."solarSystemName" AS system_name,
                mr."regionName" AS region_name, COUNT(*) AS deaths,
                COUNT(CASE WHEN (SELECT COUNT(*) FROM killmail_attackers ka2 WHERE ka2.killmail_id = km.killmail_id) <= 3 THEN 1 END) AS solo_deaths
            FROM killmails km
            JOIN "mapSolarSystems" ms ON km.solar_system_id = ms."solarSystemID"
            JOIN "mapRegions" mr ON ms."regionID" = mr."regionID"
            WHERE {vf} AND km.killmail_time >= NOW() - INTERVAL '{days} days'
            GROUP BY ms."solarSystemID", ms."solarSystemName", mr."regionName"
        )
        SELECT system_id, system_name, region_name, deaths,
            ROUND(deaths::numeric / {days}, 2) AS deaths_per_day,
            CASE WHEN ROUND(100.0 * solo_deaths / NULLIF(deaths, 0), 1) > 60 THEN true ELSE false END AS is_camp
        FROM system_deaths ORDER BY deaths DESC LIMIT 20
    """
    cur.execute(sql, p)
    return [
        {"system_id": sid, "system_name": sn, "region_name": rn, "deaths": d,
         "deaths_per_day": float(dpd or 0), "is_camp": ic}
        for sid, sn, rn, d, dpd, ic in cur.fetchall()
    ]


def _build_loss_regions(cur, ctx: EntityContext, days: int, vf: str, p: dict) -> list:
    """Section 8: Loss regions (death distribution by region)."""
    sql = f"""
        SELECT mr."regionID" AS region_id, mr."regionName" AS region_name,
            COUNT(DISTINCT km.killmail_id) AS deaths,
            ROUND(100.0 * COUNT(DISTINCT km.killmail_id) / SUM(COUNT(DISTINCT km.killmail_id)) OVER (), 1) AS percentage,
            COUNT(DISTINCT ms."solarSystemID") AS unique_systems
        FROM killmails km
        JOIN "mapSolarSystems" ms ON km.solar_system_id = ms."solarSystemID"
        JOIN "mapRegions" mr ON ms."regionID" = mr."regionID"
        WHERE {vf} AND km.killmail_time >= NOW() - INTERVAL '{days} days'
        GROUP BY mr."regionID", mr."regionName" ORDER BY deaths DESC LIMIT 15
    """
    cur.execute(sql, p)
    return [
        {"region_id": rid, "region_name": rn, "deaths": d, "percentage": float(pct or 0), "unique_systems": us}
        for rid, rn, d, pct, us in cur.fetchall()
    ]


def _build_death_timeline(cur, ctx: EntityContext, days: int, vf: str, p: dict) -> list:
    """Section 9: Death timeline (daily death counts)."""
    sql = f"""
        SELECT DATE(km.killmail_time) AS day, COUNT(*) AS deaths,
            COUNT(DISTINCT km.victim_character_id) AS active_pilots
        FROM killmails km
        WHERE {vf} AND km.killmail_time >= NOW() - INTERVAL '{days} days'
        GROUP BY day ORDER BY day
    """
    cur.execute(sql, p)
    return [
        {"day": d.isoformat(), "deaths": deaths, "active_pilots": ap}
        for d, deaths, ap in cur.fetchall()
    ]


def _build_capital_losses(cur, ctx: EntityContext, days: int, vf: str, p: dict) -> Optional[dict]:
    """Section 10: Capital losses breakdown (conditional — returns None if no cap losses)."""
    sql = f"""
        WITH capital_deaths AS (
            SELECT COUNT(*) AS total_capital_losses,
                (SELECT COUNT(*) FROM killmails km2 WHERE {vf.replace('km.', 'km2.')} AND km2.killmail_time >= NOW() - INTERVAL '{days} days') AS total_deaths,
                COUNT(CASE WHEN ig."groupName" = 'Carrier' THEN 1 END) AS carrier_losses,
                COUNT(CASE WHEN ig."groupName" = 'Dreadnought' THEN 1 END) AS dread_losses,
                COUNT(CASE WHEN ig."groupName" = 'Force Auxiliary' THEN 1 END) AS fax_losses,
                COUNT(CASE WHEN ig."groupName" IN ('Supercarrier', 'Titan') THEN 1 END) AS super_titan_losses,
                ROUND(AVG(km.ship_value)) AS avg_capital_loss_value
            FROM killmails km
            JOIN "invTypes" it ON km.ship_type_id = it."typeID"
            JOIN "invGroups" ig ON it."groupID" = ig."groupID"
            WHERE {vf}
                AND ig."groupName" IN ('Carrier', 'Dreadnought', 'Force Auxiliary', 'Supercarrier', 'Titan')
                AND km.killmail_time >= NOW() - INTERVAL '{days} days'
        )
        SELECT total_capital_losses,
            CASE WHEN total_deaths > 0 THEN ROUND(100.0 * total_capital_losses / total_deaths, 1) ELSE 0 END AS capital_loss_pct,
            carrier_losses, dread_losses, fax_losses, super_titan_losses, avg_capital_loss_value
        FROM capital_deaths WHERE total_capital_losses > 0
    """
    cur.execute(sql, p)
    cap_row = cur.fetchone()
    if cap_row:
        return {
            "capital_losses": cap_row[0], "capital_loss_pct": float(cap_row[1] or 0),
            "carrier_losses": cap_row[2], "dread_losses": cap_row[3], "fax_losses": cap_row[4],
            "super_titan_losses": cap_row[5], "avg_capital_loss_value": float(cap_row[6] or 0),
        }
    return None


def _build_top_threats(cur, ctx: EntityContext, days: int, vf: str, p: dict) -> list:
    """Section 11: Top threats (corporations that killed the entity most)."""
    sql = f"""
        WITH threat_kills AS (
            SELECT ka.corporation_id, cn.corporation_name,
                COUNT(DISTINCT km.killmail_id) AS kills_by_them,
                SUM(km.ship_value) AS isk_destroyed_by_them,
                MAX(km.killmail_time) AS last_kill_time
            FROM killmails km
            JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
            LEFT JOIN corp_name_cache cn ON ka.corporation_id = cn.corporation_id
            WHERE {vf} AND km.killmail_time >= NOW() - INTERVAL '{days} days'
                AND ka.corporation_id IS NOT NULL
            GROUP BY ka.corporation_id, cn.corporation_name
        )
        SELECT corporation_id, corporation_name, kills_by_them, isk_destroyed_by_them, last_kill_time
        FROM threat_kills ORDER BY kills_by_them DESC LIMIT 30
    """
    cur.execute(sql, p)
    return [
        {"corporation_id": cid, "corporation_name": cn, "kills_by_them": k,
         "isk_destroyed_by_them": isk or 0.0, "last_kill_time": lk.isoformat() if lk else None}
        for cid, cn, k, isk, lk in cur.fetchall()
    ]


def _build_high_value_losses(cur, ctx: EntityContext, days: int, vf: str, p: dict) -> list:
    """Section 12: High-value losses (top 10 most expensive deaths)."""
    sql = f"""
        SELECT km.killmail_id, km.killmail_time, km.ship_value, km.victim_character_id,
            vc.character_name AS victim_name, km.ship_type_id,
            it."typeName" AS ship_name, ms."solarSystemName" AS system_name
        FROM killmails km
        LEFT JOIN character_name_cache vc ON km.victim_character_id = vc.character_id
        LEFT JOIN "invTypes" it ON km.ship_type_id = it."typeID"
        LEFT JOIN "mapSolarSystems" ms ON km.solar_system_id = ms."solarSystemID"
        WHERE {vf} AND km.killmail_time >= NOW() - INTERVAL '{days} days'
        ORDER BY km.ship_value DESC LIMIT 10
    """
    cur.execute(sql, p)
    return [
        {"killmail_id": kid, "killmail_time": kt.isoformat(), "isk_value": iv,
         "victim_character_id": vcid, "victim_name": vn, "ship_type_id": stid,
         "ship_name": sn, "system_name": sys_n}
        for kid, kt, iv, vcid, vn, stid, sn, sys_n in cur.fetchall()
    ]


def _build_safe_danger_hours(cur, ctx: EntityContext, days: int, vf: str, p: dict) -> dict:
    """Section 13: Safe/danger hours (hourly death distribution + 4h window analysis)."""
    sql = f"""
        WITH hourly_deaths AS (
            SELECT EXTRACT(HOUR FROM km.killmail_time) AS hour, COUNT(*) AS deaths
            FROM killmails km
            WHERE {vf} AND km.killmail_time >= NOW() - INTERVAL '{days} days'
            GROUP BY EXTRACT(HOUR FROM km.killmail_time)
        )
        SELECT hour, deaths FROM hourly_deaths ORDER BY hour
    """
    cur.execute(sql, p)
    hourly_data = [0] * 24
    for hour, deaths in cur.fetchall():
        hourly_data[int(hour)] = deaths

    # Find most dangerous 4-hour window
    max_sum, danger_start = 0, 0
    for h in range(24):
        ws = sum(hourly_data[h:(h + 4)] if h <= 20 else hourly_data[h:] + hourly_data[:(h + 4 - 24)])
        if ws > max_sum:
            max_sum, danger_start = ws, h
    danger_end = (danger_start + 4) % 24

    # Find safest 4-hour window
    min_sum, safe_start = float('inf'), 0
    for h in range(24):
        ws = sum(hourly_data[h:(h + 4)] if h <= 20 else hourly_data[h:] + hourly_data[:(h + 4 - 24)])
        if ws < min_sum:
            min_sum, safe_start = ws, h
    safe_end = (safe_start + 4) % 24

    return {
        "safe_start": safe_start, "safe_end": safe_end,
        "danger_start": danger_start, "danger_end": danger_end,
        "hourly_deaths": hourly_data
    }


def _build_damage_taken(cur, ctx: EntityContext, days: int, vf: str, p: dict) -> list:
    """Section 14: Damage taken profile (weapon damage type distribution)."""
    sql = f"""
        WITH classified_weapons AS (
            SELECT CASE
                WHEN wdp.weapon_class = 'Hybrid' THEN 'mixed'
                WHEN wdp.primary_damage_type IS NOT NULL THEN wdp.primary_damage_type
                WHEN ig."groupName" ILIKE '%%missile%%' THEN
                    CASE
                        WHEN it."typeName" ILIKE '%%mjolnir%%' OR it."typeName" ILIKE '%%wrath%%' OR it."typeName" ILIKE '%%thunderbolt%%' THEN 'em'
                        WHEN it."typeName" ILIKE '%%inferno%%' OR it."typeName" ILIKE '%%hellfire%%' OR it."typeName" ILIKE '%%scoria%%' THEN 'thermal'
                        WHEN it."typeName" ILIKE '%%scourge%%' OR it."typeName" ILIKE '%%juror%%' OR it."typeName" ILIKE '%%concussion%%' THEN 'kinetic'
                        WHEN it."typeName" ILIKE '%%nova%%' OR it."typeName" ILIKE '%%havoc%%' OR it."typeName" ILIKE '%%bane%%' OR it."typeName" ILIKE '%%shrapnel%%' THEN 'explosive'
                        ELSE NULL
                    END
                WHEN ig."groupName" = 'Hybrid Weapon' THEN 'mixed'
                WHEN ig."groupName" = 'Energy Weapon' THEN 'em'
                WHEN ig."groupName" = 'Projectile Weapon' THEN 'explosive'
                WHEN ig."groupName" = 'Precursor Weapon' THEN 'thermal'
                WHEN ig."groupName" = 'Bomb' THEN
                    CASE
                        WHEN it."typeName" ILIKE '%%electron%%' THEN 'em'
                        WHEN it."typeName" ILIKE '%%scoria%%' THEN 'thermal'
                        WHEN it."typeName" ILIKE '%%concussion%%' THEN 'kinetic'
                        WHEN it."typeName" ILIKE '%%shrapnel%%' THEN 'explosive'
                        ELSE NULL
                    END
                ELSE NULL
            END AS damage_type
            FROM killmails km
            JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
            LEFT JOIN weapon_damage_profiles wdp ON ka.weapon_type_id = wdp.type_id
            LEFT JOIN "invTypes" it ON ka.weapon_type_id = it."typeID"
            LEFT JOIN "invGroups" ig ON it."groupID" = ig."groupID"
            WHERE {vf} AND ka.weapon_type_id IS NOT NULL
                AND km.killmail_time >= NOW() - INTERVAL '{days} days'
        )
        SELECT damage_type, COUNT(*) AS count
        FROM classified_weapons WHERE damage_type IS NOT NULL
        GROUP BY damage_type
    """
    cur.execute(sql, p)
    damage_counts = {"EM": 0, "Thermal": 0, "Kinetic": 0, "Explosive": 0, "Mixed": 0}
    total_weapons = 0
    for row in cur.fetchall():
        dt = row[0]
        cnt = row[1]
        if dt:
            dt = 'EM' if dt.lower() == 'em' else dt.capitalize()
            if dt in damage_counts:
                damage_counts[dt] += cnt
                total_weapons += cnt
    return [
        {"damage_type": dt, "count": c, "percentage": round(100.0 * c / max(total_weapons, 1), 1)}
        for dt, c in damage_counts.items() if c > 0
    ]


def _build_ewar_threats(cur, ctx: EntityContext, days: int, vf: str, p: dict) -> list:
    """Section 15: E-war threats (electronic warfare module distribution)."""
    sql = f"""
        SELECT ig."groupName", COUNT(*) AS count
        FROM killmails km
        JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
        JOIN "invTypes" it ON ka.weapon_type_id = it."typeID"
        JOIN "invGroups" ig ON it."groupID" = ig."groupID"
        WHERE {vf} AND ig."categoryID" = 7
            AND ig."groupName" IN ('Target Painter', 'Warp Scrambler', 'Stasis Web', 'Energy Neutralizer',
                                   'Warp Disrupt Field Generator', 'Weapon Disruptor', 'ECM', 'Sensor Dampener',
                                   'Remote Sensor Dampener', 'Remote ECM Burst', 'Tracking Disruptor')
            AND km.killmail_time >= NOW() - INTERVAL '{days} days'
        GROUP BY ig."groupName"
    """
    cur.execute(sql, p)
    ewar_data: dict[str, int] = {}
    total_ewar = 0
    for group_name, count in cur.fetchall():
        total_ewar += count
        if 'Disrupt Field' in group_name:
            etype = 'Warp Disruption Bubble'
        elif 'Neutraliz' in group_name:
            etype = 'Energy Neutralizer'
        elif 'ECM' in group_name:
            etype = 'ECM Jammer'
        elif 'Damp' in group_name:
            etype = 'Sensor Dampener'
        elif 'Stasis' in group_name or group_name == 'Stasis Web':
            etype = 'Stasis Webifier'
        elif 'Scrambler' in group_name:
            etype = 'Warp Scrambler'
        elif 'Target Painter' in group_name:
            etype = 'Target Painter'
        elif 'Weapon' in group_name or 'Tracking' in group_name:
            etype = 'Tracking Disruptor'
        else:
            etype = 'Other E-War'
        ewar_data[etype] = ewar_data.get(etype, 0) + count
    return [
        {"ewar_type": et, "count": c, "percentage": round(100.0 * c / max(total_ewar, 1), 1)}
        for et, c in sorted(ewar_data.items(), key=lambda x: x[1], reverse=True)
    ]


def _build_danger_systems(cur, ctx: EntityContext, days: int, vf: str, af: str, p: dict) -> list:
    """Section 16: Danger systems (top systems with high death density + gatecamp detection)."""
    sql = f"""
        WITH system_deaths AS (
            SELECT km.solar_system_id, COUNT(*) AS deaths,
                COUNT(CASE WHEN (SELECT COUNT(*) FROM killmail_attackers ka2
                    WHERE ka2.killmail_id = km.killmail_id) <= 3 THEN 1 END) AS solo_deaths,
                COUNT(*)::float / %(days)s AS deaths_per_day
            FROM killmails km
            WHERE {vf} AND km.killmail_time >= NOW() - INTERVAL '{days} days'
            GROUP BY km.solar_system_id HAVING COUNT(*) >= 3
        ),
        unique_system_kills AS (
            SELECT DISTINCT km.killmail_id, km.solar_system_id
            FROM killmails km
            JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
            WHERE {af} AND km.killmail_time >= NOW() - INTERVAL '{days} days'
        ),
        system_kills AS (
            SELECT solar_system_id, COUNT(*) AS kills FROM unique_system_kills GROUP BY solar_system_id
        )
        SELECT ms."solarSystemID", ms."solarSystemName", mr."regionName", ms.security,
            sd.deaths, sd.deaths_per_day, COALESCE(sk.kills, 0) AS kills,
            ROUND(100.0 * sd.deaths / NULLIF(sd.deaths + COALESCE(sk.kills, 0), 0), 1) AS danger_score,
            CASE WHEN (sd.solo_deaths::float / sd.deaths) > 0.6 THEN true ELSE false END AS is_gatecamp
        FROM system_deaths sd
        JOIN "mapSolarSystems" ms ON sd.solar_system_id = ms."solarSystemID"
        JOIN "mapRegions" mr ON ms."regionID" = mr."regionID"
        LEFT JOIN system_kills sk ON sd.solar_system_id = sk.solar_system_id
        ORDER BY sd.deaths DESC LIMIT 15
    """
    cur.execute(sql, _params_with_days(ctx, days))
    return [
        {"system_id": sid, "system_name": sn, "region_name": rn, "security": float(sec or 0),
         "deaths": d, "deaths_per_day": float(dpd or 0), "kills": k,
         "danger_score": float(ds or 0), "is_gatecamp": gc}
        for sid, sn, rn, sec, d, dpd, k, ds, gc in cur.fetchall()
    ]


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------


def get_full_defensive_intel(cur, ctx: EntityContext, days: int) -> dict:
    """Get complete defensive intelligence (16 sections).

    Uses tuple cursor. All WHERE clauses are parameterized via EntityContext.
    Delegates to per-section helpers and assembles the final result dict.
    """
    p = _params(ctx)
    vf = _victim_filter(ctx)
    af = _attacker_filter(ctx)

    summary = _build_summary(cur, ctx, days, vf, af, p)
    threat_profile = _build_threat_profile(cur, ctx, days, vf, p)
    death_prone_pilots = _build_death_prone_pilots(cur, ctx, days, vf, af, p)
    ship_losses = _build_ship_losses(cur, ctx, days, vf, p)
    doctrine_weakness = _build_doctrine_weakness(cur, ctx, days, vf, p)
    loss_analysis = _build_loss_analysis(cur, ctx, days, vf, p, summary["capital_losses"])
    death_heatmap = _build_death_heatmap(cur, ctx, days, vf, p)
    loss_regions = _build_loss_regions(cur, ctx, days, vf, p)
    death_timeline = _build_death_timeline(cur, ctx, days, vf, p)
    capital_losses = _build_capital_losses(cur, ctx, days, vf, p)
    top_threats = _build_top_threats(cur, ctx, days, vf, p)
    high_value_losses = _build_high_value_losses(cur, ctx, days, vf, p)
    safe_danger_hours = _build_safe_danger_hours(cur, ctx, days, vf, p)
    damage_taken = _build_damage_taken(cur, ctx, days, vf, p)
    ewar_threats = _build_ewar_threats(cur, ctx, days, vf, p)
    danger_systems = _build_danger_systems(cur, ctx, days, vf, af, p)

    return {
        "summary": summary, "threat_profile": threat_profile,
        "death_prone_pilots": death_prone_pilots, "ship_losses": ship_losses,
        "doctrine_weakness": doctrine_weakness, "loss_analysis": loss_analysis,
        "death_heatmap": death_heatmap, "loss_regions": loss_regions,
        "death_timeline": death_timeline, "capital_losses": capital_losses,
        "top_threats": top_threats, "high_value_losses": high_value_losses,
        "safe_danger_hours": safe_danger_hours, "damage_taken": damage_taken,
        "ewar_threats": ewar_threats, "danger_systems": danger_systems,
    }
