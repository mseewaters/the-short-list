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
) -> list[UserRequirement]:
    """Remove observations for the attribute being questioned when the evidence is question-like."""
    if questioned_attribute is None:
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
    """Return a short deterministic answer based on entity candidates for the attribute."""
    attribute_name = str(attribute.get("name", "this attribute"))
    relevant_entities = relevant_entities_for_question(
        latest_user_message=latest_user_message,
        attribute=attribute,
        category_context=category_context,
    )

    if relevant_entities:
        option_text = human_join([entity["name"] for entity in relevant_entities[:5]])
        return (
            f"For {attribute_name}, common options in {category_name or 'this category'} include {option_text}. "
            "The best choice depends on your situation and which tradeoffs matter most."
        )

    return (
        f"{attribute_name} is one of the decision attributes for {category_name or 'this category'}. "
        "The useful options depend on your situation; tell me what tradeoff you care about most and I can map it to a requirement."
    )


def relevant_entities_for_question(
    *,
    latest_user_message: str,
    attribute: dict,
    category_context: dict | None,
) -> list[dict]:
    """Return entities relevant to the user's question, ranked by token overlap."""
    entities = extract_entity_candidates(category_context)
    attribute_tokens = tokens(str(attribute.get("name", "")))
    message_tokens = tokens(latest_user_message)
    scored: list[tuple[int, dict]] = []

    for entity in entities:
        entity_name = str(entity.get("name", ""))
        entity_tokens = tokens(entity_name)
        source_field = str(entity.get("source_field", "")).lower()
        entity_type = str(entity.get("type", "")).lower()
        score = len(entity_tokens.intersection(attribute_tokens)) * 2
        score += len(entity_tokens.intersection(message_tokens))
        if source_field in {"common_entities", "important_attributes"}:
            score += 1
        if entity_type in {"product_type", "feature", "installation_constraint", "performance_metric", "style"}:
            score += 1
        if score > 0:
            scored.append((score, entity))

    scored.sort(key=lambda item: (-item[0], str(item[1].get("name", "")).lower()))
    return _dedupe_entities([entity for _score, entity in scored])


def _dedupe_entities(entities: list[dict]) -> list[dict]:
    seen: set[str] = set()
    deduped: list[dict] = []
    for entity in entities:
        key = str(entity.get("name", "")).lower()
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(entity)
    return deduped
