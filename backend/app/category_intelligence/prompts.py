import json


def build_category_intelligence_prompt(category: str, context: str | None = None) -> str:
    payload = {
        "category": category,
        "context": context or "",
        "task": """
            You are building concise category intelligence for a consumer decision support app.

            Your job is not to list everything about the category.
            Your job is to identify the small set of decision-relevant factors that most buyers would actually use to compare options.

            Focus on the 5-15 main attributes that drive product choice.

            Definitions:
            - important_attributes: the core product attributes a buyer would compare across options.
            - key_decision_factors: user-facing buying criteria, often derived from attributes.
            - comparison_dimensions: tradeoff axes buyers use to choose between good options.
            - common_entities: reusable product/category concepts, not brand names unless the category is brand-defined.
            - risks_or_gotchas: practical issues that could cause a bad purchase.
            - clarifying_questions: questions that map directly to important_attributes.

            Rules:
            - Keep every list concise.
            - Do not include brands as common_entities.
            - Do not include every possible feature.
            - Do not split one idea into many near-duplicates.
            - Do not include subjective filler like "style" or "aesthetics" unless it is a primary decision driver for the category.
            - Do not include room, user, or context-specific items unless the provided context makes them central.
            - Prefer decision-making attributes over technical trivia.
            - Prefer attributes that can be used later for filtering, scoring, or comparison.
            - Attribute names should be canonical and reusable.
            - Avoid duplicate concepts across fields.
            - If two attributes overlap, keep the more useful buyer-facing one.
            - Each clarifying question must map to one important attribute.

            Target list sizes:
            - key_decision_factors: 5-8 items
            - common_entities: 3-8 items
            - important_attributes: 5-15 items
            - comparison_dimensions: 4-8 items
            - risks_or_gotchas: 3-7 items
            - good_default_recommendation_logic: 3-7 items
            - clarifying_questions: 4-8 items

            Return only valid JSON matching the required output shape.
            Do not include markdown, commentary, or extra keys.
        """,
        "required_output_shape": {
            "category_summary": "string",
            "buyer_need": "string",
            "key_decision_factors": ["string"],
            "common_entities": ["string"],
            "important_attributes": ["string"],
            "comparison_dimensions": ["string"],
            "risks_or_gotchas": ["string"],
            "good_default_recommendation_logic": ["string"],
            "clarifying_questions": ["string"],
            "confidence": "low | medium | high",
        },
        "quality_bar": {
            "good_output": "Concise, deduplicated, buyer-facing, decision-relevant.",
            "bad_output": "Long feature inventory, brand list, repeated concepts, technical trivia, or generic shopping advice."
        },
        "example_attribute_filtering": {
            "category": "Road Bike Helmets",
            "good_important_attributes": [
                "Fit",
                "Safety certification",
                "Rotational-impact protection",
                "Ventilation",
                "Weight",
                "Aerodynamics",
                "Retention system",
                "Eyewear compatibility",
                "Price"
            ],
            "bad_important_attributes": [
                "Color",
                "Hair",
                "Accessories",
                "Vent count",
                "Padding thickness",
                "Aesthetics",
                "Value",
                "All-day comfort",
                "Cooling performance"
            ],
            "why_bad": "These are either too granular, subjective, duplicated by better attributes, or not primary decision drivers."
        }
    }

    return (
        "You are building category intelligence for a consumer decision support app. "
        "Return only valid JSON matching the required output shape. "
        "Do not include markdown, commentary, or extra keys.\n\n"
        f"{json.dumps(payload, indent=2)}"
    )


def build_category_normalization_prompt(category: str, raw_intelligence: dict) -> str:
    payload = {
        "category": category,
        "raw_intelligence": raw_intelligence,
        "task": """
            Convert raw category intelligence into a compact machine-usable normalized structure.

            Use semantic judgment. Do not rely on substring matching.
            Keep the output concise and decision-relevant.

            Entity type definitions:
            - product_type: category, subcategory, or product class.
            - feature: product capability, component, or included mechanism.
            - performance_metric: measurable performance outcome.
            - installation_constraint: compatibility, fit, mounting, sizing, or setup constraint.
            - risk: bad outcome or purchase gotcha.
            - style: aesthetic or design family only.

            Attribute guidance:
            - attribute_schema should contain the core attributes a user or product can answer.
            - Always include Budget as an attribute.
            - Intake questions must map exactly to an attribute_schema name.
            - Do not map budget questions to safety, fit, quality, or value attributes.
            - Do not invent scoring or recommendations.

            Assessment metadata:
            - score_direction: higher_is_better, lower_is_better, match_user_preference, must_have, informational.
            - evidence_type: spec, review, user_preference, expert_rule, mixed.
            - quantifiable: true when the attribute can be represented as a number, range, boolean, or concrete spec.

            Target list sizes:
            - entity_candidates: 3-10 items
            - attribute_schema: 5-15 items
            - decision_axes: 4-8 items
            - graph_edges: enough to connect the category, attributes, entities, axes, and risks
            - intake_questions: 4-8 items

            Return only valid JSON matching the required output shape.
            Do not include markdown, commentary, or extra keys.
        """,
        "required_output_shape": {
            "entity_candidates": [
                {
                    "name": "string",
                    "type": (
                        "product_type | feature | performance_metric | "
                        "installation_constraint | risk | style"
                    ),
                    "synonyms": ["string"],
                    "source_field": "string",
                }
            ],
            "attribute_schema": [
                {
                    "name": "string",
                    "value_type": "string | number | boolean | enum | range",
                    "unit": "string or null",
                    "importance": "high | medium | low",
                    "user_visible": True,
                    "comparison_relevant": True,
                    "score_direction": (
                        "higher_is_better | lower_is_better | match_user_preference | "
                        "must_have | informational"
                    ),
                    "evidence_type": "spec | review | user_preference | expert_rule | mixed",
                    "quantifiable": True,
                }
            ],
            "decision_axes": [
                {
                    "name": "string",
                    "positive_direction": "string",
                    "tradeoff_against": "string or null",
                    "derived_from": "string",
                }
            ],
            "graph_edges": [
                {
                    "from": "string",
                    "relationship": (
                        "HAS_ENTITY | HAS_ATTRIBUTE | IMPACTS | RELATES_TO | TRADEOFF_WITH"
                    ),
                    "to": "string",
                    "confidence": "low | medium | high",
                }
            ],
            "intake_questions": [
                {
                    "question": "string",
                    "maps_to_attribute": "must exactly match one attribute_schema.name",
                    "priority": "high | medium | low",
                    "answer_type": "string | number | boolean | enum | range",
                }
            ],
        },
    }

    return (
        "You normalize category intelligence for a consumer decision support app. "
        "Return only valid JSON matching the required output shape. "
        "Do not include markdown, commentary, or extra keys.\n\n"
        f"{json.dumps(payload, indent=2)}"
    )


def build_category_extraction_prompt(user_input: str, additional_context: str | None = None) -> str:
    payload = {
        "user_input": user_input,
        "additional_context": additional_context or "",
        "task": """
            Extract the canonical reusable product or solution category, plus one broader parent category and three narrower child categories.

            Definitions:

            - proposed_category:
            The best reusable shopping category for the user's input. It should be specific enough to support useful comparison, but broad enough to contain many competing products.

            - broader_category:
            The immediate parent category one level above proposed_category. It should contain proposed_category and related sibling categories.
            Example: "Ceiling Fans" -> "Fans"
            Example: "Robot Vacuums" -> "Vacuum Cleaners"
            Do not make this too broad, such as "Home Improvement" unless the input is genuinely vague.

            - more_specific_categories:
            Three child categories one level below proposed_category.
            These must be narrower reusable shopping categories, not attributes, preferences, rooms, brands, features, or one-off use cases.
            Good: "Low Profile Ceiling Fans", "Smart Ceiling Fans", "Outdoor Ceiling Fans"
            Bad: "Quiet Ceiling Fans", "Ceiling Fans for Bedrooms", "White Ceiling Fans", "Budget Ceiling Fans"

            Rules:

            - proposed_category should be the Goldilocks level: not too broad, not too specific.
            - broader_category should be exactly one useful level broader.
            - more_specific_categories should be exactly one useful level narrower.
            - Do not include room/location, budget, style, color, brand, user demographic, or performance preference unless it defines an established shopping subcategory.
            - A more specific category must pass this test: would a retailer, review site, or buying guide plausibly have this as a category page?
            - If the user input is too vague, return a broad proposed_category, set confidence to low, and still provide reasonable broader/more specific options.
            - Return only valid JSON.
            - Prefer concrete categories over abstract concepts.
            - Return a singular or plural category name only. No explanations.
            """,
        "examples": [
            {
                "input": "I need a quiet low-profile ceiling fan for an old house bedroom.",
                "proposed_category": "Ceiling Fans",
                "broader_category": "Home Cooling",
                "more_specific_categories": [
                    "Low Profile Ceiling Fans",
                    "Smart Ceiling Fans",
                    "Outdoor Ceiling Fans"
                ],
            },
            { 
                "input": "I want movie theater vibes in my front room.",
                "proposed_category": "Home Entertainment Systems",
                "broader_category": "Home Entertainment",
                "more_specific_categories": [
                    "Ultra Short Throw Projectors",
                    "Soundbars",
                    "Surround Sound Systems"
                ]
            },
            {
                "input": "I can't hear people during Teams calls.",
                "proposed_category": "Headsets",
                "broader_category": "Computer Accessories",
                "more_specific_categories": [
                    "Wireless Headsets",
                    "Noise-Canceling Headsets",
                    "Office Headsets"
                ]
            },
            {
                "input": "I need something for my house.",
                "proposed_category": "Home Improvement",
                "broader_category": "Home",
                "more_specific_categories": [
                    "Home Entertainment",
                    "Climate Control",
                    "Home Organization"
                ]
            }
        ],
        "required_output_shape": {
            "proposed_category": "string",
            "broader_category": "string",
            "more_specific_categories": ["string", "string", "string"],
            "confidence": "low | medium | high",
            "explanation": "string",
        },
    }

    return (
        "You identify the core reusable consumer product category from messy user input. "
        "Return only valid JSON matching the required output shape. "
        "Do not include markdown, commentary, or extra keys.\n\n"
        f"{json.dumps(payload, indent=2)}"
    )
