"""Requirements agent: extracts requirements from the user message and updates the profile."""

from app.requirement_memory import (
    answer_user_clarifying_question,
    missing_fields_from_profile,
    profile_to_requirement_display,
    update_user_requirement_profile,
)
from app.requirement_memory.attributes import extract_attribute_schema
from app.state import shortlistState


def requirements_agent(state: shortlistState) -> shortlistState:
    clarifying_answer = answer_user_clarifying_question(
        category_name=state.get("category"),
        latest_user_message=state["user_message"],
        category_context=state.get("category_context"),
    )
    profile = update_user_requirement_profile(
        state.get("user_requirement_profile"),
        category_name=state.get("category"),
        original_user_prompt=state.get("original_user_prompt"),
        latest_user_message=state["user_message"],
        category_context=state.get("category_context"),
        clarification_prompt_count=state.get("clarification_prompt_count", 0),
    )
    display_requirements = profile_to_requirement_display(profile)
    raw_requirements = {r["label"]: r["value"] for r in display_requirements}
    missing_fields = missing_fields_from_profile(profile)
    prompt_count = state.get("clarification_prompt_count", 0)

    # Build the set of search_gate attribute names so we only block on
    # "needs more specification" for attributes that actually gate the search.
    decision_attributes = extract_attribute_schema(state.get("category_context") or {})
    search_gate_names = {
        str(a.get("name", "")).lower()
        for a in decision_attributes
        if a.get("search_gate")
    }
    blocking_fields = []
    for q in profile.followUpQuestions:
        if q.reason == "missing_search_gate_requirement":
            blocking_fields.append(q)
        elif (
            q.reason == "requirement_needs_more_specification_for_scoring"
            and q.mapsToAttribute.lower() in search_gate_names
        ):
            blocking_fields.append(q)
    ready_to_search = (
        state.get("category") is not None
        and bool(display_requirements)
        and (len(blocking_fields) == 0 or prompt_count >= 4)
    )

    return {
        **state,
        "user_requirement_profile": profile.model_dump(),
        "raw_requirements": raw_requirements,
        "missing_fields": missing_fields,
        "clarifying_answer": clarifying_answer,
        "ready_to_search": ready_to_search,
        "agent_trace": [
            *state.get("agent_trace", []),
            f"Requirements Agent: updated UserRequirementProfile with {len(profile.requirements)} memory items",
            (
                "Requirements Agent: answered user clarifying question"
                if clarifying_answer
                else "Requirements Agent: no user clarifying question detected"
            ),
        ],
    }
