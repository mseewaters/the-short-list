"""LLM prompt builders for requirement memory operations.

All functions return a string suitable for passing directly to the LLM
generate_json() interface.
"""

import json

from app.requirement_memory.attributes import (
    extract_attribute_schema,
    extract_entity_candidates,
    build_attribute_matching_hints,
)
from app.schemas import UserRequirementProfile


def build_requirement_memory_prompt(
    *,
    existing_profile: UserRequirementProfile,
    category_name: str | None,
    latest_user_message: str,
    category_context: dict | None,
) -> str:
    """Return the prompt for extracting requirement observations from the latest user message."""
    payload = {
        "task_type": "requirement_memory_update",
        "categoryName": category_name,
        "latestUserMessage": latest_user_message,
        "existingUserRequirementProfile": existing_profile.model_dump(),
        "categoryDecisionAttributes": extract_attribute_schema(category_context),
        "categoryAttributeMatchingHints": build_attribute_matching_hints(category_context),
        "categoryEntityTerms": [e["name"] for e in extract_entity_candidates(category_context)],
        "task": """
            Interpret the user's latest message and return only requirement observations
            that should update durable requirement memory.

            This is not category extraction. The category is already selected.

            categoryDecisionAttributes lists the attributes for this category. Each attribute
            has extraction_signals — phrases users commonly say for that attribute. Use these
            as primary signals for mapping user language to attribute names.

            categoryAttributeMatchingHints provides additional phrase coverage and context
            for each attribute (signals, key, score direction, typical values).

            Rules:
            - Do not summarize conversation history.
            - Return only new observations from latestUserMessage.
            - If the message includes both requirement info and a question, extract the
              requirement info first; do not create a requirement for what they only asked about.
            - Preserve existing requirements by omitting them unless the latest message
              adds detail, overrides, weakens, or dismisses them.
            - status: "specified" for explicit needs; "inferred" when strongly implied;
              "ignored" when the user says it doesn't matter; "conflicted" when contradictory.
            - Prefer attribute names from categoryDecisionAttributes.
            - Use extraction_signals from categoryAttributeMatchingHints to map colloquial
              language ("my wife hates the noise" → Noise Level; "works with Alexa" →
              Smart Home Compatibility).
            - importance is the user's expressed importance for THIS requirement, not a
              schema-level property. Set it based on how strongly the user states the need.
            - evidence must be the shortest relevant phrase from latestUserMessage.
            - confidence: 0 to 1.
            - source: "explicit_user_statement" or "inferred_from_user_statement".
            - normalizedOperator: max | min | equals | one_of | avoid | prefer | match
            - normalizedValue: typed for scoring (number, boolean, list, or concise string).
            - unit: concrete unit ("usd", "feet", "inches", "square_feet", "dB") or null.
            - hardness: "hard" for strict filters/budget caps; "soft" for preferences;
              "ignore" for ignored attributes.
            - weight: 0.0–1.0, scoring influence separately from hardness.
            - scoringFunction: "numeric_max", "numeric_min", "exact_match",
              "enum_preference_match", "semantic_preference_match", "avoid_match",
              or "do_not_score".
            - needsMoreSpecification: true when the requirement is too vague to score.
            - If needsMoreSpecification is true, specificationQuestion must ask for
              the missing specificity.
        """,
        "required_output_shape": {
            "requirements": [
                {
                    "attributeName": "string",
                    "status": "specified | inferred | ignored | conflicted",
                    "value": "string, number, boolean, or null",
                    "normalizedOperator": "max | min | equals | one_of | avoid | prefer | match",
                    "normalizedValue": "typed value, list, or null",
                    "unit": "string or null",
                    "importance": "critical | high | medium | low | unknown",
                    "hardness": "hard | soft | ignore",
                    "weight": 0.0,
                    "source": "explicit_user_statement | inferred_from_user_statement",
                    "confidence": 0.0,
                    "productEvidenceConfidence": "number or null",
                    "missingProductDataStrategy": "exclude_if_missing | penalize_unknown | neutral_if_missing | manual_review",
                    "scoringFunction": "string",
                    "needsMoreSpecification": False,
                    "specificationQuestion": "string or null",
                    "evidence": "short quote from latestUserMessage",
                }
            ]
        },
        "examples": [
            {
                "categoryDecisionAttributes": [
                    {
                        "key": "noise_level",
                        "name": "Noise Level",
                        "extraction_signals": ["quiet", "silent", "noisy", "loud", "sound", "hears it"],
                    },
                    {
                        "key": "smart_home_compatibility",
                        "name": "Smart Home Compatibility",
                        "extraction_signals": ["alexa", "google home", "homekit", "smart", "voice control"],
                    },
                ],
                "latestUserMessage": "My wife hates when she can hear it running, and it needs to work with Alexa.",
                "requirements": [
                    {
                        "attributeName": "Noise Level",
                        "status": "specified",
                        "value": "quiet",
                        "normalizedOperator": "prefer",
                        "normalizedValue": "quiet",
                        "unit": None,
                        "importance": "critical",
                        "hardness": "soft",
                        "weight": 0.9,
                        "source": "explicit_user_statement",
                        "confidence": 0.95,
                        "productEvidenceConfidence": None,
                        "missingProductDataStrategy": "penalize_unknown",
                        "scoringFunction": "semantic_preference_match",
                        "needsMoreSpecification": False,
                        "specificationQuestion": None,
                        "evidence": "hates when she can hear it running",
                    },
                    {
                        "attributeName": "Smart Home Compatibility",
                        "status": "specified",
                        "value": "Alexa",
                        "normalizedOperator": "equals",
                        "normalizedValue": "Alexa",
                        "unit": None,
                        "importance": "high",
                        "hardness": "hard",
                        "weight": 0.85,
                        "source": "explicit_user_statement",
                        "confidence": 0.97,
                        "productEvidenceConfidence": None,
                        "missingProductDataStrategy": "exclude_if_missing",
                        "scoringFunction": "exact_match",
                        "needsMoreSpecification": False,
                        "specificationQuestion": None,
                        "evidence": "needs to work with Alexa",
                    },
                ],
            },
            {
                "latestUserMessage": "I don't care about style.",
                "requirements": [
                    {
                        "attributeName": "Style",
                        "status": "ignored",
                        "value": None,
                        "normalizedOperator": "match",
                        "normalizedValue": None,
                        "unit": None,
                        "importance": "low",
                        "hardness": "ignore",
                        "weight": 0,
                        "source": "explicit_user_statement",
                        "confidence": 0.95,
                        "productEvidenceConfidence": None,
                        "missingProductDataStrategy": "neutral_if_missing",
                        "scoringFunction": "do_not_score",
                        "needsMoreSpecification": False,
                        "specificationQuestion": None,
                        "evidence": "don't care about style",
                    }
                ],
            },
        ],
    }

    return (
        "You update durable user requirement memory for a consumer decision support app. "
        "Return only valid JSON matching the required output shape. "
        "Do not include markdown, commentary, or extra keys.\n\n"
        f"{json.dumps(payload, indent=2)}"
    )


def build_clarifying_answer_prompt(
    *,
    category_name: str | None,
    latest_user_message: str,
    category_context: dict | None,
    matched_attribute: dict,
) -> str:
    """Return the prompt for answering a user question about a category attribute."""
    payload = {
        "task_type": "category_attribute_clarifying_answer",
        "categoryName": category_name,
        "latestUserMessage": latest_user_message,
        "matchedAttribute": matched_attribute,
        "categoryDecisionAttributes": extract_attribute_schema(category_context),
        "categoryEntityTerms": [e["name"] for e in extract_entity_candidates(category_context)],
        "task": """
            Answer the user's question about a category decision attribute.

            Keep the answer concise and practical. Explain the common options and when each
            matters. Use the attribute's typical_values and assessment_note as guidance.
            Use categoryEntityTerms as supporting context for known options and product types.
            Do not choose for the user unless their needs clearly imply a default.
            Do not update requirement memory in this response.
            End by asking for the user's preference only if the attribute is decision-relevant.
        """,
        "required_output_shape": {
            "answer": "string",
        },
    }

    return (
        "You answer clarifying questions during product requirement intake. "
        "Return only valid JSON matching the required output shape. "
        "Do not include markdown, commentary, or extra keys.\n\n"
        f"{json.dumps(payload, indent=2)}"
    )
