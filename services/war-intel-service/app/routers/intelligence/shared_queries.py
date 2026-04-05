"""Shared query functions for Alliance, Corporation, and PowerBloc endpoints.

All functions take an EntityContext to parameterize SQL filters,
eliminating code duplication across the three entity types.
"""

from .entity_context import EntityContext
from .corp_sql_helpers import CAPITAL_GROUPS


def _corp_join_kills(ctx: EntityContext) -> str:
    """Optional JOIN corporations for kill queries."""
    if ctx.kill_attacker_needs_corp_join:
        return 'JOIN corporations c ON ka.corporation_id = c.corporation_id'
    return ''


def _corp_join_deaths(ctx: EntityContext) -> str:
    """Optional JOIN corporations for death queries."""
    if ctx.death_victim_needs_corp_join:
        return 'JOIN corporations c ON km.victim_corporation_id = c.corporation_id'
    return ''


# ============================================================================
# Geography Queries
# ============================================================================

def get_geography_regions(cur, ctx: EntityContext, days: int) -> list[dict]:
    """Get region activity distribution (kills + deaths)."""
    cur.execute(f"""
        WITH region_kills AS (
            SELECT
                r."regionID" AS region_id,
                r."regionName" AS region_name,
                COUNT(DISTINCT km.killmail_id) AS kills,
                SUM(km.ship_value) AS isk_destroyed
            FROM killmails km
            JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
            {_corp_join_kills(ctx)}
            JOIN "mapSolarSystems" s ON km.solar_system_id = s."solarSystemID"
            JOIN "mapRegions" r ON s."regionID" = r."regionID"
            WHERE {ctx.kill_attacker_filter}
              AND km.killmail_time >= NOW() - make_interval(days => %s)
            GROUP BY r."regionID", r."regionName"
        ),
        region_deaths AS (
            SELECT
                r."regionID" AS region_id,
                r."regionName" AS region_name,
                COUNT(DISTINCT km.killmail_id) AS deaths,
                SUM(km.ship_value) AS isk_lost
            FROM killmails km
            {_corp_join_deaths(ctx)}
            JOIN "mapSolarSystems" s ON km.solar_system_id = s."solarSystemID"
            JOIN "mapRegions" r ON s."regionID" = r."regionID"
            WHERE {ctx.death_victim_filter}
              AND km.killmail_time >= NOW() - make_interval(days => %s)
            GROUP BY r."regionID", r."regionName"
        )
        SELECT
            COALESCE(rk.region_id, rd.region_id) AS region_id,
            COALESCE(rk.region_name, rd.region_name) AS region_name,
            COALESCE(rk.kills, 0) AS kills,
            COALESCE(rd.deaths, 0) AS deaths,
            COALESCE(rk.kills, 0) + COALESCE(rd.deaths, 0) AS activity,
            COALESCE(rk.isk_destroyed, 0) AS isk_destroyed,
            COALESCE(rd.isk_lost, 0) AS isk_lost,
            CASE
                WHEN COALESCE(rk.isk_destroyed, 0) + COALESCE(rd.isk_lost, 0) > 0
                THEN (COALESCE(rk.isk_destroyed, 0)::FLOAT / (COALESCE(rk.isk_destroyed, 0) + COALESCE(rd.isk_lost, 0))) * 100
                ELSE 0
            END AS efficiency
        FROM region_kills rk
        FULL OUTER JOIN region_deaths rd ON rk.region_id = rd.region_id
        ORDER BY activity DESC
        LIMIT 10
    """, ctx.region_params(days))

    return [
        {
            "region_id": row['region_id'],
            "region_name": row['region_name'],
            "kills": row['kills'],
            "deaths": row['deaths'],
            "activity": row['activity'],
            "isk_destroyed": str(row['isk_destroyed']),
            "isk_lost": str(row['isk_lost']),
            "efficiency": round(float(row['efficiency'] or 0), 1)
        }
        for row in cur.fetchall()
    ]


def get_geography_systems(cur, ctx: EntityContext, days: int) -> list[dict]:
    """Get top active systems."""
    cur.execute(f"""
        WITH system_kills AS (
            SELECT
                km.solar_system_id AS system_id,
                s."solarSystemName" AS system_name,
                r."regionName" AS region_name,
                COUNT(DISTINCT km.killmail_id) AS kills
            FROM killmails km
            JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
            {_corp_join_kills(ctx)}
            JOIN "mapSolarSystems" s ON km.solar_system_id = s."solarSystemID"
            JOIN "mapRegions" r ON s."regionID" = r."regionID"
            WHERE {ctx.kill_attacker_filter}
              AND km.killmail_time >= NOW() - make_interval(days => %s)
            GROUP BY km.solar_system_id, s."solarSystemName", r."regionName"
        ),
        system_deaths AS (
            SELECT
                km.solar_system_id AS system_id,
                s."solarSystemName" AS system_name,
                r."regionName" AS region_name,
                COUNT(DISTINCT km.killmail_id) AS deaths
            FROM killmails km
            {_corp_join_deaths(ctx)}
            JOIN "mapSolarSystems" s ON km.solar_system_id = s."solarSystemID"
            JOIN "mapRegions" r ON s."regionID" = r."regionID"
            WHERE {ctx.death_victim_filter}
              AND km.killmail_time >= NOW() - make_interval(days => %s)
            GROUP BY km.solar_system_id, s."solarSystemName", r."regionName"
        )
        SELECT
            COALESCE(sk.system_id, sd.system_id) AS system_id,
            COALESCE(sk.system_name, sd.system_name) AS system_name,
            COALESCE(sk.region_name, sd.region_name) AS region_name,
            COALESCE(sk.kills, 0) AS kills,
            COALESCE(sd.deaths, 0) AS deaths,
            COALESCE(sk.kills, 0) + COALESCE(sd.deaths, 0) AS activity
        FROM system_kills sk
        FULL OUTER JOIN system_deaths sd ON sk.system_id = sd.system_id
        ORDER BY activity DESC
        LIMIT 15
    """, ctx.region_params(days))

    return [
        {
            "system_id": row['system_id'],
            "system_name": row['system_name'],
            "region_name": row['region_name'],
            "kills": row['kills'],
            "deaths": row['deaths'],
            "activity": row['activity']
        }
        for row in cur.fetchall()
    ]


def get_geography_home_systems(cur, ctx: EntityContext, days: int) -> list[dict]:
    """Get home systems (positive K/D, high activity, with sovereignty check)."""
    cur.execute(f"""
        WITH home_kills AS (
            SELECT
                km.solar_system_id AS system_id,
                s."solarSystemName" AS system_name,
                r."regionName" AS region_name,
                COUNT(DISTINCT km.killmail_id) AS kills
            FROM killmails km
            JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
            {_corp_join_kills(ctx)}
            JOIN "mapSolarSystems" s ON km.solar_system_id = s."solarSystemID"
            JOIN "mapRegions" r ON s."regionID" = r."regionID"
            WHERE {ctx.kill_attacker_filter}
              AND km.killmail_time >= NOW() - make_interval(days => %s)
            GROUP BY km.solar_system_id, s."solarSystemName", r."regionName"
        ),
        home_deaths AS (
            SELECT
                km.solar_system_id AS system_id,
                COUNT(DISTINCT km.killmail_id) AS deaths
            FROM killmails km
            {_corp_join_deaths(ctx)}
            WHERE {ctx.death_victim_filter}
              AND km.killmail_time >= NOW() - make_interval(days => %s)
            GROUP BY km.solar_system_id
        )
        SELECT
            COALESCE(hk.system_id, hd.system_id) AS system_id,
            hk.system_name,
            hk.region_name,
            COALESCE(hk.kills, 0) AS kills,
            COALESCE(hd.deaths, 0) AS deaths,
            COALESCE(hk.kills, 0) + COALESCE(hd.deaths, 0) AS activity,
            CASE WHEN {ctx.sov_filter} THEN true ELSE false END AS owned_by_alliance
        FROM home_kills hk
        FULL OUTER JOIN home_deaths hd ON hk.system_id = hd.system_id
        LEFT JOIN sovereignty_map_cache sov ON COALESCE(hk.system_id, hd.system_id) = sov.solar_system_id
        WHERE COALESCE(hk.kills, 0) > COALESCE(hd.deaths, 0)
          AND COALESCE(hk.kills, 0) + COALESCE(hd.deaths, 0) >= 10
        ORDER BY COALESCE(hk.kills, 0) DESC, COALESCE(hk.kills, 0) + COALESCE(hd.deaths, 0) DESC
        LIMIT 20
    """, ctx.home_params(days))

    return [
        {
            "system_id": row['system_id'],
            "system_name": row['system_name'],
            "region_name": row['region_name'],
            "kills": row['kills'],
            "deaths": row['deaths'],
            "activity": row['activity'],
            "owned_by_alliance": row['owned_by_alliance']
        }
        for row in cur.fetchall()
    ]


def get_full_geography(cur, ctx: EntityContext, days: int) -> dict:
    """Get complete geography data (regions, systems, home systems)."""
    return {
        "regions": get_geography_regions(cur, ctx, days),
        "top_systems": get_geography_systems(cur, ctx, days),
        "home_systems": get_geography_home_systems(cur, ctx, days),
    }


# ============================================================================
# Capital Intel Queries (use tuple cursor + named params)
# ============================================================================

def _capital_kills_cte(ctx: EntityContext, days: int) -> str:
    """CTE for unique capital kills."""
    return f"""unique_capital_kills AS (
                SELECT DISTINCT
                    km.killmail_id,
                    km.ship_type_id,
                    km.ship_value,
                    km.solar_system_id,
                    km.killmail_time
                FROM killmails km
                JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
                JOIN "invTypes" it ON km.ship_type_id = it."typeID"
                JOIN "invGroups" ig ON it."groupID" = ig."groupID"
                WHERE {ctx.capital_kill_filter}
                    AND ig."groupName" IN %(capital_groups)s
                    AND km.killmail_time >= NOW() - INTERVAL '{days} days'
            )"""


def _capital_losses_cte(ctx: EntityContext, days: int) -> str:
    """CTE for unique capital losses."""
    return f"""unique_capital_losses AS (
                SELECT
                    km.killmail_id,
                    km.ship_type_id,
                    km.ship_value,
                    km.solar_system_id,
                    km.killmail_time,
                    km.victim_character_id
                FROM killmails km
                JOIN "invTypes" it ON km.ship_type_id = it."typeID"
                JOIN "invGroups" ig ON it."groupID" = ig."groupID"
                WHERE {ctx.capital_loss_filter}
                    AND ig."groupName" IN %(capital_groups)s
                    AND km.killmail_time >= NOW() - INTERVAL '{days} days'
            )"""


def _capital_params(ctx: EntityContext) -> dict:
    """Named params for capital queries."""
    return {**ctx.capital_sql_params, "capital_groups": CAPITAL_GROUPS}


def get_capital_summary(cur, ctx: EntityContext, days: int) -> dict:
    """Enhanced capital summary with K/D, efficiency, ISK metrics."""
    sql = f"""
        WITH {_capital_kills_cte(ctx, days)},
        {_capital_losses_cte(ctx, days)},
        kills_data AS (
            SELECT
                COUNT(*) AS capital_kills,
                SUM(ship_value) AS isk_destroyed,
                (SELECT COUNT(DISTINCT ka.character_id)
                 FROM killmail_attackers ka
                 WHERE ka.killmail_id IN (SELECT killmail_id FROM unique_capital_kills)
                   AND {ctx.capital_kill_filter}) AS kill_pilots
            FROM unique_capital_kills
        ),
        losses_data AS (
            SELECT
                COUNT(*) AS capital_losses,
                SUM(ship_value) AS isk_lost,
                COUNT(DISTINCT victim_character_id) AS loss_pilots
            FROM unique_capital_losses
        )
        SELECT
            k.capital_kills,
            l.capital_losses,
            k.isk_destroyed,
            l.isk_lost,
            k.kill_pilots + l.loss_pilots AS unique_pilots,
            CASE WHEN l.capital_losses > 0 THEN ROUND(k.capital_kills::numeric / l.capital_losses, 2) ELSE k.capital_kills END AS kd_ratio,
            CASE WHEN (k.isk_destroyed + l.isk_lost) > 0 THEN ROUND(100.0 * k.isk_destroyed / (k.isk_destroyed + l.isk_lost), 1) ELSE 0 END AS efficiency
        FROM kills_data k, losses_data l
    """
    cur.execute(sql, _capital_params(ctx))
    row = cur.fetchone()
    return {
        "capital_kills": row[0] or 0,
        "capital_losses": row[1] or 0,
        "isk_destroyed": float(row[2] or 0),
        "isk_lost": float(row[3] or 0),
        "unique_pilots": row[4] or 0,
        "kd_ratio": float(row[5] or 0),
        "efficiency": float(row[6] or 0),
    }


def get_capital_fleet_composition(cur, ctx: EntityContext, days: int) -> list[dict]:
    """Fleet composition by capital type."""
    sql = f"""
        WITH {_capital_kills_cte(ctx, days)},
        {_capital_losses_cte(ctx, days)},
        kills_by_type AS (
            SELECT ig."groupName" AS capital_type, COUNT(*) AS kills
            FROM unique_capital_kills uck
            JOIN "invTypes" it ON uck.ship_type_id = it."typeID"
            JOIN "invGroups" ig ON it."groupID" = ig."groupID"
            GROUP BY ig."groupName"
        ),
        losses_by_type AS (
            SELECT ig."groupName" AS capital_type, COUNT(*) AS losses
            FROM unique_capital_losses ucl
            JOIN "invTypes" it ON ucl.ship_type_id = it."typeID"
            JOIN "invGroups" ig ON it."groupID" = ig."groupID"
            GROUP BY ig."groupName"
        )
        SELECT
            COALESCE(k.capital_type, l.capital_type) AS capital_type,
            COALESCE(k.kills, 0) AS kills,
            COALESCE(l.losses, 0) AS losses,
            COALESCE(k.kills, 0) + COALESCE(l.losses, 0) AS total_activity
        FROM kills_by_type k
        FULL OUTER JOIN losses_by_type l ON k.capital_type = l.capital_type
        ORDER BY total_activity DESC
    """
    cur.execute(sql, _capital_params(ctx))

    fleet_composition = []
    for capital_type, kills, losses, total_activity in cur.fetchall():
        fleet_composition.append({
            "capital_type": capital_type,
            "total_activity": total_activity,
            "kills": kills,
            "losses": losses,
            "kills_pct": 0.0,
            "losses_pct": 0.0,
        })

    total_kills = sum(c["kills"] for c in fleet_composition)
    total_losses = sum(c["losses"] for c in fleet_composition)
    for comp in fleet_composition:
        comp["kills_pct"] = round(100.0 * comp["kills"] / total_kills, 1) if total_kills > 0 else 0.0
        comp["losses_pct"] = round(100.0 * comp["losses"] / total_losses, 1) if total_losses > 0 else 0.0

    return fleet_composition


def get_capital_ship_details(cur, ctx: EntityContext, days: int) -> list[dict]:
    """Specific capital ships used/lost."""
    sql = f"""
        WITH {_capital_kills_cte(ctx, days)},
        {_capital_losses_cte(ctx, days)},
        kills_by_ship AS (
            SELECT it."typeName" AS ship_name, ig."groupName" AS capital_type,
                   COUNT(*) AS kills, ROUND(AVG(uck.ship_value)) AS avg_value
            FROM unique_capital_kills uck
            JOIN "invTypes" it ON uck.ship_type_id = it."typeID"
            JOIN "invGroups" ig ON it."groupID" = ig."groupID"
            GROUP BY it."typeName", ig."groupName"
        ),
        losses_by_ship AS (
            SELECT it."typeName" AS ship_name, ig."groupName" AS capital_type,
                   COUNT(*) AS losses, ROUND(AVG(ucl.ship_value)) AS avg_value
            FROM unique_capital_losses ucl
            JOIN "invTypes" it ON ucl.ship_type_id = it."typeID"
            JOIN "invGroups" ig ON it."groupID" = ig."groupID"
            GROUP BY it."typeName", ig."groupName"
        )
        SELECT
            COALESCE(k.ship_name, l.ship_name) AS ship_name,
            COALESCE(k.capital_type, l.capital_type) AS capital_type,
            COALESCE(k.kills, 0) AS kills,
            COALESCE(l.losses, 0) AS losses,
            COALESCE(k.kills, 0) + COALESCE(l.losses, 0) AS total_activity,
            COALESCE(k.avg_value, l.avg_value) AS avg_value
        FROM kills_by_ship k
        FULL OUTER JOIN losses_by_ship l ON k.ship_name = l.ship_name AND k.capital_type = l.capital_type
        ORDER BY total_activity DESC
        LIMIT 20
    """
    cur.execute(sql, _capital_params(ctx))
    return [
        {
            "ship_name": sn, "capital_type": ct, "total_activity": ta,
            "kills": k, "losses": lo, "avg_value": float(av or 0),
        }
        for sn, ct, k, lo, ta, av in cur.fetchall()
    ]


def get_capital_timeline(cur, ctx: EntityContext, days: int) -> list[dict]:
    """Daily capital activity trend."""
    sql = f"""
        WITH {_capital_kills_cte(ctx, days)},
        {_capital_losses_cte(ctx, days)},
        daily_kills AS (
            SELECT DATE(killmail_time) AS day, COUNT(*) AS kills
            FROM unique_capital_kills GROUP BY DATE(killmail_time)
        ),
        daily_losses AS (
            SELECT DATE(killmail_time) AS day, COUNT(*) AS losses
            FROM unique_capital_losses GROUP BY DATE(killmail_time)
        )
        SELECT COALESCE(k.day, l.day) AS day,
               COALESCE(k.kills, 0) AS kills,
               COALESCE(l.losses, 0) AS losses
        FROM daily_kills k
        FULL OUTER JOIN daily_losses l ON k.day = l.day
        ORDER BY day
    """
    cur.execute(sql, _capital_params(ctx))
    return [{"day": d.isoformat(), "kills": k, "losses": lo} for d, k, lo in cur.fetchall()]


def get_capital_hotspots(cur, ctx: EntityContext, days: int) -> list[dict]:
    """Geographic hotspots for capital activity."""
    sql = f"""
        WITH {_capital_kills_cte(ctx, days)},
        {_capital_losses_cte(ctx, days)},
        kills_by_system AS (
            SELECT solar_system_id, COUNT(*) AS kills FROM unique_capital_kills GROUP BY solar_system_id
        ),
        losses_by_system AS (
            SELECT solar_system_id, COUNT(*) AS losses FROM unique_capital_losses GROUP BY solar_system_id
        )
        SELECT
            COALESCE(k.solar_system_id, l.solar_system_id) AS system_id,
            ms."solarSystemName" AS system_name,
            mr."regionName" AS region_name,
            COALESCE(k.kills, 0) + COALESCE(l.losses, 0) AS activity,
            COALESCE(k.kills, 0) AS kills,
            COALESCE(l.losses, 0) AS losses
        FROM kills_by_system k
        FULL OUTER JOIN losses_by_system l ON k.solar_system_id = l.solar_system_id
        LEFT JOIN "mapSolarSystems" ms ON COALESCE(k.solar_system_id, l.solar_system_id) = ms."solarSystemID"
        LEFT JOIN "mapRegions" mr ON ms."regionID" = mr."regionID"
        ORDER BY activity DESC
        LIMIT 15
    """
    cur.execute(sql, _capital_params(ctx))
    return [
        {"system_id": sid, "system_name": sn, "region_name": rn, "activity": a, "kills": k, "losses": lo}
        for sid, sn, rn, a, k, lo in cur.fetchall()
    ]


def get_capital_top_killers(cur, ctx: EntityContext, days: int) -> list[dict]:
    """Top capital pilots by kills."""
    sql = f"""
        WITH {_capital_kills_cte(ctx, days)}
        SELECT
            ka.character_id,
            cn.character_name,
            COUNT(DISTINCT uck.killmail_id) AS capital_kills,
            SUM(uck.ship_value) AS isk_destroyed,
            MAX(it."typeName") AS primary_ship
        FROM unique_capital_kills uck
        JOIN killmail_attackers ka ON uck.killmail_id = ka.killmail_id
        LEFT JOIN character_name_cache cn ON ka.character_id = cn.character_id
        JOIN "invTypes" it ON uck.ship_type_id = it."typeID"
        WHERE {ctx.capital_kill_filter}
        GROUP BY ka.character_id, cn.character_name
        ORDER BY capital_kills DESC
        LIMIT 10
    """
    cur.execute(sql, _capital_params(ctx))
    return [
        {"character_id": cid, "character_name": cn, "capital_kills": k, "isk_destroyed": float(isk or 0), "primary_ship": ps}
        for cid, cn, k, isk, ps in cur.fetchall()
    ]


def get_capital_top_losers(cur, ctx: EntityContext, days: int) -> list[dict]:
    """Top capital pilots by losses."""
    sql = f"""
        SELECT
            km.victim_character_id,
            cn.character_name,
            COUNT(*) AS capital_losses,
            SUM(km.ship_value) AS isk_lost,
            MAX(it."typeName") AS last_ship_lost
        FROM killmails km
        LEFT JOIN character_name_cache cn ON km.victim_character_id = cn.character_id
        JOIN "invTypes" it ON km.ship_type_id = it."typeID"
        JOIN "invGroups" ig ON it."groupID" = ig."groupID"
        WHERE {ctx.capital_loss_filter}
            AND ig."groupName" IN %(capital_groups)s
            AND km.killmail_time >= NOW() - INTERVAL '{days} days'
        GROUP BY km.victim_character_id, cn.character_name
        ORDER BY capital_losses DESC
        LIMIT 10
    """
    cur.execute(sql, _capital_params(ctx))
    return [
        {"character_id": cid, "character_name": cn, "capital_losses": lo, "isk_lost": float(isk or 0), "last_ship_lost": ls}
        for cid, cn, lo, isk, ls in cur.fetchall()
    ]


def get_capital_engagements(cur, ctx: EntityContext, days: int) -> list[dict]:
    """Capital engagement size analysis."""
    sql = f"""
        WITH {_capital_kills_cte(ctx, days)},
        {_capital_losses_cte(ctx, days)},
        kill_engagement_sizes AS (
            SELECT DISTINCT killmail_id,
                (SELECT COUNT(*) FROM killmail_attackers WHERE killmail_id = uck.killmail_id) AS attacker_count
            FROM unique_capital_kills uck
        ),
        loss_engagement_sizes AS (
            SELECT DISTINCT killmail_id,
                (SELECT COUNT(*) FROM killmail_attackers WHERE killmail_id = ucl.killmail_id) AS attacker_count
            FROM unique_capital_losses ucl
        ),
        kill_sizes AS (
            SELECT CASE
                WHEN attacker_count <= 3 THEN 'solo'
                WHEN attacker_count <= 10 THEN 'small'
                WHEN attacker_count <= 30 THEN 'medium'
                WHEN attacker_count <= 100 THEN 'large'
                ELSE 'blob'
            END AS engagement_size, COUNT(*) AS kills
            FROM kill_engagement_sizes GROUP BY engagement_size
        ),
        loss_sizes AS (
            SELECT CASE
                WHEN attacker_count <= 3 THEN 'solo'
                WHEN attacker_count <= 10 THEN 'small'
                WHEN attacker_count <= 30 THEN 'medium'
                WHEN attacker_count <= 100 THEN 'large'
                ELSE 'blob'
            END AS engagement_size, COUNT(*) AS losses
            FROM loss_engagement_sizes GROUP BY engagement_size
        )
        SELECT
            COALESCE(k.engagement_size, l.engagement_size) AS engagement_size,
            COALESCE(k.kills, 0) + COALESCE(l.losses, 0) AS count,
            COALESCE(k.kills, 0) AS kills,
            COALESCE(l.losses, 0) AS losses
        FROM kill_sizes k
        FULL OUTER JOIN loss_sizes l ON k.engagement_size = l.engagement_size
        ORDER BY count DESC
    """
    cur.execute(sql, _capital_params(ctx))
    return [
        {"engagement_size": s, "total": c, "kills": k, "losses": lo}
        for s, c, k, lo in cur.fetchall()
    ]


def get_capital_recent_activity(cur, ctx: EntityContext, days: int) -> list[dict]:
    """Recent capital killmails."""
    sql = f"""
        WITH {_capital_kills_cte(ctx, days)},
        {_capital_losses_cte(ctx, days)}
        (
            SELECT DISTINCT ON (uck.killmail_id)
                uck.killmail_id, uck.killmail_time, uck.ship_value,
                'kill' AS activity_type,
                it."typeName" AS ship_name, ig."groupName" AS capital_type,
                ms."solarSystemName" AS system_name,
                COALESCE(cn.character_name, 'Unknown') AS pilot_name,
                ka.character_id
            FROM unique_capital_kills uck
            JOIN "invTypes" it ON uck.ship_type_id = it."typeID"
            JOIN "invGroups" ig ON it."groupID" = ig."groupID"
            LEFT JOIN "mapSolarSystems" ms ON uck.solar_system_id = ms."solarSystemID"
            LEFT JOIN killmail_attackers ka ON uck.killmail_id = ka.killmail_id AND {ctx.capital_recent_attacker_filter}
            LEFT JOIN character_name_cache cn ON ka.character_id = cn.character_id
            ORDER BY uck.killmail_id, uck.killmail_time DESC
        )
        UNION ALL
        (
            SELECT
                ucl.killmail_id, ucl.killmail_time, ucl.ship_value,
                'loss' AS activity_type,
                it."typeName" AS ship_name, ig."groupName" AS capital_type,
                ms."solarSystemName" AS system_name,
                COALESCE(cn.character_name, 'Unknown') AS pilot_name,
                ucl.victim_character_id AS character_id
            FROM unique_capital_losses ucl
            JOIN "invTypes" it ON ucl.ship_type_id = it."typeID"
            JOIN "invGroups" ig ON it."groupID" = ig."groupID"
            LEFT JOIN "mapSolarSystems" ms ON ucl.solar_system_id = ms."solarSystemID"
            LEFT JOIN character_name_cache cn ON ucl.victim_character_id = cn.character_id
        )
        ORDER BY killmail_time DESC
        LIMIT 20
    """
    cur.execute(sql, _capital_params(ctx))
    return [
        {
            "killmail_id": km_id, "killmail_time": km_time.isoformat(),
            "isk_value": float(isk or 0), "activity_type": at, "ship_name": sn,
            "capital_type": ct, "system_name": sysn, "pilot_name": pn, "character_id": cid,
        }
        for km_id, km_time, isk, at, sn, ct, sysn, pn, cid in cur.fetchall()
    ]


def get_full_capital_intel(cur, ctx: EntityContext, days: int) -> dict:
    """Get complete capital intel data (all 9 sections)."""
    return {
        "summary": get_capital_summary(cur, ctx, days),
        "fleet_composition": get_capital_fleet_composition(cur, ctx, days),
        "ship_details": get_capital_ship_details(cur, ctx, days),
        "capital_timeline": get_capital_timeline(cur, ctx, days),
        "geographic_hotspots": get_capital_hotspots(cur, ctx, days),
        "top_killers": get_capital_top_killers(cur, ctx, days),
        "top_losers": get_capital_top_losers(cur, ctx, days),
        "capital_engagements": get_capital_engagements(cur, ctx, days),
        "recent_activity": get_capital_recent_activity(cur, ctx, days),
    }
