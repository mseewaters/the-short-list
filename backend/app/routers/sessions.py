"""Session management router.

Provides POST /sessions to create a new search session scoped to a single
product decision. Sessions are stored in the in-memory session store.
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter

from app.schemas import CreateSessionRequest, SessionResponse
from app.session_store import sessions

router = APIRouter()


@router.post("/sessions", response_model=SessionResponse)
def create_session(request: CreateSessionRequest):
    session_id = f"sess_{uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()

    sessions[session_id] = {
        "session_id": session_id,
        "user_id": request.user_id,
        "created_at": now,
        "updated_at": now,
        "messages": [],
        "search_intent": None,
        "user_requirement_profile": None,
        "clarification_prompt_count": 0,
    }

    return SessionResponse(
        session_id=session_id,
        messages=sessions[session_id]["messages"],
        search_intent=sessions[session_id]["search_intent"],
    )
