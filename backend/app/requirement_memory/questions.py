"""Follow-up question generation for the requirement clarification phase.

Decides which attributes to ask about next, based on what the user has already
told us, which phase of the conversation we're in, and what the category schema
says is important.
"""

from app.schemas import FollowUpQuestion, UserRequirement
from app.requirement_memory.attributes import (
    extract_attribute_schema,
    canonical_attribute,
    canonical_attribute_key,
    closest_schema_attribute,
)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def build_follow_up_questions(
    *,
    requirements: list[UserRequirement],
    category_context: dict | None,
    clarification_prompt_count: int = 0,
) -> list[FollowUpQuestion]:
    """Return up to 5 follow-up questions appropriate for the current prompt count.

    Phase 0-1 (prompt_count < 2): critical attributes only.
    Phase 2-4: intake questions then decision-axis tradeoffs.
    Phase 5+: no more questions; the user can proceed to search.
    """
    attributes = extract_attribute_schema(category_context)
    intake_questions = category_context.get("intake_questions", []) if category_context else []
    known = known_attribute_names(requirements, attributes, category_context)
    questions: list[FollowUpQuestion] = []
    queued_names: set[str] = set()

    if clarification_prompt_count >= 5:
        return []

    # --- Vague requirements that need specification ---
    for requirement in requirements:
        if not requirement.needsMoreSpecification or not requirement.specificationQuestion:
            continue
        attribute_name = requirement.attributeName
        if attribute_name.lower() in queued_names:
            continue
        queued_names.add(attribute_name.lower())
        questions.append(
            FollowUpQuestion(
                question=requirement.specificationQuestion,
                mapsToAttribute=attribute_name,
                priority=requirement.importance,
                reason="requirement_needs_more_specification_for_scoring",
            )
        )
        if len(questions) >= 5:
            return questions

    # --- Early phase: critical attributes only ---
    if clarification_prompt_count < 2:
        for attribute in critical_attributes(attributes):
            attribute_name = str(attribute.get("name", "")).strip()
            attribute_key = canonical_attribute_key(attribute_name, attributes, category_context)
            if not should_queue_attribute(attribute_name, known, queued_names, attributes, category_context):
                continue
            queued_names.add(attribute_key)
            questions.append(
                FollowUpQuestion(
                    question=f"What do you need for {attribute_name}?",
                    mapsToAttribute=attribute_name,
                    priority=str(attribute.get("importance", "critical")),
                    reason="missing_absolute_minimum_critical_requirement",
                )
            )
            if len(questions) >= 5:
                return questions
        return questions

    # --- Mid phase: intake questions ---
    for question in intake_questions:
        if not isinstance(question, dict):
            continue
        attribute_name = str(question.get("maps_to_attribute", "")).strip()
        attribute_key = canonical_attribute_key(attribute_name, attributes, category_context)
        if not should_queue_attribute(attribute_name, known, queued_names, attributes, category_context):
            continue
        queued_names.add(attribute_key)
        questions.append(
            FollowUpQuestion(
                question=str(question.get("question", f"What do you need for {attribute_name}?")),
                mapsToAttribute=attribute_name,
                priority=str(question.get("priority", "medium")),
                reason="missing_intake_attribute",
            )
        )
        if len(questions) >= 5:
            return questions

    # --- Late phase: decision-axis tradeoffs ---
    for question in decision_axis_questions(category_context, attributes, known):
        attribute_name = question.mapsToAttribute
        attribute_key = canonical_attribute_key(attribute_name, attributes, category_context)
        if not should_queue_attribute(attribute_name, known, queued_names, attributes, category_context):
            continue
        queued_names.add(attribute_key)
        questions.append(question)
        if len(questions) >= 5:
            return questions

    return questions


# ---------------------------------------------------------------------------
# Attribute selection helpers
# ---------------------------------------------------------------------------

def critical_attributes(attributes: list[dict]) -> list[dict]:
    """Return critical attributes; fall back to high-importance must-have/lower-is-better."""
    critical = [
        a for a in attributes
        if a.get("importance") == "critical" and a.get("comparison_relevant", True)
    ]
    if critical:
        return critical
    return [
        a for a in attributes
        if (
            a.get("importance") == "high"
            and a.get("comparison_relevant", True)
            and str(a.get("score_direction", "")) in {"must_have", "lower_is_better"}
        )
    ]


def known_attribute_names(
    requirements: list[UserRequirement],
    attributes: list[dict],
    category_context: dict | None,
) -> set[str]:
    """Return canonical keys for all attributes already present in the profile."""
    known: set[str] = set()
    for requirement in requirements:
        if requirement.status not in {"specified", "inferred", "ignored"}:
            continue
        for name in {requirement.attributeName, canonical_attribute(requirement.attributeName, attributes, category_context)}:
            known.add(canonical_attribute_key(name, attributes, category_context))
    return known


def should_queue_attribute(
    attribute_name: str,
    known: set[str],
    queued_names: set[str],
    attributes: list[dict] | None = None,
    category_context: dict | None = None,
) -> bool:
    if not attribute_name:
        return False
    key = (
        canonical_attribute_key(attribute_name, attributes, category_context)
        if attributes is not None
        else attribute_name.lower()
    )
    return key not in known and key not in queued_names


# ---------------------------------------------------------------------------
# Decision-axis question generation
# ---------------------------------------------------------------------------

def decision_axis_questions(
    category_context: dict | None,
    attributes: list[dict],
    known: set[str],
) -> list[FollowUpQuestion]:
    """Generate questions from decision axes for attributes not yet covered."""
    axes = category_context.get("decision_axes", []) if category_context else []
    if not isinstance(axes, list):
        return []

    questions: list[FollowUpQuestion] = []
    for axis in axes:
        if not isinstance(axis, dict):
            continue
        axis_text = " ".join(
            str(axis.get(f, "")) for f in ["name", "positive_direction", "tradeoff_against"]
        )
        attribute = closest_schema_attribute(axis_text, attributes, category_context)
        if attribute is None:
            continue
        attribute_name = str(attribute.get("name", "")).strip()
        if not attribute_name or attribute_name.lower() in known:
            continue
        questions.append(
            FollowUpQuestion(
                question=axis_question_text(axis, attribute_name),
                mapsToAttribute=attribute_name,
                priority="medium",
                reason="missing_decision_axis_tradeoff",
            )
        )

    return questions


def axis_question_text(axis: dict, attribute_name: str) -> str:
    axis_name = str(axis.get("name", "")).strip()
    positive_direction = str(axis.get("positive_direction", "")).strip()
    tradeoff_against = str(axis.get("tradeoff_against", "")).strip()

    if tradeoff_against:
        return f"For {attribute_name}, how do you want to balance {axis_name or positive_direction} against {tradeoff_against}?"
    if positive_direction:
        return f"For {attribute_name}, does {positive_direction} matter for this decision?"
    return f"What tradeoff matters most for {attribute_name}?"
