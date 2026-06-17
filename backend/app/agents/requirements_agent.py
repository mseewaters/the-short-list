import re

from app.state import shortlistState


def first_match(pattern: str, message: str) -> str | None:
    match = re.search(pattern, message, re.IGNORECASE)
    if match is None:
        return None

    return match.group(0)


def requirements_agent(state: shortlistState) -> shortlistState:
    message = state["user_message"].lower()
    requirements: dict[str, str] = dict(state.get("raw_requirements", {}))

    if "old house" in message and "bedroom" in message:
        requirements["Room"] = "Old house bedroom"
    elif "bedroom" in message:
        requirements["Room"] = "Bedroom"
    elif "old house" in message:
        requirements["Room"] = "Old house"

    if "quiet" in message or "noise" in message:
        requirements["Priority: Quiet operation"] = "Quiet operation"

    if "low profile" in message or "low-profile" in message or "low ceiling" in message:
        requirements["Priority: Low profile"] = "Low profile"

    if "not ugly" in message or "style" in message or "nice looking" in message:
        requirements["Priority: Attractive design"] = "Attractive design"

    if state.get("category") == "Robot vacuum":
        if "elderly" in message or "parents" in message:
            requirements["User context"] = "Elderly parents"
            requirements["Priority: Easy maintenance"] = "Easy maintenance for older users"
        if "dog" in message or "dogs" in message or "pet" in message:
            requirements["Priority: Pet hair handling"] = "Two dogs / pet hair"
        requirements.setdefault("Priority: Simple controls", "Simple controls")

    if state.get("category") == "TV":
        if "bright room" in message or "bright" in message:
            requirements["Room"] = "Bright room"
            requirements["Priority: High brightness"] = "High brightness for glare"
        requirements.setdefault("Priority: Anti-glare screen", "Anti-glare screen")

    if state.get("category") == "Coffee maker":
        if "single person" in message or "one person" in message:
            requirements["User context"] = "Single person"
        if "on the go" in message or "go" in message:
            requirements["Priority: Fast brewing"] = "Fast coffee for leaving the house"
        requirements.setdefault("Priority: Small footprint", "Small footprint")

    if state.get("category") == "Router":
        if "3-story" in message or "3 story" in message or "three-story" in message or "three story" in message:
            requirements["Home layout"] = "3-story house"
            requirements["Priority: Whole-home coverage"] = "Coverage across multiple floors"
        requirements.setdefault("Priority: Strong signal", "Strong signal")

    budget = first_match(r"(under|below|up to|around)?\s*\$ ?\d+", state["user_message"])
    if budget:
        requirements["Budget"] = budget.strip()

    room_dimensions = first_match(
        r"\d+\s*(by|x)\s*\d+\s*(feet|foot|ft)?",
        state["user_message"],
    )
    if room_dimensions:
        requirements["Room dimensions"] = room_dimensions.strip()

    ceiling_height = first_match(
        r"ceiling (height is|is|height:)?\s*\d+\s*(feet|foot|ft)",
        state["user_message"],
    )
    if ceiling_height:
        requirements["Ceiling height"] = ceiling_height.strip()

    missing_fields = []
    if state.get("category") is None:
        missing_fields.append("product category")
    if not requirements:
        missing_fields.append("what matters most")
    if state.get("category") == "Ceiling fan":
        for field in ["Budget", "Room dimensions", "Ceiling height"]:
            if field not in requirements:
                missing_fields.append(field)

    ready_to_search = state.get("category") is not None and bool(requirements)
    if state.get("category") == "Ceiling fan":
        ready_to_search = (
            "Budget" in requirements
            and "Ceiling height" in requirements
            and len(requirements) >= 5
        )

    return {
        **state,
        "raw_requirements": requirements,
        "missing_fields": missing_fields,
        "ready_to_search": ready_to_search,
        "agent_trace": [
            *state.get("agent_trace", []),
            f"Requirements Agent: extracted {len(requirements)} requirements",
        ],
    }
