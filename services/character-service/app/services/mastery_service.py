"""
Ship Mastery Service
Calculate character mastery levels for ships based on EVE SDE certificate data.
Migrated from monolith to character-service with eve_shared database pattern.
"""

from typing import Dict, Any, List
from psycopg2.extras import RealDictCursor
from fastapi import Request


def _get_character_skills_dict(request: Request, character_id: int) -> Dict[int, int]:
    """Get character skills as dict {skill_id: level}."""
    try:
        from app.services import CharacterService
        service = CharacterService(request.app.state.db, request.app.state.redis)
        result = service.get_skills(character_id)
        if not result:
            return {}
        return {s.skill_id: s.level for s in result.skills}
    except Exception:
        return {}


def _get_ship_mastery_requirements(db, ship_type_id: int) -> Dict[int, List[Dict]]:
    """
    Get mastery requirements for a ship.
    Returns: {mastery_level: [{cert_id, cert_name, skills: [{skill_id, skill_name, level}]}]}
    """
    with db.cursor(cursor_factory=RealDictCursor) as cur:
        # Get all certificates for each mastery level
        cur.execute("""
            SELECT
                m."masteryLevel",
                m."certID",
                c."name" as cert_name
            FROM "certMasteries" m
            JOIN "certCerts" c ON m."certID" = c."certID"
            WHERE m."typeID" = %s
            ORDER BY m."masteryLevel", c."name"
        """, (ship_type_id,))

        masteries = {}
        cert_ids = set()

        for row in cur.fetchall():
            level = row["masteryLevel"]
            if level not in masteries:
                masteries[level] = []
            masteries[level].append({
                "cert_id": row["certID"],
                "cert_name": row["cert_name"],
                "skills": []
            })
            cert_ids.add(row["certID"])

        if not cert_ids:
            return {}

        # Get skill requirements for all certificates
        cur.execute("""
            SELECT
                cs."certID",
                cs."certLevelInt",
                cs."skillID",
                cs."skillLevel",
                t."typeName" as skill_name
            FROM "certSkills" cs
            JOIN "invTypes" t ON cs."skillID" = t."typeID"
            WHERE cs."certID" = ANY(%s)
            ORDER BY cs."certID", cs."certLevelInt", t."typeName"
        """, (list(cert_ids),))

        # Build skill requirements per cert per level
        cert_skills = {}  # {cert_id: {cert_level: [{skill_id, skill_name, level}]}}
        for row in cur.fetchall():
            cert_id = row["certID"]
            cert_level = row["certLevelInt"]

            if cert_id not in cert_skills:
                cert_skills[cert_id] = {}
            if cert_level not in cert_skills[cert_id]:
                cert_skills[cert_id][cert_level] = []

            if row["skillLevel"] > 0:  # Only include if level > 0
                cert_skills[cert_id][cert_level].append({
                    "skill_id": row["skillID"],
                    "skill_name": row["skill_name"],
                    "level": row["skillLevel"]
                })

        # Attach skills to mastery certificates
        for level, certs in masteries.items():
            for cert in certs:
                cert_id = cert["cert_id"]
                # For mastery level N, we need cert level N skills
                if cert_id in cert_skills and level in cert_skills[cert_id]:
                    cert["skills"] = cert_skills[cert_id][level]

        return masteries


def _calculate_mastery_level(
    char_skills: Dict[int, int],
    mastery_reqs: Dict[int, List[Dict]]
) -> Dict[str, Any]:
    """
    Calculate achieved mastery level and missing skills.
    Returns: {mastery_level, certificates, missing_skills}
    """
    achieved_level = -1
    cert_status = {}
    all_missing = []

    for level in range(5):  # 0-4
        if level not in mastery_reqs:
            continue

        level_complete = True
        level_certs = []

        for cert in mastery_reqs[level]:
            cert_complete = True
            cert_missing = []

            for skill in cert["skills"]:
                char_level = char_skills.get(skill["skill_id"], 0)
                if char_level < skill["level"]:
                    cert_complete = False
                    cert_missing.append({
                        "skill": skill["skill_name"],
                        "skill_id": skill["skill_id"],
                        "have": char_level,
                        "need": skill["level"]
                    })

            level_certs.append({
                "name": cert["cert_name"],
                "complete": cert_complete,
                "missing": cert_missing
            })

            if not cert_complete:
                level_complete = False
                all_missing.extend(cert_missing)

        cert_status[level] = {
            "complete": level_complete,
            "certificates": level_certs
        }

        if level_complete:
            achieved_level = level

    # Deduplicate missing skills (same skill might be in multiple certs)
    unique_missing = {}
    for m in all_missing:
        key = m["skill"]
        if key not in unique_missing or m["need"] > unique_missing[key]["need"]:
            unique_missing[key] = m

    return {
        "mastery_level": achieved_level,
        "certificates": cert_status,
        "missing_for_next": list(unique_missing.values())[:10]  # Limit to top 10
    }


def handle_get_ship_mastery(request: Request, args: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate character's mastery level for a ship."""
    character_id = args.get("character_id")
    ship_type_id = args.get("ship_type_id")

    if not character_id or not ship_type_id:
        return {"error": "character_id and ship_type_id are required", "isError": True}

    try:
        # Get character skills
        char_skills = _get_character_skills_dict(request, character_id)
        if not char_skills:
            return {"error": f"Could not get skills for character {character_id}", "isError": True}

        db = request.app.state.db
        # Get ship name
        with db.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT t."typeName", g."groupName"
                FROM "invTypes" t
                JOIN "invGroups" g ON t."groupID" = g."groupID"
                WHERE t."typeID" = %s
            """, (ship_type_id,))
            ship_row = cur.fetchone()

            if not ship_row:
                return {"error": f"Ship not found: {ship_type_id}", "isError": True}

        ship_name = ship_row["typeName"]
        ship_class = ship_row["groupName"]

        # Get mastery requirements
        mastery_reqs = _get_ship_mastery_requirements(db, ship_type_id)

        if not mastery_reqs:
            return {"error": f"No mastery data for ship {ship_name}", "isError": True}

        # Calculate mastery
        result = _calculate_mastery_level(char_skills, mastery_reqs)

        # Get character name
        try:
            from app.services import CharacterService
            service = CharacterService(request.app.state.db, request.app.state.redis)
            char_info = service.get_character_info(character_id)
            char_name = char_info.name if char_info else str(character_id)
        except:
            char_name = str(character_id)

        mastery_names = {-1: "None", 0: "Basic", 1: "Standard", 2: "Improved", 3: "Advanced", 4: "Elite"}

        output = {
            "character": char_name,
            "character_id": character_id,
            "ship": ship_name,
            "ship_class": ship_class,
            "ship_type_id": ship_type_id,
            "mastery_level": result["mastery_level"],
            "mastery_name": mastery_names.get(result["mastery_level"], "Unknown"),
            "can_fly_effectively": result["mastery_level"] >= 1,
            "missing_for_next_level": result["missing_for_next"]
        }

        return {"content": [{"type": "text", "text": str(output)}]}

    except Exception as e:
        return {"error": f"Failed to calculate mastery: {str(e)}", "isError": True}


def handle_get_flyable_ships(request: Request, args: Dict[str, Any]) -> Dict[str, Any]:
    """Get all ships a character can fly at mastery 1+."""
    character_id = args.get("character_id")
    ship_class_filter = args.get("ship_class")

    if not character_id:
        return {"error": "character_id is required", "isError": True}

    try:
        # Get character skills
        char_skills = _get_character_skills_dict(request, character_id)
        if not char_skills:
            return {"error": f"Could not get skills for character {character_id}", "isError": True}

        db = request.app.state.db
        with db.cursor(cursor_factory=RealDictCursor) as cur:
            # Get combat ships with masteries
            query = """
                SELECT DISTINCT
                    t."typeID",
                    t."typeName",
                    g."groupName",
                    c."categoryID"
                FROM "invTypes" t
                JOIN "invGroups" g ON t."groupID" = g."groupID"
                JOIN "invCategories" c ON g."categoryID" = c."categoryID"
                WHERE c."categoryID" = 6  -- Ships category
                  AND t."published" = 1
                  AND EXISTS (SELECT 1 FROM "certMasteries" m WHERE m."typeID" = t."typeID")
            """

            if ship_class_filter:
                query += f" AND g.\"groupName\" ILIKE '%{ship_class_filter}%'"

            query += " ORDER BY g.\"groupName\", t.\"typeName\""

            cur.execute(query)
            ships = cur.fetchall()

        # Check mastery for each ship (limited for performance)
        flyable = {}
        checked = 0
        max_check = 200  # Limit checks for performance

        for ship in ships:
            if checked >= max_check:
                break

            ship_type_id = ship["typeID"]
            mastery_reqs = _get_ship_mastery_requirements(db, ship_type_id)

            if mastery_reqs:
                result = _calculate_mastery_level(char_skills, mastery_reqs)

                if result["mastery_level"] >= 1:
                    ship_class = ship["groupName"]
                    if ship_class not in flyable:
                        flyable[ship_class] = []

                    flyable[ship_class].append({
                        "ship": ship["typeName"],
                        "type_id": ship_type_id,
                        "mastery": result["mastery_level"]
                    })

            checked += 1

        # Sort by mastery level within each class
        for ship_class in flyable:
            flyable[ship_class].sort(key=lambda x: -x["mastery"])

        # Get character name
        try:
            from app.services import CharacterService
            service = CharacterService(request.app.state.db, request.app.state.redis)
            char_info = service.get_character_info(character_id)
            char_name = char_info.name if char_info else str(character_id)
        except:
            char_name = str(character_id)

        output = {
            "character": char_name,
            "flyable_ships": flyable,
            "ship_classes": list(flyable.keys()),
            "total_ships": sum(len(ships) for ships in flyable.values())
        }

        return {"content": [{"type": "text", "text": str(output)}]}

    except Exception as e:
        return {"error": f"Failed to get flyable ships: {str(e)}", "isError": True}


def handle_search_ship(request: Request, args: Dict[str, Any]) -> Dict[str, Any]:
    """Search for a ship by name."""
    ship_name = args.get("ship_name")

    if not ship_name:
        return {"error": "ship_name is required", "isError": True}

    try:
        db = request.app.state.db
        with db.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    t."typeID",
                    t."typeName",
                    g."groupName"
                FROM "invTypes" t
                JOIN "invGroups" g ON t."groupID" = g."groupID"
                JOIN "invCategories" c ON g."categoryID" = c."categoryID"
                WHERE c."categoryID" = 6  -- Ships
                  AND t."published" = 1
                  AND t."typeName" ILIKE %s
                ORDER BY t."typeName"
                LIMIT 20
            """, (f"%{ship_name}%",))

            ships = [dict(row) for row in cur.fetchall()]

            if not ships:
                return {"error": f"No ships found matching '{ship_name}'", "isError": True}

            output = {
                "search_term": ship_name,
                "results": ships
            }

            return {"content": [{"type": "text", "text": str(output)}]}

    except Exception as e:
        return {"error": f"Failed to search ships: {str(e)}", "isError": True}


def handle_compare_ship_mastery(request: Request, args: Dict[str, Any]) -> Dict[str, Any]:
    """Compare mastery for all characters on a ship."""
    ship_type_id = args.get("ship_type_id")

    if not ship_type_id:
        return {"error": "ship_type_id is required", "isError": True}

    try:
        db = request.app.state.db

        # Get all authenticated characters
        from app.services import CharacterService
        service = CharacterService(request.app.state.db, request.app.state.redis)
        characters = service.get_all_characters()

        if not characters:
            return {"error": "No authenticated characters found", "isError": True}

        # Get ship name
        with db.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT t."typeName", g."groupName"
                FROM "invTypes" t
                JOIN "invGroups" g ON t."groupID" = g."groupID"
                WHERE t."typeID" = %s
            """, (ship_type_id,))
            ship_row = cur.fetchone()

            if not ship_row:
                return {"error": f"Ship not found: {ship_type_id}", "isError": True}

        ship_name = ship_row["typeName"]
        ship_class = ship_row["groupName"]

        # Get mastery requirements once
        mastery_reqs = _get_ship_mastery_requirements(db, ship_type_id)

        if not mastery_reqs:
            return {"error": f"No mastery data for ship {ship_name}", "isError": True}

        # Check each character
        comparisons = []
        mastery_names = {-1: "None", 0: "Basic", 1: "Standard", 2: "Improved", 3: "Advanced", 4: "Elite"}

        for char in characters:
            char_id = char["character_id"]
            char_name = char["character_name"]

            char_skills = _get_character_skills_dict(request, char_id)
            if char_skills:
                result = _calculate_mastery_level(char_skills, mastery_reqs)

                comparisons.append({
                    "character": char_name,
                    "character_id": char_id,
                    "mastery_level": result["mastery_level"],
                    "mastery_name": mastery_names.get(result["mastery_level"], "Unknown"),
                    "can_fly": result["mastery_level"] >= 1,
                    "missing_skills": len(result["missing_for_next"])
                })

        # Sort by mastery level descending
        comparisons.sort(key=lambda x: -x["mastery_level"])

        best = comparisons[0] if comparisons else None

        output = {
            "ship": ship_name,
            "ship_class": ship_class,
            "ship_type_id": ship_type_id,
            "best_pilot": best["character"] if best else None,
            "comparisons": comparisons
        }

        return {"content": [{"type": "text", "text": str(output)}]}

    except Exception as e:
        return {"error": f"Failed to compare mastery: {str(e)}", "isError": True}


# Handler mapping
HANDLERS = {
    "get_ship_mastery": handle_get_ship_mastery,
    "get_flyable_ships": handle_get_flyable_ships,
    "search_ship": handle_search_ship,
    "compare_ship_mastery": handle_compare_ship_mastery
}
