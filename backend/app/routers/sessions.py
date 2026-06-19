"""Session management router.

Provides POST /sessions to create a new search session scoped to a single
product decision. Sessions are stored in the in-memory session store.
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, HTTPException

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


@router.post("/sessions/{session_id}/reset-requirements")
def reset_requirements(session_id: str):
    session = sessions.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    now = datetime.now(timezone.utc).isoformat()
    preserved_category = (session.get("search_intent") or {}).get("category_label")

    session["user_requirement_profile"] = None
    session["clarification_prompt_count"] = 0
    session["messages"] = []
    session["updated_at"] = now
    session["search_intent"] = {
        "id": f"intent_{session_id}",
        "category_label": preserved_category,
        "category_confidence": "high" if preserved_category else "low",
        "user_requirement_profile": None,
        "raw_requirements": {},
        "requirements": [],
        "constraints": [],
        "missing_fields": [],
        "ready_to_search": False,
        "clarification_prompt_count": 0,
    } if preserved_category else None

    return {"status": "reset", "session_id": session_id}
