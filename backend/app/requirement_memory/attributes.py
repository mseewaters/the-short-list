"""Attribute schema helpers: canonical names, extraction signals, and matching hints.

Reads from CategorySchema.decision_attributes. Each attribute carries its own
extraction_signals list, which replaces the old hardcoded synonym tables.
"""

import re
from typing import Any

from app.requirement_memory.utils import tokens


# ---------------------------------------------------------------------------
# Schema extraction from category_context
# ---------------------------------------------------------------------------

def extract_attribute_schema(category_context: dict | None) -> list[dict]:
    """Return decision_attributes from category context, or empty list."""
    attributes = category_context.get("decision_attributes", []) if category_context else []
    if not isinstance(attributes, list):
        return []
    return [a for a in attributes if isinstance(a, dict) and a.get("name")]


def extract_entity_candidates(category_context: dict | None) -> list[dict]:
    """Return entity_terms as simple name dicts, or empty list."""
    terms = category_context.get("entity_terms", []) if category_context else []
    if not isinstance(terms, list):
        return []
    return [{"name": t} for t in terms if isinstance(t, str) and t]


def attribute_by_name(attribute_name: str, attributes: list[dict]) -> dict:
    """Return the attribute dict matching the name (case-insensitive), or empty dict."""
    name_lower = attribute_name.lower()
    for attribute in attributes:
        if str(attribute.get("name", "")).lower() == name_lower:
            return attribute
        if str(attribute.get("key", "")).lower() == name_lower:
            return attribute
    return {}


def schema_allows_attribute(attribute_name: str, schema_names: set[str]) -> bool:
    """Return True when the attribute is in the schema or the schema is empty."""
    return not schema_names or attribute_name.lower() in schema_names


# ---------------------------------------------------------------------------
# Attribute matching via extraction_signals
# ---------------------------------------------------------------------------

ATTRIBUTE_ALIAS_STOPWORDS = {
    "what", "which", "where", "when", "does", "need", "needs", "have",
    "with", "your", "this", "that", "should", "prefer", "preference",
    "important", "matter", "product", "option", "options",
}


def meaningful_alias_word(word: str) -> bool:
    return len(word) > 3 and word not in ATTRIBUTE_ALIAS_STOPWORDS


def attribute_name_phrases(text: str) -> set[str]:
    """Return single-word and bigram phrases from an attribute name."""
    lowered = text.lower().replace("/", " ")
    words = [w for w in re.findall(r"[a-z0-9]+", lowered) if meaningful_alias_word(w)]
    phrases: set[str] = {lowered.strip()}
    phrases.update(words)
    for i in range(len(words) - 1):
        phrases.add(f"{words[i]} {words[i + 1]}")
    return {p for p in phrases if p}


def _attribute_signal_set(attribute: dict) -> set[str]:
    """Return all matching phrases for an attribute: name phrases + extraction_signals."""
    signals: set[str] = attribute_name_phrases(str(attribute.get("name", "")))
    for signal in attribute.get("extraction_signals", []):
        if isinstance(signal, str) and signal:
            signals.add(signal.lower())
    return signals


def canonical_attribute(
    preferred_name: str,
    attributes: list[dict],
    category_context: dict | None = None,
) -> str:
    """Return the best-matching schema attribute name for a given preferred name."""
    if not attributes:
        return preferred_name

    preferred_tokens = tokens(preferred_name)
    preferred_lower = preferred_name.lower()
    best_name = preferred_name
    best_score = 0

    for attribute in attributes:
        name = str(attribute.get("name", ""))
        signals = _attribute_signal_set(attribute)

        score = len(preferred_tokens.intersection(tokens(name)))
        if preferred_lower in signals:
            score += 5
        if any(signal in preferred_lower for signal in signals if len(signal) > 2):
            score += 3
        if any(tok in signals for tok in preferred_tokens):
            score += 2

        if score > best_score:
            best_score = score
            best_name = name

    return best_name if best_score > 0 else preferred_name


def canonical_attribute_key(
    attribute_name: str,
    attributes: list[dict],
    category_context: dict | None,
) -> str:
    matched_name = canonical_attribute(attribute_name, attributes, category_context)
    for attribute in attributes:
        if str(attribute.get("name", "")).lower() == matched_name.lower():
            return str(attribute.get("key") or matched_name).lower()
    return matched_name.lower()


def closest_schema_attribute(
    message: str,
    attributes: list[dict],
    category_context: dict | None = None,
) -> dict | None:
    """Return the attribute whose signals best match the message."""
    if not attributes:
        return None

    message_lower = message.lower()
    message_tokens = tokens(message)
    best_attribute = None
    best_score = 0

    for attribute in attributes:
        signals = _attribute_signal_set(attribute)
        score = len(message_tokens.intersection(tokens(str(attribute.get("name", "")))))
        for signal in signals:
            if signal and signal in message_lower:
                score += 3 if len(signal) > 4 else 1
        if score > best_score:
            best_score = score
            best_attribute = attribute

    return best_attribute if best_score > 0 else None


# ---------------------------------------------------------------------------
# Matching hints for LLM and local extraction
# ---------------------------------------------------------------------------

def build_attribute_matching_hints(category_context: dict | None) -> list[dict[str, Any]]:
    """Build per-attribute phrase/signal hint dicts from the category schema.

    These hints drive both the LLM requirement extraction prompt and the
    local extraction fallback.
    """
    attributes = extract_attribute_schema(category_context)
    if not attributes:
        return []

    hints: list[dict[str, Any]] = []
    for attribute in attributes:
        name = str(attribute.get("name", "")).strip()
        if not name:
            continue

        extraction_signals = [
            s for s in attribute.get("extraction_signals", [])
            if isinstance(s, str) and s
        ]
        phrase_values = attribute_name_phrases(name)
        phrase_values.update(s.lower() for s in extraction_signals)

        hints.append({
            "attributeName": name,
            "attributeKey": attribute.get("key", ""),
            "valueType": attribute.get("value_type"),
            "searchGate": attribute.get("search_gate", False),
            "scoreDirection": attribute.get("score_direction"),
            "phrases": sorted(phrase_values)[:24],
            "extractionSignals": extraction_signals[:12],
            "clarifyingQuestion": attribute.get("clarifying_question", ""),
            "typicalValues": attribute.get("typical_values"),
        })

    return hints
