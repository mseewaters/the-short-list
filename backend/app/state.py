"""LangGraph state definition for the shortlist agent pipeline."""

from typing import TypedDict


class shortlistState(TypedDict):
    # The user's raw message for this turn
    user_message: str

    # Product category selected by the user or inferred from their first message
    category: str | None

    # Normalized category intelligence (attribute schema, entities, questions, etc.)
    category_context: dict | None

    # The user's very first message (preserved for context across turns)
    original_user_prompt: str | None

    # Accumulated requirement profile (serialized UserRequirementProfile)
    user_requirement_profile: dict | None

    # Flat {attributeName: value} snapshot derived from the profile
    raw_requirements: dict

    # Attribute names still needing user input
    missing_fields: list[str]

    # Answer to a clarifying question asked in this turn, if any
    clarifying_answer: str | None

    # Number of clarification prompts sent so far (drives phased question strategy)
    clarification_prompt_count: int

    # Agent reply rendered in the conversation panel
    agent_message: str

    # True when there are enough requirements to run a search
    ready_to_search: bool

    # Per-node log entries for the activity feed
    agent_trace: list[str]
