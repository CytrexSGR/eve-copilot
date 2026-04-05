"""
Skill Analysis Router - LLM-powered character and team analysis endpoints.
Migrated from monolith to character-service.
"""

from fastapi import APIRouter, HTTPException, Query, Request
from typing import Optional
from enum import Enum
from psycopg2.extras import RealDictCursor

from app.services.skill_analysis_service import (
    skill_analysis_service,
    AnalysisType
)

router = APIRouter()


class AnalysisTypeParam(str, Enum):
    """Analysis types for API parameters"""
    individual = "individual_assessment"
    team = "team_composition"
    training = "training_priorities"
    roles = "role_optimization"
    gaps = "gap_analysis"
    weekly = "weekly_summary"
    monthly = "monthly_review"


@router.get("/profile/{character_id}")
def get_character_profile(request: Request, character_id: int):
    """Get character profile formatted for analysis."""
    try:
        profile = skill_analysis_service.get_character_profile(request, character_id)
        if not profile:
            raise HTTPException(status_code=404, detail=f"Character {character_id} not found")
        return profile
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/team")
def get_team_overview(request: Request):
    """Get team overview with all characters."""
    try:
        return skill_analysis_service.get_team_overview(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/gaps")
def get_skill_gaps(request: Request):
    """Get skill gaps - skills no character has at level 4+."""
    try:
        return skill_analysis_service.get_skill_gaps(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/comparison")
def get_skill_comparison(request: Request):
    """Get skill comparison matrix for all characters."""
    try:
        return skill_analysis_service.get_skill_comparison(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/unique")
def get_unique_capabilities(request: Request):
    """Get unique capabilities per character."""
    try:
        return skill_analysis_service.get_unique_capabilities(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/progress")
def get_recent_progress(request: Request, days: int = Query(30, ge=1, le=365)):
    """Get recent SP progress for all characters."""
    try:
        return skill_analysis_service.get_recent_progress(request, days)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/snapshot")
def create_snapshots(request: Request):
    """Create skill snapshots for all characters."""
    try:
        results = skill_analysis_service.create_all_snapshots(request)
        return {
            "status": "success",
            "snapshots_created": len(results),
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/snapshot/{character_id}")
def create_character_snapshot(request: Request, character_id: int):
    """Create skill snapshot for a specific character."""
    try:
        snapshot_id = skill_analysis_service.create_snapshot(request, character_id)
        return {
            "status": "success",
            "character_id": character_id,
            "snapshot_id": snapshot_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analysis/prepare")
def prepare_analysis(
    request: Request,
    analysis_type: AnalysisTypeParam,
    character_ids: Optional[str] = Query(None, description="Comma-separated character IDs")
):
    """Prepare input data for LLM analysis."""
    try:
        char_ids = None
        if character_ids:
            char_ids = [int(x.strip()) for x in character_ids.split(",")]

        data = skill_analysis_service.prepare_analysis_input(
            request,
            AnalysisType(analysis_type.value),
            char_ids
        )
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analysis/prompt")
def get_analysis_prompt(
    request: Request,
    analysis_type: AnalysisTypeParam,
    character_ids: Optional[str] = Query(None, description="Comma-separated character IDs")
):
    """Get the LLM prompt for an analysis type."""
    try:
        char_ids = None
        if character_ids:
            char_ids = [int(x.strip()) for x in character_ids.split(",")]

        input_data = skill_analysis_service.prepare_analysis_input(
            request,
            AnalysisType(analysis_type.value),
            char_ids
        )
        prompt = skill_analysis_service.generate_analysis_prompt(
            AnalysisType(analysis_type.value),
            input_data
        )
        return {
            "analysis_type": analysis_type.value,
            "prompt": prompt,
            "input_data": input_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reports/latest")
def get_latest_report(
    request: Request,
    report_type: Optional[AnalysisTypeParam] = None
):
    """Get the latest analysis report."""
    try:
        analysis_type = AnalysisType(report_type.value) if report_type else None
        report = skill_analysis_service.get_latest_report(request, analysis_type)
        if not report:
            return {"message": "No reports found"}
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recommendations/pending")
def get_pending_recommendations(
    request: Request,
    character_id: Optional[int] = None
):
    """Get pending training recommendations."""
    try:
        return skill_analysis_service.get_pending_recommendations(request, character_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recommendations/{recommendation_id}/complete")
def complete_recommendation(request: Request, recommendation_id: int):
    """Mark a training recommendation as completed."""
    try:
        success = skill_analysis_service.mark_recommendation_completed(request, recommendation_id)
        if not success:
            raise HTTPException(status_code=404, detail="Recommendation not found or already completed")
        return {"status": "completed", "recommendation_id": recommendation_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/isk-opportunities")
def get_isk_opportunities(request: Request):
    """Get ISK-making opportunities based on team skills.

    Analyzes character skills to determine the best money-making activities
    and which character should do what.
    """
    try:
        db = request.app.state.db
        with db.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM v_isk_opportunities")
            return [dict(row) for row in cur.fetchall()]
    except Exception as e:
        # View might not exist yet
        raise HTTPException(status_code=500, detail=str(e))
