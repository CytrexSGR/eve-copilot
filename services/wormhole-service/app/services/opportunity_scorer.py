"""Opportunity scoring for wormhole hunters."""
from psycopg2.extras import RealDictCursor

from eve_shared import get_db

# Effect descriptions for hunters
EFFECT_INFO = {
    'Wolf-Rayet': {'icon': '🔴', 'bonus': 'Armor HP +, Small Weapons +', 'color': '#ff4444'},
    'Pulsar': {'icon': '⚡', 'bonus': 'Shield Cap +, Sig Radius +', 'color': '#00d4ff'},
    'Magnetar': {'icon': '🧲', 'bonus': 'Damage +, Targeting Range -', 'color': '#ff00ff'},
    'Black Hole': {'icon': '⚫', 'bonus': 'Missile Velocity +, Ship Speed +', 'color': '#444444'},
    'Cataclysmic Variable': {'icon': '💥', 'bonus': 'Local Reps -, Cap +', 'color': '#ffcc00'},
    'Red Giant': {'icon': '🌟', 'bonus': 'Smart Bomb +, Overheat +', 'color': '#ff8800'},
}

# Structure group IDs for intel
STRUCTURE_GROUPS = {
    1657: 'Citadel',      # Astrahus, Fortizar, Keepstar
    1406: 'Engineering',  # Raitaru, Azbel, Sotiyo
    1404: 'Refinery',     # Athanor, Tatara
    365: 'POS',           # Control Tower
}

# Ship class categorization for threat assessment
SHIP_CLASSES = {
    'capital': ['Archon', 'Thanatos', 'Nidhoggur', 'Chimera', 'Apostle', 'Lif', 'Minokawa', 'Ninazu',
                'Revelation', 'Naglfar', 'Moros', 'Phoenix', 'Zirnitra', 'Dagon',
                'Aeon', 'Hel', 'Nyx', 'Wyvern', 'Vendetta', 'Revenant',
                'Avatar', 'Erebus', 'Ragnarok', 'Leviathan', 'Komodo', 'Vanquisher', 'Molok'],
    'battleship': ['Apocalypse', 'Armageddon', 'Abaddon', 'Geddon', 'Nightmare', 'Bhaalgorn', 'Redeemer',
                   'Megathron', 'Hyperion', 'Dominix', 'Kronos', 'Sin', 'Vindicator',
                   'Tempest', 'Typhoon', 'Maelstrom', 'Vargur', 'Panther', 'Machariel',
                   'Raven', 'Scorpion', 'Rokh', 'Golem', 'Widow', 'Rattlesnake', 'Barghest',
                   'Praxis', 'Nestor', 'Leshak', 'Paladin'],
    'cruiser': ['Omen', 'Maller', 'Zealot', 'Devoter', 'Curse', 'Pilgrim', 'Sacrilege', 'Guardian', 'Legion', 'Stratios',
                'Vexor', 'Thorax', 'Ishtar', 'Deimos', 'Phobos', 'Arazu', 'Lachesis', 'Proteus', 'Oneiros',
                'Rupture', 'Stabber', 'Vagabond', 'Muninn', 'Broadsword', 'Huginn', 'Rapier', 'Loki', 'Scimitar',
                'Caracal', 'Moa', 'Cerberus', 'Eagle', 'Onyx', 'Falcon', 'Rook', 'Basilisk', 'Tengu',
                'Gila', 'Orthrus', 'Vedmak', 'Ikitursa', 'Drekavac', 'Osprey'],
    'destroyer': ['Coercer', 'Dragoon', 'Heretic', 'Catalyst', 'Algos', 'Eris', 'Thrasher', 'Talwar', 'Sabre',
                  'Cormorant', 'Corax', 'Flycatcher', 'Jackdaw', 'Hecate', 'Confessor', 'Svipul', 'Kikimora', 'Draugur'],
    'frigate': ['Executioner', 'Punisher', 'Tormentor', 'Crucifier', 'Magnate', 'Slicer', 'Sentinel', 'Malediction', 'Crusader', 'Vengeance', 'Anathema', 'Purifier',
                'Atron', 'Incursus', 'Tristan', 'Maulus', 'Imicus', 'Comet', 'Keres', 'Taranis', 'Ares', 'Ishkur', 'Enyo', 'Helios', 'Nemesis',
                'Slasher', 'Rifter', 'Breacher', 'Vigil', 'Probe', 'Firetail', 'Hyena', 'Claw', 'Stiletto', 'Wolf', 'Jaguar', 'Cheetah', 'Hound',
                'Condor', 'Merlin', 'Kestrel', 'Griffin', 'Heron', 'Hookbill', 'Kitsune', 'Crow', 'Raptor', 'Harpy', 'Hawk', 'Buzzard', 'Manticore',
                'Astero', 'Pacifier', 'Enforcer', 'Damavik', 'Nergal'],
}

# Threat ships that indicate active hunters
THREAT_SHIPS = {'Sabre', 'Flycatcher', 'Heretic', 'Eris', 'Lachesis', 'Arazu', 'Huginn', 'Rapier',
                'Falcon', 'Rook', 'Curse', 'Pilgrim', 'Proteus', 'Loki', 'Tengu', 'Legion', 'Stratios'}


class OpportunityScorer:
    """Score J-Space systems for hunting opportunities."""

    def __init__(self, db=None):
        self.db = db or get_db()

    def _classify_ships(self, ship_names: list) -> dict:
        """Classify ships into categories and identify threats."""
        result = {
            'capital': [],
            'battleship': [],
            'cruiser': [],
            'destroyer': [],
            'frigate': [],
            'other': [],
            'threats': [],
        }
        if not ship_names:
            return result

        for ship in ship_names:
            if not ship:
                continue
            classified = False
            # Check if threat ship
            if ship in THREAT_SHIPS:
                result['threats'].append(ship)
            # Classify by category
            for category, ships in SHIP_CLASSES.items():
                if any(s in ship for s in ships):
                    result[category].append(ship)
                    classified = True
                    break
            if not classified and ship not in ['Capsule', 'Shuttle']:
                result['other'].append(ship)

        return result

    def _get_resident_details(self, conn, system_ids: list) -> dict:
        """Get detailed resident info for systems."""
        if not system_ids:
            return {}

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    wr.system_id,
                    wr.corporation_id,
                    COALESCE(c.corporation_name, 'Unknown') as corp_name,
                    COALESCE(c.ticker, '???') as ticker,
                    wr.kill_count,
                    wr.loss_count,
                    wr.last_activity
                FROM wormhole_residents wr
                LEFT JOIN corporations c ON wr.corporation_id = c.corporation_id
                WHERE wr.system_id = ANY(%s)
                ORDER BY (wr.kill_count + wr.loss_count) DESC
            """, (system_ids,))

            residents = {}
            for row in cur.fetchall():
                sys_id = row['system_id']
                if sys_id not in residents:
                    residents[sys_id] = []
                # Only keep top 5 per system
                if len(residents[sys_id]) < 5:
                    corp_id = row['corporation_id']
                    residents[sys_id].append({
                        'corporation_id': corp_id,
                        'name': row['corp_name'],
                        'ticker': row['ticker'],
                        'kills': row['kill_count'],
                        'losses': row['loss_count'],
                        'last_seen': row['last_activity'].isoformat() if row['last_activity'] else None,
                        'is_npc': corp_id < 98000000  # NPC corps have lower IDs
                    })
            return residents

    def _get_system_effects(self, conn, system_ids: list) -> dict:
        """Get system effects from imported anoik.is data."""
        if not system_ids:
            return {}

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT system_id, effect_name, effect_class
                FROM wormhole_system_effects
                WHERE system_id = ANY(%s) AND effect_name IS NOT NULL
            """, (system_ids,))

            effects = {}
            for row in cur.fetchall():
                effect_name = row['effect_name']
                effect_info = EFFECT_INFO.get(effect_name, {})
                effects[row['system_id']] = {
                    'name': effect_name,
                    'icon': effect_info.get('icon', '❓'),
                    'bonus': effect_info.get('bonus', ''),
                    'color': effect_info.get('color', '#888888'),
                }
            return effects

    def _get_prime_time(self, conn, system_ids: list) -> dict:
        """Analyze kill timestamps to determine prime time activity."""
        if not system_ids:
            return {}

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Get hourly distribution of kills in last 30 days
            cur.execute("""
                SELECT
                    solar_system_id as system_id,
                    EXTRACT(HOUR FROM killmail_time) as hour,
                    COUNT(*) as kills
                FROM killmails
                WHERE solar_system_id = ANY(%s)
                  AND killmail_time > NOW() - INTERVAL '30 days'
                GROUP BY solar_system_id, EXTRACT(HOUR FROM killmail_time)
            """, (system_ids,))

            # Bucket into timezones:
            # EU Prime: 17:00-23:00 UTC
            # US Prime: 00:00-06:00 UTC
            # AU Prime: 08:00-14:00 UTC
            system_hours = {}
            for row in cur.fetchall():
                sys_id = row['system_id']
                if sys_id not in system_hours:
                    system_hours[sys_id] = {'EU': 0, 'US': 0, 'AU': 0, 'other': 0}

                hour = int(row['hour'])
                kills = row['kills']

                if 17 <= hour <= 23:
                    system_hours[sys_id]['EU'] += kills
                elif 0 <= hour <= 6:
                    system_hours[sys_id]['US'] += kills
                elif 8 <= hour <= 14:
                    system_hours[sys_id]['AU'] += kills
                else:
                    system_hours[sys_id]['other'] += kills

            # Determine dominant timezone
            result = {}
            for sys_id, hours in system_hours.items():
                total = sum(hours.values())
                if total == 0:
                    continue

                dominant = max(hours.items(), key=lambda x: x[1] if x[0] != 'other' else 0)
                result[sys_id] = {
                    'dominant': dominant[0] if dominant[1] > 0 else 'Unknown',
                    'eu_pct': round(hours['EU'] / total * 100) if total else 0,
                    'us_pct': round(hours['US'] / total * 100) if total else 0,
                    'au_pct': round(hours['AU'] / total * 100) if total else 0,
                }
            return result

    def _get_recent_kills(self, conn, system_ids: list) -> dict:
        """Get recent kills for each system."""
        if not system_ids:
            return {}

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    k.solar_system_id as system_id,
                    k.killmail_id,
                    k.killmail_time,
                    COALESCE(k.ship_value, 0) as total_value,
                    it."typeName" as ship_name,
                    ig."groupName" as ship_group,
                    COALESCE(
                        NULLIF(k.victim_character_name, ''),
                        ch.character_name,
                        cnc.character_name,
                        CASE WHEN it."groupID" IN (1657, 1406, 1404, 365) THEN 'Structure' ELSE NULL END
                    ) as victim_name,
                    COALESCE(c.corporation_name, 'Unknown') as victim_corp
                FROM killmails k
                JOIN "invTypes" it ON k.ship_type_id = it."typeID"
                JOIN "invGroups" ig ON it."groupID" = ig."groupID"
                LEFT JOIN corporations c ON k.victim_corporation_id = c.corporation_id
                LEFT JOIN characters ch ON k.victim_character_id = ch.character_id
                LEFT JOIN character_name_cache cnc ON k.victim_character_id = cnc.character_id
                WHERE k.solar_system_id = ANY(%s)
                  AND k.killmail_time > NOW() - INTERVAL '7 days'
                ORDER BY k.killmail_time DESC
            """, (system_ids,))

            kills = {}
            for row in cur.fetchall():
                sys_id = row['system_id']
                if sys_id not in kills:
                    kills[sys_id] = []
                # Keep top 10 per system
                if len(kills[sys_id]) < 10:
                    kills[sys_id].append({
                        'killmail_id': row['killmail_id'],
                        'time': row['killmail_time'].isoformat() if row['killmail_time'] else None,
                        'value': float(row['total_value'] or 0),
                        'ship': row['ship_name'],
                        'ship_class': row['ship_group'],
                        'victim': row['victim_name'] or 'Unknown',
                        'corp': row['victim_corp'] or 'Unknown',
                    })
            return kills

    def _get_structure_intel(self, conn, system_ids: list) -> dict:
        """Get structure kills/losses in systems."""
        if not system_ids:
            return {}

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Get structure kills in last 30 days
            cur.execute("""
                SELECT
                    k.solar_system_id as system_id,
                    it."typeName" as structure_type,
                    ig."groupID" as group_id,
                    k.killmail_time,
                    COALESCE(k.ship_value, 0) as total_value
                FROM killmails k
                JOIN "invTypes" it ON k.ship_type_id = it."typeID"
                JOIN "invGroups" ig ON it."groupID" = ig."groupID"
                WHERE k.solar_system_id = ANY(%s)
                  AND ig."groupID" IN (1657, 1406, 1404, 365)
                  AND k.killmail_time > NOW() - INTERVAL '30 days'
                ORDER BY k.killmail_time DESC
            """, (system_ids,))

            structures = {}
            for row in cur.fetchall():
                sys_id = row['system_id']
                if sys_id not in structures:
                    structures[sys_id] = {
                        'total_lost': 0,
                        'total_value': 0,
                        'recent': [],
                        'citadels': 0,
                        'engineering': 0,
                        'refineries': 0,
                    }

                structures[sys_id]['total_lost'] += 1
                structures[sys_id]['total_value'] += float(row['total_value'] or 0)

                group_id = row['group_id']
                if group_id == 1657:
                    structures[sys_id]['citadels'] += 1
                elif group_id == 1406:
                    structures[sys_id]['engineering'] += 1
                elif group_id == 1404:
                    structures[sys_id]['refineries'] += 1

                if len(structures[sys_id]['recent']) < 3:
                    structures[sys_id]['recent'].append({
                        'type': row['structure_type'],
                        'time': row['killmail_time'].isoformat() if row['killmail_time'] else None,
                        'value': float(row['total_value'] or 0),
                    })
            return structures

    def _get_hunter_activity(self, conn, system_ids: list) -> dict:
        """Get which alliances/coalitions are hunting in these systems (attackers on kills)."""
        if not system_ids:
            return {}

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Get attacker alliances from kills in these systems (last 30 days)
            cur.execute("""
                WITH attacker_alliances AS (
                    SELECT
                        k.solar_system_id as system_id,
                        ka.alliance_id,
                        COUNT(*) as kill_count
                    FROM killmails k
                    JOIN killmail_attackers ka ON k.killmail_id = ka.killmail_id
                    WHERE k.solar_system_id = ANY(%s)
                      AND k.killmail_time > NOW() - INTERVAL '30 days'
                      AND ka.alliance_id IS NOT NULL
                      AND ka.alliance_id > 0
                    GROUP BY k.solar_system_id, ka.alliance_id
                    HAVING COUNT(*) >= 2
                )
                SELECT
                    aa.system_id,
                    aa.alliance_id,
                    COALESCE(anc.alliance_name, 'Unknown') as alliance_name,
                    aa.kill_count
                FROM attacker_alliances aa
                LEFT JOIN alliance_name_cache anc ON aa.alliance_id = anc.alliance_id
                ORDER BY aa.system_id, aa.kill_count DESC
            """, (system_ids,))

            hunters = {}
            for row in cur.fetchall():
                sys_id = row['system_id']
                if sys_id not in hunters:
                    hunters[sys_id] = []
                # Keep top 5 hunting alliances per system
                if len(hunters[sys_id]) < 5:
                    hunters[sys_id].append({
                        'alliance_id': row['alliance_id'],
                        'name': row['alliance_name'],
                        'kills': row['kill_count'],
                    })
            return hunters

    def _get_resident_affiliations(self, conn, system_ids: list) -> dict:
        """Get which alliances/coalitions the residents belong to."""
        if not system_ids:
            return {}

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Get resident corps' alliance affiliations
            cur.execute("""
                SELECT
                    wr.system_id,
                    c.alliance_id,
                    COALESCE(anc.alliance_name, 'Unknown') as alliance_name,
                    COUNT(DISTINCT wr.corporation_id) as corp_count,
                    SUM(wr.kill_count) as total_kills
                FROM wormhole_residents wr
                JOIN corporations c ON wr.corporation_id = c.corporation_id
                LEFT JOIN alliance_name_cache anc ON c.alliance_id = anc.alliance_id
                WHERE wr.system_id = ANY(%s)
                  AND wr.corporation_id >= 98000000
                  AND c.alliance_id IS NOT NULL
                  AND c.alliance_id > 0
                GROUP BY wr.system_id, c.alliance_id, anc.alliance_name
                ORDER BY wr.system_id, total_kills DESC
            """, (system_ids,))

            affiliations = {}
            for row in cur.fetchall():
                sys_id = row['system_id']
                if sys_id not in affiliations:
                    affiliations[sys_id] = []
                # Keep top 5 alliances per system
                if len(affiliations[sys_id]) < 5:
                    affiliations[sys_id].append({
                        'alliance_id': row['alliance_id'],
                        'name': row['alliance_name'],
                        'corps': row['corp_count'],
                        'kills': row['total_kills'],
                    })
            return affiliations

    def get_opportunities(
        self,
        wh_class: int = None,
        min_activity: int = 3,
        limit: int = 20
    ) -> list[dict]:
        """
        Get hunting opportunity board with detailed intel.

        Scoring factors:
        - Activity level (more PvE = more targets)
        - Resident strength (smaller = easier)
        - Recent activity (recent = active now)
        """
        with self.db.connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                class_filter = "AND wa.wormhole_class = %s" if wh_class else ""
                params = [min_activity]
                if wh_class:
                    params.append(wh_class)
                params.append(limit)

                cur.execute(f"""
                    WITH system_residents AS (
                        SELECT
                            wr.system_id,
                            COUNT(DISTINCT wr.corporation_id) FILTER (WHERE wr.corporation_id >= 98000000) as corp_count,
                            SUM(wr.kill_count + wr.loss_count) FILTER (WHERE wr.corporation_id >= 98000000) as total_activity,
                            MAX(wr.last_activity) as last_resident_activity
                        FROM wormhole_residents wr
                        GROUP BY wr.system_id
                    ),
                    recent_ships AS (
                        SELECT
                            k.solar_system_id as system_id,
                            array_agg(DISTINCT it."typeName" ORDER BY it."typeName") FILTER (WHERE it."typeName" IS NOT NULL) as ship_types
                        FROM killmails k
                        JOIN "invTypes" it ON k.ship_type_id = it."typeID"
                        WHERE k.solar_system_id >= 31000000 AND k.solar_system_id < 32000000
                          AND k.killmail_time > NOW() - INTERVAL '7 days'
                        GROUP BY k.solar_system_id
                    ),
                    system_statics AS (
                        SELECT
                            st.system_id,
                            array_agg(
                                json_build_object(
                                    'code', st.type_code,
                                    'dest', CASE
                                        WHEN st.target_class = 7 THEN 'Highsec'
                                        WHEN st.target_class = 8 THEN 'Lowsec'
                                        WHEN st.target_class = 9 THEN 'Nullsec'
                                        WHEN st.target_class BETWEEN 1 AND 6 THEN 'C' || st.target_class
                                        ELSE 'Unknown'
                                    END
                                )
                                ORDER BY st.type_code
                            ) as statics_info
                        FROM v_system_statics st
                        GROUP BY st.system_id
                    )
                    SELECT
                        wa.system_id,
                        ss."solarSystemName" as system_name,
                        wa.wormhole_class,
                        sst.statics_info,
                        wa.kills_7d,
                        wa.kills_24h,
                        wa.isk_destroyed_7d,
                        wa.isk_destroyed_24h,
                        wa.last_kill_time,
                        COALESCE(sr.corp_count, 0) as resident_corps,
                        COALESCE(sr.total_activity, 0) as resident_activity,
                        rs.ship_types,
                        -- Individual score components
                        LEAST(40, wa.kills_7d * 2)::int as activity_score,
                        CASE
                            WHEN wa.last_kill_time > NOW() - INTERVAL '2 hours' THEN 30
                            WHEN wa.last_kill_time > NOW() - INTERVAL '6 hours' THEN 25
                            WHEN wa.last_kill_time > NOW() - INTERVAL '24 hours' THEN 20
                            WHEN wa.last_kill_time > NOW() - INTERVAL '3 days' THEN 10
                            ELSE 5
                        END as recency_score,
                        CASE
                            WHEN COALESCE(sr.corp_count, 0) = 0 THEN 10
                            WHEN COALESCE(sr.corp_count, 0) <= 2 THEN 30
                            WHEN COALESCE(sr.corp_count, 0) <= 5 THEN 20
                            ELSE 10
                        END as weakness_score,
                        -- Opportunity Score (0-100)
                        LEAST(100, GREATEST(0,
                            LEAST(40, wa.kills_7d * 2) +
                            CASE
                                WHEN wa.last_kill_time > NOW() - INTERVAL '2 hours' THEN 30
                                WHEN wa.last_kill_time > NOW() - INTERVAL '6 hours' THEN 25
                                WHEN wa.last_kill_time > NOW() - INTERVAL '24 hours' THEN 20
                                WHEN wa.last_kill_time > NOW() - INTERVAL '3 days' THEN 10
                                ELSE 5
                            END +
                            CASE
                                WHEN COALESCE(sr.corp_count, 0) = 0 THEN 10
                                WHEN COALESCE(sr.corp_count, 0) <= 2 THEN 30
                                WHEN COALESCE(sr.corp_count, 0) <= 5 THEN 20
                                ELSE 10
                            END
                        ))::int as opportunity_score,
                        -- Difficulty rating
                        CASE
                            WHEN COALESCE(sr.corp_count, 0) <= 2 AND COALESCE(sr.total_activity, 0) < 20 THEN 'EASY'
                            WHEN COALESCE(sr.corp_count, 0) <= 5 THEN 'MEDIUM'
                            ELSE 'HARD'
                        END as difficulty
                    FROM wormhole_system_activity wa
                    JOIN "mapSolarSystems" ss ON wa.system_id = ss."solarSystemID"
                    LEFT JOIN system_statics sst ON wa.system_id = sst.system_id
                    LEFT JOIN system_residents sr ON wa.system_id = sr.system_id
                    LEFT JOIN recent_ships rs ON wa.system_id = rs.system_id
                    WHERE wa.kills_7d >= %s
                      {class_filter}
                    ORDER BY opportunity_score DESC, wa.last_kill_time DESC
                    LIMIT %s
                """, tuple(params))

                rows = cur.fetchall()
                system_ids = [r['system_id'] for r in rows]

            # Get all detailed info in parallel queries
            resident_details = self._get_resident_details(conn, system_ids)
            system_effects = self._get_system_effects(conn, system_ids)
            prime_times = self._get_prime_time(conn, system_ids)
            recent_kills = self._get_recent_kills(conn, system_ids)
            structure_intel = self._get_structure_intel(conn, system_ids)
            hunter_activity = self._get_hunter_activity(conn, system_ids)
            resident_affiliations = self._get_resident_affiliations(conn, system_ids)

            results = []
            for row in rows:
                ship_breakdown = self._classify_ships(row['ship_types'] or [])

                # Parse statics info
                statics = []
                if row['statics_info']:
                    for s in row['statics_info']:
                        statics.append({
                            'code': s['code'],
                            'destination': s['dest'] or 'Unknown'
                        })

                sys_id = row['system_id']
                results.append({
                    'system_id': sys_id,
                    'system_name': row['system_name'],
                    'wormhole_class': row['wormhole_class'],
                    'statics': statics,
                    'opportunity_score': row['opportunity_score'],
                    'score_breakdown': {
                        'activity': row['activity_score'],
                        'recency': row['recency_score'],
                        'weakness': row['weakness_score'],
                    },
                    'difficulty': row['difficulty'],
                    'kills_7d': row['kills_7d'],
                    'kills_24h': row['kills_24h'],
                    'isk_destroyed_7d': float(row['isk_destroyed_7d'] or 0),
                    'isk_destroyed_24h': float(row['isk_destroyed_24h'] or 0),
                    'last_activity': row['last_kill_time'].isoformat() if row['last_kill_time'] else None,
                    'is_hot': row['kills_24h'] >= 3,  # "Hot" if 3+ kills in 24h
                    'resident_corps': row['resident_corps'],
                    'residents': resident_details.get(sys_id, []),
                    'ships': ship_breakdown,
                    'recent_ships': row['ship_types'] or [],  # Keep for backwards compat
                    # New features
                    'effect': system_effects.get(sys_id),
                    'prime_time': prime_times.get(sys_id),
                    'recent_kills': recent_kills.get(sys_id, []),
                    'structures': structure_intel.get(sys_id),
                    # Power bloc intel
                    'hunters': hunter_activity.get(sys_id, []),
                    'resident_alliances': resident_affiliations.get(sys_id, []),
                })

            return results
