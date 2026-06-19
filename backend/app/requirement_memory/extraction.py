"""Local (deterministic) requirement extraction from user messages.

This module runs without an LLM. It uses regex patterns, hard-coded signal
tables, entity candidate matching, and schema-aligned phrase search to pull
structured requirements from free-text user input.
"""

import re

from app.schemas import UserRequirement
from app.requirement_memory.utils import (
    make_requirement,
    first_match,
    dedupe_requirements,
    dedupe_names,
    tokens,
)
from app.requirement_memory.attributes import (
    build_attribute_matching_hints,
    canonical_attribute,
    attribute_by_name,
    schema_allows_attribute,
)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def extract_requirements_from_message(
    *,
    latest_user_message: str,
    attributes: list[dict],
    category_context: dict | None,
    timestamp: str,
) -> list[UserRequirement]:
    """Extract all requirements detectable via local rules from a single user message."""
    message = latest_user_message.strip()
    lowered = message.lower()
    requirements: list[UserRequirement] = []
    schema_names = {str(a.get("name", "")).lower() for a in attributes}

    # --- Ignored attributes ---
    ignored_attributes = ignored_attribute_names(message, attributes, category_context)
    for attribute_name in ignored_attributes:
        requirements.append(
            make_requirement(
                attribute_name=attribute_name,
                status="ignored",
                value=None,
                importance="low",
                source="explicit_user_statement",
                confidence=0.92,
                evidence=message,
                timestamp=timestamp,
            )
        )

    # --- Budget ---
    budget = first_match(r"(under|below|up to|around|about|less than)?\s*\$ ?\d+(?:,\d{3})*(?:\.\d{2})?", message)
    if budget:
        requirements.append(
            make_requirement(
                attribute_name=canonical_attribute("Budget", attributes, category_context),
                status="specified",
                value=budget.strip(),
                importance="critical" if any(t in lowered for t in ["under", "below", "up to", "less than"]) else "high",
                source="explicit_user_statement",
                confidence=0.96,
                evidence=budget.strip(),
                timestamp=timestamp,
            )
        )

    # --- Room dimensions ---
    room_dimensions = first_match(r"\d+\s*(by|x)\s*\d+\s*(feet|foot|ft|inches|inch|in)?", message)
    if room_dimensions:
        requirements.append(
            make_requirement(
                attribute_name=canonical_attribute("Room dimensions", attributes, category_context),
                status="specified",
                value=room_dimensions.strip(),
                importance="high",
                source="explicit_user_statement",
                confidence=0.9,
                evidence=room_dimensions.strip(),
                timestamp=timestamp,
            )
        )

    # --- Ceiling height ---
    ceiling_height = first_match(r"ceiling (height is|is|height:)?\s*\d+\s*(feet|foot|ft)", message)
    if ceiling_height:
        requirements.append(
            make_requirement(
                attribute_name=canonical_attribute("Ceiling height", attributes, category_context),
                status="specified",
                value=ceiling_height.strip(),
                importance="critical",
                source="explicit_user_statement",
                confidence=0.93,
                evidence=ceiling_height.strip(),
                timestamp=timestamp,
            )
        )

    # --- Room context (living room, bedroom, etc.) ---
    room_context = room_context_value(lowered)
    if room_context:
        room_attribute = canonical_attribute("Room", attributes, category_context)
        room_attribute_lower = room_attribute.lower()
        if (
            "rating" not in room_attribute_lower
            and "size" not in room_attribute_lower
            and "dimension" not in room_attribute_lower
            and any(t in room_attribute_lower for t in ["room", "location", "use context", "use case"])
            and schema_allows_attribute(room_attribute, schema_names)
        ):
            requirements.append(
                make_requirement(
                    attribute_name=room_attribute,
                    status="specified",
                    value=room_context,
                    importance="medium",
                    source="explicit_user_statement",
                    confidence=0.88,
                    evidence=message,
                    timestamp=timestamp,
                )
            )

    # --- User context (elderly parents, single person, etc.) ---
    user_context = user_context_value(lowered)
    user_context_attribute = None
    if user_context:
        candidate = canonical_attribute("User context", attributes, category_context)
        if schema_allows_attribute(candidate, schema_names):
            user_context_attribute = candidate
    if user_context_attribute:
        requirements.append(
            make_requirement(
                attribute_name=user_context_attribute,
                status="specified",
                value=user_context,
                importance="high",
                source="explicit_user_statement",
                confidence=0.88,
                evidence=message,
                timestamp=timestamp,
            )
        )

    # --- Indoor/damp/wet rating (inferred from room mention) ---
    indoor_room = indoor_room_value(lowered)
    indoor_attribute = None
    if indoor_room:
        candidate = canonical_attribute("Indoor/Damp/Wet Rating", attributes, category_context)
        if schema_allows_attribute(candidate, schema_names):
            indoor_attribute = candidate
    if indoor_attribute:
        requirements.append(
            make_requirement(
                attribute_name=indoor_attribute,
                status="inferred",
                value="indoor/dry",
                normalized_operator="equals",
                normalized_value="indoor/dry",
                importance="high",
                hardness="hard",
                source="inferred_from_user_statement",
                confidence=0.85,
                evidence=indoor_room,
                timestamp=timestamp,
            )
        )

    # --- Entity-backed requirements ---
    requirements.extend(
        extract_entity_backed_requirements(
            message=message,
            attributes=attributes,
            category_context=category_context,
            ignored_attributes=ignored_attributes,
            timestamp=timestamp,
        )
    )

    # --- Hard-coded signal table ---
    _SIGNAL_REQUIREMENTS = [
        (["quiet", "noisy", "noise"],                                          "Noise level",       "quiet",               "critical", 0.95),
        (["low profile", "low-profile", "low ceiling", "hugger"],              "Profile",           "low profile",         "critical", 0.92),
        (["not ugly", "nice looking", "modern", "attractive", "style"],        "Style",             "attractive",          "medium",   0.82),
        (["dimmable lights", "dimmable light", "dimming", "lights"],           "Lighting Control",  "dimmable lights",     "high",     0.90),
        (["voice control", "smart home", "works with", "compatible with"],     "Compatibility",     "compatible",          "high",     0.82),
        (["dog", "dogs", "pet hair", "pet"],                                   "Pet hair handling", "handles pet hair",    "high",     0.87),
        (["easy maintenance", "low maintenance", "simple maintenance",
          "elderly", "parents"],                                                "Maintenance",       "easy maintenance",    "high",     0.86),
        (["simple controls", "easy to use", "easy setup", "set up"],          "Ease of use",       "simple",              "high",     0.84),
        (["bright room", "glare", "sunny"],                                    "Brightness",        "bright-room friendly","high",     0.86),
        (["anti-glare", "anti glare"],                                         "Anti-glare",        "anti-glare",          "high",     0.88),
        (["single person", "one person"],                                      "Capacity",          "single person",       "medium",   0.82),
        (["on the go", "quick", "fast"],                                       "Speed",             "fast",                "high",     0.80),
        (["3-story", "3 story", "three-story", "three story",
          "whole-home", "whole home"],                                          "Coverage",          "whole-home coverage", "critical", 0.90),
    ]
    for terms, attribute_name, value, importance, confidence in _SIGNAL_REQUIREMENTS:
        evidence = matching_phrase(lowered, message, terms)
        if evidence and attribute_name.lower() not in {item.lower() for item in ignored_attributes}:
            canonical_name = canonical_attribute(attribute_name, attributes, category_context)
            if not schema_allows_attribute(canonical_name, schema_names):
                continue
            requirements.append(
                make_requirement(
                    attribute_name=canonical_name,
                    status="specified",
                    value=value,
                    importance=importance,
                    source="explicit_user_statement",
                    confidence=confidence,
                    evidence=evidence,
                    timestamp=timestamp,
                )
            )

    # --- Schema-aligned phrase matching ---
    requirements.extend(
        extract_schema_aligned_phrases(message, attributes, category_context, timestamp)
    )

    return dedupe_requirements(requirements)


# ---------------------------------------------------------------------------
# Entity-backed extraction
# ---------------------------------------------------------------------------

def extract_entity_backed_requirements(
    *,
    message: str,
    attributes: list[dict],
    category_context: dict | None,
    ignored_attributes: list[str],
    timestamp: str,
) -> list[UserRequirement]:
    """Create requirements for entity candidates found verbatim in the message."""
    lowered = message.lower()
    ignored = {name.lower() for name in ignored_attributes}
    schema_names = {str(a.get("name", "")).lower() for a in attributes}
    results: list[UserRequirement] = []

    for hint in build_attribute_matching_hints(category_context):
        attribute_name = str(hint.get("attributeName", "")).strip()
        if not attribute_name or attribute_name.lower() in ignored:
            continue
        if not schema_allows_attribute(attribute_name, schema_names):
            continue

        attr_def = attribute_by_name(attribute_name, attributes)
        importance = "high" if attr_def.get("search_gate") else "medium"
        for signal in hint.get("extractionSignals", []):
            signal_str = str(signal).strip()
            if not signal_str or len(signal_str) < 3:
                continue
            index = lowered.find(signal_str.lower())
            if index >= 0:
                evidence = message[index: index + len(signal_str)]
                results.append(
                    make_requirement(
                        attribute_name=attribute_name,
                        status="specified",
                        value=evidence,
                        normalized_operator="equals",
                        normalized_value=evidence,
                        importance=importance,
                        source="explicit_user_statement",
                        confidence=0.85,
                        evidence=evidence,
                        timestamp=timestamp,
                    )
                )
                break  # one signal match per attribute is enough

    return results


# ---------------------------------------------------------------------------
# Schema-aligned phrase extraction
# ---------------------------------------------------------------------------

def extract_schema_aligned_phrases(
    message: str,
    attributes: list[dict],
    category_context: dict | None,
    timestamp: str,
) -> list[UserRequirement]:
    """Create requirements by matching attribute synonym phrases directly in the message."""
    lowered = message.lower()
    results: list[UserRequirement] = []

    for attribute in attributes:
        name = str(attribute.get("name", ""))
        if name.lower() == "budget":
            continue
        if str(attribute.get("value_type", "")).lower() in {"number", "range"}:
            continue
        evidence = first_schema_phrase_match(message, attribute, category_context)
        if evidence:
            value = first_attribute_value(message, name) if name.lower() in lowered else evidence
            importance = "high" if attribute.get("search_gate") else "medium"
            results.append(
                make_requirement(
                    attribute_name=name,
                    status="specified",
                    value=value,
                    importance=importance,
                    source="explicit_user_statement",
                    confidence=0.78,
                    evidence=value,
                    timestamp=timestamp,
                )
            )

    return results


def first_schema_phrase_match(message: str, attribute: dict, category_context: dict | None) -> str | None:
    """Return the first extraction signal phrase for this attribute found in the message."""
    lowered = message.lower()
    name = str(attribute.get("name", "")).strip()
    signals: list[str] = list(attribute.get("extraction_signals", []))
    if name and name.lower() not in {s.lower() for s in signals}:
        signals.append(name)
    for phrase in sorted(signals, key=len, reverse=True):
        if len(phrase) < 3:
            continue
        index = lowered.find(phrase.lower())
        if index >= 0:
            return message[index: index + len(phrase)]
    return None


def first_attribute_value(message: str, attribute_name: str) -> str:
    """Extract the value following an attribute name in the message."""
    pattern = rf"{re.escape(attribute_name)}\s*(?:is|:|=)?\s*([^.,;]+)"
    match = re.search(pattern, message, re.IGNORECASE)
    if match and match.group(1).strip():
        return clean_attribute_value(match.group(1).strip())
    trailing_pattern = rf"((?:[a-z0-9]+\s+){{1,5}}{re.escape(attribute_name)})"
    trailing_match = re.search(trailing_pattern, message, re.IGNORECASE)
    if trailing_match:
        return clean_attribute_value(trailing_match.group(1).strip())
    return attribute_name


def clean_attribute_value(value: str) -> str:
    return re.sub(r"^(?:i(?:'d| would)?\s+)?prefer\s+(?:a\s+|an\s+)?", "", value.strip(), flags=re.IGNORECASE)


# ---------------------------------------------------------------------------
# Ignored-attribute detection
# ---------------------------------------------------------------------------

def ignored_attribute_names(
    message: str,
    attributes: list[dict],
    category_context: dict | None = None,
) -> list[str]:
    """Return canonical attribute names that the user explicitly says to ignore."""
    lowered = message.lower()
    ignore_patterns = [
        r"(?:do not|don't|dont|doesn't|doesnt)\s+care\s+about\s+([a-z0-9 \-]+)",
        r"([a-z0-9 \-]+)\s+(?:doesn't|doesnt)\s+matter",
        r"([a-z0-9 \-]+)\s+is\s+not\s+important",
    ]
    ignored: list[str] = []
    for pattern in ignore_patterns:
        for match in re.finditer(pattern, lowered):
            phrase = match.group(1).strip(" .")
            ignored.append(canonical_attribute(phrase, attributes, category_context))
    return dedupe_names(ignored)


# ---------------------------------------------------------------------------
# Context-value helpers
# ---------------------------------------------------------------------------

def room_context_value(lowered: str) -> str | None:
    if "old house" in lowered and "bedroom" in lowered:
        return "old house bedroom"
    if "bright room" in lowered:
        return "bright room"
    if "bedroom" in lowered:
        return "bedroom"
    if "living room" in lowered or "front room" in lowered:
        return "living room"
    if "old house" in lowered:
        return "old house"
    return None


def user_context_value(lowered: str) -> str | None:
    if "elderly" in lowered and "parents" in lowered:
        return "elderly parents"
    if "parents" in lowered:
        return "parents"
    if "single person" in lowered or "one person" in lowered:
        return "single person"
    return None


def indoor_room_value(lowered: str) -> str | None:
    for room in ["living room", "bedroom", "front room", "kitchen", "office", "family room", "dining room"]:
        if room in lowered:
            return room
    return None


def matching_phrase(lowered: str, original: str, terms: list[str]) -> str | None:
    """Return the first matching term from the message, preserving original casing."""
    for term in terms:
        index = lowered.find(term)
        if index >= 0:
            return original[index: index + len(term)]
    return None
