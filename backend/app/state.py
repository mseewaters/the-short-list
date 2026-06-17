from typing import TypedDict

class shortlistState(TypedDict):
    user_message: str

    category: str | None

    raw_requirements: dict

    missing_fields: list[str]

    agent_message: str

    ready_to_search: bool