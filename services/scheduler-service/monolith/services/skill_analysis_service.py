"""
Skill Analysis Service for EVE Co-Pilot

Provides LLM-powered analysis of character skills, team composition,
and training recommendations. Stores results in PostgreSQL for historical tracking.
"""

import logging
import json
from datetime import datetime, date
from typing import Dict, Any, Optional, List
from enum import Enum
import psycopg2
from psycopg2.extras import RealDictCursor, Json

from src.database import get_db_connection

logger = logging.getLogger(__name__)


class AnalysisType(str, Enum):
    """Types of skill analysis reports"""
    INDIVIDUAL_ASSESSMENT = "individual_assessment"
    TEAM_COMPOSITION = "team_composition"
    TRAINING_PRIORITIES = "training_priorities"
    ROLE_OPTIMIZATION = "role_optimization"
    GAP_ANALYSIS = "gap_analysis"
    WEEKLY_SUMMARY = "weekly_summary"
    MONTHLY_REVIEW = "monthly_review"


class SkillAnalysisService:
    """Service for LLM-powered skill analysis"""

    def __init__(self, llm_client=None):
        """Initialize the skill analysis service.

        Args:
            llm_client: Optional LLM client for generating analyses.
                       If not provided, only data preparation methods are available.
        """
        self.llm_client = llm_client

    # =========================================================
    # DATA PREPARATION METHODS
    # =========================================================

    def get_character_profile(self, character_id: int) -> Dict[str, Any]:
        """Get character profile formatted for LLM input.

        Args:
            character_id: EVE character ID

        Returns:
            Dict with character profile data
        """
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM v_llm_character_profile
                    WHERE character_id = %s
                """, (character_id,))
                result = cur.fetchone()
                return dict(result) if result else {}

    def get_team_overview(self) -> Dict[str, Any]:
        """Get team overview formatted for LLM input.

        Returns:
            Dict with team stats and character summaries
        """
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM v_llm_team_overview")
                result = cur.fetchone()
                return dict(result) if result else {}

    def get_skill_gaps(self) -> List[Dict[str, Any]]:
        """Get skill gaps formatted for LLM input.

        Returns:
            List of skill gap categories with missing skills
        """
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM v_llm_skill_gaps")
                return [dict(row) for row in cur.fetchall()]

    def get_skill_comparison(self) -> List[Dict[str, Any]]:
        """Get skill comparison matrix for LLM input.

        Returns:
            List of skill categories with character comparison
        """
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM v_llm_skill_comparison")
                return [dict(row) for row in cur.fetchall()]

    def get_unique_capabilities(self) -> List[Dict[str, Any]]:
        """Get unique capabilities per character.

        Returns:
            List of unique skills per character
        """
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT character_name, skill_category,
                           array_agg(skill_name || ' L' || active_skill_level
                                     ORDER BY skill_name) as skills
                    FROM v_unique_capabilities
                    GROUP BY character_name, skill_category
                    ORDER BY character_name, skill_category
                """)
                return [dict(row) for row in cur.fetchall()]

    def get_recent_progress(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get recent SP progress for all characters.

        Args:
            days: Number of days to look back

        Returns:
            List of progress data per character
        """
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT c.character_name,
                           COALESCE(SUM(p.sp_gained), 0) as total_sp_gained,
                           COALESCE(SUM(p.skills_gained), 0) as total_skills_gained,
                           COALESCE(SUM(p.level_5_gained), 0) as total_l5_gained,
                           COUNT(p.id) as days_tracked
                    FROM characters c
                    LEFT JOIN character_sp_progress p
                        ON c.character_id = p.character_id
                        AND p.date >= CURRENT_DATE - %s
                    GROUP BY c.character_id, c.character_name
                    ORDER BY total_sp_gained DESC
                """, (days,))
                return [dict(row) for row in cur.fetchall()]

    def prepare_analysis_input(
        self,
        analysis_type: AnalysisType,
        character_ids: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """Prepare input data for LLM analysis.

        Args:
            analysis_type: Type of analysis to prepare
            character_ids: Optional list of character IDs (None = all)

        Returns:
            Dict with all data needed for the analysis
        """
        data = {
            "analysis_type": analysis_type.value,
            "timestamp": datetime.now().isoformat(),
            "team_overview": self.get_team_overview(),
        }

        if analysis_type == AnalysisType.INDIVIDUAL_ASSESSMENT:
            if character_ids:
                data["characters"] = [
                    self.get_character_profile(cid) for cid in character_ids
                ]
            else:
                # Get all characters
                with get_db_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("SELECT character_id FROM characters")
                        all_ids = [row[0] for row in cur.fetchall()]
                data["characters"] = [
                    self.get_character_profile(cid) for cid in all_ids
                ]

        elif analysis_type == AnalysisType.TEAM_COMPOSITION:
            data["unique_capabilities"] = self.get_unique_capabilities()
            data["skill_comparison"] = self.get_skill_comparison()

        elif analysis_type == AnalysisType.TRAINING_PRIORITIES:
            data["skill_gaps"] = self.get_skill_gaps()
            data["skill_comparison"] = self.get_skill_comparison()
            data["recent_progress"] = self.get_recent_progress()

        elif analysis_type == AnalysisType.GAP_ANALYSIS:
            data["skill_gaps"] = self.get_skill_gaps()

        elif analysis_type in (AnalysisType.WEEKLY_SUMMARY, AnalysisType.MONTHLY_REVIEW):
            days = 7 if analysis_type == AnalysisType.WEEKLY_SUMMARY else 30
            data["progress"] = self.get_recent_progress(days)
            data["skill_gaps"] = self.get_skill_gaps()

        return data

    # =========================================================
    # SNAPSHOT METHODS
    # =========================================================

    def create_snapshot(self, character_id: int, snapshot_date: Optional[date] = None) -> int:
        """Create a skill snapshot for a character.

        Args:
            character_id: EVE character ID
            snapshot_date: Date for snapshot (default: today)

        Returns:
            Snapshot ID
        """
        if snapshot_date is None:
            snapshot_date = date.today()

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT create_skill_snapshot(%s, %s)",
                    (character_id, snapshot_date)
                )
                result = cur.fetchone()
                conn.commit()
                return result[0] if result else 0

    def create_all_snapshots(self, snapshot_date: Optional[date] = None) -> List[Dict[str, int]]:
        """Create snapshots for all characters.

        Args:
            snapshot_date: Date for snapshot (default: today)

        Returns:
            List of {character_id, snapshot_id}
        """
        if snapshot_date is None:
            snapshot_date = date.today()

        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM create_all_snapshots(%s)", (snapshot_date,))
                results = [dict(row) for row in cur.fetchall()]
                conn.commit()
                return results

    def calculate_progress(self, character_id: int, progress_date: Optional[date] = None) -> int:
        """Calculate SP progress for a character.

        Args:
            character_id: EVE character ID
            progress_date: Date to calculate progress for (default: today)

        Returns:
            Progress record ID
        """
        if progress_date is None:
            progress_date = date.today()

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT calculate_sp_progress(%s, %s)",
                    (character_id, progress_date)
                )
                result = cur.fetchone()
                conn.commit()
                return result[0] if result else 0

    # =========================================================
    # ANALYSIS STORAGE METHODS
    # =========================================================

    def save_analysis_report(
        self,
        report_type: AnalysisType,
        input_data: Dict[str, Any],
        analysis_text: str,
        recommendations: Optional[Dict[str, Any]] = None,
        metrics: Optional[Dict[str, Any]] = None,
        character_ids: Optional[List[int]] = None,
        model_used: Optional[str] = None,
        tokens_used: Optional[int] = None,
        processing_time_ms: Optional[int] = None
    ) -> int:
        """Save an LLM analysis report.

        Args:
            report_type: Type of analysis
            input_data: Data that was sent to LLM
            analysis_text: LLM response text
            recommendations: Structured recommendations
            metrics: Key metrics at time of analysis
            character_ids: Characters covered by analysis
            model_used: LLM model identifier
            tokens_used: Number of tokens used
            processing_time_ms: Processing time in milliseconds

        Returns:
            Report ID
        """
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO skill_analysis_reports (
                        report_type, character_ids, input_data, analysis_text,
                        recommendations, metrics, model_used, tokens_used,
                        processing_time_ms
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    report_type.value,
                    character_ids,
                    Json(input_data),
                    analysis_text,
                    Json(recommendations) if recommendations else None,
                    Json(metrics) if metrics else None,
                    model_used,
                    tokens_used,
                    processing_time_ms
                ))
                result = cur.fetchone()
                conn.commit()
                return result[0] if result else 0

    def save_training_recommendations(
        self,
        report_id: int,
        recommendations: List[Dict[str, Any]]
    ) -> List[int]:
        """Save training recommendations from an analysis.

        Args:
            report_id: Parent report ID
            recommendations: List of recommendation dicts with:
                - character_id: int
                - skill_id: int
                - skill_name: str
                - current_level: int
                - target_level: int
                - priority: int (1-5)
                - reason: str (optional)
                - estimated_training_days: float (optional)
                - category: str (optional)

        Returns:
            List of recommendation IDs
        """
        ids = []
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                for rec in recommendations:
                    cur.execute("""
                        INSERT INTO skill_training_recommendations (
                            report_id, character_id, skill_id, skill_name,
                            current_level, target_level, priority, reason,
                            estimated_training_days, category
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id
                    """, (
                        report_id,
                        rec["character_id"],
                        rec["skill_id"],
                        rec["skill_name"],
                        rec["current_level"],
                        rec["target_level"],
                        rec["priority"],
                        rec.get("reason"),
                        rec.get("estimated_training_days"),
                        rec.get("category")
                    ))
                    result = cur.fetchone()
                    if result:
                        ids.append(result[0])
                conn.commit()
        return ids

    def get_latest_report(
        self,
        report_type: Optional[AnalysisType] = None
    ) -> Optional[Dict[str, Any]]:
        """Get the latest analysis report.

        Args:
            report_type: Optional filter by report type

        Returns:
            Report dict or None
        """
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                if report_type:
                    cur.execute("""
                        SELECT * FROM skill_analysis_reports
                        WHERE report_type = %s
                        ORDER BY report_date DESC
                        LIMIT 1
                    """, (report_type.value,))
                else:
                    cur.execute("""
                        SELECT * FROM skill_analysis_reports
                        ORDER BY report_date DESC
                        LIMIT 1
                    """)
                result = cur.fetchone()
                return dict(result) if result else None

    def get_pending_recommendations(
        self,
        character_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get pending training recommendations.

        Args:
            character_id: Optional filter by character

        Returns:
            List of pending recommendation dicts
        """
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                if character_id:
                    cur.execute("""
                        SELECT r.*, c.character_name
                        FROM skill_training_recommendations r
                        JOIN characters c ON r.character_id = c.character_id
                        WHERE r.character_id = %s AND NOT r.is_completed
                        ORDER BY r.priority, r.created_at
                    """, (character_id,))
                else:
                    cur.execute("""
                        SELECT r.*, c.character_name
                        FROM skill_training_recommendations r
                        JOIN characters c ON r.character_id = c.character_id
                        WHERE NOT r.is_completed
                        ORDER BY c.character_name, r.priority, r.created_at
                    """)
                return [dict(row) for row in cur.fetchall()]

    def mark_recommendation_completed(self, recommendation_id: int) -> bool:
        """Mark a training recommendation as completed.

        Args:
            recommendation_id: Recommendation ID

        Returns:
            True if updated, False if not found
        """
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE skill_training_recommendations
                    SET is_completed = TRUE, completed_at = NOW()
                    WHERE id = %s AND NOT is_completed
                """, (recommendation_id,))
                conn.commit()
                return cur.rowcount > 0

    # =========================================================
    # LLM ANALYSIS METHODS (require llm_client)
    # =========================================================

    def generate_analysis_prompt(
        self,
        analysis_type: AnalysisType,
        input_data: Dict[str, Any]
    ) -> str:
        """Generate a prompt for LLM analysis.

        Args:
            analysis_type: Type of analysis
            input_data: Prepared input data

        Returns:
            Formatted prompt string
        """
        prompts = {
            AnalysisType.INDIVIDUAL_ASSESSMENT: """
Analysiere die folgenden EVE Online Charakter-Skill-Daten und erstelle eine detaillierte Bewertung.

Für jeden Charakter:
1. Stärken und Spezialisierungen
2. Empfohlene Rollen basierend auf Skills
3. Empfohlene Schiffe
4. Verbesserungspotential

Antworte auf Deutsch. Sei konkret und praxisorientiert.

Daten:
{data}
""",
            AnalysisType.TEAM_COMPOSITION: """
Analysiere die Team-Zusammensetzung dieser EVE Online Charaktere.

Bewerte:
1. Wie gut ergänzen sich die Charaktere?
2. Optimale Rollenverteilung
3. Team-Synergien für verschiedene Aktivitäten (Mining, Missionen, PvP)
4. Schwächen des Teams

Antworte auf Deutsch. Gib konkrete Empfehlungen.

Daten:
{data}
""",
            AnalysisType.TRAINING_PRIORITIES: """
Analysiere die Skill-Daten und erstelle priorisierte Trainingsempfehlungen.

Für jeden Charakter:
1. Top 3 Skills die als nächstes trainiert werden sollten
2. Begründung für jede Empfehlung
3. Geschätzte Trainingszeit
4. Erwarteter Nutzen

Berücksichtige Team-Synergien und Skill-Lücken.

Antworte auf Deutsch in strukturiertem Format.

Daten:
{data}
""",
            AnalysisType.GAP_ANALYSIS: """
Analysiere die Skill-Lücken dieses EVE Online Teams.

1. Kritische fehlende Skills
2. Welcher Charakter sollte welchen Skill trainieren?
3. Priorisierung nach Wichtigkeit
4. Geschätzter Zeitaufwand

Antworte auf Deutsch.

Daten:
{data}
""",
            AnalysisType.WEEKLY_SUMMARY: """
Erstelle eine Wochen-Zusammenfassung für dieses EVE Online Team.

1. SP-Fortschritt pro Charakter
2. Erreichte Meilensteine
3. Highlights der Woche
4. Fokus für nächste Woche

Antworte auf Deutsch, kurz und prägnant.

Daten:
{data}
""",
            AnalysisType.MONTHLY_REVIEW: """
Erstelle einen Monatsrückblick für dieses EVE Online Team.

1. SP-Entwicklung und Trends
2. Wichtige Skill-Fortschritte
3. Erfüllte und offene Trainingsempfehlungen
4. Strategische Ausrichtung für den nächsten Monat
5. Langfristige Ziele und Meilensteine

Antworte auf Deutsch, umfassend aber strukturiert.

Daten:
{data}
""",
        }

        template = prompts.get(analysis_type, prompts[AnalysisType.INDIVIDUAL_ASSESSMENT])
        return template.format(data=json.dumps(input_data, indent=2, default=str))


# Module-level singleton
skill_analysis_service = SkillAnalysisService()
