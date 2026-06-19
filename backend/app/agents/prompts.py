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
    2. If ready to search, acknowledge and optionally surface one optional question.
    3. If not yet ready and fields are missing, ask for them (phased by prompt count).
    4. Default: open-ended prompt to share priorities.
    """
    def _top_question() -> str | None:
        for q in follow_up_questions[:1]:
            if isinstance(q, dict):
                return q.get("question") or q.get("mapsToAttribute") or None
        return None

    # --- Clarifying answer (user asked a question) ---
    if clarifying_answer:
        if ready_to_search:
            top_q = _top_question()
            if top_q:
                return f"{clarifying_answer} One thing that could also help: {top_q}"
        elif missing_fields:
            field_list = ", ".join(missing_fields)
            return f"{clarifying_answer} I still need a little more detail about: {field_list}."
        return clarifying_answer

    # --- Ready to search: always acknowledge the turn, surface at most one optional question ---
    if ready_to_search:
        top_q = _top_question()
        if top_q:
            return f"Got it. {top_q} Or search now if you're ready."
        return (
            f"Got it — {len(raw_requirements)} requirements for {category}. "
            f"Search now or keep refining."
        )

    # --- Not yet ready: phase-appropriate follow-up ---
    if missing_fields:
        if prompt_count < 2:
            field_list = ", ".join(missing_fields)
            return f"Got it. I still need a little more detail about: {field_list}."

        question_texts = [
            q.get("question", q.get("mapsToAttribute", ""))
            for q in follow_up_questions[:5]
            if isinstance(q, dict)
        ]
        if not question_texts:
            question_texts = missing_fields[:5]
        question_list = " ".join(f"{i + 1}. {q}" for i, q in enumerate(question_texts))
        return f"A few useful follow-up questions: {question_list}"

    # --- Default: encourage the user to share more ---
    return "Got it. Tell me one or two things that matter most for this decision."
