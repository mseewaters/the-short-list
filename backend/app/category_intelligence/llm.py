import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Protocol

from app.category_intelligence.models import CategorySchema
from app.category_intelligence.prompts import (
    build_category_extraction_prompt,
    build_category_schema_prompt,
)


class CategoryIntelligenceError(Exception):
    pass


class LLMProvider(Protocol):
    def generate_json(self, prompt: str) -> tuple[dict, dict]:
        pass


def load_local_env() -> None:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        return

    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


class LocalCategoryIntelligenceProvider:
    def generate_json(self, prompt: str) -> tuple[dict, dict]:
        data = json.loads(prompt.split("\n\n", 1)[1])
        if "user_input" in data:
            return local_category_extraction(data), {
                "provider": "local",
                "model": "deterministic-category-extraction",
            }
        if data.get("schema_task") == "category_schema":
            return local_category_schema(data), {
                "provider": "local",
                "model": "deterministic-category-schema",
            }
        # Fallback for any unrecognized payload
        return {"error": "unrecognized local prompt"}, {
            "provider": "local",
            "model": "unknown",
        }


class OpenAICompatibleProvider:
    def __init__(self) -> None:
        self.api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY", "")
        self.model = os.getenv("LLM_MODEL") or os.getenv("DEFAULT_MODEL") or "gpt-4.1-mini"
        self.base_url = os.getenv("LLM_BASE_URL") or "https://api.openai.com/v1/chat/completions"

    def generate_json(self, prompt: str) -> tuple[dict, dict]:
        if not self.api_key:
            raise CategoryIntelligenceError("No LLM API key configured (LLM_API_KEY or OPENAI_API_KEY).")

        payload = json.dumps({
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }).encode("utf-8")

        req = urllib.request.Request(
            self.base_url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise CategoryIntelligenceError(f"LLM API error {exc.code}: {exc.read().decode()}") from exc
        except Exception as exc:
            raise CategoryIntelligenceError(f"LLM request failed: {exc}") from exc

        try:
            content = body["choices"][0]["message"]["content"]
            parsed = json.loads(content)
        except (KeyError, IndexError, json.JSONDecodeError) as exc:
            raise CategoryIntelligenceError("Failed to parse LLM JSON response") from exc

        metadata = {
            "provider": "openai-compatible",
            "model": self.model,
            "base_url": self.base_url,
        }
        return parsed, metadata


_provider_instance: LLMProvider | None = None


def get_llm_provider() -> LLMProvider:
    global _provider_instance
    if _provider_instance is not None:
        return _provider_instance

    load_local_env()
    provider = os.getenv("LLM_PROVIDER", "local").lower()

    if provider in {"local", "mock", "deterministic"}:
        _provider_instance = LocalCategoryIntelligenceProvider()
    elif provider in {"openai", "openai-compatible"}:
        _provider_instance = OpenAICompatibleProvider()
    else:
        raise CategoryIntelligenceError(f"Unsupported LLM_PROVIDER: {provider}")

    return _provider_instance


def get_llm_config_metadata() -> dict:
    load_local_env()
    provider = os.getenv("LLM_PROVIDER", "local").lower()

    if provider in {"local", "mock", "deterministic"}:
        return {
            "provider": "local",
            "model": "deterministic-category-schema",
        }

    if provider in {"openai", "openai-compatible"}:
        return {
            "provider": "openai-compatible",
            "model": os.getenv("LLM_MODEL") or os.getenv("DEFAULT_MODEL") or "gpt-4.1-mini",
        }

    return {"provider": provider, "model": "unknown"}


def generate_category_schema(category: str, context: str | None = None) -> tuple[CategorySchema, dict]:
    """Single LLM call: produce a CategorySchema directly."""
    prompt = build_category_schema_prompt(category=category, context=context)
    raw, metadata = get_llm_provider().generate_json(prompt)

    try:
        return CategorySchema(**raw), metadata
    except Exception as exc:
        raise CategoryIntelligenceError("LLM response did not match CategorySchema") from exc


def generate_category_extraction(user_input: str, additional_context: str | None = None) -> tuple[dict, dict]:
    prompt = build_category_extraction_prompt(
        user_input=user_input,
        additional_context=additional_context,
    )
    raw_extraction, metadata = get_llm_provider().generate_json(prompt)

    if not isinstance(raw_extraction.get("proposed_category"), str):
        raise CategoryIntelligenceError("LLM category extraction missing proposed_category")
    if not isinstance(raw_extraction.get("broader_category"), str):
        raise CategoryIntelligenceError("LLM category extraction missing broader_category")
    if not isinstance(raw_extraction.get("more_specific_categories"), list):
        raise CategoryIntelligenceError("LLM category extraction missing more_specific_categories")
    if raw_extraction.get("confidence") not in {"low", "medium", "high"}:
        raise CategoryIntelligenceError("LLM category extraction returned invalid confidence")
    if not isinstance(raw_extraction.get("explanation"), str):
        raise CategoryIntelligenceError("LLM category extraction missing explanation")

    return raw_extraction, metadata


# ---------------------------------------------------------------------------
# Local (deterministic) fallbacks
# ---------------------------------------------------------------------------

_PRESERVE_CASE = {"Wi-Fi", "HEPA", "USB", "HDMI", "TV", "LED", "AC", "UHD", "4K", "8K", "OLED", "QLED"}


def title_text(text: str) -> str:
    return " ".join(w if w in _PRESERVE_CASE else w.capitalize() for w in str(text).strip().split())


def local_category_schema(data: dict) -> dict:
    """Deterministic fallback CategorySchema for the local provider."""
    category = data.get("category", "product")
    context = data.get("context") or "general consumer purchase"

    return {
        "category": title_text(category),
        "summary": f"The buyer needs help choosing {category.lower()} for {context}.",
        "decision_attributes": [
            {
                "key": "budget",
                "name": "Budget",
                "search_gate": True,
                "value_type": "number",
                "unit": "usd",
                "score_direction": "lower_is_better",
                "typical_values": [100, 1000],
                "clarifying_question": "What's your budget for this purchase?",
                "extraction_signals": [
                    "budget", "spend", "cost", "price", "how much", "dollars", "afford",
                ],
                "assessment_note": "Exclude products above budget; prefer options toward the lower end.",
            },
            {
                "key": "fit_for_use_case",
                "name": "Fit for use case",
                "search_gate": True,
                "value_type": "string",
                "unit": None,
                "score_direction": "match_preference",
                "typical_values": None,
                "clarifying_question": f"What will you mainly use the {category.lower()} for, and in what setting?",
                "extraction_signals": [
                    "use", "need", "situation", "for", "purpose", "mainly", "primarily",
                ],
                "assessment_note": "Match product positioning to the user's stated use case and setting.",
            },
            {
                "key": "ease_of_use",
                "name": "Ease of use",
                "search_gate": False,
                "value_type": "enum",
                "unit": None,
                "score_direction": "match_preference",
                "typical_values": ["simple controls", "moderate setup", "feature-rich"],
                "clarifying_question": "How important is ease of setup and daily use to you?",
                "extraction_signals": [
                    "easy", "simple", "setup", "intuitive", "controls", "complicated", "tech-savvy",
                ],
                "assessment_note": "Prefer highly-rated ease-of-use products for users who value simplicity.",
            },
            {
                "key": "reliability",
                "name": "Reliability",
                "search_gate": False,
                "value_type": "enum",
                "unit": None,
                "score_direction": "higher_is_better",
                "typical_values": ["highly rated", "mixed reviews", "premium warranty"],
                "clarifying_question": "How important is long-term reliability and warranty support?",
                "extraction_signals": [
                    "reliable", "last", "durable", "break", "warranty", "quality", "reviews",
                ],
                "assessment_note": "Prioritize products with strong reliability track records.",
            },
        ],
        "entity_terms": [
            "entry-level option",
            "mid-range option",
            "premium option",
        ],
        "risks": [
            f"Compatibility issues that prevent the {category.lower()} from working in your situation",
            "Poor build quality at budget price points that leads to early failure",
        ],
        "confidence": "low",
    }


def local_category_extraction(data: dict) -> dict:
    text = f"{data.get('user_input', '')} {data.get('additional_context', '')}".lower()
    proposed_category = "Unknown product"
    confidence = "low"

    if "water softener" in text:
        proposed_category = "Water softener"
        confidence = "high"
    elif "ceiling fan" in text or " fan" in text:
        proposed_category = "Ceiling fan"
        confidence = "high"
    elif "robot vacuum" in text or "roomba" in text:
        proposed_category = "Robot vacuum"
        confidence = "high"
    elif "coffee maker" in text or "coffee" in text:
        proposed_category = "Coffee maker"
        confidence = "high"
    elif "router" in text or "wi-fi" in text or "wifi" in text:
        proposed_category = "Router"
        confidence = "high"
    elif "tv" in text or "television" in text:
        proposed_category = "TV"
        confidence = "high"

    return {
        "proposed_category": proposed_category,
        "broader_category": local_broader_category(proposed_category),
        "more_specific_categories": local_more_specific_categories(proposed_category),
        "confidence": confidence,
        "explanation": (
            f"The core reusable category is {proposed_category}. "
            "Specific needs and usage context belong in the Understand stage."
        ),
    }


def local_broader_category(category: str) -> str:
    broader = {
        "Ceiling fan": "Climate control",
        "Robot vacuum": "Floor care",
        "TV": "Home entertainment",
        "Coffee maker": "Kitchen appliances",
        "Router": "Home networking",
        "Water softener": "Water treatment",
    }
    return broader.get(category, "Home products")


def local_more_specific_categories(category: str) -> list[str]:
    specific = {
        "Ceiling fan": [
            "Low profile ceiling fans",
            "Smart ceiling fans",
            "Ceiling fans with lights",
        ],
        "Robot vacuum": [
            "Self-emptying robot vacuums",
            "Robot vacuums for pet hair",
            "Robot vacuum and mop combos",
        ],
        "TV": [
            "Bright room TVs",
            "OLED TVs",
            "Mini LED TVs",
        ],
        "Coffee maker": [
            "Single-serve coffee makers",
            "Travel mug coffee makers",
            "Compact coffee makers",
        ],
        "Router": [
            "Mesh Wi-Fi systems",
            "Wi-Fi 6 routers",
            "Whole-home router systems",
        ],
        "Water softener": [
            "Salt-based water softeners",
            "Salt-free water conditioners",
            "Whole-house water softeners",
        ],
    }
    return specific.get(category, [f"{category} systems", f"Compact {category}", f"Premium {category}"])
