"""Clarify router: POST /clarify.

Accepts a user message, runs the LangGraph agent pipeline, accumulates
requirement memory, and returns the updated requirement profile and agent reply.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.graph import compiled_graph
from app.requirement_memory import profile_to_requirement_display
from app.schemas import (
    ClarifyRequest,
    ClarifyResponse,
    Requirement,
    UserRequirementProfile,
)
from app.session_store import sessions

router = APIRouter()


@router.post("/clarify", response_model=ClarifyResponse)
def clarify(request: ClarifyRequest):
    session = sessions.get(request.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    now = datetime.now(timezone.utc).isoformat()
    session["updated_at"] = now
    session["messages"].append({"role": "user", "text": request.message, "timestamp": now})

    previous_intent = session.get("search_intent") or {}
    previous_profile = session.get("user_requirement_profile")
    previous_category = previous_intent.get("category_label")
    selected_category = request.category or previous_category
    category_changed = bool(request.category and previous_category and request.category != previous_category)
    active_profile = None if category_changed else previous_profile
    active_raw_requirements = {} if category_changed else previous_intent.get("raw_requirements", {})
    previous_prompt_count = 0 if category_changed else previous_intent.get(
        "clarification_prompt_count",
        session.get("clarification_prompt_count", 0),
    )

    graph_state = compiled_graph.invoke(
        {
            "user_message": request.message,
            "category": selected_category,
            "category_context": request.category_context,
            "original_user_prompt": (
                active_profile.get("originalUserPrompt")
                if isinstance(active_profile, dict)
                else request.message
            ),
            "user_requirement_profile": active_profile,
            "raw_requirements": active_raw_requirements,
            "missing_fields": previous_intent.get("missing_fields", []),
            "clarifying_answer": None,
            "clarification_prompt_count": previous_prompt_count,
            "agent_message": "Got it. I will turn that into requirements next.",
            "ready_to_search": False,
            "agent_trace": (
                ["Clarify: category changed; reset requirement memory"] if category_changed else []
            ),
        }
    )

    requirements = [
        Requirement(label=key, value=value)
        for key, value in graph_state.get("raw_requirements", {}).items()
    ]
    user_requirement_profile = UserRequirementProfile(**graph_state["user_requirement_profile"])
    next_prompt_count = previous_prompt_count
    if graph_state.get("missing_fields") and previous_prompt_count < 5:
        next_prompt_count += 1

    search_intent = {
        "id": f"intent_{request.session_id}",
        "category_label": graph_state.get("category"),
        "category_confidence": "high" if graph_state.get("category") else "low",
        "user_requirement_profile": user_requirement_profile.model_dump(),
        "raw_requirements": graph_state.get("raw_requirements", {}),
        "requirements": [r.model_dump() for r in requirements],
        "constraints": [],
        "missing_fields": graph_state.get("missing_fields", []),
        "ready_to_search": graph_state.get("ready_to_search", False),
        "clarification_prompt_count": next_prompt_count,
    }

    agent_message = graph_state.get("agent_message", "")
    session["search_intent"] = search_intent
    session["user_requirement_profile"] = user_requirement_profile.model_dump()
    session["clarification_prompt_count"] = next_prompt_count
    session["messages"].append(
        {
            "role": "agent",
            "text": agent_message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )

    return ClarifyResponse(
        category=graph_state.get("category"),
        requirements=requirements,
        user_requirement_profile=user_requirement_profile,
        missing_fields=graph_state.get("missing_fields", []),
        agent_trace=graph_state.get("agent_trace", []),
        agent_message=agent_message,
        ready_to_search=graph_state.get("ready_to_search", False),
    )
