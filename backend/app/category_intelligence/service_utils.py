import re


def normalize_name(value: str) -> str:
    cleaned = " ".join(value.strip().split())
    if not cleaned:
        return cleaned
    return cleaned[0].upper() + cleaned[1:]


def to_snake_case(text: str) -> str:
    """Convert a display name to a stable snake_case key."""
    lowered = re.sub(r"[^\w\s]", "", text.strip().lower())
    return re.sub(r"\s+", "_", lowered).strip("_") or "attribute"
