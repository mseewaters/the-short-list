import json
import logging
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path

from app.category_intelligence.models import (
    CategoryIntelligence,
    CategoryIntelligenceRecord,
    NormalizedCategoryIntelligence,
)

logger = logging.getLogger(__name__)

_MAX_CACHE_SIZE = 200
_CACHE_FILE = Path(__file__).resolve().parents[1] / "category_cache.json"

category_intelligence_cache: OrderedDict[str, CategoryIntelligenceRecord] = OrderedDict()


def _load_cache() -> None:
    if not _CACHE_FILE.exists():
        return
    try:
        data = json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
        for key, record_dict in data.items():
            category_intelligence_cache[key] = CategoryIntelligenceRecord.model_validate(record_dict)
    except Exception:
        logger.warning("Could not load category intelligence cache from disk; starting fresh.")


def _save_cache() -> None:
    try:
        serialized = {key: record.model_dump() for key, record in category_intelligence_cache.items()}
        _CACHE_FILE.write_text(json.dumps(serialized, indent=2), encoding="utf-8")
    except Exception:
        logger.warning("Could not persist category intelligence cache to disk.")


_load_cache()


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
    category_intelligence_cache.move_to_end(normalized_category_key)
    while len(category_intelligence_cache) > _MAX_CACHE_SIZE:
        category_intelligence_cache.popitem(last=False)

    _save_cache()
    return record


def clear_category_intelligence_cache() -> None:
    category_intelligence_cache.clear()
    if _CACHE_FILE.exists():
        _CACHE_FILE.unlink()
