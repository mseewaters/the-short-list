from app.state import shortlistState


def response_agent(state: shortlistState) -> shortlistState:
    category = state.get("category")
    raw_requirements = state.get("raw_requirements", {})
    missing_fields = state.get("missing_fields", [])

    if state.get("ready_to_search"):
        agent_message = (
            f"I think I have enough to start. I am hearing {category}, with "
            f"{len(raw_requirements)} requirements to review."
        )
    elif missing_fields:
        field_list = ", ".join(missing_fields)
        agent_message = f"Got it. I still need a little more detail about: {field_list}."
    else:
        agent_message = "Got it. Tell me one or two things that matter most for this decision."

    return {
        **state,
        "agent_message": agent_message,
        "agent_trace": [
            *state.get("agent_trace", []),
            f"Response Agent: ready_to_search = {str(state.get('ready_to_search', False)).lower()}",
        ],
    }
