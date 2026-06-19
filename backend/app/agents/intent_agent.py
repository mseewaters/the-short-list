"""Intent agent: validates and locks the product category for this session."""

from app.state import shortlistState


def intent_agent(state: shortlistState) -> shortlistState:
    category = state.get("category")
    trace_message = (
        f"Intent Agent: category locked = {category}"
        if category
        else "Intent Agent: category missing; category intelligence must run first"
    )

    return {
        **state,
        "category": category,
        "agent_trace": [*state.get("agent_trace", []), trace_message],
    }
