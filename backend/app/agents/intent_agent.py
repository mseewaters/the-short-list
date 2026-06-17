from app.state import shortlistState


def intent_agent(state: shortlistState) -> shortlistState:
    message = state["user_message"].lower()
    category = None

    if "ceiling fan" in message or "fan" in message:
        category = "ceiling fan"
    elif "robot vacuum" in message or "roomba" in message:
        category = "robot vacuum"
    elif "projector" in message:
        category = "projector"

    activity_events = [
        *state.get("activity_events", []),
        {
            "node": "intent_agent",
            "label": "Intent Agent",
            "detail": f"category = {category or 'unknown'}",
            "status": "complete",
        },
    ]

    return {
        **state,
        "category": category,
        "activity_events": activity_events,
    }
