import hashlib
import re

from app.category_intelligence.llm import (
    CategoryIntelligenceError,
    generate_category_schema,
)
from app.category_intelligence.models import CategoryIntelligenceRecord
from app.category_intelligence.normalizer import repair_category_schema
from app.category_intelligence.prompts import build_category_schema_prompt
from app.category_intelligence.store import (
    get_cached_category_intelligence,
    save_category_intelligence,
)


def normalize_category_key(category: str) -> str:
    key = category.strip().lower()
    key = re.sub(r"[^a-z0-9]+", "-", key)
    return key.strip("-")


def category_intelligence_prompt_hash(category: str, context: str | None = None) -> str:
    prompt = build_category_schema_prompt(category=category, context=context)
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def get_category_intelligence(category: str, context: str | None = None) -> tuple[CategoryIntelligenceRecord, bool]:
    normalized_category_key = normalize_category_key(category)
    prompt_hash = category_intelligence_prompt_hash(category=category, context=context)

    cached = get_cached_category_intelligence(normalized_category_key)
    if cached is not None and cached.model_metadata.get("prompt_hash") == prompt_hash:
        return cached, True

    schema, model_metadata = generate_category_schema(category=category, context=context)
    model_metadata["prompt_hash"] = prompt_hash
    schema = repair_category_schema(category=category, schema=schema)

    record = save_category_intelligence(
        category=category,
        normalized_category_key=normalized_category_key,
        category_schema=schema,
        model_metadata=model_metadata,
    )
    return record, False
