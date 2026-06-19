"""LLM prompt builders for requirement memory operations.

All functions return a string suitable for passing directly to the LLM
generate_json() interface. Prompts include a task description, category
schema context, output shape, and examples.
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
        "categoryAttributeSchema": extract_attribute_schema(category_context),
        "categoryAttributeMatchingHints": build_attribute_matching_hints(category_context),
        "categoryIntakeQuestions": category_context.get("intake_questions", []) if category_context else [],
        "categoryDecisionAxes": category_context.get("decision_axes", []) if category_context else [],
        "categoryEntityCandidates": extract_entity_candidates(category_context),
        "task": """
            Interpret the user's latest message and return only requirement observations that should update durable requirement memory.

            This is not category extraction. The category is already selected.
            Align observations to the category attribute schema when possible.
            Use semantic judgment for ambiguous language, indirect statements, and stakeholder needs.
            Use categoryAttributeMatchingHints as category-specific guidance. These hints are generated from the selected
            category schema, intake questions, decision axes, and entity candidates. They are not hardcoded examples.

            Rules:
            - Do not summarize conversation history.
            - Return only new observations from latestUserMessage.
            - If the latest message includes both requirement information and a clarifying question, extract the stated requirement information first.
            - Do not create a requirement for an attribute that the user only asked a question about.
            - Preserve existing requirements by omitting them unless the latest message adds detail, overrides them, weakens them, or says to ignore them.
            - Use status "specified" for explicit needs and constraints.
            - Use status "inferred" only when the user strongly implies a need without directly stating it.
            - Use status "ignored" when the user says an attribute does not matter.
            - Use status "conflicted" when the new message contradicts existing memory but does not clearly override it.
            - Prefer canonical attribute names from categoryAttributeSchema.
            - Reuse categoryAttributeSchema names whenever the user's wording is a synonym, example, entity candidate,
              answer to an intake question, decision-axis phrase, or obvious value for that attribute.
            - Do not overfit to one product category. Apply the same schema/entity/decision-axis matching process for TVs,
              helmets, routers, appliances, furniture, software, and other categories.
            - If a user mentions a concrete feature, compatibility target, certification, use context, room, activity, person,
              or product option, map it to the closest schema attribute when the category hints support that mapping.
            - Do not ask follow-up questions for schema attributes already answered by direct wording, entity mentions,
              or clear contextual inference.
            - If no schema attribute fits, use a concise buyer-facing attribute name.
            - evidence must be the shortest relevant phrase from latestUserMessage.
            - confidence must be a number from 0 to 1.
            - source must be "explicit_user_statement" or "inferred_from_user_statement".
            - importance must be "critical", "high", "medium", "low", or "unknown".
            - normalizedOperator must be one of "max", "min", "equals", "one_of", "avoid", "prefer", "match".
            - normalizedValue should be typed for scoring: number for numeric limits, boolean for yes/no, list for one_of/avoid, or concise string.
            - unit should be a concrete unit such as "usd", "feet", "inches", "square_feet", or null.
            - hardness should be "hard" for strict filters/compatibility/budget caps, "soft" for preferences, or "ignore" for ignored attributes.
            - weight should be 0.0 to 1.0 and reflect scoring influence separately from hardness.
            - productEvidenceConfidence should be null during intake unless product evidence is already known.
            - missingProductDataStrategy should be "exclude_if_missing", "penalize_unknown", "neutral_if_missing", or "manual_review".
            - scoringFunction should describe how product values should be scored, such as "numeric_max", "numeric_min", "exact_match", "enum_preference_match", "semantic_preference_match", "avoid_match", or "do_not_score".
            - needsMoreSpecification should be true when the requirement is too vague to score reliably against real product data.
            - If needsMoreSpecification is true, specificationQuestion must ask for the missing specificity.
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
                "categoryName": "Any category",
                "categoryAttributeSchema": [{"name": "Attribute A"}, {"name": "Attribute B"}],
                "categoryAttributeMatchingHints": [
                    {
                        "attributeName": "Attribute A",
                        "phrases": ["example option", "related feature"],
                        "questions": ["Which example option do you need?"],
                        "entities": ["Example entity"],
                    }
                ],
                "latestUserMessage": "I need the example option and do not care about Attribute B.",
                "requirements": [
                    {
                        "attributeName": "Attribute A",
                        "status": "specified",
                        "value": "example option",
                        "normalizedOperator": "equals",
                        "normalizedValue": "example option",
                        "unit": None,
                        "importance": "high",
                        "hardness": "soft",
                        "weight": 0.8,
                        "source": "explicit_user_statement",
                        "confidence": 0.9,
                        "productEvidenceConfidence": None,
                        "missingProductDataStrategy": "penalize_unknown",
                        "scoringFunction": "semantic_preference_match",
                        "needsMoreSpecification": False,
                        "specificationQuestion": None,
                        "evidence": "example option",
                    },
                    {
                        "attributeName": "Attribute B",
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
                        "evidence": "do not care about Attribute B",
                    },
                ],
            },
            {
                "latestUserMessage": "My wife hates noisy ones.",
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
                        "evidence": "hates noisy ones",
                    }
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
        "categoryAttributeSchema": extract_attribute_schema(category_context),
        "categoryEntityCandidates": extract_entity_candidates(category_context),
        "categoryIntakeQuestions": category_context.get("intake_questions", []) if category_context else [],
        "task": """
            Answer the user's question about a category decision attribute.

            Keep the answer concise and practical. Explain the common options and when each option matters.
            Use categoryEntityCandidates as supporting context for known options, product types, features, risks, and category concepts.
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
