import json
import logging
import os
from datetime import datetime, timezone
from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/feedback", tags=["feedback"])

FEEDBACK_FILE = os.environ.get("FEEDBACK_FILE", "/app/data/feedback.json")


class FeedbackRequest(BaseModel):
    category: str = Field(..., max_length=50)
    message: str = Field(..., min_length=10, max_length=2000)
    page_url: str = Field("", max_length=500)


@router.post("")
def submit_feedback(body: FeedbackRequest, request: Request):
    """Accept user feedback and append to JSON file."""
    account_id = None
    character_name = None
    token = request.cookies.get("session_token")
    if token:
        try:
            from app.services.jwt_service import _get_jwt_service
            jwt = _get_jwt_service()
            claims = jwt.validate_token(token)
            account_id = claims.get("account_id")
            character_name = claims.get("sub")
        except Exception:
            pass

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "account_id": account_id,
        "character_name": character_name,
        "category": body.category,
        "message": body.message,
        "page_url": body.page_url,
    }

    try:
        os.makedirs(os.path.dirname(FEEDBACK_FILE), exist_ok=True)
        entries = []
        if os.path.exists(FEEDBACK_FILE):
            with open(FEEDBACK_FILE, "r") as f:
                entries = json.load(f)
        entries.append(entry)
        with open(FEEDBACK_FILE, "w") as f:
            json.dump(entries, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to write feedback: {e}")

    logger.info(f"Feedback received: category={body.category} account={account_id}")
    return {"status": "ok"}
