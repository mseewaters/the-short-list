"""Response agent: generates the agent's reply for the current conversation turn."""

from app.agents.prompts import build_response_message
from app.state import shortlistState


def response_agent(state: shortlistState) -> shortlistState:
    follow_up_questions = (
        (state.get("user_requirement_profile") or {}).get("followUpQuestions", [])
        if isinstance(state.get("user_requirement_profile"), dict)
        else []
    )

    agent_message = build_response_message(
        category=state.get("category"),
        raw_requirements=state.get("raw_requirements", {}),
        missing_fields=state.get("missing_fields", []),
        clarifying_answer=state.get("clarifying_answer"),
        follow_up_questions=follow_up_questions,
        prompt_count=state.get("clarification_prompt_count", 0),
        ready_to_search=state.get("ready_to_search", False),
    )

    return {
        **state,
        "agent_message": agent_message,
        "agent_trace": [
            *state.get("agent_trace", []),
            f"Response Agent: ready_to_search = {str(state.get('ready_to_search', False)).lower()}",
        ],
    }
