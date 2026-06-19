import json


def build_category_schema_prompt(category: str, context: str | None = None) -> str:
    payload = {
        "schema_task": "category_schema",
        "category": category,
        "context": context or "general consumer purchase",
        "task": """
            Build a CategorySchema for a consumer decision support app.

            Your output serves TWO purposes:
            1. Guiding a conversation to understand what the user needs
            2. Scoring real products against those needs

            For each decision_attribute:

            key:
              Stable snake_case identifier. Generate from name (e.g. "Noise Level" -> "noise_level").

            name:
              Human-readable display name (title case).

            search_gate:
              true ONLY for 2-4 attributes where a product recommendation is meaningless
              without knowing the user's answer — even if the answer is "I don't care."
              Budget is always search_gate: true. Room size for fans is search_gate: true.
              Smart-home ecosystem is NOT search_gate (we can show products before knowing).

            value_type:
              number   — a single numeric value (price, dB, sq ft)
              enum     — one of a fixed option set
              boolean  — yes/no, has/doesn't have
              range    — a numeric interval (e.g. coverage area)
              string   — free text when nothing else fits

            unit:
              A concrete unit when value_type is number or range ("usd", "dB", "inches",
              "sq_ft", "watts"). null for everything else.

            score_direction:
              higher_is_better  — more is better (coverage, brightness, airflow)
              lower_is_better   — less is better (noise, price, weight)
              match_preference  — match user's stated value (style, ecosystem, color)
              must_have         — binary; product either qualifies or doesn't

            typical_values:
              enum   → the realistic option list, e.g. ["Alexa", "Google Home", "None needed"]
              number → [realistic_min, realistic_max], e.g. [30, 65]
              range  → same as number
              boolean/string → null

            clarifying_question:
              The exact question to ask the user — a complete sentence.

            extraction_signals:
              6-12 phrases or words users commonly say when expressing a preference for this
              attribute. Think colloquially: "my wife hates the noise", "works with Alexa",
              "it's a big living room". Include synonyms, slang, and typical user phrasing.

            assessment_note:
              One sentence: how to score a product against this attribute.

            entity_terms:
              5-10 product-type terms users might name by word — subcategories, form factors,
              technologies. NOT brands. E.g. for ceiling fans: "low profile", "hugger",
              "flush mount", "smart fan", "damp-rated".

            risks:
              3-5 practical purchase gotchas that catch buyers off guard.

            Rules:
            - Include Budget as an attribute (search_gate: true, value_type: number, unit: usd,
              score_direction: lower_is_better).
            - Keep decision_attributes to 6-12 items. Focus on what actually drives choice.
            - Do not include brands.
            - Do not duplicate concepts across attributes.
            - Prefer concrete, scorable attributes over vague ones.
            - extraction_signals must reflect actual user language, not attribute name synonyms.
            - Return only valid JSON. No markdown, commentary, or extra keys.
        """,
        "required_output_shape": {
            "category": "string",
            "summary": "one-sentence buyer need",
            "decision_attributes": [
                {
                    "key": "snake_case_string",
                    "name": "Display Name",
                    "search_gate": "boolean",
                    "value_type": "number | enum | boolean | range | string",
                    "unit": "string or null",
                    "score_direction": "higher_is_better | lower_is_better | match_preference | must_have",
                    "typical_values": "list or null",
                    "clarifying_question": "Complete sentence?",
                    "extraction_signals": ["phrase1", "phrase2"],
                    "assessment_note": "One sentence.",
                }
            ],
            "entity_terms": ["string"],
            "risks": ["string"],
            "confidence": "low | medium | high",
        },
        "examples": {
            "ceiling_fan_noise_level": {
                "key": "noise_level",
                "name": "Noise Level",
                "search_gate": False,
                "value_type": "number",
                "unit": "dB",
                "score_direction": "lower_is_better",
                "typical_values": [30, 65],
                "clarifying_question": "Is quiet operation important — for example, bedroom or office use?",
                "extraction_signals": [
                    "quiet", "silent", "noisy", "loud", "can hear it", "sound",
                    "disturbs sleep", "wife hates the noise", "peaceful",
                ],
                "assessment_note": "Below 40 dB is near-silent; above 55 dB is noticeable in a quiet room.",
            },
            "ceiling_fan_room_size": {
                "key": "room_size",
                "name": "Room Size",
                "search_gate": True,
                "value_type": "enum",
                "unit": None,
                "score_direction": "must_have",
                "typical_values": [
                    "small (under 144 sq ft)",
                    "medium (144-225 sq ft)",
                    "large (225-400 sq ft)",
                    "extra large (400+ sq ft)",
                ],
                "clarifying_question": "How large is the room you're shopping for?",
                "extraction_signals": [
                    "living room", "bedroom", "large room", "small room", "open plan",
                    "square feet", "sq ft", "big space", "tiny", "dining room",
                ],
                "assessment_note": "Fan blade span must match room size; undersized fans leave hot spots.",
            },
        },
    }

    return (
        "You build consumer product category schemas for a decision support app. "
        "Return only valid JSON matching the required output shape. "
        "Do not include markdown, commentary, or extra keys.\n\n"
        f"{json.dumps(payload, indent=2)}"
    )


def build_category_extraction_prompt(user_input: str, additional_context: str | None = None) -> str:
    payload = {
        "user_input": user_input,
        "additional_context": additional_context or "",
        "task": """
            Extract the canonical reusable product or solution category, plus one broader
            parent category and three narrower child categories.

            Definitions:

            proposed_category:
              The best reusable shopping category for the user's input. Specific enough to
              support useful comparison, broad enough to contain many competing products.

            broader_category:
              The immediate parent category one level above proposed_category.
              Example: "Ceiling Fans" -> "Fans"
              Do not make this too broad (e.g. "Home Improvement") unless the input is vague.

            more_specific_categories:
              Three child categories one level below proposed_category.
              Must be reusable shopping categories — not attributes, rooms, brands, or features.
              Good: "Low Profile Ceiling Fans", "Smart Ceiling Fans", "Outdoor Ceiling Fans"
              Bad:  "Quiet Ceiling Fans", "Ceiling Fans for Bedrooms", "Budget Ceiling Fans"

            Rules:
            - proposed_category: not too broad, not too specific.
            - Do not include room, budget, style, color, brand, or performance preference
              unless it defines an established shopping subcategory.
            - Return only valid JSON.
        """,
        "examples": [
            {
                "input": "I need a quiet low-profile ceiling fan for an old house bedroom.",
                "proposed_category": "Ceiling Fans",
                "broader_category": "Home Cooling",
                "more_specific_categories": [
                    "Low Profile Ceiling Fans",
                    "Smart Ceiling Fans",
                    "Outdoor Ceiling Fans",
                ],
            },
            {
                "input": "I want movie theater vibes in my front room.",
                "proposed_category": "Home Entertainment Systems",
                "broader_category": "Home Entertainment",
                "more_specific_categories": [
                    "Ultra Short Throw Projectors",
                    "Soundbars",
                    "Surround Sound Systems",
                ],
            },
            {
                "input": "I can't hear people during Teams calls.",
                "proposed_category": "Headsets",
                "broader_category": "Computer Accessories",
                "more_specific_categories": [
                    "Wireless Headsets",
                    "Noise-Canceling Headsets",
                    "Office Headsets",
                ],
            },
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
