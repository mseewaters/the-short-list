"""Agent response message builders.

Contains all user-facing message templates used by the response agent.
Separating message construction from agent orchestration keeps the agent
logic easy to read and the message copy easy to iterate on.
"""


def build_response_message(
    *,
    category: str | None,
    raw_requirements: dict,
    missing_fields: list[str],
    clarifying_answer: str | None,
    follow_up_questions: list[dict],
    prompt_count: int,
    ready_to_search: bool,
) -> str:
    """Return the agent's reply for the current turn.

    Priority order:
    1. If the user asked a question, lead with the answer.
    2. If fields are still missing, ask for them (phased by prompt count).
    3. If ready to search, confirm with a summary.
    4. Default: open-ended prompt to share priorities.
    """
    # --- Clarifying answer (user asked a question) ---
    if clarifying_answer:
        if missing_fields:
            field_list = ", ".join(missing_fields)
            return f"{clarifying_answer} I still need a little more detail about: {field_list}."
        return clarifying_answer

    # --- Missing fields: phase-appropriate follow-up ---
    if missing_fields:
        if prompt_count < 2:
            field_list = ", ".join(missing_fields)
            return f"Got it. I still need a little more detail about: {field_list}."

        if prompt_count >= 4:
            field_list = ", ".join(missing_fields)
            return f"You can move to research now, or add more detail about: {field_list}."

        question_texts = [
            q.get("question", q.get("mapsToAttribute", ""))
            for q in follow_up_questions[:5]
            if isinstance(q, dict)
        ]
        if not question_texts:
            question_texts = missing_fields[:5]
        question_list = " ".join(f"{i + 1}. {q}" for i, q in enumerate(question_texts))
        return f"A few useful follow-up questions: {question_list}"

    # --- Ready to search ---
    if ready_to_search:
        return (
            f"I think I have enough to start. I am hearing {category}, with "
            f"{len(raw_requirements)} requirements to review."
        )

    # --- Default: encourage the user to share more ---
    return "Got it. Tell me one or two things that matter most for this decision."
