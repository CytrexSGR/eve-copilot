"""
Research Service for Skill Planning

Provides skill analysis for EVE Online characters:
- Required skills for production
- Training time calculations
- Skill recommendations based on production goals

Migrated from monolith to character-service with eve_shared database pattern.
"""

import logging
from typing import List, Dict, Any, Optional
from fastapi import Request
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)


class ResearchService:
    """Analyzes skills required for manufacturing and provides recommendations"""

    def get_skills_for_item(
        self,
        request: Request,
        type_id: int,
        character_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get skills required to manufacture an item

        Args:
            request: FastAPI request object (for db access)
            type_id: Item type ID to check
            character_id: Optional character to compare skills

        Returns:
            Dict with required_skills list and optionally character comparison
        """
        # Get blueprint for this item
        blueprint_id = self._get_blueprint_for_item(request, type_id)
        if not blueprint_id:
            return {'required_skills': [], 'error': 'No blueprint found'}

        # Get required skills from blueprint
        required_skills = self._get_blueprint_skills(request, blueprint_id)

        # If character provided, compare with their skills
        if character_id:
            character_skills = self._get_character_skills(request, character_id)
            required_skills = self._compare_skills(request, required_skills, character_skills)

        return {
            'type_id': type_id,
            'blueprint_id': blueprint_id,
            'required_skills': required_skills
        }

    def _get_blueprint_for_item(self, request: Request, type_id: int) -> Optional[int]:
        """Find blueprint that produces this item"""
        try:
            db = request.app.state.db
            with db.cursor() as cursor:
                cursor.execute("""
                    SELECT "typeID"
                    FROM "industryActivityProducts"
                    WHERE "productTypeID" = %s
                    AND "activityID" = 1  -- Manufacturing
                    LIMIT 1
                """, (type_id,))

                row = cursor.fetchone()
                return row[0] if row else None
        except Exception as e:
            logger.error(f"Error finding blueprint: {e}")
            return None

    def _get_blueprint_skills(self, request: Request, blueprint_id: int) -> List[Dict[str, Any]]:
        """Get skills required for blueprint"""
        try:
            db = request.app.state.db
            with db.cursor() as cursor:
                cursor.execute("""
                    SELECT
                        ias."skillID",
                        t."typeName",
                        ias."level"
                    FROM "industryActivitySkills" ias
                    JOIN "invTypes" t ON ias."skillID" = t."typeID"
                    WHERE ias."typeID" = %s
                    AND ias."activityID" = 1  -- Manufacturing
                """, (blueprint_id,))

                rows = cursor.fetchall()

                skills = []
                for row in rows:
                    skills.append({
                        'skill_id': row[0],
                        'skill_name': row[1],
                        'required_level': row[2],
                        'character_level': 0,  # Will be updated if character provided
                        'training_time_seconds': 0
                    })

                return skills
        except Exception as e:
            logger.error(f"Error getting blueprint skills: {e}")
            return []

    def _get_character_skills(self, request: Request, character_id: int) -> Dict[int, int]:
        """Get character's current skill levels from database cache"""
        try:
            db = request.app.state.db
            with db.cursor() as cursor:
                # Query the character_skills cache table
                cursor.execute("""
                    SELECT skill_id, trained_skill_level
                    FROM character_skills
                    WHERE character_id = %s
                """, (character_id,))

                rows = cursor.fetchall()

                # Create dict of skill_id -> level
                skill_levels = {}
                for row in rows:
                    skill_levels[row[0]] = row[1]

                return skill_levels
        except Exception as e:
            logger.error(f"Error getting character skills: {e}")
            return {}

    def _compare_skills(
        self,
        request: Request,
        required_skills: List[Dict[str, Any]],
        character_skills: Dict[int, int]
    ) -> List[Dict[str, Any]]:
        """Compare required skills with character's current skills"""
        for skill in required_skills:
            skill_id = skill['skill_id']
            required_level = skill['required_level']
            character_level = character_skills.get(skill_id, 0)

            skill['character_level'] = character_level

            # Calculate training time if skill not met
            if character_level < required_level:
                training_time = self._calculate_training_time(
                    request,
                    skill_id,
                    character_level,
                    required_level
                )
                skill['training_time_seconds'] = training_time
            else:
                skill['training_time_seconds'] = 0

        return required_skills

    def _calculate_training_time(
        self,
        request: Request,
        skill_id: int,
        current_level: int,
        target_level: int
    ) -> int:
        """
        Calculate training time from current to target level

        Simplified calculation - in reality would need character attributes
        """
        # Get skill rank/multiplier
        try:
            db = request.app.state.db
            with db.cursor() as cursor:
                cursor.execute("""
                    SELECT
                        COALESCE("skillTimeConstant", 1) as rank
                    FROM "invTypes"
                    WHERE "typeID" = %s
                """, (skill_id,))

                row = cursor.fetchone()
                rank = row[0] if row else 1
        except Exception:
            rank = 1

        # Skill points per level (simplified)
        SP_PER_LEVEL = {
            1: 250,
            2: 1415,
            3: 8000,
            4: 45255,
            5: 256000
        }

        # Calculate total SP needed
        total_sp = 0
        for level in range(current_level + 1, target_level + 1):
            total_sp += SP_PER_LEVEL.get(level, 0) * rank

        # Assume 30 SP/minute (average)
        SP_PER_MINUTE = 30
        training_minutes = total_sp / SP_PER_MINUTE

        return int(training_minutes * 60)  # Convert to seconds

    def get_skill_recommendations(self, request: Request, character_id: int) -> List[Dict[str, Any]]:
        """
        Get skill training recommendations based on production history.

        Analyzes the character's most-built blueprints, checks required skills,
        and returns recommendations for skills that would unlock or improve production.
        """
        try:
            db = request.app.state.db
            with db.cursor() as cursor:
                # 1. Get top 10 most-built blueprints
                cursor.execute("""
                    SELECT blueprint_type_id, COUNT(*) as job_count
                    FROM character_industry_jobs
                    WHERE character_id = %s AND activity_id = 1
                    GROUP BY blueprint_type_id
                    ORDER BY COUNT(*) DESC
                    LIMIT 10
                """, (character_id,))
                top_blueprints = cursor.fetchall()

                if not top_blueprints:
                    return []

                # 2. Get character's current skills
                character_skills = self._get_character_skills(request, character_id)

                # 3. For each blueprint, find skill gaps
                skill_gaps: Dict[int, Dict[str, Any]] = {}
                for bp_row in top_blueprints:
                    bp_type_id = bp_row[0]
                    job_count = bp_row[1]

                    cursor.execute("""
                        SELECT ias."skillID", t."typeName", ias."level"
                        FROM "industryActivitySkills" ias
                        JOIN "invTypes" t ON ias."skillID" = t."typeID"
                        WHERE ias."typeID" = %s AND ias."activityID" = 1
                    """, (bp_type_id,))
                    required = cursor.fetchall()

                    for skill_row in required:
                        skill_id = skill_row[0]
                        skill_name = skill_row[1]
                        required_level = skill_row[2]
                        current_level = character_skills.get(skill_id, 0)

                        if current_level < required_level:
                            if skill_id not in skill_gaps:
                                skill_gaps[skill_id] = {
                                    'skill_id': skill_id,
                                    'skill_name': skill_name,
                                    'current_level': current_level,
                                    'recommended_level': required_level,
                                    'blueprints_affected': 0,
                                    'total_jobs': 0,
                                    'training_time_seconds': 0
                                }
                            gap = skill_gaps[skill_id]
                            gap['blueprints_affected'] += 1
                            gap['total_jobs'] += job_count
                            if required_level > gap['recommended_level']:
                                gap['recommended_level'] = required_level

                if not skill_gaps:
                    return []

                # 4. Calculate training time for each gap
                for gap in skill_gaps.values():
                    gap['training_time_seconds'] = self._calculate_training_time(
                        request,
                        gap['skill_id'],
                        gap['current_level'],
                        gap['recommended_level']
                    )
                    gap['training_time_hours'] = round(gap['training_time_seconds'] / 3600, 1)

                # 5. Rank by impact: more blueprints affected and more jobs = higher priority
                recommendations = sorted(
                    skill_gaps.values(),
                    key=lambda g: (g['blueprints_affected'], g['total_jobs']),
                    reverse=True
                )[:5]

                return list(recommendations)

        except Exception as e:
            logger.error(f"Error getting skill recommendations for {character_id}: {e}")
            return []


# Singleton instance
research_service = ResearchService()
