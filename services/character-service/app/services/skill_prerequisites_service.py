"""
Skill Prerequisites Service
Recursively calculates full skill trees with all prerequisites.

Used for:
- Intelligence: What skills must an enemy pilot have based on ships/modules used
- Planning: What skills does a character need to train for a goal

Uses SDE dgmTypeAttributes for skill requirements:
- 182/277: Primary skill/level
- 183/278: Secondary skill/level
- 184/279: Tertiary skill/level
- 1285/1286: Quaternary skill/level
- 1289/1287: Quinary skill/level
- 1290/1288: Senary skill/level
"""

import logging
from typing import Dict, Any, List, Set, Tuple, Optional
from dataclasses import dataclass
from psycopg2.extras import RealDictCursor, Json

logger = logging.getLogger(__name__)

# SP formula: 250 × Multiplier × (√32)^(Level-1)
SP_PER_LEVEL = {
    1: 250,
    2: 1414,
    3: 8000,
    4: 45255,
    5: 256000
}

# Skill/Level attribute pairs
SKILL_LEVEL_ATTRS = [
    (182, 277),   # Primary
    (183, 278),   # Secondary
    (184, 279),   # Tertiary
    (1285, 1286), # Quaternary
    (1289, 1287), # Quinary
    (1290, 1288), # Senary
]


@dataclass
class SkillRequirement:
    skill_id: int
    skill_name: str
    level: int
    rank: float
    sp_required: int
    primary_attribute: str
    secondary_attribute: str


class SkillPrerequisitesService:
    """
    Service for calculating complete skill prerequisite trees.
    """

    # Attribute ID to name mapping
    ATTR_NAMES = {
        164: 'charisma',
        165: 'intelligence',
        166: 'memory',
        167: 'perception',
        168: 'willpower',
    }

    def __init__(self, db):
        self.db = db
        self._skill_cache: Dict[int, Dict] = {}  # Cache skill info
        self._prereq_cache: Dict[int, List[Tuple[int, int]]] = {}  # Cache direct prereqs

    def _get_skill_info(self, skill_ids: Set[int]) -> Dict[int, Dict]:
        """Get skill info (name, rank, attributes) for multiple skills."""
        if not skill_ids:
            return {}

        # Check cache first
        uncached = [sid for sid in skill_ids if sid not in self._skill_cache]

        if uncached:
            with self.db.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT
                        t."typeID" as skill_id,
                        t."typeName" as skill_name,
                        COALESCE(rank.value, 1) as rank,
                        COALESCE(primary_attr.value, 167) as primary_attr_id,
                        COALESCE(secondary_attr.value, 168) as secondary_attr_id
                    FROM "invTypes" t
                    LEFT JOIN (
                        SELECT "typeID", COALESCE("valueInt", "valueFloat")::float as value
                        FROM "dgmTypeAttributes" WHERE "attributeID" = 275
                    ) rank ON rank."typeID" = t."typeID"
                    LEFT JOIN (
                        SELECT "typeID", COALESCE("valueInt", "valueFloat")::int as value
                        FROM "dgmTypeAttributes" WHERE "attributeID" = 180
                    ) primary_attr ON primary_attr."typeID" = t."typeID"
                    LEFT JOIN (
                        SELECT "typeID", COALESCE("valueInt", "valueFloat")::int as value
                        FROM "dgmTypeAttributes" WHERE "attributeID" = 181
                    ) secondary_attr ON secondary_attr."typeID" = t."typeID"
                    WHERE t."typeID" = ANY(%s)
                """, (uncached,))

                for row in cur.fetchall():
                    self._skill_cache[row['skill_id']] = {
                        'skill_name': row['skill_name'],
                        'rank': row['rank'] or 1,
                        'primary_attribute': self.ATTR_NAMES.get(row['primary_attr_id'], 'perception'),
                        'secondary_attribute': self.ATTR_NAMES.get(row['secondary_attr_id'], 'willpower'),
                    }

        return {sid: self._skill_cache.get(sid, {}) for sid in skill_ids}

    def _get_direct_prerequisites(self, skill_id: int) -> List[Tuple[int, int]]:
        """Get direct prerequisites for a skill (skill_id, level)."""
        if skill_id in self._prereq_cache:
            return self._prereq_cache[skill_id]

        with self.db.cursor(cursor_factory=RealDictCursor) as cur:
            # Get all skill requirement attributes for this skill
            cur.execute("""
                SELECT "attributeID", COALESCE("valueFloat", "valueInt")::float as value
                FROM "dgmTypeAttributes"
                WHERE "typeID" = %s
                  AND "attributeID" IN (182, 183, 184, 277, 278, 279, 1285, 1286, 1287, 1288, 1289, 1290)
            """, (skill_id,))

            attrs = {row['attributeID']: row['value'] for row in cur.fetchall()}

        prereqs = []
        for skill_attr, level_attr in SKILL_LEVEL_ATTRS:
            if skill_attr in attrs and level_attr in attrs:
                prereq_skill_id = int(attrs[skill_attr])
                prereq_level = int(attrs[level_attr])
                if prereq_skill_id > 0 and prereq_level > 0:
                    prereqs.append((prereq_skill_id, prereq_level))

        self._prereq_cache[skill_id] = prereqs
        return prereqs

    def get_full_skill_tree(
        self,
        skill_id: int,
        level: int,
        _visited: Optional[Set[int]] = None
    ) -> Dict[str, Any]:
        """
        Recursively get complete skill tree for a skill at a level.

        Returns tree structure:
        {
            "skill_id": 3338,
            "skill_name": "Caldari Battleship",
            "level": 1,
            "rank": 8,
            "sp_required": 2000,
            "primary_attribute": "perception",
            "secondary_attribute": "willpower",
            "requires": [
                {
                    "skill_id": 33096,
                    "skill_name": "Caldari Battlecruiser",
                    "level": 3,
                    ...
                    "requires": [...]
                }
            ]
        }
        """
        if _visited is None:
            _visited = set()

        # Prevent infinite loops
        if skill_id in _visited:
            return {}
        _visited.add(skill_id)

        # Get skill info
        info = self._get_skill_info({skill_id}).get(skill_id, {})
        if not info:
            return {}

        rank = info.get('rank', 1)
        sp = int(SP_PER_LEVEL.get(level, 0) * rank)

        result = {
            "skill_id": skill_id,
            "skill_name": info.get('skill_name', f'Skill {skill_id}'),
            "level": level,
            "rank": rank,
            "sp_required": sp,
            "primary_attribute": info.get('primary_attribute', 'perception'),
            "secondary_attribute": info.get('secondary_attribute', 'willpower'),
            "requires": []
        }

        # Get direct prerequisites
        prereqs = self._get_direct_prerequisites(skill_id)

        for prereq_skill_id, prereq_level in prereqs:
            # Recursively get prerequisite tree
            prereq_tree = self.get_full_skill_tree(
                prereq_skill_id,
                prereq_level,
                _visited.copy()  # Copy to allow same skill in different branches
            )
            if prereq_tree:
                result["requires"].append(prereq_tree)

        return result

    def get_flat_prerequisites(
        self,
        skill_id: int,
        level: int
    ) -> Dict[int, SkillRequirement]:
        """
        Get flattened list of all prerequisites (including the skill itself).
        Returns dict: {skill_id: SkillRequirement} with highest required level for each.
        """
        tree = self.get_full_skill_tree(skill_id, level)
        flat: Dict[int, SkillRequirement] = {}

        def flatten(node: Dict):
            if not node:
                return

            sid = node["skill_id"]
            lvl = node["level"]

            # Keep highest level requirement
            if sid not in flat or lvl > flat[sid].level:
                flat[sid] = SkillRequirement(
                    skill_id=sid,
                    skill_name=node["skill_name"],
                    level=lvl,
                    rank=node["rank"],
                    sp_required=node["sp_required"],
                    primary_attribute=node["primary_attribute"],
                    secondary_attribute=node["secondary_attribute"],
                )

            for prereq in node.get("requires", []):
                flatten(prereq)

        flatten(tree)
        return flat

    def get_prerequisites_for_item(self, type_id: int) -> Dict[str, Any]:
        """
        Get complete skill tree for using an item (ship, module, etc).

        Returns:
        {
            "type_id": 638,
            "type_name": "Raven",
            "skill_trees": [...],  # Tree for each direct skill requirement
            "flat_skills": [...],  # Flattened unique skills
            "total_sp": 165254
        }
        """
        with self.db.cursor(cursor_factory=RealDictCursor) as cur:
            # Get item name
            cur.execute("""
                SELECT "typeName" FROM "invTypes" WHERE "typeID" = %s
            """, (type_id,))
            item = cur.fetchone()
            if not item:
                return {"error": f"Item {type_id} not found"}

            # Get direct skill requirements for the item
            cur.execute("""
                SELECT "attributeID", COALESCE("valueFloat", "valueInt")::float as value
                FROM "dgmTypeAttributes"
                WHERE "typeID" = %s
                  AND "attributeID" IN (182, 183, 184, 277, 278, 279, 1285, 1286, 1287, 1288, 1289, 1290)
            """, (type_id,))

            attrs = {row['attributeID']: row['value'] for row in cur.fetchall()}

        # Build skill trees for each direct requirement
        trees = []
        all_flat: Dict[int, SkillRequirement] = {}

        for skill_attr, level_attr in SKILL_LEVEL_ATTRS:
            if skill_attr in attrs and level_attr in attrs:
                skill_id = int(attrs[skill_attr])
                level = int(attrs[level_attr])
                if skill_id > 0 and level > 0:
                    tree = self.get_full_skill_tree(skill_id, level)
                    if tree:
                        trees.append(tree)

                    # Merge into flat list
                    flat = self.get_flat_prerequisites(skill_id, level)
                    for sid, req in flat.items():
                        if sid not in all_flat or req.level > all_flat[sid].level:
                            all_flat[sid] = req

        # Calculate total SP
        total_sp = sum(req.sp_required for req in all_flat.values())

        return {
            "type_id": type_id,
            "type_name": item['typeName'],
            "skill_trees": trees,
            "flat_skills": [
                {
                    "skill_id": req.skill_id,
                    "skill_name": req.skill_name,
                    "level": req.level,
                    "rank": req.rank,
                    "sp_required": req.sp_required,
                    "primary_attribute": req.primary_attribute,
                    "secondary_attribute": req.secondary_attribute,
                }
                for req in sorted(all_flat.values(), key=lambda x: -x.sp_required)
            ],
            "total_sp": total_sp
        }

    def populate_prerequisites_cache(self, batch_size: int = 100) -> Dict[str, Any]:
        """
        Populate skill_prerequisites_cache table for all skills.
        Run once after SDE update.
        """
        logger.info("Starting skill prerequisites cache population")

        with self.db.cursor(cursor_factory=RealDictCursor) as cur:
            # Get all published skills (categoryID 16 = Skills)
            cur.execute("""
                SELECT t."typeID" as skill_id
                FROM "invTypes" t
                JOIN "invGroups" g ON t."groupID" = g."groupID"
                WHERE g."categoryID" = 16
                  AND t."published" = 1
                  AND g."groupName" != 'Fake Skills'
            """)

            skills = [row['skill_id'] for row in cur.fetchall()]
            logger.info(f"Found {len(skills)} skills to process")

            processed = 0
            errors = 0

            for skill_id in skills:
                try:
                    # Get flat prerequisites for level 5 (max)
                    flat = self.get_flat_prerequisites(skill_id, 5)

                    if flat:
                        # Build prerequisites JSON
                        prereqs_json = [
                            {
                                "skill_id": req.skill_id,
                                "skill_name": req.skill_name,
                                "level": req.level,
                                "rank": req.rank,
                                "sp_required": req.sp_required,
                                "primary_attribute": req.primary_attribute,
                                "secondary_attribute": req.secondary_attribute,
                            }
                            for req in sorted(flat.values(), key=lambda x: -x.sp_required)
                            if req.skill_id != skill_id  # Exclude self
                        ]

                        total_sp = sum(req.sp_required for req in flat.values() if req.skill_id != skill_id)
                        max_depth = self._calculate_tree_depth(skill_id, 5)

                        # Upsert into cache
                        cur.execute("""
                            INSERT INTO skill_prerequisites_cache
                                (skill_type_id, prerequisites, total_sp_required, max_depth, updated_at)
                            VALUES (%s, %s, %s, %s, NOW())
                            ON CONFLICT (skill_type_id) DO UPDATE SET
                                prerequisites = EXCLUDED.prerequisites,
                                total_sp_required = EXCLUDED.total_sp_required,
                                max_depth = EXCLUDED.max_depth,
                                updated_at = NOW()
                        """, (skill_id, Json(prereqs_json), total_sp, max_depth))

                    processed += 1
                    if processed % 100 == 0:
                        logger.info(f"Processed {processed}/{len(skills)} skills")

                except Exception as e:
                    logger.warning(f"Error processing skill {skill_id}: {e}")
                    errors += 1

        logger.info(f"Cache population complete: {processed} skills, {errors} errors")
        return {
            "processed": processed,
            "errors": errors,
            "total_skills": len(skills)
        }

    def _calculate_tree_depth(self, skill_id: int, level: int, depth: int = 0) -> int:
        """Calculate max depth of skill tree."""
        prereqs = self._get_direct_prerequisites(skill_id)
        if not prereqs:
            return depth

        max_child_depth = depth
        for prereq_skill_id, _ in prereqs:
            child_depth = self._calculate_tree_depth(prereq_skill_id, 5, depth + 1)
            max_child_depth = max(max_child_depth, child_depth)

        return max_child_depth

    def get_cached_prerequisites(self, skill_id: int) -> Optional[Dict]:
        """Get cached prerequisites from database."""
        with self.db.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT prerequisites, total_sp_required, max_depth
                FROM skill_prerequisites_cache
                WHERE skill_type_id = %s
            """, (skill_id,))

            row = cur.fetchone()
            if row:
                return {
                    "skill_id": skill_id,
                    "prerequisites": row['prerequisites'],
                    "total_sp_required": row['total_sp_required'],
                    "max_depth": row['max_depth']
                }
        return None
