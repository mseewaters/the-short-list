"""Attribute schema helpers: canonical names, synonyms, and matching hints.

Provides the logic that maps user language onto category attribute schema names,
builds phrase/entity/question-based matching hints, and checks schema membership.
"""

import re
from typing import Any

from app.requirement_memory.utils import tokens


# ---------------------------------------------------------------------------
# Stop-words excluded from attribute alias phrases
# ---------------------------------------------------------------------------

ATTRIBUTE_ALIAS_STOPWORDS = {
    "what", "which", "where", "when", "does", "need", "needs", "have",
    "with", "your", "this", "that", "should", "prefer", "preference",
    "important", "matter", "product", "option", "options",
}


# ---------------------------------------------------------------------------
# Schema extraction
# ---------------------------------------------------------------------------

def extract_attribute_schema(category_context: dict | None) -> list[dict]:
    """Return the attribute_schema list from category context, or empty list."""
    attributes = category_context.get("attribute_schema", []) if category_context else []
    if not isinstance(attributes, list):
        return []
    return [a for a in attributes if isinstance(a, dict) and a.get("name")]


def extract_entity_candidates(category_context: dict | None) -> list[dict]:
    """Return the entity_candidates list from category context, or empty list."""
    entities = category_context.get("entity_candidates", []) if category_context else []
    if not isinstance(entities, list):
        return []
    return [e for e in entities if isinstance(e, dict) and e.get("name")]


def attribute_by_name(attribute_name: str, attributes: list[dict]) -> dict:
    """Return the attribute dict with the matching name, or empty dict."""
    for attribute in attributes:
        if str(attribute.get("name", "")).lower() == attribute_name.lower():
            return attribute
    return {}


def schema_allows_attribute(attribute_name: str, schema_names: set[str]) -> bool:
    """Return True when the attribute is in the schema (or the schema is empty)."""
    return not schema_names or attribute_name.lower() in schema_names


# ---------------------------------------------------------------------------
# Synonym tables
# ---------------------------------------------------------------------------

def generic_attribute_synonyms(name: str) -> set[str]:
    """Return hard-coded synonym set for well-known attribute names."""
    lookup: dict[str, set[str]] = {
        "noise level": {"quiet", "quiet operation", "silent", "low noise", "noisy", "noise", "sound level", "noise level"},
        "quiet operation": {"quiet", "quiet operation", "silent", "low noise", "noisy", "noise", "sound level", "noise level"},
        "profile": {"profile", "height", "low profile"},
        "room": {"room", "location", "use location"},
        "room dimensions": {"room size", "dimensions", "size"},
        "ceiling height": {"ceiling height", "height"},
        "style": {"style", "design", "finish", "aesthetics"},
        "lighting": {"lighting", "light", "lights", "dimmable", "lighting control"},
        "lighting control": {"lighting", "light", "lights", "dimmable", "lighting control"},
        "light": {"lighting", "light", "lights", "dimmable", "lighting control"},
        "compatibility": {"compatible", "works with", "support", "supports"},
        "smart home compatibility": {"smart", "smart home", "voice control", "app control", "wifi", "wi-fi", "compatible", "works with"},
        "smart compatibility": {"smart", "smart home", "voice control", "app control", "wifi", "wi-fi", "compatible", "works with"},
        "voice assistant compatibility": {"smart", "smart home", "voice control", "app control", "wifi", "wi-fi", "compatible", "works with"},
        "indoor/damp/wet rating": {"indoor", "dry", "damp", "wet", "outdoor", "location rating", "environment rating"},
        "damp/wet rating": {"indoor", "dry", "damp", "wet", "outdoor", "location rating", "environment rating"},
        "pet hair handling": {"pet hair", "hair handling", "pet"},
        "maintenance": {"maintenance", "bin", "filter"},
        "ease of use": {"ease", "controls", "setup", "simple"},
        "brightness": {"brightness", "bright", "glare"},
        "anti-glare": {"anti-glare", "glare"},
        "glare handling": {"anti-glare", "anti glare", "glare", "reflection", "reflections", "bright room"},
        "coverage": {"coverage", "range", "whole-home"},
        "speed": {"speed", "fast", "quick"},
        "capacity": {"capacity", "serving", "size"},
        "user context": {"user context", "intended use", "use case"},
    }
    return lookup.get(name.lower(), {name.lower()})


def attribute_synonyms(name: str, category_context: dict | None = None) -> set[str]:
    """Combine hard-coded synonyms with phrases derived from the category schema."""
    synonyms = generic_attribute_synonyms(name)
    if category_context:
        for hint in build_attribute_matching_hints(category_context):
            if str(hint.get("attributeName", "")).lower() == name.lower():
                for key in ["phrases", "questions", "entities", "decisionAxes"]:
                    values = hint.get(key, [])
                    if isinstance(values, list):
                        synonyms.update(str(v).lower() for v in values if v)
    return synonyms


# ---------------------------------------------------------------------------
# Canonical attribute resolution
# ---------------------------------------------------------------------------

def canonical_attribute(
    preferred_name: str,
    attributes: list[dict],
    category_context: dict | None = None,
) -> str:
    """Return the best-matching attribute schema name for a given preferred name."""
    if not attributes:
        return preferred_name

    preferred_tokens = tokens(preferred_name)
    synonyms = attribute_synonyms(preferred_name, category_context)
    preferred_text = preferred_name.lower()
    best_name = preferred_name
    best_score = 0

    for attribute in attributes:
        name = str(attribute.get("name", ""))
        candidate_tokens = tokens(name)
        candidate_synonyms = attribute_synonyms(name, category_context)
        score = len(preferred_tokens.intersection(candidate_tokens))
        score += len(preferred_tokens.intersection(tokens(" ".join(candidate_synonyms))))
        if name.lower() in synonyms:
            score += 5
        if preferred_text in candidate_synonyms:
            score += 5
        if any(synonym in name.lower() for synonym in synonyms):
            score += 3
        if any(synonym in candidate_synonyms for synonym in synonyms):
            score += 4
        if any(synonym in preferred_text for synonym in candidate_synonyms):
            score += 3
        if score > best_score:
            best_score = score
            best_name = name

    return best_name if best_score > 0 else preferred_name


def canonical_attribute_key(
    attribute_name: str,
    attributes: list[dict],
    category_context: dict | None,
) -> str:
    return canonical_attribute(attribute_name, attributes, category_context).lower()


def closest_schema_attribute(
    message: str,
    attributes: list[dict],
    category_context: dict | None = None,
) -> dict | None:
    """Return the attribute whose name best matches the message tokens."""
    if not attributes:
        return None

    message_tokens = tokens(message)
    best_attribute = None
    best_score = 0
    for attribute in attributes:
        name = str(attribute.get("name", ""))
        attribute_tokens = tokens(name)
        score = len(message_tokens.intersection(attribute_tokens))
        for synonym in attribute_synonyms(name, category_context):
            if synonym in message.lower():
                score += 3
        if score > best_score:
            best_score = score
            best_attribute = attribute

    return best_attribute if best_score > 0 else None


# ---------------------------------------------------------------------------
# Phrase helpers for hint building
# ---------------------------------------------------------------------------

def meaningful_alias_word(word: str) -> bool:
    return len(word) > 3 and word not in ATTRIBUTE_ALIAS_STOPWORDS


def attribute_name_phrases(text: str) -> set[str]:
    """Return single-word and bigram phrases from an attribute name or entity name."""
    lowered = text.lower().replace("/", " ")
    words = [w for w in re.findall(r"[a-z0-9]+", lowered) if meaningful_alias_word(w)]
    phrases: set[str] = {lowered.strip()}
    phrases.update(words)
    for i in range(len(words) - 1):
        phrases.add(f"{words[i]} {words[i + 1]}")
    return {p for p in phrases if p}


def question_attribute_phrases(question_text: str, attribute_name: str) -> set[str]:
    """Return phrases from a question that overlap with the attribute name."""
    if not tokens(question_text).intersection(tokens(attribute_name)):
        return set()
    return related_text_attribute_phrases(question_text, attribute_name)


def related_text_attribute_phrases(text: str, attribute_name: str) -> set[str]:
    """Return words and bigrams from text that share tokens with the attribute name."""
    words = [w for w in re.findall(r"[a-z0-9]+", text.lower()) if meaningful_alias_word(w)]
    attribute_tokens = tokens(attribute_name)
    phrases: set[str] = set()
    for i, word in enumerate(words):
        if word in attribute_tokens:
            phrases.add(word)
        if i < len(words) - 1:
            pair = f"{words[i]} {words[i + 1]}"
            if tokens(pair).intersection(attribute_tokens):
                phrases.add(pair)
    return phrases


def entity_maps_to_attribute(entity_text: str, attribute_name: str, attribute_phrases: set[str]) -> bool:
    entity_tokens = tokens(entity_text)
    attribute_tokens = tokens(attribute_name)
    if entity_tokens.intersection(attribute_tokens):
        return True
    entity_lower = entity_text.lower()
    return any(phrase and phrase in entity_lower for phrase in attribute_phrases if len(phrase) > 2)


# ---------------------------------------------------------------------------
# Matching hints
# ---------------------------------------------------------------------------

def build_attribute_matching_hints(category_context: dict | None) -> list[dict[str, Any]]:
    """Build per-attribute phrase/entity/question/axis hint dicts from category context.

    These hints drive both the LLM prompt and the local extraction fallback.
    """
    attributes = extract_attribute_schema(category_context)
    if not attributes:
        return []

    intake_questions = category_context.get("intake_questions", []) if category_context else []
    decision_axes = category_context.get("decision_axes", []) if category_context else []
    entities = extract_entity_candidates(category_context)

    hints: list[dict[str, Any]] = []
    for attribute in attributes:
        name = str(attribute.get("name", "")).strip()
        if not name:
            continue

        phrase_values = set(attribute_name_phrases(name))
        questions: list[str] = []
        axes: list[str] = []
        entity_names: list[str] = []

        for question in (intake_questions if isinstance(intake_questions, list) else []):
            if not isinstance(question, dict):
                continue
            mapped = str(question.get("maps_to_attribute", "")).strip()
            text = str(question.get("question", "")).strip()
            if mapped.lower() == name.lower() and text:
                questions.append(text)
                phrase_values.update(question_attribute_phrases(text, name))

        for axis in (decision_axes if isinstance(decision_axes, list) else []):
            if not isinstance(axis, dict):
                continue
            axis_text = " ".join(
                str(axis.get(field, "")) for field in ["name", "positive_direction", "tradeoff_against"]
            ).strip()
            if axis_text and tokens(name).intersection(tokens(axis_text)):
                axes.append(axis_text)
                phrase_values.update(related_text_attribute_phrases(axis_text, name))

        for entity in entities:
            entity_name = str(entity.get("name", "")).strip()
            if not entity_name:
                continue
            mapped_attribute = str(
                entity.get("maps_to_attribute") or entity.get("attribute") or entity.get("attribute_name") or ""
            ).strip()
            if mapped_attribute and mapped_attribute.lower() != name.lower():
                continue
            entity_text = " ".join(str(entity.get(f, "")) for f in ["name", "type", "source_field"])
            if mapped_attribute.lower() == name.lower() or entity_maps_to_attribute(entity_text, name, phrase_values):
                entity_names.append(entity_name)
                phrase_values.update(attribute_name_phrases(entity_name))

        hints.append({
            "attributeName": name,
            "valueType": attribute.get("value_type"),
            "importance": attribute.get("importance"),
            "scoreDirection": attribute.get("score_direction"),
            "phrases": sorted(phrase_values)[:24],
            "questions": questions[:4],
            "entities": entity_names[:12],
            "decisionAxes": axes[:4],
        })

    return hints
