"""Shared DOTLAN query functions for Alliance, Corporation, and PowerBloc.

All functions take an EntityContext to parameterize SQL filters,
correlating DOTLAN system activity with entity's operational regions.
"""

from .entity_context import EntityContext, EntityType


def _corp_join_kills(ctx: EntityContext) -> str:
    """Optional JOIN corporations for kill queries."""
    if ctx.kill_attacker_needs_corp_join:
        return 'JOIN corporations c ON ka.corporation_id = c.corporation_id'
    return ''


def get_dotlan_live_activity(cur, ctx: EntityContext, days: int, limit: int = 20) -> dict:
    """Get live system activity from DOTLAN for entity-relevant systems.

    Correlates with entity's top systems from zKillboard activity to filter
    to operationally relevant regions only.

    Returns dict with systems list and metadata.
    """
    # First, get entity's active regions based on recent zKill activity
    cur.execute(f"""
        WITH entity_regions AS (
            SELECT DISTINCT r."regionID" as region_id
            FROM killmails km
            JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
            {_corp_join_kills(ctx)}
            JOIN "mapSolarSystems" s ON km.solar_system_id = s."solarSystemID"
            JOIN "mapRegions" r ON s."regionID" = r."regionID"
            WHERE {ctx.kill_attacker_filter}
              AND km.killmail_time >= NOW() - make_interval(days => %s)
        ),
        recent_activity AS (
            SELECT
                a.solar_system_id,
                SUM(a.npc_kills) as npc_kills,
                SUM(a.ship_kills) as ship_kills,
                SUM(a.pod_kills) as pod_kills,
                SUM(a.jumps) as jumps,
                MAX(a.timestamp) as last_activity
            FROM dotlan_system_activity a
            JOIN "mapSolarSystems" s ON a.solar_system_id = s."solarSystemID"
            WHERE s."regionID" IN (SELECT region_id FROM entity_regions)
              AND a.timestamp > NOW() - INTERVAL '24 hours'
            GROUP BY a.solar_system_id
        ),
        max_activity AS (
            SELECT MAX(ship_kills + pod_kills) as max_pvp FROM recent_activity
        )
        SELECT
            ra.solar_system_id,
            s."solarSystemName" as system_name,
            r."regionName" as region_name,
            s."security" as security_status,
            COALESCE(ra.npc_kills, 0) as npc_kills,
            COALESCE(ra.ship_kills, 0) as ship_kills,
            COALESCE(ra.pod_kills, 0) as pod_kills,
            COALESCE(ra.jumps, 0) as jumps,
            ra.last_activity,
            CASE
                WHEN ma.max_pvp > 0
                THEN ROUND((ra.ship_kills + ra.pod_kills)::numeric / ma.max_pvp, 2)
                ELSE 0
            END as heat_index
        FROM recent_activity ra
        JOIN "mapSolarSystems" s ON ra.solar_system_id = s."solarSystemID"
        JOIN "mapRegions" r ON s."regionID" = r."regionID"
        CROSS JOIN max_activity ma
        WHERE (ra.ship_kills + ra.pod_kills + ra.npc_kills + ra.jumps) > 0
        ORDER BY heat_index DESC, (ra.ship_kills + ra.pod_kills) DESC
        LIMIT %s
    """, (ctx.filter_value, days, limit))

    systems = [
        {
            "solar_system_id": row['solar_system_id'],
            "system_name": row['system_name'],
            "region_name": row['region_name'],
            "security_status": round(float(row['security_status'] or 0), 1),
            "npc_kills": row['npc_kills'],
            "ship_kills": row['ship_kills'],
            "pod_kills": row['pod_kills'],
            "jumps": row['jumps'],
            "heat_index": float(row['heat_index'] or 0),
            "last_activity": row['last_activity'].isoformat() if row['last_activity'] else None
        }
        for row in cur.fetchall()
    ]

    # Get last scrape timestamp
    cur.execute("SELECT MAX(scraped_at) as last_scraped FROM dotlan_system_activity")
    row = cur.fetchone()
    last_scraped = row['last_scraped'] if row else None

    return {
        "systems": systems,
        "refresh_rate_seconds": 3600,  # 1 hour
        "last_scraped": last_scraped.isoformat() if last_scraped else None
    }


def get_dotlan_sov_campaigns(cur, ctx: EntityContext) -> dict:
    """Get active sovereignty campaigns affecting entity's space.

    For Alliance/PowerBloc: Systems where alliance is defender
    For Corporation: Systems in corporation's active alliance

    Returns dict with campaigns list and alert counts.
    """
    # Get the alliance IDs to check (for sov, we need alliance level)
    if ctx.entity_type == EntityType.POWERBLOC:
        alliance_filter = "c.defender_id = ANY(%s)"
        alliance_value = ctx.member_ids
    elif ctx.entity_type == EntityType.CORPORATION:
        alliance_filter = "c.defender_id = %s"
        alliance_value = ctx.alliance_id_for_sov
    else:  # Alliance
        alliance_filter = "c.defender_id = %s"
        alliance_value = ctx.entity_id

    # Skip if no alliance context (e.g., NPC corp)
    if alliance_value is None:
        return {
            "campaigns": [],
            "total_active": 0,
            "critical_count": 0,
            "refresh_rate_seconds": 600
        }

    cur.execute(f"""
        SELECT
            c.campaign_id,
            c.solar_system_id,
            s."solarSystemName" as system_name,
            r."regionName" as region_name,
            c.structure_type,
            c.defender_name,
            c.score,
            c.status,
            c.last_updated,
            adm.adm_level,
            CASE
                WHEN adm.adm_level IS NULL THEN 'unknown'
                WHEN adm.adm_level < 2 THEN 'critical'
                WHEN adm.adm_level < 4 THEN 'vulnerable'
                ELSE 'defended'
            END as vulnerability
        FROM dotlan_sov_campaigns c
        LEFT JOIN "mapSolarSystems" s ON c.solar_system_id = s."solarSystemID"
        LEFT JOIN "mapRegions" r ON s."regionID" = r."regionID"
        LEFT JOIN LATERAL (
            SELECT adm_level FROM dotlan_adm_history
            WHERE solar_system_id = c.solar_system_id
            ORDER BY timestamp DESC LIMIT 1
        ) adm ON true
        WHERE c.status = 'active'
          AND {alliance_filter}
        ORDER BY
            CASE WHEN adm.adm_level < 2 THEN 0 ELSE 1 END,
            c.score DESC NULLS LAST
    """, (alliance_value,))

    campaigns = [
        {
            "campaign_id": row['campaign_id'],
            "solar_system_id": row['solar_system_id'],
            "system_name": row['system_name'],
            "region_name": row['region_name'],
            "structure_type": row['structure_type'],
            "defender_name": row['defender_name'],
            "score": round(float(row['score']), 1) if row['score'] else None,
            "status": row['status'],
            "last_updated": row['last_updated'].isoformat() if row['last_updated'] else None,
            "adm_level": round(float(row['adm_level']), 1) if row['adm_level'] else None,
            "vulnerability": row['vulnerability']
        }
        for row in cur.fetchall()
    ]

    critical_count = sum(1 for c in campaigns if c['vulnerability'] == 'critical')

    return {
        "campaigns": campaigns,
        "total_active": len(campaigns),
        "critical_count": critical_count,
        "refresh_rate_seconds": 600  # 10 minutes
    }


def get_dotlan_sov_changes(cur, ctx: EntityContext, days: int = 7) -> dict:
    """Get recent sovereignty changes for entity.

    Returns changes with gained/lost classification.
    """
    # Get the alliance IDs to check
    if ctx.entity_type == EntityType.POWERBLOC:
        alliance_ids = ctx.member_ids
    elif ctx.entity_type == EntityType.CORPORATION:
        alliance_ids = [ctx.alliance_id_for_sov] if ctx.alliance_id_for_sov else []
    else:  # Alliance
        alliance_ids = [ctx.entity_id]

    if not alliance_ids or alliance_ids == [None]:
        return {
            "changes": [],
            "net_gained": 0,
            "net_lost": 0,
            "period_days": days
        }

    cur.execute("""
        SELECT
            sc.id,
            sc.solar_system_id,
            s."solarSystemName" as system_name,
            r."regionName" as region_name,
            sc.change_type,
            sc.old_alliance_name,
            sc.new_alliance_name,
            sc.old_alliance_id,
            sc.new_alliance_id,
            sc.changed_at,
            CASE
                WHEN sc.new_alliance_id = ANY(%s) THEN 'gained'
                WHEN sc.old_alliance_id = ANY(%s) THEN 'lost'
                ELSE 'neutral'
            END as change_direction
        FROM dotlan_sov_changes sc
        LEFT JOIN "mapSolarSystems" s ON sc.solar_system_id = s."solarSystemID"
        LEFT JOIN "mapRegions" r ON s."regionID" = r."regionID"
        WHERE sc.changed_at > NOW() - make_interval(days => %s)
          AND (sc.old_alliance_id = ANY(%s) OR sc.new_alliance_id = ANY(%s))
        ORDER BY sc.changed_at DESC
        LIMIT 50
    """, (alliance_ids, alliance_ids, days, alliance_ids, alliance_ids))

    changes = [
        {
            "id": row['id'],
            "solar_system_id": row['solar_system_id'],
            "system_name": row['system_name'],
            "region_name": row['region_name'],
            "change_type": row['change_type'],
            "old_alliance_name": row['old_alliance_name'],
            "new_alliance_name": row['new_alliance_name'],
            "changed_at": row['changed_at'].isoformat() if row['changed_at'] else None,
            "change_direction": row['change_direction']
        }
        for row in cur.fetchall()
    ]

    net_gained = sum(1 for c in changes if c['change_direction'] == 'gained')
    net_lost = sum(1 for c in changes if c['change_direction'] == 'lost')

    return {
        "changes": changes,
        "net_gained": net_gained,
        "net_lost": net_lost,
        "period_days": days
    }


def get_dotlan_alliance_power(cur, ctx: EntityContext) -> dict:
    """Get alliance power index metrics.

    For Alliance: Own stats + trends
    For Corporation: Parent alliance stats
    For PowerBloc: All member alliances
    """
    # Get the alliance IDs to query
    if ctx.entity_type == EntityType.POWERBLOC:
        alliance_ids = ctx.member_ids
    elif ctx.entity_type == EntityType.CORPORATION:
        alliance_ids = [ctx.alliance_id_for_sov] if ctx.alliance_id_for_sov else []
    else:  # Alliance
        alliance_ids = [ctx.entity_id]

    if not alliance_ids or alliance_ids == [None]:
        return {
            "alliances": [],
            "total_systems": 0,
            "total_members": 0
        }

    cur.execute("""
        WITH latest_stats AS (
            SELECT DISTINCT ON (alliance_id)
                alliance_name,
                alliance_id,
                systems_count,
                member_count,
                corp_count,
                rank_by_systems,
                snapshot_date
            FROM dotlan_alliance_stats
            WHERE alliance_id = ANY(%s)
            ORDER BY alliance_id, snapshot_date DESC
        ),
        previous_stats AS (
            SELECT DISTINCT ON (alliance_id)
                alliance_id,
                systems_count as prev_systems,
                member_count as prev_members
            FROM dotlan_alliance_stats
            WHERE alliance_id = ANY(%s)
              AND snapshot_date <= CURRENT_DATE - 7
            ORDER BY alliance_id, snapshot_date DESC
        )
        SELECT
            l.alliance_name,
            l.alliance_id,
            l.systems_count,
            l.member_count,
            l.corp_count,
            l.rank_by_systems,
            l.snapshot_date,
            COALESCE(l.systems_count - p.prev_systems, 0) as systems_delta,
            COALESCE(l.member_count - p.prev_members, 0) as member_delta
        FROM latest_stats l
        LEFT JOIN previous_stats p ON l.alliance_id = p.alliance_id
        ORDER BY l.systems_count DESC NULLS LAST
    """, (alliance_ids, alliance_ids))

    alliances = [
        {
            "alliance_name": row['alliance_name'],
            "alliance_id": row['alliance_id'],
            "systems_count": row['systems_count'] or 0,
            "member_count": row['member_count'] or 0,
            "corp_count": row['corp_count'] or 0,
            "rank_by_systems": row['rank_by_systems'],
            "systems_delta": row['systems_delta'],
            "member_delta": row['member_delta']
        }
        for row in cur.fetchall()
    ]

    total_systems = sum(a['systems_count'] for a in alliances)
    total_members = sum(a['member_count'] for a in alliances)

    return {
        "alliances": alliances,
        "total_systems": total_systems,
        "total_members": total_members
    }


def get_full_geography_extended(cur, ctx: EntityContext, days: int) -> dict:
    """Get complete geography data including DOTLAN integration.

    Combines existing zKill data with DOTLAN enrichment.
    """
    # Import existing shared queries
    from .shared_queries import get_geography_regions, get_geography_systems, get_geography_home_systems

    # Existing zKill data
    regions = get_geography_regions(cur, ctx, days)
    top_systems = get_geography_systems(cur, ctx, days)
    home_systems = get_geography_home_systems(cur, ctx, days)

    # New DOTLAN data
    live_activity = get_dotlan_live_activity(cur, ctx, days)
    sov_defense = get_dotlan_sov_campaigns(cur, ctx)
    territorial_changes = get_dotlan_sov_changes(cur, ctx, days=7)
    alliance_power = get_dotlan_alliance_power(cur, ctx)

    return {
        # Existing
        "regions": regions,
        "top_systems": top_systems,
        "home_systems": home_systems,
        # New DOTLAN sections
        "live_activity": live_activity,
        "sov_defense": sov_defense,
        "territorial_changes": territorial_changes,
        "alliance_power": alliance_power
    }
