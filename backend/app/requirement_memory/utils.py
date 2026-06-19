"""Shared low-level utilities: constructors, deduplication, text helpers."""

import re
from datetime import datetime, timezone
from typing import Any

from app.schemas import UserRequirement


RequirementValue = str | int | float | bool | None


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def first_match(pattern: str, message: str) -> str | None:
    match = re.search(pattern, message, re.IGNORECASE)
    if match is None:
        return None
    return match.group(0)


def contains_number(text: str) -> bool:
    return first_number(text) is not None


def first_number(text: str) -> int | float | None:
    match = re.search(r"\d+(?:,\d{3})*(?:\.\d+)?", text)
    if match is None:
        return None
    value = match.group(0).replace(",", "")
    number = float(value)
    return int(number) if number.is_integer() else number


def valid_choice(value: Any, allowed: set[str], fallback: str) -> str:
    if isinstance(value, str) and value in allowed:
        return value
    return fallback


def human_join(items: list[str]) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return f"{', '.join(items[:-1])}, and {items[-1]}"


def make_requirement(
    *,
    attribute_name: str,
    status: str,
    value: RequirementValue,
    normalized_operator: str = "match",
    normalized_value: Any = None,
    unit: str | None = None,
    importance: str,
    hardness: str = "soft",
    weight: float = 0.5,
    source: str,
    confidence: float,
    product_evidence_confidence: float | None = None,
    missing_product_data_strategy: str = "penalize_unknown",
    scoring_function: str = "match_user_preference",
    needs_more_specification: bool = False,
    specification_question: str | None = None,
    evidence: str,
    timestamp: str,
) -> UserRequirement:
    return UserRequirement(
        attributeName=attribute_name,
        status=status,
        value=value,
        normalizedOperator=normalized_operator,
        normalizedValue=normalized_value,
        unit=unit,
        importance=importance,
        hardness=hardness,
        weight=min(max(weight, 0), 1),
        source=source,
        confidence=min(max(confidence, 0), 1),
        productEvidenceConfidence=product_evidence_confidence,
        missingProductDataStrategy=missing_product_data_strategy,
        scoringFunction=scoring_function,
        needsMoreSpecification=needs_more_specification,
        specificationQuestion=specification_question,
        evidence=evidence,
        updatedAt=timestamp,
    )


def dedupe_requirements(requirements: list[UserRequirement]) -> list[UserRequirement]:
    """Keep the highest-confidence requirement per attribute name."""
    by_key: dict[str, UserRequirement] = {}
    for requirement in requirements:
        key = requirement.attributeName.lower()
        existing = by_key.get(key)
        if existing is None or requirement.confidence >= existing.confidence:
            by_key[key] = requirement
    return list(by_key.values())


def dedupe_names(names: list[str]) -> list[str]:
    """Return names with duplicates removed, preserving order."""
    seen: set[str] = set()
    deduped: list[str] = []
    for name in names:
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(name)
    return deduped
