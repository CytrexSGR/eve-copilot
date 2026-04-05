"""HR Application Portal endpoints."""
import logging
from typing import Optional
from fastapi import APIRouter, Request, Query, HTTPException
from pydantic import BaseModel
from eve_shared.utils.error_handling import handle_endpoint_errors

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/applications", tags=["applications"])


class ApplicationSubmit(BaseModel):
    character_id: int
    character_name: str
    corporation_id: Optional[int] = None
    motivation: Optional[str] = None


class ApplicationReview(BaseModel):
    recruiter_id: int
    recruiter_notes: Optional[str] = None
    status: str  # reviewing, approved, rejected


@router.post("/submit")
@handle_endpoint_errors()
def submit_application(request: Request, app_data: ApplicationSubmit):
    """Submit a new recruitment application."""
    db = request.app.state.db
    with db.cursor() as cur:
        cur.execute("""
            SELECT id FROM hr_applications
            WHERE character_id = %s AND status IN ('pending', 'reviewing')
        """, (app_data.character_id,))
        existing = cur.fetchone()
        if existing:
            return {"error": "Active application already exists", "application_id": existing["id"]}

        cur.execute("""
            INSERT INTO hr_applications (character_id, character_name, corporation_id, motivation)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (app_data.character_id, app_data.character_name,
              app_data.corporation_id, app_data.motivation))
        row = cur.fetchone()

    return {"application_id": row["id"], "status": "pending"}


@router.get("/")
@handle_endpoint_errors()
def list_applications(
    request: Request,
    status: Optional[str] = None,
    corporation_id: Optional[int] = None,
    limit: int = Query(default=50, le=200),
):
    """List applications, optionally filtered."""
    db = request.app.state.db
    conditions = []
    params = {"limit": limit}

    if status:
        conditions.append("status = %(status)s")
        params["status"] = status
    if corporation_id:
        conditions.append("corporation_id = %(corporation_id)s")
        params["corporation_id"] = corporation_id

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    with db.cursor() as cur:
        cur.execute(f"""
            SELECT id, character_id, character_name, corporation_id,
                   status, motivation, recruiter_id, submitted_at, decided_at
            FROM hr_applications
            {where}
            ORDER BY submitted_at DESC
            LIMIT %(limit)s
        """, params)
        rows = cur.fetchall()

    return {"applications": [dict(r) for r in rows], "count": len(rows)}


@router.get("/{application_id}")
@handle_endpoint_errors()
def get_application(request: Request, application_id: int):
    """Get application detail with vetting report."""
    db = request.app.state.db
    with db.cursor() as cur:
        cur.execute("""
            SELECT a.*, v.risk_score, v.flags as vetting_flags
            FROM hr_applications a
            LEFT JOIN vetting_reports v ON a.vetting_report_id = v.id
            WHERE a.id = %s
        """, (application_id,))
        row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Application not found")
    return dict(row)


@router.put("/{application_id}/review")
@handle_endpoint_errors()
def review_application(
    request: Request,
    application_id: int,
    review: ApplicationReview,
):
    """Review an application — assign recruiter and update status."""
    if review.status not in ("reviewing", "approved", "rejected"):
        raise HTTPException(status_code=400, detail="Invalid status")

    db = request.app.state.db
    with db.cursor() as cur:
        set_parts = [
            "recruiter_id = %s",
            "recruiter_notes = %s",
            "status = %s",
            "reviewed_at = COALESCE(reviewed_at, NOW())",
        ]
        params = [review.recruiter_id, review.recruiter_notes, review.status]

        if review.status in ("approved", "rejected"):
            set_parts.append("decided_at = NOW()")

        params.append(application_id)

        cur.execute(f"""
            UPDATE hr_applications
            SET {', '.join(set_parts)}
            WHERE id = %s
            RETURNING id, status
        """, params)
        row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Application not found")
    return {"application_id": row["id"], "status": row["status"]}


@router.post("/{application_id}/vet")
@handle_endpoint_errors()
async def trigger_vetting(request: Request, application_id: int):
    """Trigger automated vetting for an application."""
    db = request.app.state.db
    with db.cursor() as cur:
        cur.execute("SELECT character_id FROM hr_applications WHERE id = %s", (application_id,))
        app_row = cur.fetchone()

    if not app_row:
        raise HTTPException(status_code=404, detail="Application not found")

    from app.services.vetting_engine import VettingEngine
    engine = VettingEngine()
    report = await engine.check_applicant(app_row["character_id"])

    with db.cursor() as cur:
        cur.execute("""
            UPDATE hr_applications
            SET vetting_report_id = (
                SELECT id FROM vetting_reports
                WHERE character_id = %s ORDER BY checked_at DESC LIMIT 1
            )
            WHERE id = %s
        """, (app_row["character_id"], application_id))

    return {"application_id": application_id, "vetting_report": report}
