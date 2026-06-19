from app.category_intelligence.llm import generate_category_extraction
from app.category_intelligence.service import normalize_category_key
from app.category_intelligence.store import get_cached_category_intelligence


def extract_category(user_input: str, additional_context: str | None = None) -> dict:
    extraction, _metadata = generate_category_extraction(
        user_input=user_input,
        additional_context=additional_context,
    )
    proposed_category = extraction["proposed_category"]
    broader_category = extraction["broader_category"]
    more_specific_categories = extraction["more_specific_categories"][:3]
    confidence = extraction["confidence"]
    explanation = extraction["explanation"]

    normalized_category_key = normalize_category_key(proposed_category)
    matched_existing_category = get_cached_category_intelligence(normalized_category_key) is not None

    return {
        "proposed_category": proposed_category,
        "normalized_category_key": normalized_category_key,
        "broader_category": broader_category,
        "more_specific_categories": more_specific_categories,
        "confidence": confidence,
        "explanation": explanation,
        "matched_existing_category": matched_existing_category,
    }
