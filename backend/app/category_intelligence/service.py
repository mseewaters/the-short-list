import hashlib
import re

from app.category_intelligence.llm import (
    CategoryIntelligenceError,
    generate_category_intelligence,
    generate_normalized_category_intelligence,
)
from app.category_intelligence.models import CategoryIntelligenceRecord
from app.category_intelligence.normalizer import (
    enforce_normalized_category_intelligence,
    normalize_category_intelligence,
)
from app.category_intelligence.prompts import build_category_intelligence_prompt
from app.category_intelligence.store import (
    get_cached_category_intelligence,
    save_category_intelligence,
)


def normalize_category_key(category: str) -> str:
    key = category.strip().lower()
    key = re.sub(r"[^a-z0-9]+", "-", key)
    return key.strip("-")


def category_intelligence_prompt_hash(category: str, context: str | None = None) -> str:
    prompt = build_category_intelligence_prompt(category=category, context=context)
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def get_category_intelligence(category: str, context: str | None = None) -> tuple[CategoryIntelligenceRecord, bool]:
    normalized_category_key = normalize_category_key(category)
    prompt_hash = category_intelligence_prompt_hash(category=category, context=context)
    cached = get_cached_category_intelligence(normalized_category_key)
    if cached is not None and cached.model_metadata.get("prompt_hash") == prompt_hash:
        return cached, True

    raw_intelligence, model_metadata = generate_category_intelligence(category=category, context=context)
    model_metadata["prompt_hash"] = prompt_hash
    try:
        llm_normalized_intelligence, normalization_metadata = generate_normalized_category_intelligence(
            category=category,
            raw_intelligence=raw_intelligence,
        )
        normalized_intelligence = enforce_normalized_category_intelligence(
            category=category,
            raw_intelligence=raw_intelligence,
            normalized_intelligence=llm_normalized_intelligence,
        )
        model_metadata["normalization"] = {
            **normalization_metadata,
            "source": "llm_with_code_enforcement",
        }
    except CategoryIntelligenceError:
        normalized_intelligence = normalize_category_intelligence(
            category=category,
            raw_intelligence=raw_intelligence,
        )
        model_metadata["normalization"] = {
            "provider": "local",
            "model": "deterministic-normalizer",
            "source": "fallback_after_llm_failure",
        }
    record = save_category_intelligence(
        category=category,
        normalized_category_key=normalized_category_key,
        raw_intelligence=raw_intelligence,
        normalized_intelligence=normalized_intelligence,
        model_metadata=model_metadata,
    )
    return record, False
