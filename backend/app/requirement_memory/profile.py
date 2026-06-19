"""User requirement profile: create, update, merge, and display.

The profile is the durable record of everything the user has told us about
what they need. It accumulates across conversation turns and is the primary
input to search and recommendation.
"""

import os
from typing import Any

from app.schemas import FollowUpQuestion, UserRequirement, UserRequirementProfile
from app.category_intelligence.llm import CategoryIntelligenceError, get_llm_provider, load_local_env
from app.requirement_memory.utils import make_requirement, valid_choice, dedupe_requirements, now_iso
from app.requirement_memory.attributes import (
    extract_attribute_schema,
    canonical_attribute,
)
from app.requirement_memory.extraction import extract_requirements_from_message
from app.requirement_memory.enrichment import enrich_requirements_for_scoring
from app.requirement_memory.questions import build_follow_up_questions
from app.requirement_memory.clarification import (
    questioned_attribute_name,
    filter_questioned_attribute_observations,
)
from app.requirement_memory.prompts import build_requirement_memory_prompt


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def update_user_requirement_profile(
    existing_profile: dict | UserRequirementProfile | None,
    *,
    category_name: str | None,
    original_user_prompt: str | None,
    latest_user_message: str,
    category_context: dict | None,
    clarification_prompt_count: int = 0,
    updated_at: str | None = None,
) -> UserRequirementProfile:
    """Update (or create) the requirement profile with observations from the latest message.

    Merges new observations into existing requirements, rebuilds follow-up questions,
    and returns a fresh profile instance.
    """
    timestamp = updated_at or now_iso()
    profile = _coerce_profile(existing_profile)

    if profile is None:
        profile = UserRequirementProfile(
            categoryName=category_name,
            originalUserPrompt=original_user_prompt or latest_user_message,
            latestUserMessage=latest_user_message,
            requirements=[],
            followUpQuestions=[],
            summary="No requirements captured yet.",
            createdAt=timestamp,
            updatedAt=timestamp,
        )

    if category_name and profile.categoryName != category_name:
        profile.categoryName = category_name

    profile.latestUserMessage = latest_user_message
    profile.updatedAt = timestamp

    attributes = extract_attribute_schema(category_context)
    observed = _generate_requirement_observations(
        existing_profile=profile,
        category_name=category_name,
        latest_user_message=latest_user_message,
        attributes=attributes,
        category_context=category_context,
        timestamp=timestamp,
    )

    current_by_attribute = {item.attributeName.lower(): item for item in profile.requirements}
    for requirement in observed:
        current_by_attribute[requirement.attributeName.lower()] = _merge_requirement(
            previous=current_by_attribute.get(requirement.attributeName.lower()),
            incoming=requirement,
        )

    profile.requirements = sorted(
        current_by_attribute.values(),
        key=lambda item: (_status_sort_key(item.status), item.attributeName.lower()),
    )
    profile.followUpQuestions = build_follow_up_questions(
        requirements=profile.requirements,
        category_context=category_context,
        clarification_prompt_count=clarification_prompt_count,
    )
    profile.summary = _summarize_profile(profile)
    return profile


# ---------------------------------------------------------------------------
# Observation generation
# ---------------------------------------------------------------------------

def _generate_requirement_observations(
    *,
    existing_profile: UserRequirementProfile,
    category_name: str | None,
    latest_user_message: str,
    attributes: list[dict],
    category_context: dict | None,
    timestamp: str,
) -> list[UserRequirement]:
    """Extract observations from the message via local rules or LLM, then enrich them."""
    questioned_attribute = questioned_attribute_name(latest_user_message, category_context)
    load_local_env()
    provider_name = os.getenv("LLM_PROVIDER", "local").lower()

    if provider_name in {"local", "mock", "deterministic"}:
        observations = extract_requirements_from_message(
            latest_user_message=latest_user_message,
            attributes=attributes,
            category_context=category_context,
            timestamp=timestamp,
        )
        observations = filter_questioned_attribute_observations(observations, questioned_attribute)
        return enrich_requirements_for_scoring(observations, attributes)

    prompt = build_requirement_memory_prompt(
        existing_profile=existing_profile,
        category_name=category_name,
        latest_user_message=latest_user_message,
        category_context=category_context,
    )
    try:
        raw_observations, _metadata = get_llm_provider().generate_json(prompt)
        observations = _parse_requirement_observations(
            raw_observations=raw_observations,
            attributes=attributes,
            category_context=category_context,
            timestamp=timestamp,
        )
        observations = filter_questioned_attribute_observations(observations, questioned_attribute)
        return enrich_requirements_for_scoring(observations, attributes)
    except (CategoryIntelligenceError, ValueError, TypeError):
        observations = extract_requirements_from_message(
            latest_user_message=latest_user_message,
            attributes=attributes,
            category_context=category_context,
            timestamp=timestamp,
        )
        observations = filter_questioned_attribute_observations(observations, questioned_attribute)
        return enrich_requirements_for_scoring(observations, attributes)


def _parse_requirement_observations(
    *,
    raw_observations: dict,
    attributes: list[dict],
    category_context: dict | None,
    timestamp: str,
) -> list[UserRequirement]:
    """Parse and validate raw LLM output into UserRequirement instances."""
    raw_requirements = raw_observations.get("requirements", [])
    if not isinstance(raw_requirements, list):
        raise ValueError("Requirement memory response missing requirements list")

    parsed: list[UserRequirement] = []
    for raw in raw_requirements[:12]:
        if not isinstance(raw, dict):
            continue
        attribute_name = str(raw.get("attributeName", "")).strip()
        evidence = str(raw.get("evidence", "")).strip()
        if not attribute_name or not evidence:
            continue

        parsed.append(
            make_requirement(
                attribute_name=canonical_attribute(attribute_name, attributes, category_context),
                status=valid_choice(raw.get("status"), {"specified", "inferred", "ignored", "conflicted"}, "specified"),
                value=raw.get("value"),
                normalized_operator=valid_choice(
                    raw.get("normalizedOperator"),
                    {"max", "min", "equals", "one_of", "avoid", "prefer", "match"},
                    "match",
                ),
                normalized_value=raw.get("normalizedValue"),
                unit=raw.get("unit"),
                importance=valid_choice(
                    raw.get("importance"), {"critical", "high", "medium", "low", "unknown"}, "medium"
                ),
                hardness=valid_choice(raw.get("hardness"), {"hard", "soft", "ignore"}, "soft"),
                weight=float(raw.get("weight", 0.5)),
                source=valid_choice(
                    raw.get("source"),
                    {"explicit_user_statement", "inferred_from_user_statement"},
                    "explicit_user_statement",
                ),
                confidence=float(raw.get("confidence", 0.75)),
                product_evidence_confidence=raw.get("productEvidenceConfidence"),
                missing_product_data_strategy=valid_choice(
                    raw.get("missingProductDataStrategy"),
                    {"exclude_if_missing", "penalize_unknown", "neutral_if_missing", "manual_review"},
                    "penalize_unknown",
                ),
                scoring_function=str(raw.get("scoringFunction", "match_user_preference")),
                needs_more_specification=bool(raw.get("needsMoreSpecification", False)),
                specification_question=raw.get("specificationQuestion"),
                evidence=evidence,
                timestamp=timestamp,
            )
        )

    return dedupe_requirements(parsed)


# ---------------------------------------------------------------------------
# Merge logic
# ---------------------------------------------------------------------------

def _merge_requirement(previous: UserRequirement | None, incoming: UserRequirement) -> UserRequirement:
    """Merge an incoming observation into the existing requirement for that attribute."""
    if previous is None:
        return incoming
    if incoming.status == "ignored":
        return incoming
    if previous.status == "ignored" and incoming.status != "ignored":
        return incoming
    if _is_explicit_override(incoming.evidence):
        return incoming
    if incoming.confidence >= previous.confidence or previous.status in {"missing", "inferred"}:
        return incoming
    return UserRequirement(
        attributeName=previous.attributeName,
        status=previous.status,
        value=incoming.value if incoming.value not in {None, ""} else previous.value,
        importance=_max_importance(previous.importance, incoming.importance),
        source=previous.source,
        confidence=max(previous.confidence, incoming.confidence),
        evidence=f"{previous.evidence} | {incoming.evidence}",
        updatedAt=incoming.updatedAt,
    )


def _is_explicit_override(evidence: str) -> bool:
    lowered = evidence.lower()
    return any(term in lowered for term in ["actually", "changed my mind", "instead", "make it", "now i want"])


def _max_importance(left: str, right: str) -> str:
    order = {"critical": 4, "high": 3, "medium": 2, "low": 1, "unknown": 0}
    return left if order.get(left, 0) >= order.get(right, 0) else right


# ---------------------------------------------------------------------------
# Profile utilities
# ---------------------------------------------------------------------------

def _coerce_profile(profile: dict | UserRequirementProfile | None) -> UserRequirementProfile | None:
    if profile is None:
        return None
    if isinstance(profile, UserRequirementProfile):
        return profile.model_copy(deep=True)
    return UserRequirementProfile(**profile)


def _summarize_profile(profile: UserRequirementProfile) -> str:
    specified = [item for item in profile.requirements if item.status == "specified"]
    ignored = [item for item in profile.requirements if item.status == "ignored"]
    parts: list[str] = []
    if profile.categoryName:
        parts.append(f"Category: {profile.categoryName}.")
    parts.append(f"{len(specified)} specified requirement{'s' if len(specified) != 1 else ''}.")
    if ignored:
        parts.append(f"{len(ignored)} ignored attribute{'s' if len(ignored) != 1 else ''}.")
    if profile.followUpQuestions:
        parts.append(f"{len(profile.followUpQuestions)} follow-up question{'s' if len(profile.followUpQuestions) != 1 else ''}.")
    return " ".join(parts)


def _status_sort_key(status: str) -> int:
    return {"specified": 0, "inferred": 1, "ignored": 2, "missing": 3, "conflicted": 4}.get(status, 5)


# ---------------------------------------------------------------------------
# Display helpers (used by routers and agents)
# ---------------------------------------------------------------------------

def profile_to_requirement_display(profile: UserRequirementProfile | None) -> list[dict[str, Any]]:
    """Convert the profile to the flat label/value list used by the search router."""
    if profile is None:
        return []
    return [
        {"label": r.attributeName, "value": str(r.value)}
        for r in profile.requirements
        if r.status in {"specified", "inferred"} and r.value not in {None, ""}
    ]


def missing_fields_from_profile(profile: UserRequirementProfile | None) -> list[str]:
    """Return the list of attribute names still needing answers."""
    if profile is None:
        return ["what matters most"]
    return [q.mapsToAttribute for q in profile.followUpQuestions]
