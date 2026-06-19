"""Clarifying question detection and answering.

Detects when the user asks a question about a category attribute and generates
a concise educational answer, with or without an LLM depending on configuration.
"""

import os

from app.schemas import UserRequirement
from app.category_intelligence.llm import CategoryIntelligenceError, get_llm_provider, load_local_env
from app.requirement_memory.utils import tokens, human_join
from app.requirement_memory.attributes import (
    extract_attribute_schema,
    extract_entity_candidates,
    attribute_by_name,
    closest_schema_attribute,
)
from app.requirement_memory.prompts import build_clarifying_answer_prompt


# ---------------------------------------------------------------------------
# Question detection
# ---------------------------------------------------------------------------

def is_user_clarifying_question(message: str) -> bool:
    """Return True if the message looks like a question about the category."""
    lowered = message.strip().lower()
    if "?" in lowered:
        return True
    return lowered.startswith(
        ("what ", "which ", "how ", "why ", "do ", "does ", "can ", "should ", "tell me ", "explain ")
    )


def evidence_looks_like_question(evidence: str) -> bool:
    """Return True if the evidence string itself looks like a question phrase."""
    lowered = evidence.strip().lower()
    if "?" in lowered:
        return True
    return lowered.startswith(("what ", "which ", "how ", "why ", "do ", "does ", "can ", "should ", "tell me ", "explain "))


def questioned_attribute_name(message: str, category_context: dict | None) -> str | None:
    """Return the attribute name being asked about, or None if not a question."""
    if not is_user_clarifying_question(message):
        return None
    attributes = extract_attribute_schema(category_context)
    matched = closest_schema_attribute(message, attributes, category_context)
    if matched is None:
        return None
    return str(matched.get("name", "")).strip() or None


def filter_questioned_attribute_observations(
    observations: list[UserRequirement],
    questioned_attribute: str | None,
    message_is_question: bool = False,
) -> list[UserRequirement]:
    """Remove observations for the attribute being questioned when the evidence is question-like.

    When the whole message is a general question but no specific attribute was
    matched (questioned_attribute is None), still remove any observation whose
    evidence phrase looks like question language — those are vague inferences
    from the question itself, not real requirements.
    """
    if questioned_attribute is None:
        if message_is_question:
            return [o for o in observations if not evidence_looks_like_question(o.evidence)]
        return observations
    filtered = []
    for observation in observations:
        if observation.attributeName.lower() != questioned_attribute.lower():
            filtered.append(observation)
        elif not evidence_looks_like_question(observation.evidence):
            filtered.append(observation)
    return filtered


# ---------------------------------------------------------------------------
# Clarifying answer generation
# ---------------------------------------------------------------------------

def answer_user_clarifying_question(
    *,
    category_name: str | None,
    latest_user_message: str,
    category_context: dict | None,
) -> str | None:
    """Return an educational answer if the message is a question about a category attribute.

    Uses the LLM when configured, falls back to a local deterministic answer.
    Returns None if the message is not a recognizable question.
    """
    if not is_user_clarifying_question(latest_user_message):
        return None

    attributes = extract_attribute_schema(category_context)
    matched_attribute = closest_schema_attribute(latest_user_message, attributes, category_context)
    if matched_attribute is None:
        return None

    load_local_env()
    provider_name = os.getenv("LLM_PROVIDER", "local").lower()

    if provider_name in {"local", "mock", "deterministic"}:
        return local_attribute_answer(
            category_name=category_name,
            latest_user_message=latest_user_message,
            attribute=matched_attribute,
            category_context=category_context,
        )

    prompt = build_clarifying_answer_prompt(
        category_name=category_name,
        latest_user_message=latest_user_message,
        category_context=category_context,
        matched_attribute=matched_attribute,
    )
    try:
        raw_answer, _metadata = get_llm_provider().generate_json(prompt)
        answer = str(raw_answer.get("answer", "")).strip()
        return answer or None
    except (CategoryIntelligenceError, ValueError, TypeError):
        return local_attribute_answer(
            category_name=category_name,
            latest_user_message=latest_user_message,
            attribute=matched_attribute,
            category_context=category_context,
        )


# ---------------------------------------------------------------------------
# Local (deterministic) answer
# ---------------------------------------------------------------------------

def local_attribute_answer(
    *,
    category_name: str | None,
    latest_user_message: str,
    attribute: dict,
    category_context: dict | None,
) -> str:
    """Return a short deterministic answer using the attribute's own context."""
    attribute_name = str(attribute.get("name", "this attribute"))
    typical_values = attribute.get("typical_values") or []
    assessment_note = str(attribute.get("assessment_note", "")).strip()

    # Use typical_values as option list when available
    if isinstance(typical_values, list) and typical_values:
        option_text = human_join([str(v) for v in typical_values[:5]])
        base = (
            f"For {attribute_name}, common options include {option_text}. "
            "The best choice depends on your situation and which tradeoffs matter most."
        )
        if assessment_note:
            base += f" {assessment_note}"
        return base

    # Fall back to entity terms
    entity_terms = [e["name"] for e in extract_entity_candidates(category_context)]
    message_tokens = tokens(latest_user_message)
    relevant = [t for t in entity_terms if tokens(t).intersection(message_tokens)][:5]

    if relevant:
        option_text = human_join(relevant)
        return (
            f"For {attribute_name}, related options in {category_name or 'this category'} "
            f"include {option_text}. {assessment_note or 'The best choice depends on your tradeoffs.'}"
        )

    return (
        f"{attribute_name} is one of the key decision attributes for "
        f"{category_name or 'this category'}. "
        f"{assessment_note or 'Tell me what matters most to you and I can map it to a requirement.'}"
    )
