from app.state import shortlistState


def intent_agent(state: shortlistState) -> shortlistState:
    message = state["user_message"].lower()
    category = state.get("category")

    if "ceiling fan" in message or "fan" in message:
        category = "Ceiling fan"
    elif "robot vacuum" in message or "roomba" in message:
        category = "Robot vacuum"
    elif "tv" in message or "television" in message:
        category = "TV"
    elif "coffee maker" in message or "coffee" in message:
        category = "Coffee maker"
    elif "router" in message or "wi-fi" in message or "wifi" in message:
        category = "Router"

    return {
        **state,
        "category": category,
        "agent_trace": [
            *state.get("agent_trace", []),
            f"Intent Agent: category = {category or 'unknown'}",
        ],
    }
