"""
Equipment Intelligence Service - Weapons, Tank, and Cargo Analysis.

Analyzes killmail item data to provide insights on:
- Weapon systems lost (high slots, flag 27-34)
- Tank modules lost (mid slots, flag 19-26)
- Cargo hold contents (flag 5)
"""

import logging
from typing import Dict, List, Any

from app.database import db_cursor
from app.services.intelligence.esi_utils import resolve_type_info_via_esi

logger = logging.getLogger(__name__)


class EquipmentIntelligenceService:
    """Equipment intelligence analysis using killmail item data."""

    # Damage type mappings for weapon groups
    WEAPON_DAMAGE_PROFILES = {
        # Energy weapons (EM/Thermal)
        "beam laser": {"em": 0.5, "thermal": 0.5, "kinetic": 0, "explosive": 0},
        "pulse laser": {"em": 0.5, "thermal": 0.5, "kinetic": 0, "explosive": 0},
        "mining laser": {"em": 0, "thermal": 0, "kinetic": 0, "explosive": 0},
        # Projectile weapons (Explosive/Kinetic)
        "autocannon": {"em": 0, "thermal": 0, "kinetic": 0.5, "explosive": 0.5},
        "artillery": {"em": 0, "thermal": 0, "kinetic": 0.5, "explosive": 0.5},
        # Hybrid weapons (Kinetic/Thermal)
        "blaster": {"em": 0, "thermal": 0.5, "kinetic": 0.5, "explosive": 0},
        "railgun": {"em": 0, "thermal": 0.5, "kinetic": 0.5, "explosive": 0},
        # Missiles - varied by type
        "missile launcher": {"em": 0.25, "thermal": 0.25, "kinetic": 0.25, "explosive": 0.25},
        "rocket launcher": {"em": 0.25, "thermal": 0.25, "kinetic": 0.25, "explosive": 0.25},
        "torpedo launcher": {"em": 0.25, "thermal": 0.25, "kinetic": 0.25, "explosive": 0.25},
        "cruise missile": {"em": 0.25, "thermal": 0.25, "kinetic": 0.25, "explosive": 0.25},
        "heavy assault missile": {"em": 0.25, "thermal": 0.25, "kinetic": 0.25, "explosive": 0.25},
        "heavy missile": {"em": 0.25, "thermal": 0.25, "kinetic": 0.25, "explosive": 0.25},
        "light missile": {"em": 0.25, "thermal": 0.25, "kinetic": 0.25, "explosive": 0.25},
        # Drones
        "drone": {"em": 0.25, "thermal": 0.25, "kinetic": 0.25, "explosive": 0.25},
    }

    # Tank module keywords for filtering
    TANK_MODULE_KEYWORDS = [
        "hardener", "amplifier", "extender", "booster", "repairer",
        "resistance", "ward", "invulnerability", "membrane", "plating", "energized"
    ]

    # Resist type mappings for common tank modules
    RESIST_MAPPINGS = {
        "em": ["em ward", "em shield", "em armor", "em amplifier", "em membrane", "em plating", "em coating"],
        "thermal": ["thermal shield", "thermal armor", "thermal dissipation", "thermal amplifier", "thermal membrane", "thermal plating", "thermal coating"],
        "kinetic": ["kinetic shield", "kinetic armor", "kinetic deflection", "kinetic amplifier", "kinetic membrane", "kinetic plating", "kinetic coating"],
        "explosive": ["explosive shield", "explosive armor", "explosive deflection", "explosive amplifier", "explosive membrane", "explosive plating", "explosive coating"],
        "omni": ["invulnerability", "adaptive", "multispectrum", "reactive armor"]
    }

    # Strategic classification keywords for cargo
    STRATEGIC_CATEGORIES = {
        "fuel": ["isotope", "liquid ozone", "strontium", "fuel block", "nitrogen", "helium"],
        "minerals": ["tritanium", "pyerite", "mexallon", "isogen", "nocxium", "zydrine", "megacyte", "morphite"],
        "moon_materials": ["moon material", "platinum", "cadmium", "technetium", "hafnium", "tungsten", "scandium",
                          "composite", "polymer", "ceramic", "sylramic", "ferrogel", "fermionic", "crystallite",
                          "neo mercurite", "dysporite", "promethium", "thulium", "titanium chromide"],
        "gas": ["fullerite", "harvestable cloud", "cytoserocin", "mykoserocin", "c-320", "c-540", "c-72", "c-84"],
        "salvage": ["salvaged material", "logic circuit", "trigger unit", "power circuit", "fried interface",
                   "burned logic", "tripped power", "smashed trigger", "armor plate", "ward console", "capacitor console"],
        "construction": ["capital component", "structure component", "upwell", "citadel", "engineering complex",
                        "refinery", "standup", "moon drill"],
        "ammo_charges": ["missile", "projectile ammo", "hybrid charge", "frequency crystal", "script",
                        "nanite repair paste", "cap booster", "scanner probe", "combat probe",
                        "interdiction probe", "warp disrupt probe", "fuel block", "stront",
                        "bomb launcher", "guided bomb", "void bomb", "electron bomb", "concussion bomb"],
        "deployables": ["mobile tractor", "mobile depot", "mobile cyno", "mobile scan", "mobile warp",
                       "mobile micro jump", "deployable"],
        "drones": ["drone", "fighter", "mining drone", "salvage drone", "combat drone", "sentry drone"],
        "implants": ["implant", "accelerator", "hardwiring", "cyberimplant", "dose",
                    "blue pill", "exile", "drop", "crash", "mindflood", "x-instinct", "frentix",
                    "synth", "strong", "standard", "improved", "cerebral", "agency"],
        "commodities": ["overseer", "personal effect", "encrypted bond", "bounty", "data", "filament",
                       "mutaplasmid", "triglavian", "abyssal", "rogue drone analysis", "survey database",
                       "commodit", "decryptor", "blueprint"],
        "ships": ["frigate", "destroyer", "cruiser", "battlecruiser", "battleship", "carrier",
                 "dreadnought", "titan", "supercarrier", "force auxiliary", "freighter", "jump freighter"],
        "modules": ["module", "hardener", "repairer", "booster", "extender", "amplifier", "neutralizer",
                   "shield booster", "armor repair", "propulsion", "afterburner", "microwarpdrive",
                   "warp scrambler", "warp disruptor", "stasis web", "sensor", "tracking", "gyrostabilizer",
                   "ballistic control", "damage control", "capacitor", "power diagnostic", "reactor control"]
    }

    def get_weapons_lost(self, alliance_id: int, days: int = 7, limit: int = 20) -> Dict[str, Any]:
        """Analyze weapon systems lost by an alliance."""
        with db_cursor() as cur:
            cur.execute("""
                SELECT
                    ki.item_type_id,
                    t."typeName" as weapon_name,
                    g."groupName" as weapon_group,
                    SUM(ki.quantity) as total_lost,
                    COUNT(DISTINCT ki.killmail_id) as kills_with_weapon,
                    COALESCE(AVG(mpc.average_price), 0) as avg_price
                FROM killmail_items ki
                JOIN killmails k ON ki.killmail_id = k.killmail_id
                LEFT JOIN "invTypes" t ON ki.item_type_id = t."typeID"
                LEFT JOIN "invGroups" g ON t."groupID" = g."groupID"
                LEFT JOIN "invCategories" c ON g."categoryID" = c."categoryID"
                LEFT JOIN market_prices_cache mpc ON ki.item_type_id = mpc.type_id
                WHERE k.victim_alliance_id = %s
                  AND k.killmail_time >= NOW() - INTERVAL '%s days'
                  AND ki.flag >= 27 AND ki.flag <= 34
                  AND c."categoryName" ILIKE '%%module%%'
                  AND (
                      g."groupName" ILIKE '%%laser%%'
                      OR g."groupName" ILIKE '%%cannon%%'
                      OR g."groupName" ILIKE '%%railgun%%'
                      OR g."groupName" ILIKE '%%blaster%%'
                      OR g."groupName" ILIKE '%%artillery%%'
                      OR g."groupName" ILIKE '%%missile%%'
                      OR g."groupName" ILIKE '%%rocket%%'
                      OR g."groupName" ILIKE '%%torpedo%%'
                      OR g."groupName" ILIKE '%%launcher%%'
                  )
                GROUP BY ki.item_type_id, t."typeName", g."groupName"
                ORDER BY total_lost DESC
                LIMIT %s
            """, (alliance_id, days, limit))

            weapons = []
            damage_profile = {"em": 0.0, "thermal": 0.0, "kinetic": 0.0, "explosive": 0.0}
            total_weapons = 0

            for row in cur.fetchall():
                type_id = row["item_type_id"]
                weapon_name = row["weapon_name"] or f"Unknown ({type_id})"
                weapon_group = (row["weapon_group"] or "").lower()
                total_lost = row["total_lost"] or 0
                kills_with_weapon = row["kills_with_weapon"] or 0
                avg_price = float(row["avg_price"] or 0)

                weapons.append({
                    "type_id": type_id,
                    "weapon_name": weapon_name,
                    "weapon_group": row["weapon_group"] or "Unknown",
                    "total_lost": total_lost,
                    "kills_with_weapon": kills_with_weapon,
                    "avg_price": avg_price,
                    "total_isk_lost": total_lost * avg_price
                })

                # Calculate damage profile contribution
                total_weapons += total_lost
                for weapon_key, profile in self.WEAPON_DAMAGE_PROFILES.items():
                    if weapon_key in weapon_group:
                        for dmg_type, ratio in profile.items():
                            damage_profile[dmg_type] += total_lost * ratio
                        break

            # Normalize damage profile to percentages
            if total_weapons > 0:
                for dmg_type in damage_profile:
                    damage_profile[dmg_type] = round(
                        (damage_profile[dmg_type] / total_weapons) * 100, 1
                    )

            # Determine primary and secondary damage types
            sorted_damage = sorted(damage_profile.items(), key=lambda x: -x[1])
            primary_damage_type = sorted_damage[0][0] if sorted_damage else "mixed"
            secondary_damage_type = sorted_damage[1][0] if len(sorted_damage) > 1 else None

            # Calculate weapon class distribution
            weapon_class_counts = {
                "laser": 0, "projectile": 0, "hybrid": 0,
                "missile": 0, "drone": 0, "other": 0
            }
            for weapon in weapons:
                weapon_group = (weapon.get("weapon_group") or "").lower()
                if "laser" in weapon_group:
                    weapon_class_counts["laser"] += weapon["total_lost"]
                elif "autocannon" in weapon_group or "artillery" in weapon_group or "projectile" in weapon_group:
                    weapon_class_counts["projectile"] += weapon["total_lost"]
                elif "blaster" in weapon_group or "railgun" in weapon_group or "hybrid" in weapon_group:
                    weapon_class_counts["hybrid"] += weapon["total_lost"]
                elif "missile" in weapon_group or "rocket" in weapon_group or "torpedo" in weapon_group or "launcher" in weapon_group:
                    weapon_class_counts["missile"] += weapon["total_lost"]
                elif "drone" in weapon_group:
                    weapon_class_counts["drone"] += weapon["total_lost"]
                else:
                    weapon_class_counts["other"] += weapon["total_lost"]

            # Convert to percentages
            weapon_class_distribution = {}
            for wc, count in weapon_class_counts.items():
                weapon_class_distribution[wc] = round((count / total_weapons) * 100, 1) if total_weapons > 0 else 0.0

            # Determine primary weapon class
            primary_weapon_class = max(weapon_class_counts, key=weapon_class_counts.get) if total_weapons > 0 else "other"

            # Generate counter-tank advice
            weapon_class_advice = {
                "laser": "Fit EM/Thermal hardeners - enemy uses laser weapons",
                "projectile": "Fit Explosive/Kinetic hardeners - enemy uses projectile weapons",
                "hybrid": "Fit Kinetic/Thermal hardeners - enemy uses hybrid weapons",
                "missile": "Fit omni-tank - enemy uses missiles (selectable damage)",
                "drone": "Fit omni-tank - enemy uses drones (mixed damage)",
                "other": "Fit omni-tank - enemy uses mixed weapon types"
            }

            return {
                "weapons": weapons,
                "damage_profile": damage_profile,
                "primary_damage_type": primary_damage_type,
                "secondary_damage_type": secondary_damage_type,
                "weapon_class_distribution": weapon_class_distribution,
                "primary_weapon_class": primary_weapon_class,
                "counter_tank_advice": weapon_class_advice.get(primary_weapon_class, weapon_class_advice["other"]),
                "total_weapons_lost": total_weapons
            }

    def get_tank_profile(self, alliance_id: int, days: int = 7, limit: int = 20) -> Dict[str, Any]:
        """Analyze tank modules lost by an alliance."""
        with db_cursor() as cur:
            # Build ILIKE conditions for tank modules
            ilike_conditions = " OR ".join([f"t.\"typeName\" ILIKE '%%{kw}%%'" for kw in self.TANK_MODULE_KEYWORDS])

            cur.execute(f"""
                SELECT
                    ki.item_type_id,
                    t."typeName" as module_name,
                    g."groupName" as module_group,
                    SUM(ki.quantity) as total_lost,
                    COUNT(DISTINCT ki.killmail_id) as kills_with_module,
                    COALESCE(AVG(mpc.average_price), 0) as avg_price
                FROM killmail_items ki
                JOIN killmails k ON ki.killmail_id = k.killmail_id
                LEFT JOIN "invTypes" t ON ki.item_type_id = t."typeID"
                LEFT JOIN "invGroups" g ON t."groupID" = g."groupID"
                LEFT JOIN market_prices_cache mpc ON ki.item_type_id = mpc.type_id
                WHERE k.victim_alliance_id = %s
                  AND k.killmail_time >= NOW() - INTERVAL '%s days'
                  AND ki.flag >= 19 AND ki.flag <= 26
                  AND ({ilike_conditions})
                GROUP BY ki.item_type_id, t."typeName", g."groupName"
                ORDER BY total_lost DESC
                LIMIT %s
            """, (alliance_id, days, limit))

            modules = []
            shield_count = 0
            armor_count = 0
            active_count = 0
            passive_count = 0
            resist_coverage = {"em": 0, "thermal": 0, "kinetic": 0, "explosive": 0}
            total_modules = 0

            active_keywords = ["hardener", "booster", "repairer", "invulnerability"]
            passive_keywords = ["extender", "amplifier", "membrane", "plating"]

            for row in cur.fetchall():
                type_id = row["item_type_id"]
                module_name = (row["module_name"] or f"Unknown ({type_id})").lower()
                module_group = row["module_group"] or "Unknown"
                total_lost = row["total_lost"] or 0
                kills_with_module = row["kills_with_module"] or 0
                avg_price = float(row["avg_price"] or 0)

                modules.append({
                    "type_id": type_id,
                    "module_name": row["module_name"] or f"Unknown ({type_id})",
                    "module_group": module_group,
                    "total_lost": total_lost,
                    "kills_with_module": kills_with_module,
                    "avg_price": avg_price,
                    "total_isk_lost": total_lost * avg_price
                })

                total_modules += total_lost

                # Classify as shield or armor
                if any(kw in module_name for kw in ["shield", "amplifier", "extender", "ward", "invulnerability"]):
                    shield_count += total_lost
                elif any(kw in module_name for kw in ["armor", "membrane", "plating", "energized", "repairer"]):
                    armor_count += total_lost

                # Classify as active or passive
                if any(kw in module_name for kw in active_keywords):
                    active_count += total_lost
                elif any(kw in module_name for kw in passive_keywords):
                    passive_count += total_lost

                # Track resist coverage
                for resist_type, keywords in self.RESIST_MAPPINGS.items():
                    if any(kw in module_name for kw in keywords):
                        if resist_type == "omni":
                            for r in resist_coverage:
                                resist_coverage[r] += total_lost
                        else:
                            resist_coverage[resist_type] += total_lost

            # Calculate percentages
            total_tank = shield_count + armor_count
            shield_percent = round((shield_count / total_tank) * 100, 1) if total_tank > 0 else 0
            armor_percent = round((armor_count / total_tank) * 100, 1) if total_tank > 0 else 0

            total_active_passive = active_count + passive_count
            active_percent = round((active_count / total_active_passive) * 100, 1) if total_active_passive > 0 else 0
            passive_percent = round((passive_count / total_active_passive) * 100, 1) if total_active_passive > 0 else 0

            # Detect resist gap
            total_resist_coverage = sum(resist_coverage.values())
            if total_modules > 0 and total_resist_coverage > 0:
                resist_gap = min(resist_coverage, key=resist_coverage.get)
                resist_gap_value = resist_coverage[resist_gap]
                resist_gap_severity = round((resist_gap_value / total_resist_coverage) * 100, 1)
                resist_breakdown_pct = {
                    k: round((v / total_resist_coverage) * 100, 1)
                    for k, v in resist_coverage.items()
                }
            else:
                resist_gap = "unknown"
                resist_gap_value = 0
                resist_gap_severity = 0
                resist_breakdown_pct = {"em": 25.0, "thermal": 25.0, "kinetic": 25.0, "explosive": 25.0}

            # Generate counter-damage advice
            counter_advice = {
                "em": "Use EM damage weapons (lasers) - enemy weak to EM",
                "thermal": "Use Thermal damage (lasers, hybrids) - enemy weak to Thermal",
                "kinetic": "Use Kinetic damage (hybrids, missiles) - enemy weak to Kinetic",
                "explosive": "Use Explosive damage (projectiles, missiles) - enemy weak to Explosive",
                "unknown": "Insufficient data - use mixed damage"
            }

            # 5-value doctrine classification
            if shield_percent > 70:
                doctrine = "heavy_shield"
            elif shield_percent > 55:
                doctrine = "shield_leaning"
            elif armor_percent > 70:
                doctrine = "heavy_armor"
            elif armor_percent > 55:
                doctrine = "armor_leaning"
            else:
                doctrine = "mixed"

            return {
                "top_modules": modules,
                "shield_percent": shield_percent,
                "armor_percent": armor_percent,
                "active_percent": active_percent,
                "passive_percent": passive_percent,
                "doctrine": doctrine,
                "resist_breakdown": resist_breakdown_pct,
                "resist_gap": resist_gap,
                "resist_gap_value": resist_gap_value,
                "resist_gap_severity": resist_gap_severity,
                "counter_damage_advice": counter_advice.get(resist_gap, counter_advice["unknown"]),
                "total_tank_modules": total_modules
            }

    def get_cargo_intel(self, alliance_id: int, days: int = 7, limit: int = 50) -> Dict[str, Any]:
        """Analyze cargo hold contents lost by an alliance."""
        with db_cursor() as cur:
            cur.execute("""
                SELECT
                    ki.item_type_id,
                    t."typeName" as item_name,
                    g."groupName" as item_group,
                    c."categoryName" as item_category,
                    SUM(ki.quantity) as total_lost,
                    COUNT(DISTINCT ki.killmail_id) as kills_with_item,
                    COALESCE(AVG(mpc.average_price), 0) as avg_price
                FROM killmail_items ki
                JOIN killmails k ON ki.killmail_id = k.killmail_id
                LEFT JOIN "invTypes" t ON ki.item_type_id = t."typeID"
                LEFT JOIN "invGroups" g ON t."groupID" = g."groupID"
                LEFT JOIN "invCategories" c ON g."categoryID" = c."categoryID"
                LEFT JOIN market_prices_cache mpc ON ki.item_type_id = mpc.type_id
                WHERE k.victim_alliance_id = %s
                  AND k.killmail_time >= NOW() - INTERVAL '%s days'
                  AND ki.flag = 5
                GROUP BY ki.item_type_id, t."typeName", g."groupName", c."categoryName"
                ORDER BY SUM(ki.quantity) * COALESCE(AVG(mpc.average_price), 0) DESC
                LIMIT %s
            """, (alliance_id, days, limit))

            cargo = []
            strategic_breakdown = {cat: {"count": 0, "isk": 0, "percentage": 0.0, "items": []} 
                                 for cat in list(self.STRATEGIC_CATEGORIES.keys()) + ["other"]}
            total_cargo_isk = 0

            # First pass: collect all data and identify unknown items
            raw_items = []
            unknown_type_ids = []

            for row in cur.fetchall():
                type_id = row["item_type_id"]
                sde_name = row["item_name"]
                sde_group = row["item_group"]
                sde_category = row["item_category"]
                total_lost = row["total_lost"] or 0
                kills_with_item = row["kills_with_item"] or 0
                avg_price = float(row["avg_price"] or 0)

                raw_items.append({
                    "type_id": type_id,
                    "sde_name": sde_name,
                    "sde_group": sde_group,
                    "sde_category": sde_category,
                    "total_lost": total_lost,
                    "kills_with_item": kills_with_item,
                    "avg_price": avg_price
                })

                if sde_name is None:
                    unknown_type_ids.append(type_id)

            # Resolve unknown items via ESI
            esi_info = {}
            if unknown_type_ids:
                esi_info = resolve_type_info_via_esi(unknown_type_ids)

            # Second pass: build cargo list and classify
            for raw in raw_items:
                type_id = raw["type_id"]
                total_lost = raw["total_lost"]
                avg_price = raw["avg_price"]
                total_isk = total_lost * avg_price

                # Use ESI info if available, otherwise SDE
                if type_id in esi_info:
                    item_name = esi_info[type_id]["name"]
                    item_group = esi_info[type_id]["group_name"]
                    item_category = esi_info[type_id]["category_name"]
                else:
                    item_name = raw["sde_name"] or f"Unknown ({type_id})"
                    item_group = raw["sde_group"] or "Unknown"
                    item_category = raw["sde_category"] or "Unknown"

                cargo_item = {
                    "type_id": type_id,
                    "item_name": item_name,
                    "item_group": item_group,
                    "item_category": item_category,
                    "total_lost": total_lost,
                    "kills_with_item": raw["kills_with_item"],
                    "avg_price": avg_price,
                    "total_isk_lost": total_isk
                }
                cargo.append(cargo_item)
                total_cargo_isk += total_isk

                # Classify strategically
                item_name_lower = item_name.lower()
                item_group_lower = item_group.lower()
                item_category_lower = item_category.lower()

                classified = False
                for category, keywords in self.STRATEGIC_CATEGORIES.items():
                    if any(kw in item_name_lower or kw in item_group_lower or kw in item_category_lower for kw in keywords):
                        strategic_breakdown[category]["count"] += total_lost
                        strategic_breakdown[category]["isk"] += total_isk
                        if len(strategic_breakdown[category]["items"]) < 5:
                            strategic_breakdown[category]["items"].append(item_name)
                        classified = True
                        break

                if not classified:
                    strategic_breakdown["other"]["count"] += total_lost
                    strategic_breakdown["other"]["isk"] += total_isk

            # Calculate percentages
            for category in strategic_breakdown:
                if total_cargo_isk > 0:
                    strategic_breakdown[category]["percentage"] = round(
                        (strategic_breakdown[category]["isk"] / total_cargo_isk) * 100, 1
                    )

            # Determine primary logistics focus
            non_other_categories = {k: v for k, v in strategic_breakdown.items() if k != "other"}
            primary_logistics_focus = max(non_other_categories, key=lambda k: non_other_categories[k]["percentage"]) if non_other_categories else "other"

            # Generate logistics insights
            insights = []
            fuel_pct = strategic_breakdown["fuel"]["percentage"]
            construction_pct = strategic_breakdown["construction"]["percentage"]
            moon_pct = strategic_breakdown["moon_materials"]["percentage"]
            ships_pct = strategic_breakdown["ships"]["percentage"]

            if fuel_pct > 20:
                insights.append({
                    "type": "capital_movement",
                    "message": f"Heavy fuel losses ({fuel_pct}% of cargo) - indicates active capital operations",
                    "priority": "high"
                })

            if construction_pct > 15:
                insights.append({
                    "type": "staging_buildup",
                    "message": f"Construction materials lost ({construction_pct}% of cargo) - possible staging/construction activity",
                    "priority": "medium"
                })

            if moon_pct > 15:
                insights.append({
                    "type": "moon_mining",
                    "message": f"Moon materials lost ({moon_pct}% of cargo) - active moon mining operations",
                    "priority": "medium"
                })

            if ships_pct > 20:
                insights.append({
                    "type": "ship_transport",
                    "message": f"Ships lost in cargo ({ships_pct}% of cargo) - potential logistics convoy losses",
                    "priority": "high"
                })

            if total_cargo_isk > 10_000_000_000:
                insights.append({
                    "type": "major_logistics",
                    "message": f"Massive cargo losses ({total_cargo_isk / 1e9:.1f}B ISK) - major logistics vulnerability",
                    "priority": "critical"
                })

            return {
                "cargo": cargo,
                "strategic_breakdown": strategic_breakdown,
                "primary_logistics_focus": primary_logistics_focus,
                "total_cargo_isk": total_cargo_isk,
                "logistics_insights": insights
            }

    def get_equipment_intel(self, alliance_id: int, days: int = 7) -> Dict[str, Any]:
        """Comprehensive equipment intelligence combining weapons, tank, and cargo analysis."""
        weapons_lost = self.get_weapons_lost(alliance_id, days)
        tank_profile = self.get_tank_profile(alliance_id, days)
        cargo_intel = self.get_cargo_intel(alliance_id, days)

        # Generate strategic summary
        strategic_summary = []

        # Add primary damage type
        if weapons_lost["total_weapons_lost"] > 0:
            primary_damage = weapons_lost.get("primary_damage_type", "unknown")
            strategic_summary.append(f"Primary damage type: {primary_damage.upper()}")

        # Add tank doctrine
        if tank_profile["total_tank_modules"] > 0:
            doctrine = tank_profile.get("doctrine", "unknown")
            strategic_summary.append(f"Tank doctrine: {doctrine}")

        # Add resist gap if present
        resist_gap = tank_profile.get("resist_gap", "unknown")
        if resist_gap != "unknown":
            strategic_summary.append(f"Resist gap: {resist_gap}")

        # Add logistics insights from cargo
        for insight in cargo_intel.get("logistics_insights", []):
            if insight["priority"] in ["high", "critical"]:
                strategic_summary.append(insight["message"])

        return {
            "alliance_id": alliance_id,
            "analysis_period_days": days,
            "weapons_lost": weapons_lost,
            "tank_profile": tank_profile,
            "cargo_intel": cargo_intel,
            "strategic_summary": strategic_summary
        }


# Singleton instance
equipment_intel_service = EquipmentIntelligenceService()
