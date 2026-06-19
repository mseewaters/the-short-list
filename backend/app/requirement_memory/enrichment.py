"""Requirement enrichment: infer operator, unit, hardness, weight, and scoring function.

Takes raw UserRequirement objects (as extracted from user messages) and fills in
the scoring metadata fields needed downstream for product comparison.
"""

import re
from typing import Any

from app.schemas import UserRequirement
from app.requirement_memory.utils import contains_number, first_number
from app.requirement_memory.attributes import attribute_by_name


def enrich_requirements_for_scoring(
    requirements: list[UserRequirement],
    attributes: list[dict],
) -> list[UserRequirement]:
    """Enrich each requirement with inferred operator, unit, hardness, weight, and scoring metadata."""
    enriched = []
    for requirement in requirements:
        attribute = attribute_by_name(requirement.attributeName, attributes)
        operator = infer_operator(requirement, attribute)
        normalized_value = requirement.normalizedValue
        if normalized_value is None and requirement.value is not None:
            normalized_value = infer_normalized_value(requirement.value, operator)
        unit = requirement.unit or attribute.get("unit") or infer_unit_from_requirement(requirement)
        hardness = infer_hardness(requirement, attribute)
        scoring_function = infer_scoring_function(requirement, attribute, operator)
        missing_strategy = infer_missing_product_data_strategy(requirement, hardness)
        needs_specification = needs_more_specification(requirement, attribute, normalized_value)
        specification_question = requirement.specificationQuestion
        if needs_specification and not specification_question:
            specification_question = specification_question_for(requirement, attribute)

        enriched.append(
            requirement.model_copy(
                update={
                    "normalizedOperator": operator,
                    "normalizedValue": normalized_value,
                    "unit": unit,
                    "hardness": hardness,
                    "weight": infer_weight(requirement, hardness),
                    "missingProductDataStrategy": missing_strategy,
                    "scoringFunction": scoring_function,
                    "needsMoreSpecification": needs_specification,
                    "specificationQuestion": specification_question,
                }
            )
        )
    return enriched


# ---------------------------------------------------------------------------
# Operator inference
# ---------------------------------------------------------------------------

def infer_operator(requirement: UserRequirement, attribute: dict) -> str:
    if requirement.status == "ignored":
        return "match"
    if requirement.normalizedOperator != "match":
        return requirement.normalizedOperator

    evidence = f"{requirement.evidence} {requirement.value}".lower()
    score_direction = str(attribute.get("score_direction", "")).lower()

    if any(term in evidence for term in ["under", "below", "less than", "up to", "at most", "no more than"]):
        return "max"
    if any(term in evidence for term in ["at least", "minimum", "more than", "over"]):
        return "min"
    if any(term in evidence for term in ["avoid", "not ", "no "]):
        return "avoid"
    if score_direction == "must_have":
        return "equals"
    if score_direction == "lower_is_better":
        return "max" if contains_number(evidence) else "prefer"
    if score_direction == "higher_is_better":
        return "min" if contains_number(evidence) else "prefer"
    if score_direction == "match_user_preference":
        return "prefer"
    return "match"


def infer_normalized_value(value: Any, operator: str) -> Any:
    if isinstance(value, (int, float, bool)):
        return value
    text = str(value).strip()
    number = first_number(text)
    if number is not None and operator in {"max", "min"}:
        return number
    if operator in {"one_of", "avoid"}:
        return [part.strip() for part in re.split(r",|/|\bor\b", text) if part.strip()]
    return text


# ---------------------------------------------------------------------------
# Unit inference
# ---------------------------------------------------------------------------

def infer_unit_from_requirement(requirement: UserRequirement) -> str | None:
    text = f"{requirement.attributeName} {requirement.evidence} {requirement.value}".lower()
    if "$" in text or any(term in text for term in ["budget", "price", "cost"]):
        return "usd"
    if any(term in text for term in ["feet", "foot", "ft"]):
        return "feet"
    if any(term in text for term in ["inch", "inches"]):
        return "inches"
    if "square feet" in text or "sq ft" in text:
        return "square_feet"
    return None


# ---------------------------------------------------------------------------
# Hardness, weight, and missing-data strategy
# ---------------------------------------------------------------------------

def infer_hardness(requirement: UserRequirement, attribute: dict) -> str:
    if requirement.status == "ignored":
        return "ignore"
    if requirement.hardness in {"hard", "ignore"}:
        return requirement.hardness
    evidence = f"{requirement.evidence} {requirement.value}".lower()
    score_direction = str(attribute.get("score_direction", "")).lower()
    if requirement.importance == "critical" and (
        score_direction == "must_have"
        or any(term in evidence for term in ["under", "below", "less than", "must", "need", "required"])
    ):
        return "hard"
    return "soft"


def infer_weight(requirement: UserRequirement, hardness: str) -> float:
    if hardness == "ignore":
        return 0
    if requirement.weight != 0.5:
        return min(max(requirement.weight, 0), 1)
    weights = {"critical": 1.0, "high": 0.8, "medium": 0.55, "low": 0.25, "unknown": 0.4}
    return weights.get(requirement.importance, 0.5)


def infer_missing_product_data_strategy(requirement: UserRequirement, hardness: str) -> str:
    if requirement.status == "ignored":
        return "neutral_if_missing"
    if hardness == "hard":
        return "exclude_if_missing"
    if requirement.needsMoreSpecification:
        return "manual_review"
    return requirement.missingProductDataStrategy or "penalize_unknown"


# ---------------------------------------------------------------------------
# Scoring function and specification
# ---------------------------------------------------------------------------

def infer_scoring_function(requirement: UserRequirement, attribute: dict, operator: str) -> str:
    if requirement.status == "ignored":
        return "do_not_score"
    if operator == "max":
        return "numeric_max"
    if operator == "min":
        return "numeric_min"
    if operator == "equals":
        return "exact_match"
    if operator == "one_of":
        return "enum_preference_match"
    if operator == "avoid":
        return "avoid_match"
    if str(attribute.get("value_type", "")) == "enum":
        return "enum_preference_match"
    return "semantic_preference_match"


def needs_more_specification(requirement: UserRequirement, attribute: dict, normalized_value: Any) -> bool:
    if requirement.status in {"ignored", "conflicted"}:
        return False
    value_type = str(attribute.get("value_type", "")).lower()
    if value_type in {"number", "range"} and not isinstance(normalized_value, (int, float)):
        return True
    if requirement.confidence < 0.65:
        return True
    vague_terms = {"good", "nice", "better", "decent", "reasonable", "not bad", "solid"}
    return str(requirement.value or "").lower() in vague_terms


def specification_question_for(requirement: UserRequirement, attribute: dict) -> str:
    unit = attribute.get("unit") or infer_unit_from_requirement(requirement)
    if unit:
        return f"What specific {requirement.attributeName} value or range should I use for scoring, in {unit}?"
    return f"What specific {requirement.attributeName} value should I use when comparing products?"
