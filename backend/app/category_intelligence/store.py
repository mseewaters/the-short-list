from datetime import datetime, timezone

from app.category_intelligence.models import (
    CategoryIntelligence,
    CategoryIntelligenceRecord,
    NormalizedCategoryIntelligence,
)


category_intelligence_cache: dict[str, CategoryIntelligenceRecord] = {}


def get_cached_category_intelligence(normalized_category_key: str) -> CategoryIntelligenceRecord | None:
    return category_intelligence_cache.get(normalized_category_key)


def save_category_intelligence(
    category: str,
    normalized_category_key: str,
    raw_intelligence: CategoryIntelligence,
    normalized_intelligence: NormalizedCategoryIntelligence,
    model_metadata: dict,
) -> CategoryIntelligenceRecord:
    now = datetime.now(timezone.utc).isoformat()
    existing = category_intelligence_cache.get(normalized_category_key)

    record = CategoryIntelligenceRecord(
        category=category,
        normalized_category_key=normalized_category_key,
        raw_intelligence=raw_intelligence,
        normalized_intelligence=normalized_intelligence,
        created_at=existing.created_at if existing else now,
        updated_at=now,
        model_metadata=model_metadata,
    )
    category_intelligence_cache[normalized_category_key] = record
    return record


def clear_category_intelligence_cache() -> None:
    category_intelligence_cache.clear()
