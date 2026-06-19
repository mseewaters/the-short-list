"""Follow-up question generation for the requirement clarification phase.

Decides which attributes to ask about next, based on what the user has told us,
the conversation phase, and which attributes are search-gated in the category schema.
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

    Phase 0-1 (prompt_count < 2): search_gate attributes only.
    Phase 2+: all unresolved attributes, search_gate first. No upper cap —
    search_gate controls what actually blocks; optional questions are surfaced
    for as long as unresolved attributes remain.
    """
    attributes = extract_attribute_schema(category_context)
    known = known_attribute_names(requirements, attributes, category_context)
    questions: list[FollowUpQuestion] = []
    queued_keys: set[str] = set()

    # --- Vague requirements that need specification ---
    for requirement in requirements:
        if not requirement.needsMoreSpecification or not requirement.specificationQuestion:
            continue
        attr_key = canonical_attribute_key(requirement.attributeName, attributes, category_context)
        if attr_key in queued_keys:
            continue
        queued_keys.add(attr_key)
        questions.append(
            FollowUpQuestion(
                question=requirement.specificationQuestion,
                mapsToAttribute=requirement.attributeName,
                priority=requirement.importance,
                reason="requirement_needs_more_specification_for_scoring",
            )
        )
        if len(questions) >= 5:
            return questions

    if clarification_prompt_count < 2:
        # --- Early phase: search_gate attributes only ---
        for attribute in search_gate_attributes(attributes):
            attr_name = str(attribute.get("name", "")).strip()
            attr_key = canonical_attribute_key(attr_name, attributes, category_context)
            if not should_queue_attribute(attr_key, known, queued_keys):
                continue
            queued_keys.add(attr_key)
            question_text = attribute.get("clarifying_question") or f"What do you need for {attr_name}?"
            questions.append(
                FollowUpQuestion(
                    question=question_text,
                    mapsToAttribute=attr_name,
                    priority="high",
                    reason="missing_search_gate_requirement",
                )
            )
            if len(questions) >= 5:
                return questions
        return questions

    # --- Mid/late phase: all attributes, search_gate first ---
    ordered = sorted(attributes, key=lambda a: (not a.get("search_gate", False), a.get("name", "")))
    for attribute in ordered:
        attr_name = str(attribute.get("name", "")).strip()
        attr_key = canonical_attribute_key(attr_name, attributes, category_context)
        if not should_queue_attribute(attr_key, known, queued_keys):
            continue
        queued_keys.add(attr_key)
        question_text = attribute.get("clarifying_question") or f"What matters to you about {attr_name}?"
        priority = "high" if attribute.get("search_gate") else "medium"
        questions.append(
            FollowUpQuestion(
                question=question_text,
                mapsToAttribute=attr_name,
                priority=priority,
                reason="missing_search_gate_requirement" if attribute.get("search_gate") else "missing_attribute",
            )
        )
        if len(questions) >= 5:
            return questions

    return questions


# ---------------------------------------------------------------------------
# Attribute selection helpers
# ---------------------------------------------------------------------------

def search_gate_attributes(attributes: list[dict]) -> list[dict]:
    """Return attributes with search_gate=True.

    Falls back to attributes with score_direction must_have or lower_is_better
    if no explicit search_gate attributes are present (e.g. local fallback schema).
    """
    gated = [a for a in attributes if a.get("search_gate")]
    if gated:
        return gated
    return [
        a for a in attributes
        if str(a.get("score_direction", "")) in {"must_have", "lower_is_better"}
    ][:3]


# Keep old name as alias so any code that calls critical_attributes still works.
critical_attributes = search_gate_attributes


def known_attribute_names(
    requirements: list[UserRequirement],
    attributes: list[dict],
    category_context: dict | None,
) -> set[str]:
    """Return canonical keys for all attributes already resolved in the profile."""
    known: set[str] = set()
    for requirement in requirements:
        if requirement.status not in {"specified", "inferred", "ignored"}:
            continue
        key = canonical_attribute_key(requirement.attributeName, attributes, category_context)
        known.add(key)
    return known


def should_queue_attribute(
    attr_key: str,
    known: set[str],
    queued_keys: set[str],
) -> bool:
    if not attr_key:
        return False
    return attr_key not in known and attr_key not in queued_keys
