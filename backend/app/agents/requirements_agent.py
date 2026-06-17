from app.state import shortlistState


def requirements_agent(state: shortlistState) -> shortlistState:
    message = state["user_message"].lower()
    requirements: dict[str, str] = {}

    if "quiet" in message or "noise" in message:
        requirements["quiet_operation"] = "User wants the product to be quiet."

    if "low profile" in message or "low-profile" in message or "low ceiling" in message:
        requirements["low_profile"] = "User needs a low-profile fit for limited ceiling height."

    if "not ugly" in message or "style" in message or "nice looking" in message:
        requirements["appearance"] = "User cares about appearance and wants it to look acceptable."

    if "bedroom" in message:
        requirements["bedroom_use"] = "Product will be used in a bedroom."

    if "old house" in message:
        requirements["old_house_compatibility"] = "Product should work in an older house context."

    missing_fields = []
    if state.get("category") is None:
        missing_fields.append("product category")
    if not requirements:
        missing_fields.append("what matters most")

    ready_to_search = state.get("category") is not None and len(requirements) >= 3
    activity_events = [
        *state.get("activity_events", []),
        {
            "node": "requirements_agent",
            "label": "Requirements Agent",
            "detail": f"extracted {len(requirements)} requirements",
            "status": "complete",
        },
    ]

    return {
        **state,
        "raw_requirements": requirements,
        "missing_fields": missing_fields,
        "ready_to_search": ready_to_search,
        "activity_events": activity_events,
    }
