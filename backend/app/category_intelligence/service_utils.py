def normalize_name(value: str) -> str:
    cleaned = " ".join(value.strip().split())
    if not cleaned:
        return cleaned
    return cleaned[0].upper() + cleaned[1:]
